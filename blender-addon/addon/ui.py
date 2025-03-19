import bpy
from bpy.types import Panel, Operator, PropertyGroup
import sys
import logging
import os
import tempfile
from ..handlers import resource_handlers, tool_handlers
from .operators import _mcp_server_running, get_server_running_status, set_server_running_status
import time

# 设置日志
logger = logging.getLogger("BlenderMCP.UI")
# 配置日志格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# 添加控制台处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# 添加文件处理器
log_file = os.path.join(tempfile.gettempdir(), "blender_mcp_ui.log")
file_handler = logging.FileHandler(log_file, mode='a')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

logger.setLevel(logging.DEBUG)

# 全局变量
_mcp_show_tools_list = True
_mcp_show_resources_list = True

# MCP客户端连接信息
class MCPClientProperties(PropertyGroup):
    host: bpy.props.StringProperty(
        name="主机",
        description="MCP服务器主机地址",
        default="127.0.0.1"
    )
    port: bpy.props.IntProperty(
        name="端口",
        description="MCP服务器端口",
        default=27015,
        min=1024,
        max=65535
    )

# MCP侧边栏面板
class MCP_PT_Panel(Panel):
    bl_label = "Blender MCP"
    bl_idname = "MCP_PT_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MCP"
    bl_order = 0  # 确保它是MCP分类中的第一个面板
    
    _tools_list = []  # 缓存工具列表
    _resources_list = []  # 缓存资源列表
    
    @staticmethod
    def update():
        """强制更新面板和工具列表"""
        update_tools_list()
        update_resources_list()
        
        # 刷新所有区域以更新UI
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
        
        logger.debug("面板UI已更新")
    
    @classmethod
    def filter_tools(cls, filter_text):
        """根据过滤文本筛选工具"""
        if not filter_text:
            return cls._tools_list
        
        filter_text = filter_text.lower()
        return [tool for tool in cls._tools_list 
                if filter_text in tool.get("name", "").lower() 
                or filter_text in tool.get("description", "").lower()]
                
    @classmethod
    def filter_resources(cls, filter_text):
        """根据过滤文本筛选资源"""
        if not filter_text:
            return cls._resources_list
        
        filter_text = filter_text.lower()
        return [res for res in cls._resources_list 
                if filter_text in res.get("name", "").lower() 
                or filter_text in res.get("type", "").lower()]
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # 显示连接状态
        global _mcp_show_tools_list
        global _mcp_show_resources_list
        
        # 获取最新服务器状态
        server_running = get_server_running_status()
        
        # 获取工具处理器状态
        tools_handler_available = get_tools_handler_status()
        
        # 服务器状态区域
        box = layout.box()
        row = box.row()
        if server_running:
            row.label(text="服务器状态: 运行中", icon='CHECKMARK')
        else:
            row.label(text="服务器状态: 已停止", icon='X')
            
        # 工具处理器状态
        row = box.row()
        if tools_handler_available:
            row.label(text="工具处理器: 可用", icon='CHECKMARK')
        else:
            row.label(text="工具处理器: 不可用", icon='ERROR')
            
        # 服务器控制按钮
        row = box.row(align=True)
        if server_running:
            row.operator("mcp.stop_server", text="停止服务器", icon='PAUSE')
        else:
            row.operator("mcp.start_server", text="启动服务器", icon='PLAY')
            
        # 创建测试对象按钮
        row = box.row()
        op = row.operator("mcp.create_test_object", text="创建测试对象", icon='MESH_CUBE')
        op.enabled = server_running and tools_handler_available
        
        # 工具列表标题
        row = layout.row()
        tool_count = len(self._tools_list)
        row.label(text=f"可用工具 ({tool_count})")
        row.operator("mcp.toggle_tools_list", text="", icon='DOWNARROW_HLT' if _mcp_show_tools_list else 'RIGHTARROW')
        
        # 显示工具列表
        if _mcp_show_tools_list and server_running:
            # 过滤工具
            box = layout.box()
            row = box.row()
            row.prop(scene, "mcp_tools_filter", text="", icon='VIEWZOOM')
            row.operator("mcp.refresh_tools", text="", icon='FILE_REFRESH')
            
            # 显示过滤后的工具列表
            filtered_tools = self.filter_tools(scene.mcp_tools_filter)
            
            if not filtered_tools:
                box.label(text="无匹配工具", icon='INFO')
            else:
                # 在列布局中显示工具
                col = box.column(align=True)
                for tool in filtered_tools:
                    tool_name = tool.get("name", "未命名工具")
                    tool_desc = tool.get("description", "")
                    
                    row = col.row(align=True)
                    op = row.operator("mcp.execute_tool", text=tool_name)
                    op.tool_name = tool_name
                    
                    # 工具信息按钮
                    if tool_desc:
                        info_op = row.operator("mcp.tool_info", text="", icon='INFO')
                        info_op.tool_name = tool_name
                        info_op.tool_description = tool_desc
        elif not server_running:
            layout.label(text="请先启动MCP服务器", icon='ERROR')
        
        # 资源列表标题
        row = layout.row()
        resource_count = len(self._resources_list)
        row.label(text=f"可用资源 ({resource_count})")
        row.operator("mcp.toggle_resources_list", text="", icon='DOWNARROW_HLT' if _mcp_show_resources_list else 'RIGHTARROW')
        
        # 显示资源列表
        if _mcp_show_resources_list and server_running:
            # 过滤资源
            box = layout.box()
            row = box.row()
            row.prop(scene, "mcp_resources_filter", text="", icon='VIEWZOOM')
            row.operator("mcp.refresh_resources", text="", icon='FILE_REFRESH')
            
            # 显示过滤后的资源列表
            filtered_resources = self.filter_resources(scene.mcp_resources_filter)
            
            if not filtered_resources:
                box.label(text="无匹配资源", icon='INFO')
            else:
                # 按资源类型分组显示
                resource_by_type = {}
                for res in filtered_resources:
                    res_type = res.get("type", "未知类型")
                    if res_type not in resource_by_type:
                        resource_by_type[res_type] = []
                    resource_by_type[res_type].append(res)
                
                # 显示分组资源
                for res_type, resources in resource_by_type.items():
                    row = box.row()
                    row.label(text=f"{res_type.capitalize()} ({len(resources)})")
                    
                    col = box.column(align=True)
                    for res in resources:
                        res_name = res.get("name", "未命名资源")
                        res_id = res.get("id", "")
                        
                        row = col.row(align=True)
                        # 资源查看按钮
                        view_op = row.operator("mcp.view_resource", text=res_name, icon=get_resource_icon(res_type))
                        view_op.resource_type = res_type
                        view_op.resource_id = res_id
                    
                    # 添加小间距
                    box.separator(factor=0.5)

# 添加工具刷新操作符
class MCP_OT_RefreshTools(Operator):
    bl_idname = "mcp.refresh_tools"
    bl_label = "刷新工具列表"
    bl_description = "从服务器获取最新的工具列表"
    
    def execute(self, context):
        logger.debug("执行刷新工具列表")
        update_tools_list()
        self.report({'INFO'}, f"已刷新工具列表，找到 {len(MCP_PT_Panel._tools_list)} 个工具")
        return {'FINISHED'}

# 添加资源刷新操作符
class MCP_OT_RefreshResources(Operator):
    bl_idname = "mcp.refresh_resources"
    bl_label = "刷新资源列表"
    bl_description = "从Blender获取最新的资源列表"
    
    def execute(self, context):
        logger.debug("执行刷新资源列表")
        update_resources_list()
        self.report({'INFO'}, f"已刷新资源列表，找到 {len(MCP_PT_Panel._resources_list)} 个资源")
        return {'FINISHED'}

# 添加切换资源列表显示操作符
class MCP_OT_ToggleResourcesList(Operator):
    bl_idname = "mcp.toggle_resources_list"
    bl_label = "显示/隐藏资源列表"
    bl_description = "切换资源列表的显示状态"
    
    def execute(self, context):
        # 直接使用模块内的全局变量
        global _mcp_show_resources_list
        _mcp_show_resources_list = not _mcp_show_resources_list
        logger.debug(f"切换资源列表显示: {_mcp_show_resources_list}")
        return {'FINISHED'}
        
# 添加查看资源操作符
class MCP_OT_ViewResource(Operator):
    bl_idname = "mcp.view_resource"
    bl_label = "查看资源"
    bl_description = "查看资源详细信息"
    
    resource_type: bpy.props.StringProperty(
        name="资源类型",
        description="要查看的资源类型"
    )
    
    resource_id: bpy.props.StringProperty(
        name="资源ID",
        description="要查看的资源ID"
    )
    
    def execute(self, context):
        logger.debug(f"查看资源: {self.resource_type}/{self.resource_id}")
        
        try:
            # 获取资源详情
            resource_data = resource_handlers.handle_read_resource(self.resource_type, self.resource_id)
            
            if "error" in resource_data:
                self.report({'ERROR'}, f"获取资源失败: {resource_data['error']}")
                return {'CANCELLED'}
                
            # 在信息区显示摘要
            summary = f"资源: {self.resource_id} (类型: {self.resource_type})"
            
            # 根据资源类型添加额外信息
            if self.resource_type == "mesh":
                summary += f", 顶点数: {resource_data.get('vertices_count', 0)}, 面数: {resource_data.get('faces_count', 0)}"
            elif self.resource_type == "material":
                if "base_color" in resource_data:
                    color = resource_data["base_color"]
                    summary += f", 颜色: [{color[0]:.2f}, {color[1]:.2f}, {color[2]:.2f}]"
            elif self.resource_type == "light":
                summary += f", 类型: {resource_data.get('type', '')}, 能量: {resource_data.get('energy', 0)}"
            elif self.resource_type == "camera":
                summary += f", 焦距: {resource_data.get('lens', 0)}mm"
            
            self.report({'INFO'}, summary)
            
            # 将详细数据写入控制台
            import json
            print(f"\n===== 资源详情: {self.resource_type}/{self.resource_id} =====")
            print(json.dumps(resource_data, indent=2))
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"查看资源时出错: {str(e)}")
            logger.error(f"查看资源时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {'CANCELLED'}

def get_tools_handler_status():
    """获取工具处理器的状态"""
    try:
        # 不使用bpy.context，因为它可能在某些上下文中不可用
        if "mcp_tools_handler" in bpy.app.driver_namespace:
            return bpy.app.driver_namespace["mcp_tools_handler"] is not None
        
        # 检查场景属性
        for scene in bpy.data.scenes:
            if hasattr(scene, "mcp_tools_handler") and scene.mcp_tools_handler is not None:
                return True
                
        return False
    except Exception as e:
        print(f"检查工具处理器状态时出错: {e}")
        return False

# 所有UI类
classes = [
    MCP_PT_Panel,
    # MCP_PT_InfoPanel,  # 已禁用，因为与主面板重复
    MCP_OT_RefreshTools,
    MCP_OT_RefreshResources,
    MCP_OT_ToggleResourcesList,
    MCP_OT_ViewResource,
    MCPClientProperties,
]

def get_resource_icon(resource_type):
    """根据资源类型返回对应的图标"""
    type_icons = {
        "mesh": "MESH_DATA",
        "curve": "CURVE_DATA",
        "surface": "SURFACE_DATA",
        "meta": "META_DATA",
        "font": "FONT_DATA",
        "armature": "ARMATURE_DATA",
        "lattice": "LATTICE_DATA",
        "empty": "EMPTY_DATA",
        "gpencil": "GREASEPENCIL",
        "camera": "CAMERA_DATA",
        "light": "LIGHT_DATA",
        "material": "MATERIAL",
        "texture": "TEXTURE",
        "image": "IMAGE_DATA",
        "scene": "SCENE_DATA",
    }
    
    return type_icons.get(resource_type.lower(), "QUESTION")

def update_tools_list():
    """获取并更新工具列表"""
    if not get_server_running_status():
        MCP_PT_Panel._tools_list = []
        logger.debug("服务器未运行，不更新工具列表")
        return
    
    # 如果最近一次更新时间小于10秒，不进行更新
    if hasattr(update_tools_list, "_last_update") and time.time() - update_tools_list._last_update < 10.0:
        logger.debug("工具列表最近已更新，跳过当前更新")
        return
    
    try:
        logger.debug("开始更新工具列表")
        tools = tool_handlers.list_tools()
        
        if isinstance(tools, list):
            MCP_PT_Panel._tools_list = tools
            logger.info(f"更新了工具列表，找到 {len(tools)} 个工具")
        else:
            logger.error("获取工具列表失败: 返回值不是列表")
            MCP_PT_Panel._tools_list = []
            
        # 记录更新时间
        update_tools_list._last_update = time.time()
        
    except Exception as e:
        logger.error(f"更新工具列表时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        MCP_PT_Panel._tools_list = []

def update_resources_list():
    """获取并更新资源列表"""
    if not get_server_running_status():
        MCP_PT_Panel._resources_list = []
        logger.debug("服务器未运行，不更新资源列表")
        return
        
    # 如果最近一次更新时间小于10秒，不进行更新
    if hasattr(update_resources_list, "_last_update") and time.time() - update_resources_list._last_update < 10.0:
        logger.debug("资源列表最近已更新，跳过当前更新")
        return
    
    try:
        logger.debug("开始更新资源列表")
        resources = resource_handlers.handle_list_resources()
        
        if isinstance(resources, list):
            MCP_PT_Panel._resources_list = resources
            logger.info(f"更新了资源列表，找到 {len(resources)} 个资源")
        else:
            logger.error("获取资源列表失败: 返回值不是列表")
            MCP_PT_Panel._resources_list = []
            
        # 记录更新时间
        update_resources_list._last_update = time.time()
        
    except Exception as e:
        logger.error(f"更新资源列表时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        MCP_PT_Panel._resources_list = []

# 创建一个定时器来更新工具和资源列表
def update_timer():
    """非阻塞的UI更新定时器，降低更新频率"""
    try:
        # 获取服务器状态
        server_running = get_server_running_status()
        
        # 只在服务器运行时才更新
        if server_running:
            # 低频率更新工具和资源列表
            update_tools_list()
            update_resources_list()
        
        # 标记UI需要重绘，但不强制立即重绘
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':  # 只更新3D视图区域
                    area.tag_redraw()
                    
    except Exception as e:
        logger.error(f"更新UI时出错: {e}")
        
    return 5.0  # 降低更新频率到5秒

def register_ui():
    # 注册UI类
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # 注册工具过滤属性
    bpy.types.Scene.mcp_tools_filter = bpy.props.StringProperty(
        name="过滤工具",
        description="输入关键字过滤工具列表",
        default=""
    )
    
    # 注册资源过滤属性
    bpy.types.Scene.mcp_resources_filter = bpy.props.StringProperty(
        name="过滤资源",
        description="输入关键字过滤资源列表",
        default=""
    )
    
    # 注册工具参数属性
    bpy.types.Scene.mcp_temp_object_type = bpy.props.EnumProperty(
        name="对象类型",
        description="要创建的对象类型",
        items=[
            ('cube', "立方体", "创建立方体"),
            ('sphere', "球体", "创建球体"),
            ('plane', "平面", "创建平面"),
            ('cylinder', "圆柱体", "创建圆柱体"),
            ('cone', "圆锥体", "创建圆锥体"),
        ],
        default='cube'
    )
    
    bpy.types.Scene.mcp_temp_object_size = bpy.props.FloatProperty(
        name="对象大小",
        description="对象的大小",
        default=2.0,
        min=0.01,
        max=100.0
    )
    
    bpy.types.Scene.mcp_temp_object_name = bpy.props.StringProperty(
        name="对象名称",
        description="对象的名称",
        default="New_Object"
    )
    
    bpy.types.Scene.mcp_temp_color = bpy.props.FloatVectorProperty(
        name="颜色",
        description="对象的颜色",
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.8, 0.2, 0.2, 1.0)
    )
    
    # 灯光参数
    bpy.types.Scene.mcp_temp_light_type = bpy.props.EnumProperty(
        name="灯光类型",
        description="要创建的灯光类型",
        items=[
            ('POINT', "点光源", "创建点光源"),
            ('SUN', "太阳光", "创建太阳光"),
            ('SPOT', "聚光灯", "创建聚光灯"),
            ('AREA', "面光源", "创建面光源"),
        ],
        default='POINT'
    )
    
    bpy.types.Scene.mcp_temp_light_energy = bpy.props.FloatProperty(
        name="灯光能量",
        description="灯光的亮度",
        default=1000.0,
        min=0.0,
        max=100000.0
    )
    
    # 添加客户端连接信息属性
    bpy.types.Scene.mcp_client = bpy.props.PointerProperty(
        type=MCPClientProperties
    )
 
    # 注册更新定时器
    bpy.app.timers.register(update_timer, persistent=True)
    logger.debug("已注册更新定时器")

def unregister_ui():
    # 移除工具参数属性
    del bpy.types.Scene.mcp_client
    del bpy.types.Scene.mcp_temp_color
    del bpy.types.Scene.mcp_temp_object_name
    del bpy.types.Scene.mcp_temp_object_size
    del bpy.types.Scene.mcp_temp_object_type
    del bpy.types.Scene.mcp_tools_filter
    del bpy.types.Scene.mcp_resources_filter
    
    # 删除定时器
    if bpy.app.timers.is_registered(update_timer):
        bpy.app.timers.unregister(update_timer)
        logger.debug("已移除更新定时器")
    
    # 注销UI类
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

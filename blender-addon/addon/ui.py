import bpy
from bpy.types import Panel, Operator
import sys
from ..handlers import tool_handlers
from .operators import _mcp_show_tools_list, _mcp_server_running

# MCP侧边栏面板
class MCP_PT_Panel(Panel):
    bl_label = "Blender MCP"
    bl_idname = "MCP_PT_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MCP"
    
    _tools_list = []  # 缓存工具列表
    
    @staticmethod
    def update():
        """强制更新面板和工具列表"""
        update_tools_list()
        
        # 刷新所有区域以更新UI
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
    
    @classmethod
    def filter_tools(cls, filter_text):
        """根据过滤文本筛选工具"""
        if not filter_text:
            return cls._tools_list
        
        filter_text = filter_text.lower()
        return [tool for tool in cls._tools_list 
                if filter_text in tool.get("name", "").lower() 
                or filter_text in tool.get("description", "").lower()]
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # 显示连接状态
        global _mcp_server_running
        
        # 服务器状态区域
        box = layout.box()
        row = box.row()
        if _mcp_server_running:
            row.label(text="服务器状态: 运行中", icon='CHECKMARK')
        else:
            row.label(text="服务器状态: 已停止", icon='X')
            
        # 服务器控制按钮
        row = box.row(align=True)
        if _mcp_server_running:
            row.operator("mcp.stop_server", text="停止服务器", icon='PAUSE')
        else:
            row.operator("mcp.start_server", text="启动服务器", icon='PLAY')
            
        # 创建测试对象按钮
        row = box.row()
        row.operator("mcp.create_test_object", text="创建测试对象", icon='MESH_CUBE')
        
        # 工具列表标题
        row = layout.row()
        tool_count = len(self._tools_list)
        row.label(text=f"可用工具 ({tool_count})")
        row.operator("mcp.toggle_tools_list", text="", icon='DOWNARROW_HLT' if _mcp_show_tools_list else 'RIGHTARROW')
        
        # 显示工具列表
        global _mcp_show_tools_list
        if _mcp_show_tools_list:
            # 过滤工具
            box = layout.box()
            row = box.row()
            row.prop(scene, "mcp_tools_filter", text="", icon='VIEWZOOM')
            
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
        else:
            layout.label(text="请先启动MCP服务器", icon='ERROR')

# MCP信息面板（属性编辑器中）
class MCP_PT_InfoPanel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MCP"
    bl_label = "MCP信息"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # 显示连接信息
        box = layout.box()
        box.label(text="连接信息", icon='INFO')
        
        # 检查连接状态
        global _mcp_server_running
        if _mcp_server_running:
            # 服务器信息
            row = box.row()
            preferences = context.preferences.addons["blender-addon"].preferences
            box.label(text=f"主机: {preferences.server_host}")
            box.label(text=f"端口: {preferences.server_port}")
            
            # 工具列表
            tools_count = len(MCP_PT_Panel._tools_list)
            row = layout.row()
            row.label(text=f"可用工具 ({tools_count})")
            
            # 使用工具列表显示控制按钮
            global _mcp_show_tools_list
            row.operator("mcp.toggle_tools_list", text="", icon='DOWNARROW_HLT' if _mcp_show_tools_list else 'RIGHTARROW')
            
            # 工具列表部分
            if _mcp_show_tools_list:
                box = layout.box()
                # 搜索框
                row = box.row()
                row.prop(scene, "mcp_tools_filter", text="", icon='VIEWZOOM')
                
                # 显示过滤后的工具
                filtered_tools = MCP_PT_Panel.filter_tools(scene.mcp_tools_filter)
                
                if not filtered_tools:
                    box.label(text="无匹配工具", icon='INFO')
                else:
                    # 使用列显示工具
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
        else:
            box.label(text="服务器未运行", icon='ERROR')
            box.operator("mcp.start_server", text="启动服务器", icon='PLAY')

# 所有UI类
classes = [
    MCP_PT_Panel,
    MCP_PT_InfoPanel,
]

def update_tools_list():
    """从服务器获取并更新工具列表"""
    global _mcp_server_running
    
    if not _mcp_server_running:
        MCP_PT_Panel._tools_list = []
        return
    
    try:
        # 获取当前上下文的scene
        scene = bpy.context.scene
        
        # 检查是否有可用的工具处理器
        if hasattr(scene, "mcp_tools_handler") and scene.mcp_tools_handler:
            # 尝试获取工具列表
            tools = scene.mcp_tools_handler.list_tools()
            if isinstance(tools, list):
                MCP_PT_Panel._tools_list = tools
                print(f"更新了工具列表，找到 {len(tools)} 个工具")
            else:
                print("获取工具列表失败: 返回值不是列表")
                MCP_PT_Panel._tools_list = []
        else:
            print("工具处理器不可用")
            MCP_PT_Panel._tools_list = []
    except Exception as e:
        print(f"更新工具列表时出错: {str(e)}")
        MCP_PT_Panel._tools_list = []

# 创建一个定时器来定期更新工具列表
def tools_update_timer():
    update_tools_list()
    return 5.0  # 每5秒更新一次

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
        default=(0.8, 0.8, 0.8, 1.0)
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
 
    # 启动工具列表更新定时器
    bpy.app.timers.register(tools_update_timer, first_interval=1.0)

def unregister_ui():
    # 移除工具参数属性
    del bpy.types.Scene.mcp_temp_object_type
    del bpy.types.Scene.mcp_temp_object_size
    del bpy.types.Scene.mcp_temp_object_name
    del bpy.types.Scene.mcp_temp_color
    
    # 移除灯光参数
    del bpy.types.Scene.mcp_temp_light_type
    del bpy.types.Scene.mcp_temp_light_energy
    
    # 移除工具过滤属性
    del bpy.types.Scene.mcp_tools_filter
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

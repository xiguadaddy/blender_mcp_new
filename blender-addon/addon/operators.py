import bpy
from bpy.types import Operator
import socket
import json
import sys
import os
import threading
import time
import tempfile
from ..logger import get_logger

# 设置日志
logger = get_logger("BlenderMCP.Operators")


# 全局变量
_mcp_server_running = False

# 获取服务器运行状态
def get_server_running_status():
    """从bpy.types获取服务器运行状态，确保全局状态一致"""
    return hasattr(bpy.types, "_mcp_server_running") and bpy.types._mcp_server_running

# 设置服务器运行状态
def set_server_running_status(status):
    """设置服务器运行状态，并确保全局状态一致"""
    global _mcp_server_running
    _mcp_server_running = status
    bpy.types._mcp_server_running = status
    logger.debug(f"更新服务器状态: {status}")

# 启动MCP服务器操作符
class StartServerOperator(bpy.types.Operator):
    bl_idname = "mcp.start_server"
    bl_label = "启动MCP服务器"
    bl_description = "启动MCP IPC服务器"
    
    def execute(self, context):
        global _mcp_server_running
        
        from ..ipc.server import start_ipc_server
        
        # 从首选项获取设置
        addon_id = __package__.split('.')[0]
        try:
            preferences = context.preferences.addons[addon_id].preferences
            socket_path = preferences.socket_path
            debug_mode = preferences.debug_mode
            
            # 重新配置日志级别
            try:
                from ..logger import configure_logging
                import logging
                log_level = logging.DEBUG if debug_mode else logging.INFO
                configure_logging(log_level=log_level)
                logger.info(f"根据首选项设置日志级别: {'DEBUG' if debug_mode else 'INFO'}")
            except Exception as e:
                logger.error(f"设置日志级别时出错: {str(e)}")
            
            success = start_ipc_server(socket_path, debug_mode)
            
            if success:
                self.report({'INFO'}, f"MCP服务器已启动，通信路径: {socket_path}")
                set_server_running_status(True)
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "启动MCP服务器失败")
                return {'CANCELLED'}
        except Exception as e:
            logger.error(f"启动服务器时出错: {str(e)}")
            self.report({'ERROR'}, f"启动服务器时出错: {str(e)}")
            return {'CANCELLED'}

# 停止MCP服务器操作符
class MCP_OT_StopServer(Operator):
    bl_idname = "mcp.stop_server"
    bl_label = "停止MCP服务器"
    bl_description = "停止运行中的MCP服务器"
    
    def execute(self, context):
        try:
            from ..ipc.server import stop_ipc_server
            
            success = stop_ipc_server()
            if success:
                self.report({'INFO'}, "MCP服务器已停止")
                set_server_running_status(False)
                return {'FINISHED'}
            else:
                self.report({'WARNING'}, "MCP服务器已经停止或不存在")
                set_server_running_status(False)
                return {'CANCELLED'}
        except Exception as e:
            logger.error(f"停止服务器时出错: {str(e)}")
            self.report({'ERROR'}, f"停止服务器时出错: {str(e)}")
            return {'CANCELLED'}

# 创建测试对象
class MCP_OT_CreateTestObject(bpy.types.Operator):
    bl_idname = "mcp.create_test_object"
    bl_label = "创建测试对象"
    bl_description = "创建一个测试对象来验证MCP连接"
    
    # 添加启用状态属性
    enabled: bpy.props.BoolProperty(default=True)
    
    # 添加定时器标识
    _timer = None
    _is_running = False
    _result = None
    _stage = "start"  # 执行阶段：start -> create_object -> set_material -> finish
    
    @classmethod
    def poll(cls, context):
        from ..addon.ui import get_server_running_status, get_tools_handler_status
        return get_server_running_status() and get_tools_handler_status()
    
    def modal(self, context, event):
        """模态执行函数，处理异步操作"""
        if event.type == 'TIMER':
            if self._stage == "start" and not self._is_running:
                # 第一阶段：创建立方体
                self.report({'INFO'}, "创建测试对象 - 第一阶段: 创建立方体")
                self._stage = "create_object"
                self._is_running = True
                
                # 执行创建对象任务
                self.execute_async_task("create_object")
                
            elif self._stage == "create_object" and self._result is not None:
                # 处理创建对象结果
                if "error" in self._result:
                    self.report({'ERROR'}, f"创建对象失败: {self._result['error']}")
                    self.cleanup()
                    return {'CANCELLED'}
                
                # 成功创建对象，提取对象名称
                if "object_name" in self._result:
                    obj_name = self._result["object_name"]
                    self._stage = "set_material"
                    self._is_running = False
                    self._result = None
                    
                    self.report({'INFO'}, f"对象创建成功: {obj_name}")
                    self.report({'INFO'}, "创建测试对象 - 第二阶段: 设置材质")
                else:
                    # 旧格式兼容或错误处理
                    text_content = ""
                    if "content" in self._result and len(self._result["content"]) > 0:
                        content = self._result["content"][0]
                        if "text" in content:
                            text_content = content["text"]
                    
                    self.report({'INFO'}, f"对象创建完成: {text_content}")
                    self.cleanup()
                    return {'FINISHED'}
                
            elif self._stage == "set_material" and not self._is_running:
                # 执行设置材质任务
                obj = context.active_object
                if obj:
                    self._is_running = True
                    self.execute_async_task("set_material", {"object_name": obj.name})
                else:
                    self.report({'WARNING'}, "没有活动对象，跳过材质设置")
                    self.cleanup()
                    return {'FINISHED'}
                
            elif self._stage == "set_material" and self._result is not None:
                # 处理设置材质结果
                if "error" in self._result:
                    self.report({'WARNING'}, f"设置材质警告: {self._result['error']}")
                else:
                    # 成功设置材质
                    text_content = ""
                    if "text" in self._result:
                        text_content = self._result["text"]
                    elif "content" in self._result and len(self._result["content"]) > 0:
                        content = self._result["content"][0]
                        if "text" in content:
                            text_content = content["text"]
                    
                    self.report({'INFO'}, f"材质设置完成: {text_content}")
                
                # 完成所有操作
                self._stage = "finish"
                self.cleanup()
                return {'FINISHED'}
        
        # 用户取消操作
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cleanup()
            self.report({'INFO'}, "操作已取消")
            return {'CANCELLED'}
            
        return {'RUNNING_MODAL'}
        
    def execute_async_task(self, task_type, additional_params=None):
        """在后台线程中异步执行任务"""
        
        def run_task():
            try:
                self._is_running = True
                tools_handler = bpy.context.scene.mcp_tools_handler
                
                if task_type == "create_object":
                    # 创建立方体
                    params = {
                        "object_type": "cube", 
                        "name": "MCP_Test_Cube",
                        "size": 2.0,
                        "location": [0, 0, 0]
                    }
                    result = tools_handler.execute_tool("create_object", params)
                elif task_type == "set_material" and additional_params:
                    # 设置红色材质
                    params = {
                        "object_name": additional_params["object_name"],
                        "color": [1.0, 0.0, 0.0, 1.0]
                    }
                    result = tools_handler.execute_tool("set_material", params)
                else:
                    result = {"error": "未知任务类型"}
                    
                # 保存结果
                self._result = result
                self._is_running = False
                    
            except Exception as e:
                import traceback
                traceback.print_exc()
                self._result = {"error": str(e)}
                self._is_running = False
                
        # 创建并启动线程
        thread = threading.Thread(target=run_task)
        thread.daemon = True
        thread.start()
    
    def execute(self, context):
        """启动模态操作"""
        try:
            print("开始创建测试对象（异步模式）...")
            
            # 检查服务器是否运行
            if not hasattr(bpy.types, "_mcp_server_running") or not bpy.types._mcp_server_running:
                self.report({'ERROR'}, "MCP服务器未运行，请先启动服务器")
                return {'CANCELLED'}
            
            # 检查工具处理器
            if not hasattr(context.scene, "mcp_tools_handler") or not context.scene.mcp_tools_handler:
                self.report({'ERROR'}, "MCP工具处理器不可用，请确保服务器已连接")
                return {'CANCELLED'}
            
            # 启动模态定时器
            self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            error_msg = f"启动创建测试对象时出错: {str(e)}"
            print(f"异常: {error_msg}")
            self.report({'ERROR'}, error_msg)
            return {'CANCELLED'}
            
    def cleanup(self):
        """清理定时器和状态"""
        if self._timer:
            bpy.context.window_manager.event_timer_remove(self._timer)
            self._timer = None
        self._is_running = False
        self._result = None

# 查看MCP资源操作符
class MCP_OT_ViewResources(Operator):
    bl_idname = "mcp.view_resources"
    bl_label = "查看MCP资源"
    bl_description = "在信息区域显示可用的MCP资源"
    
    def execute(self, context):
        try:
            from ..handlers import resource_handlers
            
            resources = resource_handlers.handle_list_resources()
            count = len(resources)
            
            # 在信息区显示资源计数
            self.report({'INFO'}, f"找到 {count} 个MCP资源")
            
            # 在控制台打印详细信息
            print(f"===== MCP资源列表({count}个) =====")
            for res in resources:
                print(f"资源: {res['name']} (类型: {res['type']}, ID: {res['id']})")
            
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"查看资源时出错: {str(e)}")
            return {'CANCELLED'}

# 检查MCP服务器操作符
class MCP_OT_CheckServer(Operator):
    bl_idname = "mcp.check_server"
    bl_label = "检查MCP服务器"
    bl_description = "检查MCP服务器是否真正运行"
    
    def execute(self, context):
        port = 27015  # 默认端口
        
        # 从首选项或全局变量获取实际端口
        if hasattr(bpy.types, "_mcp_server_port"):
            port = bpy.types._mcp_server_port
        
        # 尝试连接本地服务器
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(1.0)  # 设置超时
        
        try:
            client_socket.connect(("127.0.0.1", port))
            # 发送测试信息
            test_data = json.dumps({"action": "test"}).encode()
            client_socket.sendall(f"{len(test_data)}:".encode() + test_data)
            
            # 如果连接成功，服务器真的在运行
            self.report({'INFO'}, f"服务器正在运行，端口: {port}")
            return {'FINISHED'}
        except Exception as e:
            # 连接失败，服务器可能没有运行
            if hasattr(bpy.types, "_mcp_server_running"):
                bpy.types._mcp_server_running = False
            self.report({'ERROR'}, f"服务器未运行: {str(e)}")
            return {'CANCELLED'}
        finally:
            client_socket.close()

# 切换工具列表显示操作符
class MCP_OT_ToggleToolsList(Operator):
    bl_idname = "mcp.toggle_tools_list"
    bl_label = "显示/隐藏工具列表"
    bl_description = "切换工具列表的显示状态"
    
    def execute(self, context):
        # 直接从ui模块获取变量
        from . import ui
        ui._mcp_show_tools_list = not ui._mcp_show_tools_list
        logger.debug(f"切换工具列表显示: {ui._mcp_show_tools_list}")
            
        # 强制更新UI
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
                
        return {'FINISHED'}

# 执行工具
class MCP_OT_ExecuteTool(bpy.types.Operator):
    bl_idname = "mcp.execute_tool"
    bl_label = "执行工具"
    bl_description = "执行选中的MCP工具"
    bl_options = {'REGISTER', 'UNDO'}
    
    tool_name: bpy.props.StringProperty(
        name="工具名称",
        description="要执行的工具名称"
    )
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # 根据工具名称显示不同参数
        if self.tool_name == "create_object":
            layout.prop(scene, "mcp_temp_object_type")
            layout.prop(scene, "mcp_temp_object_size")
            layout.prop(scene, "mcp_temp_object_name")
        
        elif self.tool_name == "set_material":
            layout.prop(scene, "mcp_temp_color")
            
        elif self.tool_name == "add_light":
            layout.prop(scene, "mcp_temp_light_type")
            layout.prop(scene, "mcp_temp_light_energy")
            layout.prop(scene, "mcp_temp_color")
    
    def execute(self, context):
        tools_handler = context.scene.mcp_tools_handler
        
        if not tools_handler:
            self.report({'ERROR'}, "MCP工具处理器不可用，请确保服务器已连接")
            return {'CANCELLED'}
        
        print(f"执行工具: {self.tool_name}")
        
        # 获取参数
        parameters = {}
        scene = context.scene
        
        # 根据工具设置对应参数
        if self.tool_name == "create_object":
            parameters = {
                "object_type": scene.mcp_temp_object_type,
                "size": scene.mcp_temp_object_size,
                "name": scene.mcp_temp_object_name
            }
            print(f"创建对象参数: {parameters}")
            
        elif self.tool_name == "set_material":
            parameters = {
                "object_name": context.active_object.name if context.active_object else "",
                "color": [scene.mcp_temp_color[0], scene.mcp_temp_color[1], scene.mcp_temp_color[2], scene.mcp_temp_color[3]]
            }
            print(f"设置材质参数: {parameters}")
            
        elif self.tool_name == "add_light":
            parameters = {
                "light_type": scene.mcp_temp_light_type,
                "energy": scene.mcp_temp_light_energy,
                "color": [scene.mcp_temp_color[0], scene.mcp_temp_color[1], scene.mcp_temp_color[2]]
            }
            print(f"添加灯光参数: {parameters}")
        
        # 执行工具调用
        try:
            print(f"发送工具请求: {self.tool_name}，参数: {parameters}")
            result = tools_handler.execute_tool(self.tool_name, parameters)
            print(f"工具执行结果: {result}")
            
            if "error" in result:
                self.report({'ERROR'}, f"工具执行失败: {result['error']}")
                return {'CANCELLED'}
            
            self.report({'INFO'}, f"工具 {self.tool_name} 执行成功")
            return {'FINISHED'}
        except Exception as e:
            print(f"工具执行异常: {str(e)}")
            self.report({'ERROR'}, f"执行工具时出错: {str(e)}")
            return {'CANCELLED'}

# 工具信息操作符
class MCP_OT_ToolInfo(bpy.types.Operator):
    bl_idname = "mcp.tool_info"
    bl_label = "工具信息"
    bl_description = "显示工具的详细信息"
    
    tool_name: bpy.props.StringProperty(
        name="工具名称",
        description="要显示信息的工具名称"
    )
    
    tool_description: bpy.props.StringProperty(
        name="工具描述",
        description="工具的详细描述"
    )
    
    def execute(self, context):
        self.report({'INFO'}, f"{self.tool_name}: {self.tool_description}")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=300)
    
    def draw(self, context):
        layout = self.layout
        layout.label(text=self.tool_name, icon='INFO')
        
        # 分行显示描述
        description = self.tool_description
        if description:
            box = layout.box()
            for line in description.split(". "):
                if line:
                    box.label(text=line + ".")

def register_operators():
    # 注册所有操作符类
    classes = [
        StartServerOperator,
        MCP_OT_StopServer,
        MCP_OT_CreateTestObject,
        MCP_OT_ToggleToolsList,
        MCP_OT_ExecuteTool,
        MCP_OT_ToolInfo,
        MCP_OT_ViewResources,
        MCP_OT_CheckServer,
    ]
    
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister_operators():
    # 注销所有操作符类
    classes = [
        StartServerOperator,
        MCP_OT_StopServer,
        MCP_OT_CreateTestObject,
        MCP_OT_ToggleToolsList,
        MCP_OT_ExecuteTool,
        MCP_OT_ToolInfo,
        MCP_OT_ViewResources,
        MCP_OT_CheckServer,
    ]
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

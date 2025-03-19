import bpy
from bpy.types import Operator
import socket
import json
import sys
import os
import threading
import time
import logging
import tempfile

# 设置日志
logger = logging.getLogger("BlenderMCP.Operators")
# 配置日志格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# 添加控制台处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

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
class MCP_OT_StartServer(Operator):
    bl_idname = "mcp.start_server"
    bl_label = "启动MCP服务器"
    bl_description = "启动MCP协议服务器"
    
    def execute(self, context):
        try:
            # 获取插件首选项
            import bpy.types
            
            # 获取插件ID
            addon_id = __package__.split('.')[0]  # 提取插件的主包名
            
            socket_path = None
            debug_mode = False
            
            # 检查插件是否注册并获取首选项
            if addon_id in context.preferences.addons:
                preferences = context.preferences.addons[addon_id].preferences
                if preferences is not None:
                    socket_path = preferences.socket_path
                    debug_mode = preferences.debug_mode
                    logger.debug(f"从首选项获取配置: {socket_path}, 调试模式: {debug_mode}")
                else:
                    logger.warning(f"插件 {addon_id} 的首选项对象为None")
            else:
                logger.warning(f"插件 {addon_id} 未在context.preferences.addons中找到")
                
            # 如果无法获取socket_path，使用默认值
            if not socket_path:
                if sys.platform == "win32":
                    socket_path = "port:27015"
                else:
                    socket_path = os.path.join(tempfile.gettempdir(), "blender-mcp.sock")
                logger.info(f"使用默认socket路径: {socket_path}")
            
            # 启动IPC服务器但避免直接导入UI模块
            from ..core import server_manager
            
            # 直接启动服务器，不使用状态检测
            self.report({'INFO'}, "正在启动MCP服务器...")
            success = server_manager.start_server(socket_path, debug_mode)
            
            if not success:
                self.report({'ERROR'}, "启动服务器失败，详情请查看控制台日志")
                return {'CANCELLED'}
            
            # 设置状态但不触发UI更新
            set_server_running_status(True)
            
            # 简单地强制重绘所有区域，避免直接导入UI模块
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    area.tag_redraw()
            
            # 设置MCPClient
            if "port:" in socket_path:
                # 从socket_path中提取端口
                port = int(socket_path.split(":", 1)[1])
                host = "127.0.0.1"
            else:
                # 使用默认配置
                port = 27015
                host = "127.0.0.1"
                
            # 设置客户端连接信息
            context.scene.mcp_client.host = host
            context.scene.mcp_client.port = port
            
            # 使用简单的状态检测，避免定时器嵌套
            if not bpy.app.timers.is_registered(self.simple_status_check):
                bpy.app.timers.register(self.simple_status_check, first_interval=1.0)
            
            self.report({'INFO'}, "MCP服务器已启动")
            return {'FINISHED'}
            
        except Exception as e:
            set_server_running_status(False)
            self.report({'ERROR'}, f"启动服务器时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}
            
    def simple_status_check(self):
        """简化的状态检查函数，避免UI模块循环导入"""
        try:
            # 检查服务器状态，但不更新UI
            if not hasattr(bpy.context.scene, "mcp_client"):
                return None  # 停止定时器
                
            client_info = bpy.context.scene.mcp_client
            if hasattr(client_info, "host") and hasattr(client_info, "port"):
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(0.5)
                    s.connect((client_info.host, client_info.port))
                    s.close()
                    # 服务器正在运行，更新状态但不更新UI
                    set_server_running_status(True)
                    # 强制重绘所有区域
                    for window in bpy.context.window_manager.windows:
                        for area in window.screen.areas:
                            area.tag_redraw()
                    return 5.0  # 继续检查，但降低频率
                except:
                    # 连接失败，服务器可能已停止
                    set_server_running_status(False)
                    # 强制重绘所有区域
                    for window in bpy.context.window_manager.windows:
                        for area in window.screen.areas:
                            area.tag_redraw()
                    return None  # 停止定时器
        except:
            # 出现任何异常都停止定时器
            return None
            
        return 5.0  # 继续检查，但降低频率

# 停止MCP服务器操作符
class MCP_OT_StopServer(Operator):
    bl_idname = "mcp.stop_server"
    bl_label = "停止MCP服务器"
    bl_description = "停止运行中的MCP协议服务器"
    
    def execute(self, context):
        try:
            # 通知用户
            self.report({'INFO'}, "正在停止MCP服务器...")
            
            # 使用server_manager停止服务器
            from ..core import server_manager
            success = server_manager.stop_server()
            
            if not success:
                self.report({'ERROR'}, "停止服务器失败")
                return {'CANCELLED'}
            
            # 清理状态
            set_server_running_status(False)
            
            # 简单地标记需要重绘
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    area.tag_redraw()
            
            self.report({'INFO'}, "MCP服务器已停止")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"停止服务器时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            set_server_running_status(False)  # 确保状态一致
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
                # 开始异步执行创建对象
                self._is_running = True
                self.execute_async_task("create_object")
                return {'RUNNING_MODAL'}
                
            elif self._stage == "create_object" and self._result is not None:
                # 创建对象完成，检查结果
                result = self._result
                self._result = None
                
                if "error" in result:
                    error_msg = f"创建测试对象失败: {result['error']}"
                    print(f"错误: {error_msg}")
                    self.report({'ERROR'}, error_msg)
                    self.cleanup()
                    return {'CANCELLED'}
                
                # 保存对象名称用于设置材质
                self._object_name = result["object_name"]
                print(f"创建对象成功: {self._object_name}")
                
                # 进入下一阶段：设置材质
                self._stage = "set_material"
                self._is_running = False
                return {'RUNNING_MODAL'}
                
            elif self._stage == "set_material" and not self._is_running:
                # 开始异步执行设置材质
                self._is_running = True
                self.execute_async_task("set_material")
                return {'RUNNING_MODAL'}
                
            elif self._stage == "set_material" and self._result is not None:
                # 设置材质完成，结束操作
                material_result = self._result
                self._result = None
                
                if "error" in material_result:
                    print(f"设置材质警告: {material_result['error']}")
                    # 材质设置失败不影响整体结果，仍然返回成功
                
                success_msg = f"创建了测试对象: {self._object_name}"
                print(f"成功: {success_msg}")
                self.report({'INFO'}, success_msg)
                
                # 结束定时器和模态操作
                self.cleanup()
                return {'FINISHED'}
                
        # 用户取消操作
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cleanup()
            self.report({'INFO'}, "操作已取消")
            return {'CANCELLED'}
            
        return {'RUNNING_MODAL'}
        
    def execute_async_task(self, task_type):
        """在后台线程中异步执行任务"""
        import threading
        
        def run_task():
            try:
                if task_type == "create_object":
                    print("异步发送创建对象请求...")
                    result = bpy.context.scene.mcp_tools_handler.execute_tool(
                        "create_object", 
                        {
                            "object_type": "cube", 
                            "size": 2.0, 
                            "name": "MCP_Test_Cube",
                            "location": [0, 0, 0]
                        }
                    )
                    self._result = result
                    self._stage = "create_object"  # 更新阶段
                    
                elif task_type == "set_material":
                    print("异步发送设置材质请求...")
                    result = bpy.context.scene.mcp_tools_handler.execute_tool(
                        "set_material", 
                        {
                            "object_name": self._object_name,
                            "color": [1.0, 0.2, 0.2, 1.0],
                            "metallic": 0.2,
                            "roughness": 0.5
                        }
                    )
                    self._result = result
                    self._stage = "set_material"  # 更新阶段
                    
            except Exception as e:
                import traceback
                traceback.print_exc()
                self._result = {"error": str(e)}
                
        # 创建并启动线程
        thread = threading.Thread(target=run_task)
        thread.daemon = True
        thread.start()
    
    def execute(self, context):
        """启动模态操作"""
        try:
            print("开始创建测试对象（异步模式）...")
            
            # 检查服务器是否运行
            if not get_server_running_status():
                self.report({'ERROR'}, "MCP服务器未运行，请先启动服务器")
                return {'CANCELLED'}
            
            # 检查工具处理器
            if not hasattr(context.scene, "mcp_tools_handler") or not context.scene.mcp_tools_handler:
                error_msg = "工具处理器不可用，请手动停止并重新启动服务器"
                print(f"错误: {error_msg}")
                self.report({'ERROR'}, error_msg)
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
        MCP_OT_StartServer,
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
        MCP_OT_StartServer,
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

import bpy
from bpy.types import Operator
import socket
import json
import sys
import os
import threading
import time

# 全局变量
_mcp_show_tools_list = True
_mcp_server_running = False

# 启动MCP服务器操作符
class MCP_OT_StartServer(Operator):
    bl_idname = "mcp.start_server"
    bl_label = "启动MCP服务器"
    bl_description = "启动MCP协议服务器"
    
    def execute(self, context):
        global _mcp_server_running
        
        try:
            preferences = context.preferences.addons["blender-addon"].preferences
            server_path = preferences.server_path
            
            if not server_path or not os.path.exists(server_path):
                self.report({'ERROR'}, "服务器路径不存在，请在插件首选项中设置")
                return {'CANCELLED'}
            
            # 使用启动脚本启动服务器
            start_script = os.path.join(server_path, "start_server.py")
            
            if not os.path.exists(start_script):
                self.report({'ERROR'}, f"启动脚本不存在: {start_script}")
                return {'CANCELLED'}
            
            cmd = [sys.executable, start_script]
            
            # 使用子进程启动服务器
            import subprocess
            subprocess.Popen(cmd, 
                            cwd=server_path,
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE,
                            shell=False)
            
            self.report({'INFO'}, "MCP服务器启动中...")
            _mcp_server_running = True
            
            # 延迟导入避免循环引用
            from .ui import MCP_PT_Panel
            MCP_PT_Panel.update()
            
            # 等待服务器启动
            time.sleep(2)
            
            # 尝试连接
            host = preferences.server_host
            port = preferences.server_port
            
            # 设置MCPClient
            context.scene.mcp_client = {"host": host, "port": port}
            
            # 创建并添加handler
            bpy.app.timers.register(self.check_server_status, first_interval=1.0)
            
            return {'FINISHED'}
            
        except Exception as e:
            _mcp_server_running = False
            self.report({'ERROR'}, f"启动服务器时出错: {str(e)}")
            return {'CANCELLED'}
            
    def check_server_status(self):
        # 检查服务器状态的定时器函数
        global _mcp_server_running
        prev_status = _mcp_server_running
        
        try:
            # 尝试连接服务器
            context = bpy.context
            if hasattr(context.scene, "mcp_client"):
                client_info = context.scene.mcp_client
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)
                try:
                    s.connect((client_info["host"], client_info["port"]))
                    s.close()
                    _mcp_server_running = True
                except:
                    _mcp_server_running = False
                    
                # 如果状态变化，刷新UI
                if prev_status != _mcp_server_running:
                    from .ui import MCP_PT_Panel
                    MCP_PT_Panel.update()
                    
                if not _mcp_server_running:
                    return 5.0  # 继续检查
                return None  # 连接成功后停止定时器
        except:
            pass
        
        return 5.0  # 5秒后再次检查

# 停止MCP服务器操作符
class MCP_OT_StopServer(Operator):
    bl_idname = "mcp.stop_server"
    bl_label = "停止MCP服务器"
    bl_description = "停止运行中的MCP协议服务器"
    
    def execute(self, context):
        global _mcp_server_running
        
        try:
            # 通知用户
            self.report({'INFO'}, "已发送停止命令到MCP服务器")
            
            # 发送停止请求
            if hasattr(context.scene, "mcp_client"):
                client_info = context.scene.mcp_client
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(1)
                    s.connect((client_info["host"], client_info["port"]))
                    s.sendall(b'{"command":"stop"}\n')
                    s.close()
                except:
                    pass
            
            _mcp_server_running = False
            
            # 更新UI
            from .ui import MCP_PT_Panel
            MCP_PT_Panel.update()
            
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"停止服务器时出错: {str(e)}")
            return {'CANCELLED'}

# 创建测试对象
class MCP_OT_CreateTestObject(bpy.types.Operator):
    bl_idname = "mcp.create_test_object"
    bl_label = "创建测试对象"
    bl_description = "创建一个测试对象来验证MCP连接"
    
    def execute(self, context):
        try:
            print("开始创建测试对象...")
            
            if not hasattr(context.scene, "mcp_tools_handler") or not context.scene.mcp_tools_handler:
                error_msg = "MCP工具处理器不可用，请确保服务器已连接"
                print(f"错误: {error_msg}")
                self.report({'ERROR'}, error_msg)
                return {'CANCELLED'}
            
            # 执行创建对象工具
            print("发送创建对象请求...")
            result = context.scene.mcp_tools_handler.execute_tool(
                "create_object", 
                {
                    "object_type": "cube", 
                    "size": 2.0, 
                    "name": "MCP_Test_Cube",
                    "location": [0, 0, 0]
                }
            )
            
            print(f"创建对象结果: {result}")
            if "error" in result:
                error_msg = f"创建测试对象失败: {result['error']}"
                print(f"错误: {error_msg}")
                self.report({'ERROR'}, error_msg)
                return {'CANCELLED'}
                
            # 设置材质
            print("发送设置材质请求...")
            material_result = context.scene.mcp_tools_handler.execute_tool(
                "set_material", 
                {
                    "object_name": result["object_name"],
                    "color": [1.0, 0.2, 0.2, 1.0],
                    "metallic": 0.2,
                    "roughness": 0.5
                }
            )
            print(f"设置材质结果: {material_result}")
            
            success_msg = f"创建了测试对象: {result['object_name']}"
            print(f"成功: {success_msg}")
            self.report({'INFO'}, success_msg)
            return {'FINISHED'}
        except Exception as e:
            import traceback
            traceback.print_exc()
            error_msg = f"创建测试对象时出错: {str(e)}"
            print(f"异常: {error_msg}")
            self.report({'ERROR'}, error_msg)
            return {'CANCELLED'}

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

# 切换工具列表显示的操作符
class MCP_OT_ToggleToolsList(bpy.types.Operator):
    bl_idname = "mcp.toggle_tools_list"
    bl_label = "显示/隐藏工具列表"
    bl_description = "切换工具列表的显示状态"
    
    def execute(self, context):
        global _mcp_show_tools_list
        _mcp_show_tools_list = not _mcp_show_tools_list
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
    ]
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

import bpy
from bpy.types import Operator
import socket
import json

# 启动MCP服务器操作符
class MCP_OT_StartServer(Operator):
    bl_idname = "mcp.start_server"
    bl_label = "启动MCP服务器"
    bl_description = "启动MCP服务器进程"
    
    def execute(self, context):
        try:
            # 延迟导入避免循环引用
            from ..core import server_manager
            
            # 获取首选项
            preferences = context.preferences.addons[__package__.split('.')[0]].preferences
            socket_path = preferences.socket_path
            debug_mode = preferences.debug_mode
            
            server_manager.start_server(socket_path, debug_mode)
            self.report({'INFO'}, "MCP服务器已启动")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"启动服务器时出错: {str(e)}")
            return {'CANCELLED'}

# 停止MCP服务器操作符
class MCP_OT_StopServer(Operator):
    bl_idname = "mcp.stop_server"
    bl_label = "停止MCP服务器"
    bl_description = "停止MCP服务器进程"
    
    def execute(self, context):
        try:
            # 延迟导入避免循环引用
            from ..core import server_manager
            server_manager.stop_server()
            self.report({'INFO'}, "MCP服务器已停止")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"停止服务器时出错: {str(e)}")
            return {'CANCELLED'}

# 创建测试对象操作符
class MCP_OT_CreateTestObject(Operator):
    bl_idname = "mcp.create_test_object"
    bl_label = "创建测试对象"
    bl_description = "创建一个测试对象以验证MCP连接"
    
    def execute(self, context):
        try:
            # 创建立方体
            bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0, 0, 0))
            obj = bpy.context.active_object
            obj.name = "MCP_Test_Cube"
            
            # 创建材质
            mat = bpy.data.materials.new(name="MCP_Test_Material")
            mat.use_nodes = True
            principled_bsdf = mat.node_tree.nodes.get('Principled BSDF')
            if principled_bsdf:
                principled_bsdf.inputs["Base Color"].default_value = (1.0, 0.2, 0.2, 1.0)
            
            # 应用材质
            if obj.data.materials:
                obj.data.materials[0] = mat
            else:
                obj.data.materials.append(mat)
                
            self.report({'INFO'}, "创建测试对象成功")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"创建测试对象时出错: {str(e)}")
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

# 注册所有操作符
classes = [
    MCP_OT_StartServer,
    MCP_OT_StopServer,
    MCP_OT_CreateTestObject,
    MCP_OT_ViewResources,
    MCP_OT_CheckServer
]

def register_operators():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister_operators():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

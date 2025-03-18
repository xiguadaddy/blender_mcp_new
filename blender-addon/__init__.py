bl_info = {
    "name": "Blender MCP",
    "author": "xiguadaddy",
    "version": (0, 1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > MCP",
    "description": "Blender 的MCP集成工具",
    "category": "Interface",
}

import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import AddonPreferences
import sys

# 插件首选项
class BlenderMCPPreferences(AddonPreferences):
    bl_idname = __name__
    
    # 检测平台并设置默认路径
    default_socket_path = "port:27015" if sys.platform == "win32" else "/tmp/blender-mcp.sock" 
    
    socket_path: StringProperty(
        name="IPC 通信路径",
        description="Windows上使用'port:端口号'格式，Unix/Linux上使用套接字文件路径",
        default=default_socket_path,
        subtype='FILE_PATH' if sys.platform != "win32" else 'NONE'
    )
    
    auto_start_server: BoolProperty(
        name="Blender启动时自动启动服务器",
        description="当Blender启动时自动启动IPC服务器",
        default=True
    )
    
    debug_mode: BoolProperty(
        name="调试模式",
        description="启用详细日志记录",
        default=False
    )
    
    max_resource_items: EnumProperty(
        name="最大资源项数",
        description="列出资源时的最大项数",
        items=[
            ('50', "50", "最多列出50个资源项"),
            ('100', "100", "最多列出100个资源项"),
            ('200', "200", "最多列出200个资源项"),
            ('ALL', "全部", "列出所有资源项")
        ],
        default='100'
    )
    
    def draw(self, context):
        layout = self.layout
        
        layout.prop(self, "socket_path")
        layout.prop(self, "auto_start_server")
        layout.prop(self, "debug_mode")
        layout.prop(self, "max_resource_items")
        
        # 添加手动启动/停止按钮
        box = layout.box()
        box.label(text="服务器控制")
        row = box.row()
        
        if not hasattr(bpy.types, "_mcp_server_running") or not bpy.types._mcp_server_running:
            row.operator("mcp.start_server", text="启动MCP服务器")
        else:
            row.operator("mcp.stop_server", text="停止MCP服务器")
            
        # 显示连接信息
        if hasattr(bpy.types, "_mcp_server_running") and bpy.types._mcp_server_running:
            box.label(text=f"服务器状态: 运行中", icon='CHECKMARK')
        else:
            box.label(text=f"服务器状态: 已停止", icon='X')

# 获取插件首选项
def get_preferences():
    return bpy.context.preferences.addons[__name__].preferences

# 注册和注销函数
def register():
    bpy.utils.register_class(BlenderMCPPreferences)
    
    # 推迟导入，避免循环引用
    from .addon import register_addon
    register_addon()
    
    # 如果设置为自动启动，启动IPC服务器
    preferences = get_preferences()
    if preferences.auto_start_server:
        from .core import server_manager
        server_manager.start_server(preferences.socket_path, preferences.debug_mode)

def unregister():
    # 停止IPC服务器
    if hasattr(bpy.types, "_mcp_server_running") and bpy.types._mcp_server_running:
        from .core import server_manager
        server_manager.stop_server()
    
    from .addon import unregister_addon
    unregister_addon()
    bpy.utils.unregister_class(BlenderMCPPreferences)

if __name__ == "__main__":
    register()

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
from bpy.app.handlers import persistent
import sys
from . import addon
import os

from . import logger

# 配置日志
logger = logger.get_logger("BlenderMCP")

# 用于标记插件是否已完全初始化
_initialization_complete = False

# 场景加载处理函数定义在全局作用域
@persistent
def load_handler(dummy):
    """场景加载时初始化插件状态"""
    from .handlers.resource_handlers import update_resource_state
    update_resource_state()
    
    # 确保每个场景都有工具处理器
    if hasattr(bpy.types, "_mcp_server_running") and bpy.types._mcp_server_running:
        try:
            from .handlers.tool_handlers import update_tools_handler
            update_tools_handler()
        except Exception as e:
            logger.error(f"更新工具处理器时出错: {e}")
    
    logger.info("Blender MCP插件状态已初始化")

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

# 延迟服务器启动，避免在注册过程中卡死
def delayed_server_start():
    """延迟启动IPC服务器，确保插件已完全注册"""
    global _initialization_complete
    
    # 如果初始化已完成，则不需要再次启动
    if _initialization_complete:
        return None
        
    try:
        # 安全导入，避免循环导入
        from .ipc.server import start_ipc_server
        
        # 获取插件首选项
        socket_path = None
        debug_mode = False
        
        addon_id = __package__.split('.')[0]
        try:
            if addon_id in bpy.context.preferences.addons:
                preferences = bpy.context.preferences.addons[addon_id].preferences
                if preferences is not None:
                    socket_path = preferences.socket_path
                    debug_mode = preferences.debug_mode
        except:
            pass
            
        # 如果无法获取首选项，使用默认值
        if not socket_path:
            if sys.platform == "win32":
                socket_path = "port:27015"
            else:
                import tempfile
                socket_path = os.path.join(tempfile.gettempdir(), "blender-mcp.sock")
            
        # 启动IPC服务器
        start_ipc_server(socket_path, debug_mode)
        bpy.types._mcp_socket_path = socket_path
        print(f"MCP服务器延迟启动成功: {socket_path}")
        
        _initialization_complete = True
    except Exception as e:
        print(f"延迟启动MCP服务器时出错: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return None  # 确保函数只运行一次

# 导入日志系统
from .logger import configure_logging

# 注册和注销函数
def register():
    # 配置日志系统
    configure_logging()
    
    # 先注册首选项类
    try:
        bpy.utils.register_class(BlenderMCPPreferences)
        logger.info("首选项类注册成功")
    except Exception as e:
        logger.error(f"注册首选项类时出错: {str(e)}")
        # 如果注册失败，这不应该阻止插件的其余部分注册
    
    # 再注册其他组件
    addon.register()
    
    # 注册场景加载处理器
    bpy.app.handlers.load_post.append(load_handler)
    
    # 不要自动启动服务器，避免可能的卡死
    logger.info("MCP插件注册完成，请通过界面手动启动服务器")
    
def unregister():
    # 停止IPC服务器
    try:
        from .ipc.server import stop_ipc_server
        stop_ipc_server()
    except Exception as e:
        logger.error(f"停止服务器时出错: {str(e)}")
    
    # 移除场景加载处理器
    if load_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_handler)
    
    # 注销其他组件
    addon.unregister()
    
    # 最后注销首选项类
    try:
        bpy.utils.unregister_class(BlenderMCPPreferences)
        logger.info("首选项类注销成功")
    except Exception as e:
        logger.error(f"注销首选项类时出错: {str(e)}")
        # 如果注销失败，不应阻止插件的其余部分注销
    
    global _initialization_complete
    _initialization_complete = False
    print("MCP插件已卸载，服务器已停止")

if __name__ == "__main__":
    register()

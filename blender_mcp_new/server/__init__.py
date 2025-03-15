"""
BlenderMCP 服务器模块
提供与Blender互操作的网络API服务器

版本: 0.2.0
"""

__version__ = "0.2.0"

import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('blender_mcp.server')
logger.info(f"BlenderMCP服务器模块初始化，版本: {__version__}")

# 此模块需要在Blender内部导入
try:
    import bpy
except ImportError:
    raise ImportError("server模块必须在Blender内部运行，无法在常规Python环境中导入")


class MCPServerPanel(bpy.types.Panel):
    """BlenderMCP服务器控制面板"""
    bl_label = "BlenderMCP Server"
    bl_idname = "VIEW3D_PT_mcp_server"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BlenderMCP"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # 服务器设置
        layout.prop(scene, "mcp_server_host")
        layout.prop(scene, "mcp_server_port")
        
        # 启动/停止按钮
        if scene.mcp_server_running:
            layout.operator("mcp.stop_server", text="停止服务器", icon='CANCEL')
        else:
            layout.operator("mcp.start_server", text="启动服务器", icon='PLAY')
        
        # 服务器状态
        if scene.mcp_server_running:
            layout.label(text=f"服务器运行中: {scene.mcp_server_host}:{scene.mcp_server_port}")


# 当此包在Blender中加载时，将自动导入服务器类
from .server import BlenderMCPServer

__all__ = ['BlenderMCPServer'] 
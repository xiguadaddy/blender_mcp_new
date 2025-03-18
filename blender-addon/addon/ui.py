import bpy
from bpy.types import Panel
import sys
from ..handlers import tool_handlers

# MCP侧边栏面板
class MCP_PT_Panel(Panel):
    bl_label = "Blender MCP"
    bl_idname = "MCP_PT_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MCP"
    
    def draw(self, context):
        layout = self.layout
        
        # 显示服务器状态
        box = layout.box()
        
        # 添加平台信息
        platform = "Windows" if sys.platform == "win32" else "Unix/Linux"
        box.label(text=f"平台: {platform}")
        
        # 显示通信设置
        preferences = context.preferences.addons[__package__.split('.')[0]].preferences
        socket_path = preferences.socket_path
        
        if sys.platform == "win32":
            if socket_path.startswith("port:"):
                port = socket_path.split(":", 1)[1]
                box.label(text=f"TCP端口: {port}")
            else:
                box.label(text=f"通信设置: {socket_path}")
        else:
            box.label(text=f"套接字路径: {socket_path}")
        
        if hasattr(bpy.types, "_mcp_server_running") and bpy.types._mcp_server_running:
            status_row = box.row()
            status_row.label(text="服务器状态: 运行中", icon='CHECKMARK')
            box.operator("mcp.stop_server", text="停止服务器", icon='PAUSE')
        else:
            status_row = box.row()
            status_row.label(text="服务器状态: 已停止", icon='X')
            box.operator("mcp.start_server", text="启动服务器", icon='PLAY')
        
        # 资源和工具部分
        if hasattr(bpy.types, "_mcp_server_running") and bpy.types._mcp_server_running:
            # 测试工具
            test_box = layout.box()
            test_box.label(text="测试工具", icon='TOOL_SETTINGS')
            test_row = test_box.row()
            test_row.operator("mcp.create_test_object", text="创建测试对象", icon='MESH_CUBE')
            test_row = test_box.row()
            test_row.operator("mcp.view_resources", text="查看资源", icon='VIEWZOOM')
            
            # 资源信息
            info_box = layout.box()
            info_box.label(text="MCP集成信息", icon='INFO')
            info_box.label(text=f"可用工具: {len(tool_handlers.TOOLS.keys())}个工具")
            info_box.label(text="端点: /tmp/blender-mcp.sock")
        else:
            layout.label(text="请先启动MCP服务器", icon='ERROR')

# MCP信息面板（属性编辑器中）
class MCP_PT_InfoPanel(Panel):
    bl_label = "MCP信息"
    bl_idname = "MCP_PT_InfoPanel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    
    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.label(text="MCP集成信息", icon='INFO')
        
        if hasattr(bpy.types, "_mcp_server_running") and bpy.types._mcp_server_running:
            box.label(text="MCP服务器: 运行中", icon='CHECKMARK')
            box.label(text="支持的功能:")
            box.label(text="- 资源访问 (网格、材质、灯光、相机)")
            box.label(text="- 对象创建和编辑")
            box.label(text="- 材质设置")
            box.label(text="- 渲染控制")
        else:
            box.label(text="MCP服务器: 已停止", icon='X')
            box.label(text="请启动MCP服务器以启用功能")
            box.operator("mcp.start_server", text="启动服务器", icon='PLAY')

# 注册所有UI类
classes = [
    MCP_PT_Panel,
    MCP_PT_InfoPanel
]

def register_ui():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister_ui():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

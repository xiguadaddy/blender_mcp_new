from . import ui
from . import operators

# 从各模块导入全局变量
_mcp_server_running = operators._mcp_server_running
# 这些变量定义在ui模块中
_mcp_show_tools_list = ui._mcp_show_tools_list
_mcp_show_resources_list = ui._mcp_show_resources_list

def register():
    operators.register_operators()
    ui.register_ui()

def unregister():
    ui.unregister_ui()
    operators.unregister_operators()

def register_addon():
    operators.register_operators()
    ui.register_ui()

def unregister_addon():
    ui.unregister_ui()
    operators.unregister_operators()

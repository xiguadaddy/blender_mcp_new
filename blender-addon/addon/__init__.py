from . import ui
from . import operators

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

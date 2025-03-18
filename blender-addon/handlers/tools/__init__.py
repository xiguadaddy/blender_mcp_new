"""
Blender MCP工具包

包含所有可通过MCP协议调用的Blender工具，按功能分类组织。
"""

# 导入工具模块
from . import object_tools
from . import material_tools
from . import lighting_tools
from . import camera_tools
from . import scene_tools
from . import modeling_tools
from . import animation_tools
from . import effect_tools

def register_all_tools():
    """
    注册所有工具
    
    该函数从各个工具模块中收集工具，并返回一个包含所有工具的字典。
    
    Returns:
        dict: 键为工具名称，值为对应的工具函数
    """
    all_tools = {}
    
    # 从各个模块注册工具
    all_tools.update(object_tools.TOOLS)
    all_tools.update(material_tools.TOOLS)
    all_tools.update(lighting_tools.TOOLS)
    all_tools.update(camera_tools.TOOLS)
    all_tools.update(scene_tools.TOOLS)
    all_tools.update(modeling_tools.TOOLS)
    all_tools.update(animation_tools.TOOLS)
    all_tools.update(effect_tools.TOOLS)
    
    return all_tools

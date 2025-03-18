"""
核心工具模块

包含 Blender MCP 核心功能，例如列出可用工具。
"""

import bpy
import logging
from ..tool_handlers import execute_in_main_thread

# 设置日志
logger = logging.getLogger("BlenderMCP.CoreTools")

def list_tools():
    """返回可用工具列表"""
    from . import register_all_tools
    
    logger.debug("列出可用工具")
    
    # 获取所有注册的工具
    tools_dict = register_all_tools()
    
    tools = []
    for tool_name, tool_func in tools_dict.items():
        # 获取工具的docstring作为描述
        description = tool_func.__doc__ or f"执行{tool_name}操作"
        
        # 构建工具信息
        tool_info = {
            "name": tool_name,
            "description": description.strip(),
            "version": "1.0"
        }
        
        # 针对特定工具添加额外信息
        if tool_name == "create_object":
            tool_info["input_schema"] = {
                "type": "object",
                "properties": {
                    "object_type": {
                        "type": "string",
                        "enum": ["cube", "sphere", "plane", "cylinder", "cone", "torus", "empty"],
                        "description": "要创建的对象类型"
                    },
                    "location": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "对象位置坐标 [x, y, z]"
                    },
                    "name": {
                        "type": "string",
                        "description": "对象名称"
                    },
                    "size": {
                        "type": "number",
                        "description": "对象大小"
                    }
                },
                "required": ["object_type"]
            }
        elif tool_name == "set_material":
            tool_info["input_schema"] = {
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "目标对象名称"},
                    "material_name": {"type": "string", "description": "材质名称"},
                    "color": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "RGBA颜色值 [r, g, b, a]"
                    },
                    "metallic": {"type": "number", "description": "金属度(0-1)"},
                    "roughness": {"type": "number", "description": "粗糙度(0-1)"}
                },
                "required": ["object_name"]
            }
        elif tool_name == "add_light":
            tool_info["input_schema"] = {
                "type": "object",
                "properties": {
                    "light_type": {
                        "type": "string",
                        "enum": ["POINT", "SUN", "SPOT", "AREA"],
                        "description": "灯光类型"
                    },
                    "location": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "灯光位置 [x, y, z]"
                    },
                    "name": {"type": "string", "description": "灯光名称"},
                    "color": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "RGB颜色值 [r, g, b]"
                    },
                    "energy": {"type": "number", "description": "灯光强度"}
                },
                "required": ["light_type"]
            }
        
        tools.append(tool_info)
    
    return tools

# 注册工具
TOOLS = {
    "list_tools": list_tools,
}

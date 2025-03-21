"""
添加Blender修改器的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.AddModifier")

class AddModifierHandler(BaseToolHandler):
    """添加修改器工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_add_modifier"
        
    @property
    def description(self) -> Optional[str]:
        return "为3D对象添加修改器"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "要添加修改器的对象名称"
                },
                "modifier_type": {
                    "type": "string",
                    "title": "修改器类型",
                    "description": "要添加的修改器类型",
                    "enum": [
                        "SUBSURF", "BEVEL", "ARRAY", "MIRROR", "SOLIDIFY", 
                        "BOOLEAN", "SHRINKWRAP", "DISPLACE", "ARMATURE", "CURVE"
                    ]
                },
                "modifier_name": {
                    "type": "string",
                    "title": "修改器名称",
                    "description": "修改器的自定义名称(可选)"
                },
                "parameters": {
                    "type": "object",
                    "title": "参数",
                    "description": "修改器的特定参数"
                }
            },
            "required": ["object_name", "modifier_type"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查对象名称
        if not arguments.get("object_name"):
            return "必须提供对象名称"
            
        # 检查修改器类型
        modifier_type = arguments.get("modifier_type")
        if not modifier_type:
            return "必须提供修改器类型"
            
        # 验证修改器类型是否支持
        valid_types = [
            "SUBSURF", "BEVEL", "ARRAY", "MIRROR", "SOLIDIFY", 
            "BOOLEAN", "SHRINKWRAP", "DISPLACE", "ARMATURE", "CURVE"
        ]
        if modifier_type not in valid_types:
            return f"不支持的修改器类型: {modifier_type}，有效类型: {', '.join(valid_types)}"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行添加修改器操作"""
        logger.info(f"添加修改器，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._add_modifier, arguments)
        
    def _add_modifier(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中添加修改器"""
        object_name = arguments.get("object_name")
        modifier_type = arguments.get("modifier_type")
        modifier_name = arguments.get("modifier_name", "")
        parameters = arguments.get("parameters", {})
        
        # 检查对象是否存在
        if object_name not in bpy.data.objects:
            text_content = self.create_text_content(f"找不到对象: {object_name}")
            return self.create_result([text_content], is_error=True)
        
        # 获取对象
        obj = bpy.data.objects[object_name]
        
        # 检查对象类型是否适合添加修改器
        if obj.type not in {'MESH', 'CURVE', 'SURFACE', 'FONT', 'LATTICE'}:
            text_content = self.create_text_content(f"对象类型 '{obj.type}' 不支持添加修改器")
            return self.create_result([text_content], is_error=True)
        
        # 添加修改器
        mod = obj.modifiers.new(name=modifier_name or modifier_type, type=modifier_type)
        
        # 设置特定参数
        for param_name, param_value in parameters.items():
            try:
                # 尝试设置参数
                setattr(mod, param_name, param_value)
            except:
                logger.warning(f"无法设置参数 '{param_name}' 为 '{param_value}'")
        
        # 特定修改器类型处理
        if modifier_type == "SUBSURF":
            # 设置细分曲面默认值
            if "levels" not in parameters:
                mod.levels = 2
                mod.render_levels = 2
                
        elif modifier_type == "BEVEL":
            # 设置倒角默认值
            if "width" not in parameters:
                mod.width = 0.1
                
        elif modifier_type == "ARRAY":
            # 设置阵列默认值
            if "count" not in parameters:
                mod.count = 2
                
        elif modifier_type == "MIRROR":
            # 设置镜像默认值
            if "use_axis" not in parameters:
                mod.use_axis[0] = True  # 沿X轴镜像
        
        # 创建结果信息
        text_content = self.create_text_content(f"已为对象 '{object_name}' 添加 {modifier_type} 修改器")
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(AddModifierHandler())
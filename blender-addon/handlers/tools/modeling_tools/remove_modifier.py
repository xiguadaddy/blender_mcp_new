"""
删除Blender修改器的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.RemoveModifier")

class RemoveModifierHandler(BaseToolHandler):
    """删除修改器工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_remove_modifier"
        
    @property
    def description(self) -> Optional[str]:
        return "删除3D对象上的修改器"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "要删除修改器的对象名称"
                },
                "modifier_name": {
                    "type": "string",
                    "title": "修改器名称",
                    "description": "要删除的修改器名称"
                },
                "remove_all": {
                    "type": "boolean",
                    "title": "删除所有",
                    "description": "是否删除对象上的所有修改器",
                    "default": False
                }
            },
            "required": ["object_name"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查对象名称
        if not arguments.get("object_name"):
            return "必须提供对象名称"
            
        # 如果不是删除所有，则必须提供修改器名称
        if not arguments.get("remove_all") and not arguments.get("modifier_name"):
            return "必须提供修改器名称或设置删除所有标志"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行删除修改器操作"""
        logger.info(f"删除修改器，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._remove_modifier, arguments)
        
    def _remove_modifier(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中删除修改器"""
        object_name = arguments.get("object_name")
        modifier_name = arguments.get("modifier_name", "")
        remove_all = arguments.get("remove_all", False)
        
        # 检查对象是否存在
        if object_name not in bpy.data.objects:
            text_content = self.create_text_content(f"找不到对象: {object_name}")
            return self.create_result([text_content], is_error=True)
        
        # 获取对象
        obj = bpy.data.objects[object_name]
        
        removed_modifiers = []
        
        if remove_all:
            # 删除所有修改器
            for mod in list(obj.modifiers):  # 创建列表副本，因为删除过程中会修改原列表
                mod_name = mod.name
                obj.modifiers.remove(mod)
                removed_modifiers.append(mod_name)
            
            if removed_modifiers:
                text_content = self.create_text_content(f"已删除对象 '{object_name}' 上的所有修改器: {', '.join(removed_modifiers)}")
            else:
                text_content = self.create_text_content(f"对象 '{object_name}' 上没有修改器")
                
        else:
            # 删除特定修改器
            if modifier_name in obj.modifiers:
                mod = obj.modifiers[modifier_name]
                obj.modifiers.remove(mod)
                removed_modifiers.append(modifier_name)
                text_content = self.create_text_content(f"已删除对象 '{object_name}' 上的修改器: {modifier_name}")
            else:
                text_content = self.create_text_content(f"对象 '{object_name}' 上找不到修改器: {modifier_name}")
                return self.create_result([text_content], is_error=True)
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(RemoveModifierHandler())
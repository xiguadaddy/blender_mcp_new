"""
应用Blender修改器的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.ApplyModifier")

class ApplyModifierHandler(BaseToolHandler):
    """应用修改器工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_apply_modifier"
        
    @property
    def description(self) -> Optional[str]:
        return "应用3D对象上的修改器"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "要应用修改器的对象名称"
                },
                "modifier_name": {
                    "type": "string",
                    "title": "修改器名称",
                    "description": "要应用的修改器名称"
                },
                "apply_all": {
                    "type": "boolean",
                    "title": "应用所有",
                    "description": "是否应用对象上的所有修改器",
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
            
        # 如果不是应用所有，则必须提供修改器名称
        if not arguments.get("apply_all") and not arguments.get("modifier_name"):
            return "必须提供修改器名称或设置应用所有标志"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行应用修改器操作"""
        logger.info(f"应用修改器，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._apply_modifier, arguments)
        
    def _apply_modifier(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中应用修改器"""
        object_name = arguments.get("object_name")
        modifier_name = arguments.get("modifier_name", "")
        apply_all = arguments.get("apply_all", False)
        
        # 检查对象是否存在
        if object_name not in bpy.data.objects:
            text_content = self.create_text_content(f"找不到对象: {object_name}")
            return self.create_result([text_content], is_error=True)
        
        # 获取对象
        obj = bpy.data.objects[object_name]
        
        # 检查对象类型是否适合应用修改器
        if obj.type != 'MESH':
            text_content = self.create_text_content(f"只能对网格对象应用修改器，'{object_name}' 是 '{obj.type}' 类型")
            return self.create_result([text_content], is_error=True)
        
        # 确保对象是当前活动对象
        bpy.context.view_layer.objects.active = obj
        
        applied_modifiers = []
        
        if apply_all:
            # 应用所有修改器
            for mod in list(obj.modifiers):  # 创建列表副本，因为应用过程中会修改原列表
                mod_name = mod.name
                try:
                    bpy.ops.object.modifier_apply(modifier=mod_name)
                    applied_modifiers.append(mod_name)
                except Exception as e:
                    logger.error(f"应用修改器 '{mod_name}' 时出错: {str(e)}")
            
            if applied_modifiers:
                text_content = self.create_text_content(f"已应用对象 '{object_name}' 上的所有修改器: {', '.join(applied_modifiers)}")
            else:
                text_content = self.create_text_content(f"对象 '{object_name}' 上没有可应用的修改器")
                
        else:
            # 应用特定修改器
            if modifier_name in obj.modifiers:
                try:
                    bpy.ops.object.modifier_apply(modifier=modifier_name)
                    applied_modifiers.append(modifier_name)
                    text_content = self.create_text_content(f"已应用对象 '{object_name}' 上的修改器: {modifier_name}")
                except Exception as e:
                    text_content = self.create_text_content(f"应用修改器 '{modifier_name}' 时出错: {str(e)}")
                    return self.create_result([text_content], is_error=True)
            else:
                text_content = self.create_text_content(f"对象 '{object_name}' 上找不到修改器: {modifier_name}")
                return self.create_result([text_content], is_error=True)
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(ApplyModifierHandler())
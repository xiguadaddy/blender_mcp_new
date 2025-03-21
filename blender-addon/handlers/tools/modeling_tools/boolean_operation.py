"""
执行布尔运算的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.BooleanOperation")

class BooleanOperationHandler(BaseToolHandler):
    """布尔运算工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_boolean_operation"
        
    @property
    def description(self) -> Optional[str]:
        return "在两个3D对象之间执行布尔运算"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "target_object": {
                    "type": "string",
                    "title": "目标对象",
                    "description": "执行布尔运算的目标对象名称"
                },
                "tool_object": {
                    "type": "string",
                    "title": "工具对象",
                    "description": "用作布尔运算工具的对象名称"
                },
                "operation": {
                    "type": "string",
                    "title": "运算类型",
                    "description": "要执行的布尔运算类型",
                    "enum": ["UNION", "INTERSECT", "DIFFERENCE"],
                    "default": "DIFFERENCE"
                },
                "apply_modifier": {
                    "type": "boolean",
                    "title": "应用修改器",
                    "description": "是否立即应用布尔修改器",
                    "default": True
                },
                "delete_tool": {
                    "type": "boolean",
                    "title": "删除工具对象",
                    "description": "操作后是否删除工具对象",
                    "default": True
                }
            },
            "required": ["target_object", "tool_object", "operation"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查目标对象名称
        if not arguments.get("target_object"):
            return "必须提供目标对象名称"
            
        # 检查工具对象名称
        if not arguments.get("tool_object"):
            return "必须提供工具对象名称"
            
        # 检查运算类型
        operation = arguments.get("operation")
        if not operation:
            return "必须提供运算类型"
            
        # 验证运算类型是否支持
        valid_operations = ["UNION", "INTERSECT", "DIFFERENCE"]
        if operation not in valid_operations:
            return f"不支持的运算类型: {operation}，有效类型: {', '.join(valid_operations)}"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行布尔运算操作"""
        logger.info(f"布尔运算，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._boolean_operation, arguments)
        
    def _boolean_operation(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中执行布尔运算"""
        target_object = arguments.get("target_object")
        tool_object = arguments.get("tool_object")
        operation = arguments.get("operation")
        apply_modifier = arguments.get("apply_modifier", True)
        delete_tool = arguments.get("delete_tool", True)
        
        # 检查目标对象是否存在
        if target_object not in bpy.data.objects:
            text_content = self.create_text_content(f"找不到目标对象: {target_object}")
            return self.create_result([text_content], is_error=True)
        
        # 检查工具对象是否存在
        if tool_object not in bpy.data.objects:
            text_content = self.create_text_content(f"找不到工具对象: {tool_object}")
            return self.create_result([text_content], is_error=True)
        
        # 获取对象
        target = bpy.data.objects[target_object]
        tool = bpy.data.objects[tool_object]
        
        # 检查对象类型
        if target.type != 'MESH' or tool.type != 'MESH':
            text_content = self.create_text_content("布尔运算只能在网格对象之间进行")
            return self.create_result([text_content], is_error=True)
        
        # 添加布尔修改器
        bool_mod = target.modifiers.new(name="Boolean", type='BOOLEAN')
        bool_mod.object = tool
        bool_mod.operation = operation
        
        # 确保目标对象是活动对象
        bpy.context.view_layer.objects.active = target
        
        # 应用修改器（如果需要）
        if apply_modifier:
            try:
                bpy.ops.object.modifier_apply(modifier=bool_mod.name)
            except Exception as e:
                text_content = self.create_text_content(f"应用布尔修改器时出错: {str(e)}")
                return self.create_result([text_content], is_error=True)
        
        # 删除工具对象（如果需要）
        if delete_tool:
            bpy.data.objects.remove(tool)
        
        # 创建结果信息
        text_content = self.create_text_content(
            f"已在对象 '{target_object}' 上执行布尔{operation}运算" +
            (f"，并删除了工具对象 '{tool_object}'" if delete_tool else "")
        )
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(BooleanOperationHandler())
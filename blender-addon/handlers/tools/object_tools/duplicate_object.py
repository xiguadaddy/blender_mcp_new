from ..registry import register_tool
import bpy
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.DuplicateObject")

class DuplicateObjectHandler(BaseToolHandler):
    """复制3D对象工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_duplicate_object"
        
    @property
    def description(self) -> Optional[str]:
        return "复制一个现有的3D对象"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "title": "源对象名称",
                    "description": "要复制的对象名称"
                },
                "new_name": {
                    "type": "string",
                    "title": "新对象名称",
                    "description": "复制对象的新名称（可选）"
                },
                "linked": {
                    "type": "boolean",
                    "title": "链接复制",
                    "description": "是否创建链接复制（共享相同的网格数据）",
                    "default": False
                },
                "offset": {
                    "type": "array",
                    "title": "位置偏移",
                    "description": "复制对象的位置偏移 [x, y, z]",
                    "items": {
                        "type": "number"
                    },
                    "default": [1.0, 0.0, 0.0]
                }
            },
            "required": ["name"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查源对象名称
        if not arguments.get("name"):
            return "必须提供源对象名称"
            
        # 检查偏移参数
        offset = arguments.get("offset")
        if offset and not (isinstance(offset, list) and len(offset) == 3 and all(isinstance(v, (int, float)) for v in offset)):
            return "位置偏移参数必须是包含3个数字的数组 [x, y, z]"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行复制对象操作"""
        logger.info(f"复制对象，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._duplicate_object, arguments)
        
    def _duplicate_object(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中复制对象"""
        obj_name = arguments.get("name")
        new_name = arguments.get("new_name")
        linked = arguments.get("linked", False)
        offset = arguments.get("offset", [1.0, 0.0, 0.0])
        
        # 检查对象是否存在
        if obj_name not in bpy.data.objects:
            text_content = self.create_text_content(f"找不到对象: {obj_name}")
            return self.create_result([text_content], is_error=True)
        
        # 获取原始对象
        orig_obj = bpy.data.objects[obj_name]
        
        # 确保所有对象都取消选择
        bpy.ops.object.select_all(action='DESELECT')
        
        # 选择要复制的对象
        orig_obj.select_set(True)
        bpy.context.view_layer.objects.active = orig_obj
        
        # 执行复制
        if linked:
            bpy.ops.object.duplicate_move_linked(
                OBJECT_OT_duplicate={
                    "linked": True, 
                    "mode": 'TRANSLATION'
                },
                TRANSFORM_OT_translate={
                    "value": offset
                }
            )
        else:
            bpy.ops.object.duplicate_move(
                OBJECT_OT_duplicate={
                    "linked": False, 
                    "mode": 'TRANSLATION'
                },
                TRANSFORM_OT_translate={
                    "value": offset
                }
            )
        
        # 获取新创建的对象(当前选中的对象即为复制出的对象)
        new_obj = bpy.context.selected_objects[0]
        
        # 如果提供了新名称，则重命名
        if new_name:
            new_obj.name = new_name
        
        # 创建结果信息
        text_content = self.create_text_content(f"已复制对象: {obj_name} -> {new_obj.name}")
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(DuplicateObjectHandler())
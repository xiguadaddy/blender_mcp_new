"""
合并Blender对象的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.JoinObjects")

class JoinObjectsHandler(BaseToolHandler):
    """合并对象工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_join_objects"
        
    @property
    def description(self) -> Optional[str]:
        return "将多个3D对象合并为一个"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "target_object": {
                    "type": "string",
                    "title": "目标对象",
                    "description": "要合并到的目标对象名称"
                },
                "object_names": {
                    "type": "array",
                    "title": "要合并的对象",
                    "description": "要合并的对象名称列表",
                    "items": {
                        "type": "string"
                    }
                },
                "result_name": {
                    "type": "string",
                    "title": "结果名称",
                    "description": "合并后的对象名称（可选）"
                }
            },
            "required": ["target_object", "object_names"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查目标对象名称
        if not arguments.get("target_object"):
            return "必须提供目标对象名称"
            
        # 检查要合并的对象列表
        obj_names = arguments.get("object_names")
        if not obj_names or not isinstance(obj_names, list) or len(obj_names) == 0:
            return "必须提供至少一个要合并的对象名称"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行合并对象操作"""
        logger.info(f"合并对象，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._join_objects, arguments)
        
    def _join_objects(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中合并对象"""
        target_object = arguments.get("target_object")
        object_names = arguments.get("object_names", [])
        result_name = arguments.get("result_name", "")
        
        # 检查目标对象是否存在
        if target_object not in bpy.data.objects:
            text_content = self.create_text_content(f"找不到目标对象: {target_object}")
            return self.create_result([text_content], is_error=True)
        
        # 获取目标对象
        target = bpy.data.objects[target_object]
        
        # 确保目标是网格对象
        if target.type != 'MESH':
            text_content = self.create_text_content(f"目标对象必须是网格类型，而 '{target_object}' 是 '{target.type}' 类型")
            return self.create_result([text_content], is_error=True)
        
        # 检查并收集要合并的对象
        objects_to_join = []
        invalid_objects = []
        
        for obj_name in object_names:
            if obj_name == target_object:
                continue  # 跳过目标对象本身
                
            if obj_name in bpy.data.objects:
                obj = bpy.data.objects[obj_name]
                if obj.type == 'MESH':
                    objects_to_join.append(obj)
                else:
                    invalid_objects.append(f"{obj_name} (不是网格对象)")
            else:
                invalid_objects.append(f"{obj_name} (不存在)")
        
        if not objects_to_join:
            text_content = self.create_text_content("没有找到可合并的有效对象")
            return self.create_result([text_content], is_error=True)
        
        # 确保所有对象都被选中，且目标对象是活动对象
        bpy.ops.object.select_all(action='DESELECT')
        target.select_set(True)
        bpy.context.view_layer.objects.active = target
        
        for obj in objects_to_join:
            obj.select_set(True)
        
        # 执行合并操作
        try:
            bpy.ops.object.join()
            
            # 如果提供了结果名称，重命名合并后的对象
            if result_name:
                target.name = result_name
                
            joined_names = ", ".join([obj.name for obj in objects_to_join])
            text_content = self.create_text_content(f"已将对象 {joined_names} 合并到 '{target.name}'")
            
            # 如果有无效对象，添加警告信息
            if invalid_objects:
                text_content.text += f"\n警告: 以下对象无法合并: {', '.join(invalid_objects)}"
                
        except Exception as e:
            text_content = self.create_text_content(f"合并对象时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(JoinObjectsHandler())
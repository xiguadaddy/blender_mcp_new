"""
删除Blender对象的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.DeleteObject")

class DeleteObjectHandler(BaseToolHandler):
    """删除3D对象工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_delete_object"
        
    @property
    def description(self) -> Optional[str]:
        return "删除一个或多个指定的3D对象"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "要删除的对象名称"
                },
                "all": {
                    "type": "boolean",
                    "title": "删除全部",
                    "description": "是否删除场景中的所有对象"
                }
            }
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 如果既没有提供对象名称也没有设置删除全部标志，则返回错误
        if not arguments.get("name") and not arguments.get("all"):
            return "需要提供对象名称或设置删除全部标志"
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行删除对象操作"""
        logger.info(f"删除对象，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._delete_object, arguments)
        
    def _delete_object(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中删除对象"""
        obj_name = arguments.get("name", None)
        delete_all = arguments.get("all", False)
        
        deleted_objects = []
        
        if delete_all:
            # 删除所有对象
            for obj in list(bpy.data.objects):
                obj_name = obj.name
                bpy.data.objects.remove(obj)
                deleted_objects.append(obj_name)
            
            text_content = self.create_text_content(f"已删除所有对象，共 {len(deleted_objects)} 个")
        
        elif obj_name:
            # 删除特定对象
            if obj_name in bpy.data.objects:
                obj = bpy.data.objects[obj_name]
                bpy.data.objects.remove(obj)
                deleted_objects.append(obj_name)
                
                text_content = self.create_text_content(f"已删除对象: {obj_name}")
            else:
                text_content = self.create_text_content(f"找不到对象: {obj_name}")
                return self.create_result([text_content], is_error=True)
        
        else:
            text_content = self.create_text_content("未提供对象名称或删除所有标志")
            return self.create_result([text_content], is_error=True)
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(DeleteObjectHandler())
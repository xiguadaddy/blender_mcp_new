"""
重命名Blender对象的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.RenameObject")

class RenameObjectHandler(BaseToolHandler):
    """重命名3D对象工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_rename_object"
        
    @property
    def description(self) -> Optional[str]:
        return "重命名一个现有的3D对象"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "old_name": {
                    "type": "string",
                    "title": "原对象名称",
                    "description": "要重命名的对象原名称"
                },
                "new_name": {
                    "type": "string",
                    "title": "新对象名称",
                    "description": "对象的新名称"
                }
            },
            "required": ["old_name", "new_name"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查原名称
        if not arguments.get("old_name"):
            return "必须提供原对象名称"
            
        # 检查新名称
        if not arguments.get("new_name"):
            return "必须提供新对象名称"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行重命名对象操作"""
        logger.info(f"重命名对象，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._rename_object, arguments)
        
    def _rename_object(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中重命名对象"""
        old_name = arguments.get("old_name")
        new_name = arguments.get("new_name")
        
        # 检查对象是否存在
        if old_name not in bpy.data.objects:
            text_content = self.create_text_content(f"找不到对象: {old_name}")
            return self.create_result([text_content], is_error=True)
        
        # 获取对象
        obj = bpy.data.objects[old_name]
        
        # 保存原名称
        original_name = obj.name
        
        # 重命名对象
        obj.name = new_name
        
        # 创建结果信息
        text_content = self.create_text_content(f"已重命名对象: {original_name} -> {obj.name}")
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(RenameObjectHandler())
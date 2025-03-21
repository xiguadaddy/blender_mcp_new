"""
选择Blender对象的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.SelectObject")

class SelectObjectHandler(BaseToolHandler):
    """选择3D对象工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_select_object"
        
    @property
    def description(self) -> Optional[str]:
        return "选择一个或多个指定的3D对象"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "要选择的对象名称"
                },
                "names": {
                    "type": "array",
                    "title": "对象名称列表",
                    "description": "要选择的多个对象名称",
                    "items": {
                        "type": "string"
                    }
                },
                "all": {
                    "type": "boolean",
                    "title": "选择全部",
                    "description": "是否选择场景中的所有对象",
                    "default": False
                },
                "deselect": {
                    "type": "boolean",
                    "title": "先取消选择",
                    "description": "在选择前是否先取消当前所有选择",
                    "default": True
                }
            }
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 如果既没有提供对象名称也没有设置选择全部标志，则返回错误
        if not arguments.get("name") and not arguments.get("names") and not arguments.get("all"):
            return "需要提供对象名称、名称列表或设置选择全部标志"
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行选择对象操作"""
        logger.info(f"选择对象，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._select_object, arguments)
        
    def _select_object(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中选择对象"""
        obj_name = arguments.get("name", None)
        obj_names = arguments.get("names", [])
        select_all = arguments.get("all", False)
        deselect_first = arguments.get("deselect", True)
        
        # 如果单个名称提供了但没有提供列表，则将单个名称加入列表
        if obj_name and not obj_names:
            obj_names = [obj_name]
        
        # 先取消所有选择（如果需要）
        if deselect_first:
            bpy.ops.object.select_all(action='DESELECT')
        
        selected_objects = []
        
        if select_all:
            # 选择所有对象
            bpy.ops.object.select_all(action='SELECT')
            selected_objects = [obj.name for obj in bpy.data.objects]
            
            text_content = self.create_text_content(f"已选择所有对象，共 {len(selected_objects)} 个")
        
        elif obj_names:
            # 选择指定的对象
            for name in obj_names:
                if name in bpy.data.objects:
                    obj = bpy.data.objects[name]
                    obj.select_set(True)
                    selected_objects.append(name)
            
            if selected_objects:
                # 设置活动对象
                if selected_objects[0] in bpy.data.objects:
                    bpy.context.view_layer.objects.active = bpy.data.objects[selected_objects[0]]
                
                text_content = self.create_text_content(f"已选择 {len(selected_objects)} 个对象")
            else:
                text_content = self.create_text_content("未找到指定的对象")
                return self.create_result([text_content], is_error=True)
        
        else:
            text_content = self.create_text_content("未提供对象名称或选择所有标志")
            return self.create_result([text_content], is_error=True)
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(SelectObjectHandler())
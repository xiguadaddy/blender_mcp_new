"""
删除Blender灯光的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.DeleteLight")

class DeleteLightHandler(BaseToolHandler):
    """删除灯光工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_delete_light"
        
    @property
    def description(self) -> Optional[str]:
        return "删除一个或多个场景中的灯光"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "light_name": {
                    "type": "string",
                    "title": "灯光名称",
                    "description": "要删除的灯光名称"
                },
                "all_lights": {
                    "type": "boolean",
                    "title": "删除所有灯光",
                    "description": "是否删除场景中的所有灯光",
                    "default": False
                },
                "type_filter": {
                    "type": "string",
                    "title": "类型过滤",
                    "description": "按类型过滤要删除的灯光",
                    "enum": ["POINT", "SUN", "SPOT", "AREA"]
                }
            }
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 如果既没有提供灯光名称也没有设置删除所有标志，则返回错误
        if not arguments.get("light_name") and not arguments.get("all_lights"):
            return "需要提供灯光名称或设置删除所有灯光标志"
            
        # 验证类型过滤器
        type_filter = arguments.get("type_filter")
        if type_filter and type_filter not in ["POINT", "SUN", "SPOT", "AREA"]:
            return "类型过滤必须是 'POINT'、'SUN'、'SPOT' 或 'AREA'"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行删除灯光操作"""
        logger.info(f"删除灯光，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._delete_light, arguments)
        
    def _delete_light(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中删除灯光"""
        light_name = arguments.get("light_name")
        all_lights = arguments.get("all_lights", False)
        type_filter = arguments.get("type_filter")
        
        deleted_lights = []
        
        if all_lights:
            # 删除所有灯光或特定类型的灯光
            for obj in list(bpy.data.objects):
                if obj.type == 'LIGHT':
                    # 如果指定了类型过滤器，只删除匹配类型的灯光
                    if type_filter and obj.data.type != type_filter:
                        continue
                        
                    light_name = obj.name
                    light_type = obj.data.type
                    bpy.data.objects.remove(obj)
                    deleted_lights.append((light_name, light_type))
            
            if deleted_lights:
                type_text = f"{self._get_light_type_name(type_filter)} " if type_filter else ""
                text_content = self.create_text_content(f"已删除所有{type_text}灯光，共 {len(deleted_lights)} 个")
            else:
                type_text = f"{self._get_light_type_name(type_filter)}" if type_filter else ""
                text_content = self.create_text_content(f"场景中没有{type_text}灯光")
                
        elif light_name:
            # 删除特定灯光
            if light_name in bpy.data.objects:
                obj = bpy.data.objects[light_name]
                
                if obj.type == 'LIGHT':
                    light_type = obj.data.type
                    bpy.data.objects.remove(obj)
                    deleted_lights.append((light_name, light_type))
                    
                    text_content = self.create_text_content(f"已删除{self._get_light_type_name(light_type)}: {light_name}")
                else:
                    text_content = self.create_text_content(f"对象 '{light_name}' 不是灯光")
                    return self.create_result([text_content], is_error=True)
            else:
                text_content = self.create_text_content(f"找不到灯光: {light_name}")
                return self.create_result([text_content], is_error=True)
        
        # 返回结果
        return self.create_result([text_content])
        
    def _get_light_type_name(self, light_type: str) -> str:
        """获取灯光类型的中文名称"""
        if not light_type:
            return ""
            
        type_names = {
            "POINT": "点光源",
            "SUN": "太阳光",
            "SPOT": "聚光灯",
            "AREA": "面光源"
        }
        return type_names.get(light_type, light_type)


# 在导入时自动注册工具实例
register_tool(DeleteLightHandler())
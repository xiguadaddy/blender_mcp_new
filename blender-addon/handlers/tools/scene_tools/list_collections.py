"""
列出Blender场景中集合的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional, Tuple

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.ListCollections")

class ListCollectionsHandler(BaseToolHandler):
    """列出集合工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_list_collections"
        
    @property
    def description(self) -> Optional[str]:
        return "列出Blender场景中的集合及其内容"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "scene_name": {
                    "type": "string",
                    "title": "场景名称",
                    "description": "要列出集合的场景（默认为当前活动场景）"
                },
                "collection_name": {
                    "type": "string",
                    "title": "集合名称",
                    "description": "要查看的特定集合（如果为空则列出所有集合）"
                },
                "include_objects": {
                    "type": "boolean",
                    "title": "包含对象",
                    "description": "是否包含集合中的对象信息",
                    "default": True
                },
                "include_hierarchy": {
                    "type": "boolean",
                    "title": "包含层级",
                    "description": "是否以层级结构显示集合",
                    "default": True
                }
            }
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查场景名称（如果提供）
        scene_name = arguments.get("scene_name")
        if scene_name and scene_name not in bpy.data.scenes:
            return f"场景 '{scene_name}' 不存在"
            
        # 检查集合名称（如果提供）
        collection_name = arguments.get("collection_name")
        if collection_name and collection_name not in bpy.data.collections:
            return f"集合 '{collection_name}' 不存在"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行列出集合操作"""
        logger.info(f"列出集合，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._list_collections, arguments)
        
    def _list_collections(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中列出集合"""
        scene_name = arguments.get("scene_name")
        collection_name = arguments.get("collection_name")
        include_objects = arguments.get("include_objects", True)
        include_hierarchy = arguments.get("include_hierarchy", True)
        
        # 获取场景
        if scene_name:
            scene = bpy.data.scenes[scene_name]
        else:
            scene = bpy.context.scene
            scene_name = scene.name
        
        try:
            # 结果文本内容
            result_text = f"场景 '{scene_name}' 中的集合:\n\n"
            
            if collection_name:
                # 查看特定集合
                collection = bpy.data.collections[collection_name]
                result_text += self._format_collection_info(collection, include_objects, include_hierarchy, level=0)
            else:
                # 如果使用层级结构，从场景主集合开始递归
                if include_hierarchy:
                    result_text += "集合层级结构:\n"
                    result_text += self._format_collection_info(scene.collection, include_objects, include_hierarchy, level=0)
                else:
                    # 否则，平铺列出所有集合
                    collections = list(bpy.data.collections)
                    result_text += f"找到 {len(collections)} 个集合:\n\n"
                    
                    for collection in collections:
                        result_text += self._format_collection_info(collection, include_objects, include_hierarchy, level=0, flat=True)
            
            # 创建结果信息
            text_content = self.create_text_content(result_text)
            
            return self.create_result([text_content])
            
        except Exception as e:
            text_content = self.create_text_content(f"列出集合时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
    
    def _format_collection_info(self, collection, include_objects: bool, include_hierarchy: bool, level: int = 0, flat: bool = False) -> str:
        """格式化集合信息"""
        indent = "  " * level if not flat else ""
        result = f"{indent}• 集合: {collection.name} (包含 {len(collection.objects)} 个对象)\n"
        
        # 添加对象信息
        if include_objects and collection.objects:
            obj_indent = "  " * (level + 1) if not flat else "  "
            result += f"{obj_indent}对象: "
            
            # 列出前10个对象
            obj_names = [obj.name for obj in collection.objects]
            if len(obj_names) > 10:
                result += ", ".join(obj_names[:10]) + f" ... (共 {len(obj_names)} 个)\n"
            else:
                result += ", ".join(obj_names) + "\n"
        
        # 递归添加子集合信息
        if include_hierarchy and not flat:
            for child in collection.children:
                result += self._format_collection_info(child, include_objects, include_hierarchy, level + 1)
                
        return result


# 在导入时自动注册工具实例
register_tool(ListCollectionsHandler())
"""
创建Blender集合的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.CreateCollection")

class CreateCollectionHandler(BaseToolHandler):
    """创建集合工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_create_collection"
        
    @property
    def description(self) -> Optional[str]:
        return "在Blender场景中创建新的集合"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "title": "集合名称",
                    "description": "新集合的名称"
                },
                "parent_collection": {
                    "type": "string",
                    "title": "父集合",
                    "description": "将新集合添加到的父集合（如果为空则添加到场景集合）"
                },
                "objects": {
                    "type": "array",
                    "title": "对象",
                    "description": "要添加到集合的对象名称列表",
                    "items": {
                        "type": "string"
                    }
                },
                "scene_name": {
                    "type": "string",
                    "title": "场景名称",
                    "description": "要创建集合的场景（默认为当前活动场景）"
                }
            },
            "required": ["name"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查集合名称
        if not arguments.get("name"):
            return "必须提供集合名称"
            
        # 检查父集合（如果提供）
        parent_collection = arguments.get("parent_collection")
        if parent_collection and parent_collection not in bpy.data.collections:
            return f"父集合 '{parent_collection}' 不存在"
            
        # 检查对象名称（如果提供）
        objects = arguments.get("objects", [])
        if objects:
            missing_objects = [name for name in objects if name not in bpy.data.objects]
            if missing_objects:
                return f"找不到以下对象: {', '.join(missing_objects)}"
                
        # 检查场景名称（如果提供）
        scene_name = arguments.get("scene_name")
        if scene_name and scene_name not in bpy.data.scenes:
            return f"场景 '{scene_name}' 不存在"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行创建集合操作"""
        logger.info(f"创建集合，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._create_collection, arguments)
        
    def _create_collection(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中创建集合"""
        name = arguments.get("name")
        parent_collection_name = arguments.get("parent_collection")
        object_names = arguments.get("objects", [])
        scene_name = arguments.get("scene_name")
        
        # 获取场景
        if scene_name:
            scene = bpy.data.scenes[scene_name]
        else:
            scene = bpy.context.scene
            scene_name = scene.name
        
        # 确保该场景是活动场景
        original_scene = bpy.context.scene
        bpy.context.window.scene = scene
        
        try:
            # 检查集合是否已存在
            if name in bpy.data.collections:
                text_content = self.create_text_content(f"集合 '{name}' 已存在")
                return self.create_result([text_content], is_error=True)
            
            # 创建新集合
            new_collection = bpy.data.collections.new(name)
            
            # 将集合添加到父集合或场景集合
            if parent_collection_name:
                parent_collection = bpy.data.collections[parent_collection_name]
                parent_collection.children.link(new_collection)
                parent_info = f"父集合: {parent_collection_name}"
            else:
                scene.collection.children.link(new_collection)
                parent_info = "父集合: 场景集合"
            
            # 添加对象到集合
            added_objects = []
            for obj_name in object_names:
                obj = bpy.data.objects[obj_name]
                # 检查对象是否已在集合中
                if obj_name not in new_collection.objects:
                    new_collection.objects.link(obj)
                    added_objects.append(obj_name)
            
            # 创建结果信息
            if added_objects:
                objects_info = f"已添加 {len(added_objects)} 个对象: {', '.join(added_objects)}"
            else:
                objects_info = "没有添加对象"
                
            text_content = self.create_text_content(
                f"已创建集合: {name}\n"
                f"{parent_info}\n"
                f"{objects_info}"
            )
            
            return self.create_result([text_content])
            
        except Exception as e:
            text_content = self.create_text_content(f"创建集合时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
            
        finally:
            # 恢复原始场景
            bpy.context.window.scene = original_scene


# 在导入时自动注册工具实例
register_tool(CreateCollectionHandler())
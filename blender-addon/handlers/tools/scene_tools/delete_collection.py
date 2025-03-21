"""
删除Blender集合的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.DeleteCollection")

class DeleteCollectionHandler(BaseToolHandler):
    """删除集合工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_delete_collection"
        
    @property
    def description(self) -> Optional[str]:
        return "删除Blender场景中的集合"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "collection_name": {
                    "type": "string",
                    "title": "集合名称",
                    "description": "要删除的集合名称"
                },
                "recursive": {
                    "type": "boolean",
                    "title": "递归删除",
                    "description": "是否递归删除子集合",
                    "default": True
                },
                "delete_objects": {
                    "type": "boolean",
                    "title": "删除对象",
                    "description": "是否同时删除集合中的对象",
                    "default": False
                },
                "unlink_only": {
                    "type": "boolean",
                    "title": "仅取消链接",
                    "description": "是否仅取消集合链接而不删除集合数据",
                    "default": False
                }
            },
            "required": ["collection_name"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查集合名称
        collection_name = arguments.get("collection_name")
        if not collection_name:
            return "必须提供集合名称"
            
        # 检查集合是否存在
        if collection_name not in bpy.data.collections:
            return f"集合 '{collection_name}' 不存在"
            
        # 不能删除场景主集合
        for scene in bpy.data.scenes:
            if scene.collection.name == collection_name:
                return f"不能删除场景主集合 '{collection_name}'"
                
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行删除集合操作"""
        logger.info(f"删除集合，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._delete_collection, arguments)
        
    def _delete_collection(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中删除集合"""
        collection_name = arguments.get("collection_name")
        recursive = arguments.get("recursive", True)
        delete_objects = arguments.get("delete_objects", False)
        unlink_only = arguments.get("unlink_only", False)
        
        try:
            # 获取集合
            collection = bpy.data.collections[collection_name]
            
            # 记录统计信息
            deleted_collections = [collection_name]
            deleted_objects = []
            
            # 如果需要递归，先收集所有子集合
            child_collections = []
            if recursive:
                self._collect_child_collections(collection, child_collections)
                deleted_collections.extend([c.name for c in child_collections])
            
            # 如果需要删除对象，先收集所有对象
            if delete_objects:
                # 收集主集合中的对象
                for obj in collection.objects:
                    if obj.name not in deleted_objects:
                        deleted_objects.append(obj.name)
                
                # 收集子集合中的对象
                if recursive:
                    for child in child_collections:
                        for obj in child.objects:
                            if obj.name not in deleted_objects:
                                deleted_objects.append(obj.name)
            
            # 确定集合在场景中的父集合
            parent_collections = []
            for scene in bpy.data.scenes:
                for parent in scene.collection.children:
                    if parent.name == collection_name:
                        parent_collections.append(scene.collection)
                        break
            
            for parent in bpy.data.collections:
                for child in parent.children:
                    if child.name == collection_name:
                        parent_collections.append(parent)
            
            # 从父集合中取消链接
            for parent in parent_collections:
                parent.children.unlink(collection)
            
            # 执行删除操作
            if not unlink_only:
                # 删除对象（如果需要）
                if delete_objects:
                    for obj_name in deleted_objects:
                        obj = bpy.data.objects[obj_name]
                        bpy.data.objects.remove(obj)
                
                # 按照从子到父的顺序删除集合
                if recursive:
                    for child in reversed(child_collections):
                        bpy.data.collections.remove(child)
                
                # 删除主集合
                bpy.data.collections.remove(collection)
                operation = "已删除"
            else:
                operation = "已取消链接"
            
            # 创建结果信息
            result_parts = [f"{operation}集合: {collection_name}"]
            
            if recursive and len(child_collections) > 0:
                result_parts.append(f"递归{operation} {len(child_collections)} 个子集合")
                
            if delete_objects and len(deleted_objects) > 0:
                result_parts.append(f"删除了 {len(deleted_objects)} 个对象")
                
            text_content = self.create_text_content("\n".join(result_parts))
            
            return self.create_result([text_content])
            
        except Exception as e:
            text_content = self.create_text_content(f"删除集合时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
    
    def _collect_child_collections(self, parent_collection, result_list):
        """递归收集子集合"""
        for child in parent_collection.children:
            result_list.append(child)
            self._collect_child_collections(child, result_list)


# 在导入时自动注册工具实例
register_tool(DeleteCollectionHandler())
"""
删除Blender场景的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.DeleteScene")

class DeleteSceneHandler(BaseToolHandler):
    """删除场景工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_delete_scene"
        
    @property
    def description(self) -> Optional[str]:
        return "删除Blender场景"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "title": "场景名称",
                    "description": "要删除的场景名称"
                },
                "force": {
                    "type": "boolean",
                    "title": "强制删除",
                    "description": "如果是最后一个场景也强制删除（会创建新场景）",
                    "default": False
                }
            },
            "required": ["name"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查场景名称
        if not arguments.get("name"):
            return "必须提供场景名称"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行删除场景操作"""
        logger.info(f"删除场景，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._delete_scene, arguments)
        
    def _delete_scene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中删除场景"""
        name = arguments.get("name")
        force = arguments.get("force", False)
        
        # 检查场景是否存在
        if name not in bpy.data.scenes:
            text_content = self.create_text_content(f"场景 '{name}' 不存在")
            return self.create_result([text_content], is_error=True)
        
        # 如果只有一个场景且不是强制删除，则返回错误
        if len(bpy.data.scenes) <= 1 and not force:
            text_content = self.create_text_content("不能删除唯一的场景，请使用强制删除选项或先创建其他场景")
            return self.create_result([text_content], is_error=True)
        
        # 检查是否是当前活动场景
        is_active = (bpy.context.scene.name == name)
        
        # 如果只有一个场景且强制删除，先创建一个新场景
        if len(bpy.data.scenes) <= 1 and force:
            new_scene = bpy.data.scenes.new("新场景")
            bpy.context.window.scene = new_scene
        
        # 切换到其他场景（如果要删除的是当前活动场景）
        if is_active:
            for scene in bpy.data.scenes:
                if scene.name != name:
                    bpy.context.window.scene = scene
                    break
        
        # 获取要删除的场景
        scene_to_delete = bpy.data.scenes[name]
        
        # 删除场景
        bpy.data.scenes.remove(scene_to_delete)
        
        # 创建结果信息
        text_content = self.create_text_content(f"已删除场景: {name}")
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(DeleteSceneHandler())
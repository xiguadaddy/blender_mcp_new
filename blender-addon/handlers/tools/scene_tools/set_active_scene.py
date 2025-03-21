"""
设置活动Blender场景的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.SetActiveScene")

class SetActiveSceneHandler(BaseToolHandler):
    """设置活动场景工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_set_active_scene"
        
    @property
    def description(self) -> Optional[str]:
        return "设置当前活动的Blender场景"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "title": "场景名称",
                    "description": "要设为活动的场景名称"
                },
                "list_scenes": {
                    "type": "boolean",
                    "title": "列出所有场景",
                    "description": "是否列出所有场景",
                    "default": False
                }
            }
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 如果既没有提供场景名称，也没有设置列出场景标志，则返回错误
        if not arguments.get("name") and not arguments.get("list_scenes"):
            return "需要提供场景名称或设置列出场景标志"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行设置活动场景操作"""
        logger.info(f"设置活动场景，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._set_active_scene, arguments)
        
    def _set_active_scene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中设置活动场景"""
        scene_name = arguments.get("name")
        list_scenes = arguments.get("list_scenes", False)
        
        # 处理列出所有场景的请求
        if list_scenes:
            scenes = []
            
            for scene in bpy.data.scenes:
                is_active = (bpy.context.scene == scene)
                scenes.append({
                    "name": scene.name,
                    "is_active": is_active,
                    "objects_count": len(scene.objects)
                })
                
            # 构建场景列表文本
            scenes_list = "\n".join([
                f"- {s['name']} {'(活动)' if s['is_active'] else ''} (对象数: {s['objects_count']})"
                for s in scenes
            ])
            
            text_content = self.create_text_content(f"场景列表 ({len(scenes)} 个):\n{scenes_list}")
            return self.create_result([text_content])
        
        # 处理设置活动场景的请求
        if scene_name:
            # 检查场景是否存在
            if scene_name not in bpy.data.scenes:
                text_content = self.create_text_content(f"场景 '{scene_name}' 不存在")
                return self.create_result([text_content], is_error=True)
                
            # 获取场景
            scene = bpy.data.scenes[scene_name]
            
            # 设置为活动场景
            bpy.context.window.scene = scene
            
            text_content = self.create_text_content(f"已将场景 '{scene_name}' 设为活动场景")
            return self.create_result([text_content])
        
        # 如果没有提供场景名称也没有要求列出场景，返回当前活动场景信息
        current_scene = bpy.context.scene
        text_content = self.create_text_content(f"当前活动场景是: {current_scene.name}")
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(SetActiveSceneHandler())
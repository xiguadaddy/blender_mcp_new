"""
创建Blender场景的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.CreateScene")

class CreateSceneHandler(BaseToolHandler):
    """创建场景工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_create_scene"
        
    @property
    def description(self) -> Optional[str]:
        return "创建新的Blender场景"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "title": "场景名称",
                    "description": "新场景的名称"
                },
                "set_active": {
                    "type": "boolean",
                    "title": "设为活动场景",
                    "description": "是否将新场景设为活动场景",
                    "default": True
                },
                "empty": {
                    "type": "boolean",
                    "title": "创建空场景",
                    "description": "是否创建空白场景（不包含默认物体）",
                    "default": False
                },
                "copy_current": {
                    "type": "boolean",
                    "title": "复制当前场景",
                    "description": "是否复制当前场景的内容",
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
            
        # 创建空场景和复制当前场景不能同时为真
        if arguments.get("empty") and arguments.get("copy_current"):
            return "不能同时设置'创建空场景'和'复制当前场景'"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行创建场景操作"""
        logger.info(f"创建场景，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._create_scene, arguments)
        
    def _create_scene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中创建场景"""
        name = arguments.get("name")
        set_active = arguments.get("set_active", True)
        empty = arguments.get("empty", False)
        copy_current = arguments.get("copy_current", False)
        
        # 检查场景名称是否已存在
        if name in bpy.data.scenes:
            text_content = self.create_text_content(f"场景 '{name}' 已存在")
            return self.create_result([text_content], is_error=True)
        
        # 创建新场景
        if copy_current:
            # 复制当前场景
            new_scene = bpy.data.scenes.new(name)
            current_scene = bpy.context.scene
            
            # 复制场景设置
            new_scene.render.resolution_x = current_scene.render.resolution_x
            new_scene.render.resolution_y = current_scene.render.resolution_y
            new_scene.render.resolution_percentage = current_scene.render.resolution_percentage
            new_scene.render.fps = current_scene.render.fps
            new_scene.frame_start = current_scene.frame_start
            new_scene.frame_end = current_scene.frame_end
            
            # 复制世界设置
            if current_scene.world:
                new_scene.world = current_scene.world
            
            # 复制所有对象
            for obj in current_scene.objects:
                new_scene.collection.objects.link(obj)
            
            desc = "（复制当前场景）"
        else:
            # 创建新场景
            new_scene = bpy.data.scenes.new(name)
            
            if empty:
                # 如果需要创建空场景，移除所有默认对象
                for obj in new_scene.objects:
                    bpy.data.objects.remove(obj)
                desc = "（空场景）"
            else:
                desc = "（带默认物体）"
        
        # 设置为活动场景
        if set_active:
            bpy.context.window.scene = new_scene
        
        # 创建结果信息
        text_content = self.create_text_content(f"已创建场景: {new_scene.name} {desc}")
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(CreateSceneHandler())
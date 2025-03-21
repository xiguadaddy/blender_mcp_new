"""
控制Blender动画播放的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.PlayAnimation")

class PlayAnimationHandler(BaseToolHandler):
    """播放动画工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_play_animation"
        
    @property
    def description(self) -> Optional[str]:
        return "控制Blender动画的播放、暂停和停止"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "title": "动作",
                    "description": "要执行的动画动作",
                    "enum": ["play", "pause", "stop", "toggle", "status"],
                    "default": "play"
                },
                "start_frame": {
                    "type": "integer",
                    "title": "开始帧",
                    "description": "从指定帧开始播放（仅当动作为play时有效）"
                },
                "end_frame": {
                    "type": "integer",
                    "title": "结束帧",
                    "description": "播放到指定帧（仅当动作为play时有效）"
                },
                "scene_name": {
                    "type": "string",
                    "title": "场景名称",
                    "description": "要控制动画的场景（默认为当前活动场景）"
                }
            }
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查动作类型
        action = arguments.get("action", "play")
        valid_actions = ["play", "pause", "stop", "toggle", "status"]
        if action not in valid_actions:
            return f"无效的动作: {action}，有效值: {', '.join(valid_actions)}"
            
        # 检查场景名称（如果提供）
        scene_name = arguments.get("scene_name")
        if scene_name and scene_name not in bpy.data.scenes:
            return f"场景 '{scene_name}' 不存在"
            
        # 检查开始帧和结束帧
        start_frame = arguments.get("start_frame")
        end_frame = arguments.get("end_frame")
        
        if start_frame is not None and not isinstance(start_frame, int):
            return "开始帧必须是整数"
            
        if end_frame is not None and not isinstance(end_frame, int):
            return "结束帧必须是整数"
            
        if start_frame is not None and end_frame is not None and start_frame > end_frame:
            return "开始帧必须小于或等于结束帧"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行播放动画操作"""
        logger.info(f"播放动画，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._play_animation, arguments)
        
    def _play_animation(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中控制动画播放"""
        action = arguments.get("action", "play")
        start_frame = arguments.get("start_frame")
        end_frame = arguments.get("end_frame")
        scene_name = arguments.get("scene_name")
        
        # 获取场景
        if scene_name:
            scene = bpy.data.scenes[scene_name]
        else:
            scene = bpy.context.scene
            scene_name = scene.name
        
        # 如果是'status'动作，只返回当前状态
        if action == "status":
            is_playing = bpy.context.screen.is_animation_playing if hasattr(bpy.context.screen, "is_animation_playing") else False
            text_content = self.create_text_content(
                f"场景 '{scene_name}' 的动画状态:\n"
                f"当前帧: {scene.frame_current}\n"
                f"帧范围: {scene.frame_start} - {scene.frame_end}\n"
                f"播放状态: {'播放中' if is_playing else '已停止'}"
            )
            return self.create_result([text_content])
        
        # 设置开始帧和结束帧（如果提供）
        if start_frame is not None:
            scene.frame_start = start_frame
            
        if end_frame is not None:
            scene.frame_end = end_frame
        
        # 执行对应的动画控制操作
        if action == "play":
            # 如果指定了开始帧，先跳转到开始帧
            if start_frame is not None:
                scene.frame_set(start_frame)
            
            # 开始播放动画
            if not bpy.context.screen.is_animation_playing:
                bpy.ops.screen.animation_play()
                status = "已开始播放"
            else:
                status = "动画已在播放中"
        
        elif action == "pause":
            # 暂停动画
            if bpy.context.screen.is_animation_playing:
                bpy.ops.screen.animation_play()
                status = "已暂停播放"
            else:
                status = "动画已经暂停"
        
        elif action == "stop":
            # 停止动画并回到起始帧
            if bpy.context.screen.is_animation_playing:
                bpy.ops.screen.animation_play()
            
            scene.frame_set(scene.frame_start)
            status = "已停止播放并回到起始帧"
        
        elif action == "toggle":
            # 切换播放状态
            bpy.ops.screen.animation_play()
            if bpy.context.screen.is_animation_playing:
                status = "已开始播放"
            else:
                status = "已暂停播放"
        
        # 创建结果信息
        range_info = ""
        if start_frame is not None or end_frame is not None:
            range_info = f"\n帧范围: {scene.frame_start} - {scene.frame_end}"
            
        text_content = self.create_text_content(
            f"场景 '{scene_name}' 的动画控制:\n{status}{range_info}"
        )
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(PlayAnimationHandler())
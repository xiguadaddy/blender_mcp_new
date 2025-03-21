"""
获取Blender场景帧范围的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.GetFrameRange")

class GetFrameRangeHandler(BaseToolHandler):
    """获取帧范围工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_get_frame_range"
        
    @property
    def description(self) -> Optional[str]:
        return "获取场景的动画帧范围和帧率信息"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "scene_name": {
                    "type": "string",
                    "title": "场景名称",
                    "description": "要获取帧范围的场景（默认为当前活动场景）"
                }
            }
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查场景名称（如果提供）
        scene_name = arguments.get("scene_name")
        if scene_name and scene_name not in bpy.data.scenes:
            return f"场景 '{scene_name}' 不存在"
        
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行获取帧范围操作"""
        logger.info(f"获取帧范围，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._get_frame_range, arguments)
        
    def _get_frame_range(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中获取帧范围"""
        scene_name = arguments.get("scene_name")
        
        # 获取场景
        if scene_name:
            scene = bpy.data.scenes[scene_name]
        else:
            scene = bpy.context.scene
            scene_name = scene.name
        
        try:
            # 获取帧范围和相关信息
            info = {
                "scene_name": scene_name,
                "frame_start": scene.frame_start,
                "frame_end": scene.frame_end,
                "frame_current": scene.frame_current,
                "frame_step": scene.frame_step,
                "fps": scene.render.fps,
                "fps_base": scene.render.fps_base,
                "duration_seconds": (scene.frame_end - scene.frame_start + 1) / (scene.render.fps / scene.render.fps_base),
                "has_animation": False
            }
            
            # 检查场景中是否有动画
            animated_objects = []
            for obj in scene.objects:
                if obj.animation_data and obj.animation_data.action:
                    animated_objects.append(obj.name)
                    info["has_animation"] = True
            
            # 格式化信息文本
            info_text = (
                f"场景 '{scene_name}' 的帧范围信息:\n"
                f"开始帧: {info['frame_start']}\n"
                f"结束帧: {info['frame_end']}\n"
                f"当前帧: {info['frame_current']}\n"
                f"帧步长: {info['frame_step']}\n"
                f"帧率: {info['fps']}/{info['fps_base']} = {info['fps'] / info['fps_base']} FPS\n"
                f"持续时间: {info['duration_seconds']:.2f} 秒"
            )
            
            if animated_objects:
                if len(animated_objects) > 10:
                    object_list = ", ".join(animated_objects[:10]) + f"... (共 {len(animated_objects)} 个)"
                else:
                    object_list = ", ".join(animated_objects)
                info_text += f"\n动画对象: {object_list}"
            else:
                info_text += "\n场景中没有动画对象"
                
            text_content = self.create_text_content(info_text)
            
            # 创建结果
            return self.create_result([text_content])
            
        except Exception as e:
            text_content = self.create_text_content(f"获取帧范围信息时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)


# 在导入时自动注册工具实例
register_tool(GetFrameRangeHandler())
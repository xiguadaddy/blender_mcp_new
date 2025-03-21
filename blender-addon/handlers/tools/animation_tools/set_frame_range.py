"""
设置场景帧范围的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.SetFrameRange")

class SetFrameRangeHandler(BaseToolHandler):
    """设置帧范围工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_set_frame_range"
        
    @property
    def description(self) -> Optional[str]:
        return "设置场景的动画帧范围和帧率"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "scene_name": {
                    "type": "string",
                    "title": "场景名称",
                    "description": "要设置帧范围的场景（默认为当前活动场景）"
                },
                "frame_start": {
                    "type": "integer",
                    "title": "开始帧",
                    "description": "动画的开始帧"
                },
                "frame_end": {
                    "type": "integer",
                    "title": "结束帧",
                    "description": "动画的结束帧"
                },
                "frame_step": {
                    "type": "integer",
                    "title": "帧步长",
                    "description": "动画的帧步长",
                    "minimum": 1
                },
                "fps": {
                    "type": "number",
                    "title": "帧率",
                    "description": "动画的帧率（每秒帧数）",
                    "minimum": 1
                },
                "fps_base": {
                    "type": "number",
                    "title": "基础帧率",
                    "description": "用于计算实际帧率的基础值（fps/fps_base）",
                    "default": 1.0
                },
                "get_only": {
                    "type": "boolean",
                    "title": "仅获取",
                    "description": "是否仅获取当前帧范围而不修改",
                    "default": False
                },
                "update_scene_duration": {
                    "type": "boolean",
                    "title": "更新场景时长",
                    "description": "是否同时更新场景渲染设置中的时长",
                    "default": False
                }
            }
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查场景名称（如果提供）
        scene_name = arguments.get("scene_name")
        if scene_name and scene_name not in bpy.data.scenes:
            return f"场景 '{scene_name}' 不存在"
            
        # 检查开始帧、结束帧和帧步长
        frame_start = arguments.get("frame_start")
        frame_end = arguments.get("frame_end")
        
        if frame_start is not None and not isinstance(frame_start, int):
            return "开始帧必须是整数"
            
        if frame_end is not None and not isinstance(frame_end, int):
            return "结束帧必须是整数"
            
        if frame_start is not None and frame_end is not None and frame_start > frame_end:
            return "开始帧必须小于或等于结束帧"
            
        frame_step = arguments.get("frame_step")
        if frame_step is not None and (not isinstance(frame_step, int) or frame_step < 1):
            return "帧步长必须是大于或等于1的整数"
            
        # 检查帧率
        fps = arguments.get("fps")
        if fps is not None and (not isinstance(fps, (int, float)) or fps < 1):
            return "帧率必须是大于或等于1的数字"
            
        # 检查基础帧率
        fps_base = arguments.get("fps_base")
        if fps_base is not None and (not isinstance(fps_base, (int, float)) or fps_base <= 0):
            return "基础帧率必须是大于0的数字"
            
        # 如果是仅获取模式，不需要参数也可以
        if arguments.get("get_only", False):
            return None
            
        # 如果不是仅获取模式，需要至少有一个参数
        if frame_start is None and frame_end is None and frame_step is None and fps is None:
            return "必须提供至少一个要修改的参数"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行设置帧范围操作"""
        logger.info(f"设置帧范围，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._set_frame_range, arguments)
        
    def _set_frame_range(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中设置帧范围"""
        scene_name = arguments.get("scene_name")
        frame_start = arguments.get("frame_start")
        frame_end = arguments.get("frame_end")
        frame_step = arguments.get("frame_step")
        fps = arguments.get("fps")
        fps_base = arguments.get("fps_base", 1.0)
        get_only = arguments.get("get_only", False)
        update_scene_duration = arguments.get("update_scene_duration", False)
        
        # 获取场景
        if scene_name:
            scene = bpy.data.scenes[scene_name]
        else:
            scene = bpy.context.scene
            scene_name = scene.name
        
        # 获取当前帧范围信息
        current_info = {
            "scene_name": scene_name,
            "frame_start": scene.frame_start,
            "frame_end": scene.frame_end,
            "frame_step": scene.frame_step,
            "frame_current": scene.frame_current,
            "fps": scene.render.fps,
            "fps_base": scene.render.fps_base
        }
        
        # 如果是仅获取模式，直接返回当前信息
        if get_only:
            info_text = (
                f"场景 '{scene_name}' 的帧范围信息:\n"
                f"开始帧: {current_info['frame_start']}\n"
                f"结束帧: {current_info['frame_end']}\n"
                f"当前帧: {current_info['frame_current']}\n"
                f"帧步长: {current_info['frame_step']}\n"
                f"帧率: {current_info['fps']}/{current_info['fps_base']} = {current_info['fps'] / current_info['fps_base']} FPS"
            )
            text_content = self.create_text_content(info_text)
            return self.create_result([text_content])
        
        # 修改帧范围和帧率
        try:
            # 跟踪修改的属性
            modified_props = []
            
            if frame_start is not None:
                scene.frame_start = frame_start
                modified_props.append(f"开始帧: {frame_start}")
                
            if frame_end is not None:
                scene.frame_end = frame_end
                modified_props.append(f"结束帧: {frame_end}")
                
            if frame_step is not None:
                scene.frame_step = frame_step
                modified_props.append(f"帧步长: {frame_step}")
                
            if fps is not None:
                scene.render.fps = fps
                scene.render.fps_base = fps_base
                modified_props.append(f"帧率: {fps}/{fps_base} = {fps / fps_base} FPS")
            
            # 创建结果信息
            if modified_props:
                text_content = self.create_text_content(
                    f"已设置场景 '{scene_name}' 的:\n" + "\n".join(modified_props)
                )
            else:
                text_content = self.create_text_content(f"未修改场景 '{scene_name}' 的任何帧范围属性")
                
            # 如果更新场景时长，更新场景渲染设置中的时长
            if update_scene_duration:
                scene.render.duration = (frame_end - frame_start + 1) / fps
            
        except Exception as e:
            text_content = self.create_text_content(f"设置帧范围时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(SetFrameRangeHandler())
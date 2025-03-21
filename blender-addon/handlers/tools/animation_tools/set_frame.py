"""
设置Blender时间轴当前帧的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.SetFrame")

class SetFrameHandler(BaseToolHandler):
    """设置当前帧工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_set_frame"
        
    @property
    def description(self) -> Optional[str]:
        return "设置Blender动画的当前帧"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "frame": {
                    "type": "integer",
                    "title": "帧数",
                    "description": "要设置的当前帧"
                },
                "scene_name": {
                    "type": "string",
                    "title": "场景名称",
                    "description": "要设置当前帧的场景（默认为当前活动场景）"
                },
                "adjust_frame_range": {
                    "type": "boolean",
                    "title": "调整帧范围",
                    "description": "如果当前帧超出帧范围，是否自动调整帧范围",
                    "default": False
                },
                "set_start_frame": {
                    "type": "integer",
                    "title": "设置开始帧",
                    "description": "同时设置场景的开始帧"
                },
                "set_end_frame": {
                    "type": "integer",
                    "title": "设置结束帧",
                    "description": "同时设置场景的结束帧"
                }
            },
            "required": ["frame"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查帧数
        frame = arguments.get("frame")
        if frame is None:
            return "必须提供帧数"
        if not isinstance(frame, int):
            return "帧数必须是整数"
            
        # 检查场景名称（如果提供）
        scene_name = arguments.get("scene_name")
        if scene_name and scene_name not in bpy.data.scenes:
            return f"场景 '{scene_name}' 不存在"
            
        # 检查开始帧和结束帧
        start_frame = arguments.get("set_start_frame")
        end_frame = arguments.get("set_end_frame")
        
        if start_frame is not None and not isinstance(start_frame, int):
            return "开始帧必须是整数"
            
        if end_frame is not None and not isinstance(end_frame, int):
            return "结束帧必须是整数"
            
        if start_frame is not None and end_frame is not None and start_frame > end_frame:
            return "开始帧必须小于或等于结束帧"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行设置当前帧操作"""
        logger.info(f"设置当前帧，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._set_frame, arguments)
        
    def _set_frame(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中设置当前帧"""
        frame = arguments.get("frame")
        scene_name = arguments.get("scene_name")
        adjust_frame_range = arguments.get("adjust_frame_range", False)
        set_start_frame = arguments.get("set_start_frame")
        set_end_frame = arguments.get("set_end_frame")
        
        # 获取场景
        if scene_name:
            scene = bpy.data.scenes[scene_name]
        else:
            scene = bpy.context.scene
            scene_name = scene.name
            
        # 设置当前帧
        scene.frame_set(frame)
        
        # 记录修改内容
        changes = [f"当前帧: {frame}"]
        
        # 调整帧范围（如果需要）
        if adjust_frame_range:
            if frame < scene.frame_start:
                scene.frame_start = frame
                changes.append(f"开始帧: {frame}")
            if frame > scene.frame_end:
                scene.frame_end = frame
                changes.append(f"结束帧: {frame}")
        
        # 设置开始帧和结束帧（如果提供）
        if set_start_frame is not None:
            scene.frame_start = set_start_frame
            changes.append(f"开始帧: {set_start_frame}")
            
        if set_end_frame is not None:
            scene.frame_end = set_end_frame
            changes.append(f"结束帧: {set_end_frame}")
        
        # 创建结果信息
        text_content = self.create_text_content(
            f"已设置场景 '{scene_name}' 的:\n" + "\n".join(changes)
        )
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(SetFrameHandler())
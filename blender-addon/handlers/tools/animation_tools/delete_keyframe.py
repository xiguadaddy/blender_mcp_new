"""
删除关键帧的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.DeleteKeyframe")

class DeleteKeyframeHandler(BaseToolHandler):
    """删除关键帧工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_delete_keyframe"
        
    @property
    def description(self) -> Optional[str]:
        return "删除对象属性的关键帧"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "要删除关键帧的对象名称"
                },
                "frame": {
                    "type": "integer",
                    "title": "帧数",
                    "description": "要删除的关键帧的帧数（如果未指定，则删除当前帧的关键帧）"
                },
                "data_path": {
                    "type": "string",
                    "title": "数据路径",
                    "description": "要删除关键帧的属性路径，如'location'或'rotation_euler'"
                },
                "index": {
                    "type": "integer",
                    "title": "索引",
                    "description": "要删除关键帧的数组属性的索引（-1表示整个数组）",
                    "default": -1
                },
                "all_keyframes": {
                    "type": "boolean",
                    "title": "所有关键帧",
                    "description": "是否删除指定属性的所有关键帧",
                    "default": False
                }
            },
            "required": ["object_name"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查对象名称
        object_name = arguments.get("object_name")
        if not object_name:
            return "必须提供对象名称"
            
        # 检查对象是否存在
        if object_name not in bpy.data.objects:
            return f"找不到对象: {object_name}"
            
        # 如果不是删除所有关键帧，就需要数据路径
        if not arguments.get("all_keyframes") and not arguments.get("data_path"):
            return "必须提供数据路径或设置删除所有关键帧"
            
        # 检查帧数是否是整数
        frame = arguments.get("frame")
        if frame is not None and not isinstance(frame, int):
            return "帧数必须是整数"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行删除关键帧操作"""
        logger.info(f"删除关键帧，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._delete_keyframe, arguments)
        
    def _delete_keyframe(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中删除关键帧"""
        object_name = arguments.get("object_name")
        frame = arguments.get("frame")
        data_path = arguments.get("data_path")
        index = arguments.get("index", -1)
        all_keyframes = arguments.get("all_keyframes", False)
        
        # 获取对象
        obj = bpy.data.objects[object_name]
        
        # 如果未指定帧数，使用当前帧
        if frame is None:
            frame = bpy.context.scene.frame_current
        
        # 确保对象有动画数据
        if not obj.animation_data or not obj.animation_data.action:
            text_content = self.create_text_content(f"对象 '{object_name}' 没有动画数据")
            return self.create_result([text_content], is_error=True)
        
        try:
            deleted_count = 0
            
            if all_keyframes:
                # 删除所有关键帧
                if data_path:
                    # 删除特定属性的所有关键帧
                    fcurves_to_remove = []
                    for fcurve in obj.animation_data.action.fcurves:
                        if fcurve.data_path == data_path:
                            if index == -1 or fcurve.array_index == index:
                                fcurves_to_remove.append(fcurve)
                    
                    # 删除匹配的FCurves
                    for fcurve in fcurves_to_remove:
                        obj.animation_data.action.fcurves.remove(fcurve)
                        deleted_count += len(fcurve.keyframe_points)
                    
                    description = f"已删除对象 '{object_name}' 的数据路径 '{data_path}' 的所有关键帧，共 {deleted_count} 个"
                else:
                    # 删除对象的所有关键帧（清除整个动作）
                    deleted_count = sum(len(fcurve.keyframe_points) for fcurve in obj.animation_data.action.fcurves)
                    obj.animation_data.action = None
                    description = f"已删除对象 '{object_name}' 的所有关键帧，共 {deleted_count} 个"
            else:
                # 删除特定帧的关键帧
                result = obj.keyframe_delete(data_path=data_path, index=index, frame=frame)
                if result:
                    deleted_count = 1
                    description = f"已删除对象 '{object_name}' 在帧 {frame} 的数据路径 '{data_path}' 的关键帧"
                else:
                    description = f"未找到对象 '{object_name}' 在帧 {frame} 的数据路径 '{data_path}' 的关键帧"
            
            text_content = self.create_text_content(description)
            
        except Exception as e:
            text_content = self.create_text_content(f"删除关键帧时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(DeleteKeyframeHandler())
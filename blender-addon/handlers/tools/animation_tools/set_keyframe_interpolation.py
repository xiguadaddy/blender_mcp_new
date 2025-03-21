"""
设置关键帧插值方式的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.SetKeyframeInterpolation")

class SetKeyframeInterpolationHandler(BaseToolHandler):
    """设置关键帧插值工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_set_keyframe_interpolation"
        
    @property
    def description(self) -> Optional[str]:
        return "设置对象关键帧的插值和缓动方式"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "要设置关键帧插值的对象名称"
                },
                "data_path": {
                    "type": "string",
                    "title": "数据路径",
                    "description": "要设置插值的数据路径（如果为空则应用于所有FCurves）"
                },
                "index": {
                    "type": "integer",
                    "title": "索引",
                    "description": "数组属性的索引（-1表示所有索引）",
                    "default": -1
                },
                "interpolation": {
                    "type": "string",
                    "title": "插值方式",
                    "description": "关键帧的插值方式",
                    "enum": ["CONSTANT", "LINEAR", "BEZIER", "BOUNCE", "ELASTIC", "BACK", "QUAD", "CUBIC", "QUART", "QUINT", "SINE", "EXPO", "CIRC"],
                    "default": "BEZIER"
                },
                "easing": {
                    "type": "string",
                    "title": "缓动方式",
                    "description": "关键帧的缓动方式",
                    "enum": ["AUTO", "EASE_IN", "EASE_OUT", "EASE_IN_OUT"],
                    "default": "AUTO"
                },
                "frame_range": {
                    "type": "array",
                    "title": "帧范围",
                    "description": "要设置插值的帧范围[开始帧, 结束帧]（如果为空则应用于所有帧）",
                    "items": {
                        "type": "integer"
                    },
                    "minItems": 2,
                    "maxItems": 2
                }
            },
            "required": ["object_name", "interpolation"]
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
            
        # 检查插值方式
        interpolation = arguments.get("interpolation")
        valid_interpolations = ["CONSTANT", "LINEAR", "BEZIER", "BOUNCE", "ELASTIC", "BACK", "QUAD", "CUBIC", "QUART", "QUINT", "SINE", "EXPO", "CIRC"]
        if interpolation not in valid_interpolations:
            return f"无效的插值方式，有效值: {', '.join(valid_interpolations)}"
            
        # 检查缓动方式
        easing = arguments.get("easing", "AUTO")
        valid_easings = ["AUTO", "EASE_IN", "EASE_OUT", "EASE_IN_OUT"]
        if easing not in valid_easings:
            return f"无效的缓动方式，有效值: {', '.join(valid_easings)}"
            
        # 检查帧范围
        frame_range = arguments.get("frame_range")
        if frame_range:
            if not isinstance(frame_range, list) or len(frame_range) != 2:
                return "帧范围必须是包含两个整数的数组[开始帧, 结束帧]"
            
            if not all(isinstance(frame, int) for frame in frame_range):
                return "帧范围的值必须是整数"
                
            if frame_range[0] > frame_range[1]:
                return "帧范围的开始帧必须小于或等于结束帧"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行设置关键帧插值操作"""
        logger.info(f"设置关键帧插值，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._set_keyframe_interpolation, arguments)
        
    def _set_keyframe_interpolation(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中设置关键帧插值"""
        object_name = arguments.get("object_name")
        data_path = arguments.get("data_path")
        index = arguments.get("index", -1)
        interpolation = arguments.get("interpolation")
        easing = arguments.get("easing", "AUTO")
        frame_range = arguments.get("frame_range")
        
        # 获取对象
        obj = bpy.data.objects[object_name]
        
        # 如果对象没有动画数据或动作，则返回相应信息
        if not obj.animation_data or not obj.animation_data.action:
            text_content = self.create_text_content(f"对象 '{object_name}' 没有动画数据或动作")
            return self.create_result([text_content], is_error=True)
        
        try:
            # 计算帧范围（如果提供）
            min_frame = frame_range[0] if frame_range else float("-inf")
            max_frame = frame_range[1] if frame_range else float("inf")
            
            # 跟踪修改的关键帧
            modified_fcurves = 0
            modified_keyframes = 0
            
            # 处理所有匹配的FCurves
            for fcurve in obj.animation_data.action.fcurves:
                # 检查数据路径和索引是否匹配
                if (not data_path or fcurve.data_path == data_path) and (index == -1 or fcurve.array_index == index):
                    # 对于每个关键帧点设置插值方式
                    for keyframe in fcurve.keyframe_points:
                        # 检查帧是否在指定范围内
                        if min_frame <= keyframe.co[0] <= max_frame:
                            keyframe.interpolation = interpolation
                            
                            # 对于贝塞尔插值，还可以设置缓动方式
                            if interpolation == 'BEZIER':
                                keyframe.easing = easing
                                
                            modified_keyframes += 1
                            
                    # 如果该FCurve中有关键帧被修改，增加计数
                    if modified_keyframes > 0:
                        modified_fcurves += 1
            
            # 创建结果信息
            if modified_keyframes > 0:
                text_content = self.create_text_content(
                    f"已修改对象 '{object_name}' 的 {modified_fcurves} 条FCurve中的 {modified_keyframes} 个关键帧\n"
                    f"插值方式: {interpolation}" + (f", 缓动方式: {easing}" if interpolation == 'BEZIER' else "")
                )
            else:
                text_content = self.create_text_content(f"未找到要修改的关键帧")
                
        except Exception as e:
            text_content = self.create_text_content(f"设置关键帧插值时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(SetKeyframeInterpolationHandler())
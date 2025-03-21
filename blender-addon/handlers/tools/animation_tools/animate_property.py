"""
为对象属性创建动画的工具
"""

import bpy
from ..registry import register_tool
import logging
import math
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.AnimateProperty")

class AnimatePropertyHandler(BaseToolHandler):
    """属性动画工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_animate_property"
        
    @property
    def description(self) -> Optional[str]:
        return "自动为对象属性创建关键帧动画"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "要为其创建动画的对象名称"
                },
                "data_path": {
                    "type": "string",
                    "title": "数据路径",
                    "description": "要为其创建动画的属性路径，如'location'或'rotation_euler'"
                },
                "index": {
                    "type": "integer",
                    "title": "索引",
                    "description": "要为其创建动画的数组属性的索引（-1表示整个数组）",
                    "default": -1
                },
                "frame_start": {
                    "type": "integer",
                    "title": "开始帧",
                    "description": "动画开始帧",
                    "default": 1
                },
                "frame_end": {
                    "type": "integer",
                    "title": "结束帧",
                    "description": "动画结束帧",
                    "default": 100
                },
                "animation_type": {
                    "type": "string",
                    "title": "动画类型",
                    "description": "要创建的动画类型",
                    "enum": ["linear", "sine", "bounce", "elastic", "back", "quadratic", "cubic", "back_forth"],
                    "default": "linear"
                },
                "start_value": {
                    "type": "array",
                    "title": "起始值",
                    "description": "动画的起始值",
                    "items": {
                        "type": "number"
                    }
                },
                "end_value": {
                    "type": "array",
                    "title": "结束值",
                    "description": "动画的结束值",
                    "items": {
                        "type": "number"
                    }
                },
                "amplitude": {
                    "type": "number",
                    "title": "振幅",
                    "description": "动画的振幅（用于sine等周期性动画）",
                    "default": 1.0
                },
                "frequency": {
                    "type": "number",
                    "title": "频率",
                    "description": "动画的频率（用于sine等周期性动画）",
                    "default": 0.1
                },
                "keyframe_count": {
                    "type": "integer",
                    "title": "关键帧数量",
                    "description": "要生成的关键帧数量",
                    "default": 10
                }
            },
            "required": ["object_name", "data_path", "start_value", "end_value"]
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
            
        # 检查数据路径
        data_path = arguments.get("data_path")
        if not data_path:
            return "必须提供数据路径"
            
        # 检查开始值和结束值
        start_value = arguments.get("start_value")
        if start_value is None:
            return "必须提供起始值"
            
        end_value = arguments.get("end_value")
        if end_value is None:
            return "必须提供结束值"
            
        # 检查起始值和结束值的长度是否匹配
        if len(start_value) != len(end_value):
            return "起始值和结束值的长度必须相同"
            
        # 检查关键帧数量
        keyframe_count = arguments.get("keyframe_count", 10)
        if not isinstance(keyframe_count, int) or keyframe_count < 2:
            return "关键帧数量必须是大于或等于2的整数"
            
        # 检查动画类型
        animation_type = arguments.get("animation_type", "linear")
        valid_types = ["linear", "sine", "bounce", "elastic", "back", "quadratic", "cubic", "back_forth"]
        if animation_type not in valid_types:
            return f"无效的动画类型: {animation_type}，有效类型: {', '.join(valid_types)}"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行创建属性动画操作"""
        logger.info(f"创建属性动画，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._animate_property, arguments)
        
    def _animate_property(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中创建属性动画"""
        object_name = arguments.get("object_name")
        data_path = arguments.get("data_path")
        index = arguments.get("index", -1)
        frame_start = arguments.get("frame_start", 1)
        frame_end = arguments.get("frame_end", 100)
        animation_type = arguments.get("animation_type", "linear")
        start_value = arguments.get("start_value")
        end_value = arguments.get("end_value")
        amplitude = arguments.get("amplitude", 1.0)
        frequency = arguments.get("frequency", 0.1)
        keyframe_count = arguments.get("keyframe_count", 10)
        
        # 获取对象
        obj = bpy.data.objects[object_name]
        
        # 验证数据路径是否有效
        try:
            if "." in data_path:
                # 处理嵌套属性
                path_parts = data_path.split(".")
                target = obj
                for part in path_parts[:-1]:
                    if "[" in part and "]" in part:
                        # 处理列表/字典访问
                        base_part = part.split("[")[0]
                        key = part.split("[")[1].split("]")[0].strip('"\'')
                        target = getattr(target, base_part)[key]
                    else:
                        target = getattr(target, part)
                final_attr = path_parts[-1]
                attr_value = getattr(target, final_attr)
            else:
                attr_value = getattr(obj, data_path)
        except (AttributeError, KeyError, IndexError) as e:
            text_content = self.create_text_content(f"无效的数据路径: {data_path}, 错误: {str(e)}")
            return self.create_result([text_content], is_error=True)
        
        # 计算每个关键帧之间的帧距离
        frame_step = (frame_end - frame_start) / (keyframe_count - 1) if keyframe_count > 1 else 0
        
        try:
            # 存储当前帧以供稍后恢复
            current_frame = bpy.context.scene.frame_current
            
            # 生成并应用关键帧
            keyframes_added = 0
            for i in range(keyframe_count):
                # 计算当前帧
                frame = int(frame_start + i * frame_step)
                
                # 计算动画位置 (0 - 1 范围)
                t = i / (keyframe_count - 1) if keyframe_count > 1 else 0
                
                # 应用动画缓动函数
                t_eased = self._ease_function(t, animation_type, amplitude, frequency)
                
                # 计算当前值
                if isinstance(attr_value, (list, tuple)):
                    # 对于向量属性
                    if index >= 0 and index < len(attr_value):
                        # 对单个分量设置动画
                        value = [start_value[0] + t_eased * (end_value[0] - start_value[0])]
                        array_index = index
                    else:
                        # 对整个向量设置动画
                        value = [
                            start_value[j] + t_eased * (end_value[j] - start_value[j])
                            for j in range(len(start_value))
                        ]
                        array_index = -1
                else:
                    # 对于单值属性
                    value = [start_value[0] + t_eased * (end_value[0] - start_value[0])]
                    array_index = -1
                
                # 设置当前帧
                bpy.context.scene.frame_set(frame)
                
                # 设置属性值
                if isinstance(attr_value, (list, tuple)):
                    if array_index >= 0:
                        # 设置单个分量
                        if hasattr(attr_value, "__setitem__"):
                            attr_value[array_index] = value[0]
                        else:
                            # 如果不可变，创建一个新的
                            new_value = list(attr_value)
                            new_value[array_index] = value[0]
                            setattr(obj, data_path, type(attr_value)(new_value))
                    else:
                        # 设置整个向量
                        if hasattr(attr_value, "__iter__") and hasattr(attr_value, "__setitem__"):
                            for j, v in enumerate(value):
                                attr_value[j] = v
                        else:
                            setattr(obj, data_path, type(attr_value)(value))
                else:
                    # 设置单值属性
                    setattr(obj, data_path, value[0])
                
                # 添加关键帧
                obj.keyframe_insert(data_path=data_path, index=array_index, frame=frame)
                keyframes_added += 1
            
            # 设置关键帧插值类型
            if obj.animation_data and obj.animation_data.action:
                for fcurve in obj.animation_data.action.fcurves:
                    if fcurve.data_path == data_path:
                        if index == -1 or fcurve.array_index == index:
                            for keyframe in fcurve.keyframe_points:
                                keyframe.interpolation = 'BEZIER'
                                
            # 创建结果信息
            text_content = self.create_text_content(
                f"已为对象 '{object_name}' 的 '{data_path}' 创建 {animation_type} 动画\n"
                f"添加了 {keyframes_added} 个关键帧，范围: {frame_start} - {frame_end}"
            )
            
        except Exception as e:
            text_content = self.create_text_content(f"创建属性动画时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
            
        finally:
            # 恢复原始帧
            bpy.context.scene.frame_set(current_frame)
        
        # 返回结果
        return self.create_result([text_content])
    
    def _ease_function(self, t: float, animation_type: str, amplitude: float = 1.0, frequency: float = 0.1) -> float:
        """应用缓动函数"""
        if animation_type == "linear":
            return t
        elif animation_type == "sine":
            return amplitude * math.sin(frequency * t * 2 * math.pi)
        elif animation_type == "bounce":
            # 反弹效果
            return 1 - (math.cos(t * math.pi * 4) * (1 - t))
        elif animation_type == "elastic":
            # 弹性效果
            return (math.sin(13 * math.pi / 2 * t) * math.pow(2, 10 * (t - 1)) + 1) * 0.5
        elif animation_type == "back":
            # 回弹效果
            return math.pow(t, 2) * ((1.70158 + 1) * t - 1.70158)
        elif animation_type == "quadratic":
            # 二次方缓动
            return t * t
        elif animation_type == "cubic":
            # 三次方缓动
            return t * t * t
        elif animation_type == "back_forth":
            # 来回运动
            return 0.5 - 0.5 * math.cos(t * 2 * math.pi)
        else:
            return t


# 在导入时自动注册工具实例
register_tool(AnimatePropertyHandler())
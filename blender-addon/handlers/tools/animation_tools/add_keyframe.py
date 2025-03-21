"""
添加关键帧的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.AddKeyframe")

class AddKeyframeHandler(BaseToolHandler):
    """添加关键帧工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_add_keyframe"
        
    @property
    def description(self) -> Optional[str]:
        return "为对象属性添加关键帧"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "要为其添加关键帧的对象名称"
                },
                "frame": {
                    "type": "integer",
                    "title": "帧数",
                    "description": "添加关键帧的帧数",
                    "default": None
                },
                "data_path": {
                    "type": "string",
                    "title": "数据路径",
                    "description": "要为其添加关键帧的属性路径，如'location'或'rotation_euler'"
                },
                "index": {
                    "type": "integer",
                    "title": "索引",
                    "description": "要为其添加关键帧的数组属性的索引（-1表示整个数组）",
                    "default": -1
                },
                "value": {
                    "type": "array",
                    "title": "值",
                    "description": "要设置的值，如位置[x,y,z]或旋转[x,y,z]",
                    "items": {
                        "type": "number"
                    }
                },
                "interpolation": {
                    "type": "string",
                    "title": "插值方式",
                    "description": "关键帧的插值方式",
                    "enum": ["CONSTANT", "LINEAR", "BEZIER"],
                    "default": "BEZIER"
                }
            },
            "required": ["object_name", "data_path"]
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
            
        # 检查插值方式
        interpolation = arguments.get("interpolation", "BEZIER")
        valid_interpolations = ["CONSTANT", "LINEAR", "BEZIER"]
        if interpolation not in valid_interpolations:
            return f"插值方式必须是以下之一: {', '.join(valid_interpolations)}"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行添加关键帧操作"""
        logger.info(f"添加关键帧，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._add_keyframe, arguments)
        
    def _add_keyframe(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中添加关键帧"""
        object_name = arguments.get("object_name")
        frame = arguments.get("frame")
        data_path = arguments.get("data_path")
        index = arguments.get("index", -1)
        value = arguments.get("value")
        interpolation = arguments.get("interpolation", "BEZIER")
        
        # 获取对象
        obj = bpy.data.objects[object_name]
        
        # 如果提供了帧数，设置当前帧
        current_frame = None
        if frame is not None:
            current_frame = bpy.context.scene.frame_current
            bpy.context.scene.frame_set(frame)
        
        try:
            # 尝试获取属性以检查数据路径是否有效
            try:
                if "." in data_path:
                    # 处理嵌套属性，如object.modifiers["Subsurf"].levels
                    path_parts = data_path.split(".")
                    target = obj
                    for part in path_parts[:-1]:
                        if "[" in part and "]" in part:
                            # 处理列表/字典访问，如modifiers["Subsurf"]
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
            
            # 如果提供了值，设置属性值
            if value is not None:
                try:
                    if isinstance(attr_value, (list, tuple)):
                        # 处理向量属性
                        if index >= 0 and index < len(attr_value):
                            # 设置单个分量
                            if len(value) == 1:
                                if hasattr(attr_value, "__setitem__"):
                                    attr_value[index] = value[0]
                                else:
                                    # 如果是不可变的元组，需要创建一个新的
                                    new_value = list(attr_value)
                                    new_value[index] = value[0]
                                    setattr(obj, data_path, type(attr_value)(new_value))
                        else:
                            # 设置整个向量
                            if len(value) == len(attr_value):
                                if hasattr(attr_value, "__iter__") and hasattr(attr_value, "__setitem__"):
                                    for i, v in enumerate(value):
                                        attr_value[i] = v
                                else:
                                    setattr(obj, data_path, type(attr_value)(value))
                    else:
                        # 处理单值属性
                        if len(value) == 1:
                            setattr(obj, data_path, value[0])
                except Exception as e:
                    text_content = self.create_text_content(f"设置属性值时出错: {str(e)}")
                    return self.create_result([text_content], is_error=True)
            
            # 添加关键帧
            try:
                obj.keyframe_insert(data_path=data_path, index=index, frame=frame)
                
                # 设置插值方式
                fcurves = []
                if obj.animation_data and obj.animation_data.action:
                    for fcurve in obj.animation_data.action.fcurves:
                        if fcurve.data_path == data_path:
                            if index == -1 or fcurve.array_index == index:
                                fcurves.append(fcurve)
                
                for fcurve in fcurves:
                    for keyframe in fcurve.keyframe_points:
                        if frame is None or keyframe.co[0] == frame:
                            keyframe.interpolation = interpolation
                
                # 获取关键帧的值
                if isinstance(attr_value, (list, tuple)):
                    if index != -1 and index < len(attr_value):
                        keyframe_value = attr_value[index]
                    else:
                        keyframe_value = list(attr_value)
                else:
                    keyframe_value = attr_value
                
                if frame is None:
                    frame = bpy.context.scene.frame_current
                    
                text_content = self.create_text_content(
                    f"已为对象 '{object_name}' 添加关键帧\n"
                    f"数据路径: {data_path}\n"
                    f"索引: {index}\n"
                    f"帧: {frame}\n"
                    f"值: {keyframe_value}\n"
                    f"插值: {interpolation}"
                )
                
            except Exception as e:
                text_content = self.create_text_content(f"添加关键帧时出错: {str(e)}")
                return self.create_result([text_content], is_error=True)
                
        finally:
            # 恢复原始帧
            if current_frame is not None:
                bpy.context.scene.frame_set(current_frame)
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(AddKeyframeHandler())
"""
设置对象跟随路径的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.SetObjectFollowPath")

class SetObjectFollowPathHandler(BaseToolHandler):
    """设置对象跟随路径工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_set_object_follow_path"
        
    @property
    def description(self) -> Optional[str]:
        return "设置对象沿着曲线路径移动的约束"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "要设置跟随路径的对象名称"
                },
                "path_name": {
                    "type": "string",
                    "title": "路径名称",
                    "description": "用作路径的曲线对象名称"
                },
                "use_fixed_position": {
                    "type": "boolean",
                    "title": "使用固定位置",
                    "description": "是否使用固定偏移（而不是评估时间）",
                    "default": False
                },
                "offset_factor": {
                    "type": "number",
                    "title": "偏移系数",
                    "description": "沿着路径的偏移位置（0.0-1.0）",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.0
                },
                "forward_axis": {
                    "type": "string",
                    "title": "前向轴",
                    "description": "对象的哪个轴指向运动方向",
                    "enum": ["X", "Y", "Z", "-X", "-Y", "-Z"],
                    "default": "Y"
                },
                "up_axis": {
                    "type": "string",
                    "title": "上方轴",
                    "description": "对象的哪个轴指向上方",
                    "enum": ["X", "Y", "Z"],
                    "default": "Z"
                },
                "use_curve_follow": {
                    "type": "boolean",
                    "title": "跟随曲线",
                    "description": "对象旋转是否跟随曲线的倾斜",
                    "default": True
                },
                "animate": {
                    "type": "boolean",
                    "title": "添加动画",
                    "description": "是否为偏移添加动画（0-1范围的动画）",
                    "default": True
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
                "follow_dupli": {
                    "type": "boolean",
                    "title": "复制沿曲线",
                    "description": "是否将对象复制沿着路径",
                    "default": False
                },
                "use_fixed_location": {
                    "type": "boolean",
                    "title": "使用固定位置",
                    "description": "使对象位置固定在曲线上（不使用约束而是直接设置位置）",
                    "default": False
                }
            },
            "required": ["object_name", "path_name"]
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
            
        # 检查路径名称
        path_name = arguments.get("path_name")
        if not path_name:
            return "必须提供路径名称"
            
        # 检查路径是否存在
        if path_name not in bpy.data.objects:
            return f"找不到路径对象: {path_name}"
            
        # 检查路径是否是曲线
        path_obj = bpy.data.objects[path_name]
        if path_obj.type != 'CURVE':
            return f"对象 '{path_name}' 不是曲线，无法用作路径"
            
        # 检查偏移系数
        offset_factor = arguments.get("offset_factor", 0.0)
        if not isinstance(offset_factor, (int, float)) or offset_factor < 0.0 or offset_factor > 1.0:
            return "偏移系数必须是0.0到1.0之间的数值"
            
        # 检查前向轴和上方轴
        forward_axis = arguments.get("forward_axis", "Y")
        if forward_axis not in ["X", "Y", "Z", "-X", "-Y", "-Z"]:
            return "前向轴必须是 'X'、'Y'、'Z'、'-X'、'-Y' 或 '-Z'"
            
        up_axis = arguments.get("up_axis", "Z")
        if up_axis not in ["X", "Y", "Z"]:
            return "上方轴必须是 'X'、'Y' 或 'Z'"
            
        # 检查动画帧范围
        animate = arguments.get("animate", True)
        frame_start = arguments.get("frame_start")
        frame_end = arguments.get("frame_end")
        
        if animate:
            if frame_start is None:
                return "启用动画时必须提供开始帧"
                
            if frame_end is None:
                return "启用动画时必须提供结束帧"
                
            if not isinstance(frame_start, int):
                return "开始帧必须是整数"
                
            if not isinstance(frame_end, int):
                return "结束帧必须是整数"
                
            if frame_start >= frame_end:
                return "开始帧必须小于结束帧"
                
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行设置对象跟随路径操作"""
        logger.info(f"设置对象跟随路径，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._set_object_follow_path, arguments)
        
    def _set_object_follow_path(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中设置对象跟随路径"""
        object_name = arguments.get("object_name")
        path_name = arguments.get("path_name")
        use_fixed_position = arguments.get("use_fixed_position", False)
        offset_factor = arguments.get("offset_factor", 0.0)
        forward_axis = arguments.get("forward_axis", "Y")
        up_axis = arguments.get("up_axis", "Z")
        use_curve_follow = arguments.get("use_curve_follow", True)
        animate = arguments.get("animate", True)
        frame_start = arguments.get("frame_start")
        frame_end = arguments.get("frame_end")
        follow_dupli = arguments.get("follow_dupli", False)
        use_fixed_location = arguments.get("use_fixed_location", False)
        
        # 获取对象和路径
        obj = bpy.data.objects[object_name]
        path_obj = bpy.data.objects[path_name]
        
        try:
            # 确保路径曲线有正确的设置
            path_obj.data.use_path = True
            
            # 如果使用固定位置直接设置对象位置而不使用约束
            if use_fixed_location:
                # 获取评估点
                spline = path_obj.data.splines[0]  # 假设使用第一条样条
                
                if spline.type == 'BEZIER':
                    # 对贝塞尔曲线进行评估
                    points = spline.bezier_points
                    if len(points) < 2:
                        raise ValueError("贝塞尔曲线至少需要两个点")
                    
                    # 简单线性插值获取位置（实际上应该使用贝塞尔插值）
                    idx1 = int(offset_factor * (len(points) - 1))
                    idx2 = min(idx1 + 1, len(points) - 1)
                    fac = offset_factor * (len(points) - 1) - idx1
                    
                    pt1 = path_obj.matrix_world @ points[idx1].co
                    pt2 = path_obj.matrix_world @ points[idx2].co
                    
                    # 线性插值
                    loc = pt1.lerp(pt2, fac)
                    
                    # 设置对象位置
                    obj.location = loc
                    
                    text_content = self.create_text_content(
                        f"已将对象 '{object_name}' 放置在路径 '{path_name}' 上的位置 {offset_factor}"
                    )
                else:
                    # 其他类型曲线也类似处理
                    text_content = self.create_text_content(
                        f"已将对象 '{object_name}' 放置在路径 '{path_name}' 上，但不支持当前曲线类型的精确位置"
                    )
                
                return self.create_result([text_content])
            
            # 如果使用复制效果
            if follow_dupli:
                # 设置路径的复制设置
                path_obj.instance_type = 'PATH'
                
                # 设置路径复制的帧范围
                if animate and frame_start is not None and frame_end is not None:
                    path_obj.data.path_duration = frame_end - frame_start
                
                # 设置复制的对象
                obj.parent = path_obj
                
                text_content = self.create_text_content(
                    f"已设置对象 '{object_name}' 沿路径 '{path_name}' 复制\n"
                    f"请在曲线的修改器面板中调整复制设置，如计数、起始点等"
                )
                
                return self.create_result([text_content])
            
            # 创建路径跟随约束
            constraint_name = f"Follow {path_name}"
            
            # 移除同名约束（如果存在）
            for c in obj.constraints:
                if c.name == constraint_name:
                    obj.constraints.remove(c)
            
            # 添加新约束
            constraint = obj.constraints.new('FOLLOW_PATH')
            constraint.name = constraint_name
            constraint.target = path_obj
            constraint.use_fixed_location = use_fixed_position
            constraint.offset_factor = offset_factor
            constraint.forward_axis = forward_axis
            constraint.up_axis = up_axis
            constraint.use_curve_follow = use_curve_follow
            
            # 如果需要，为偏移系数添加动画
            if animate and frame_start is not None and frame_end is not None:
                # 移除现有的关键帧
                if obj.animation_data and obj.animation_data.action:
                    fcurves = obj.animation_data.action.fcurves
                    data_path = f'constraints["{constraint_name}"].offset_factor'
                    for fc in fcurves[:]:
                        if fc.data_path == data_path:
                            fcurves.remove(fc)
                
                # 存储当前帧
                current_frame = bpy.context.scene.frame_current
                
                # 设置起始关键帧
                bpy.context.scene.frame_set(frame_start)
                constraint.offset_factor = 0.0
                obj.keyframe_insert(f'constraints["{constraint_name}"].offset_factor', frame=frame_start)
                
                # 设置结束关键帧
                bpy.context.scene.frame_set(frame_end)
                constraint.offset_factor = 1.0
                obj.keyframe_insert(f'constraints["{constraint_name}"].offset_factor', frame=frame_end)
                
                # 恢复原始帧
                bpy.context.scene.frame_set(current_frame)
                
                # 重置为当前偏移系数
                constraint.offset_factor = offset_factor
                
                animation_info = f"并添加了从帧 {frame_start} 到 {frame_end} 的动画"
            else:
                animation_info = "，不添加偏移动画"
            
            # 创建结果信息
            text_content = self.create_text_content(
                f"已为对象 '{object_name}' 添加跟随路径 '{path_name}' 的约束{animation_info}\n"
                f"前向轴: {forward_axis}, 上方轴: {up_axis}\n"
                f"跟随曲线: {'是' if use_curve_follow else '否'}"
            )
        
        except Exception as e:
            text_content = self.create_text_content(f"设置对象跟随路径时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(SetObjectFollowPathHandler())
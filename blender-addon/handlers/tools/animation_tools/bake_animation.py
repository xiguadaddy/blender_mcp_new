"""
烘焙Blender动画的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.BakeAnimation")

class BakeAnimationHandler(BaseToolHandler):
    """烘焙动画工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_bake_animation"
        
    @property
    def description(self) -> Optional[str]:
        return "烘焙对象动画到关键帧"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "要烘焙动画的对象名称"
                },
                "frame_start": {
                    "type": "integer",
                    "title": "开始帧",
                    "description": "烘焙的开始帧"
                },
                "frame_end": {
                    "type": "integer",
                    "title": "结束帧",
                    "description": "烘焙的结束帧"
                },
                "step": {
                    "type": "integer",
                    "title": "步长",
                    "description": "烘焙的帧步长",
                    "default": 1
                },
                "only_selected": {
                    "type": "boolean",
                    "title": "仅选中对象",
                    "description": "是否只烘焙选中的对象",
                    "default": False
                },
                "do_pose": {
                    "type": "boolean",
                    "title": "烘焙姿态",
                    "description": "是否烘焙姿态骨骼",
                    "default": True
                },
                "do_object": {
                    "type": "boolean",
                    "title": "烘焙对象",
                    "description": "是否烘焙对象变换",
                    "default": True
                },
                "do_visual_keying": {
                    "type": "boolean",
                    "title": "视觉关键帧",
                    "description": "是否使用视觉关键帧（烘焙实际的视觉变换）",
                    "default": True
                },
                "do_constraint_clear": {
                    "type": "boolean",
                    "title": "清除约束",
                    "description": "是否在烘焙后清除约束",
                    "default": False
                },
                "do_parents_clear": {
                    "type": "boolean",
                    "title": "清除父级",
                    "description": "是否在烘焙后清除父级关系",
                    "default": False
                },
                "action_name": {
                    "type": "string",
                    "title": "动作名称",
                    "description": "烘焙到的动作名称（如果未提供，使用默认名称）"
                }
            },
            "required": ["object_name"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 如果不是'only_selected'模式，需要对象名称
        if not arguments.get("only_selected") and not arguments.get("object_name"):
            return "必须提供对象名称或设置'仅选中对象'"
            
        # 检查对象是否存在（如果提供）
        object_name = arguments.get("object_name")
        if object_name and object_name not in bpy.data.objects:
            return f"找不到对象: {object_name}"
            
        # 检查帧范围
        frame_start = arguments.get("frame_start")
        frame_end = arguments.get("frame_end")
        
        if frame_start is None:
            return "必须提供开始帧"
            
        if frame_end is None:
            return "必须提供结束帧"
            
        if not isinstance(frame_start, int):
            return "开始帧必须是整数"
            
        if not isinstance(frame_end, int):
            return "结束帧必须是整数"
            
        if frame_start > frame_end:
            return "开始帧必须小于或等于结束帧"
            
        # 检查步长
        step = arguments.get("step", 1)
        if not isinstance(step, int) or step < 1:
            return "步长必须是正整数"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行烘焙动画操作"""
        logger.info(f"烘焙动画，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._bake_animation, arguments)
        
    def _bake_animation(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中烘焙动画"""
        object_name = arguments.get("object_name")
        frame_start = arguments.get("frame_start")
        frame_end = arguments.get("frame_end")
        step = arguments.get("step", 1)
        only_selected = arguments.get("only_selected", False)
        do_pose = arguments.get("do_pose", True)
        do_object = arguments.get("do_object", True)
        do_visual_keying = arguments.get("do_visual_keying", True)
        do_constraint_clear = arguments.get("do_constraint_clear", False)
        do_parents_clear = arguments.get("do_parents_clear", False)
        action_name = arguments.get("action_name")
        
        # 保存当前选择状态
        original_selected_objects = [obj for obj in bpy.context.selected_objects]
        original_active_object = bpy.context.active_object
        
        try:
            # 如果指定了对象并且不是仅选中模式，选择该对象
            if object_name and not only_selected:
                # 取消选择所有对象
                bpy.ops.object.select_all(action='DESELECT')
                
                # 选择指定对象
                obj = bpy.data.objects[object_name]
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                
                # 记录要烘焙的对象
                bake_objects = [obj]
            else:
                # 使用当前选择的对象
                bake_objects = bpy.context.selected_objects
            
            # 如果没有对象可烘焙，返回错误
            if not bake_objects:
                text_content = self.create_text_content("没有选择要烘焙的对象")
                return self.create_result([text_content], is_error=True)
            
            # 如果指定了动作名称并且该动作不存在，创建新动作
            if action_name and action_name not in bpy.data.actions:
                action = bpy.data.actions.new(action_name)
                
                # 将动作分配给活动对象
                active_obj = bpy.context.active_object
                if active_obj:
                    if not active_obj.animation_data:
                        active_obj.animation_data_create()
                    active_obj.animation_data.action = action
            
            # 执行烘焙操作
            bpy.ops.nla.bake(
                frame_start=frame_start,
                frame_end=frame_end,
                step=step,
                only_selected=only_selected,
                visual_keying=do_visual_keying,
                clear_constraints=do_constraint_clear,
                clear_parents=do_parents_clear,
                use_current_action=True,
                bake_types={'POSE' if do_pose else '', 'OBJECT' if do_object else ''}
            )
            
            # 如果指定了动作名称但操作会创建一个新动作，重命名新创建的动作
            if action_name:
                active_obj = bpy.context.active_object
                if active_obj and active_obj.animation_data and active_obj.animation_data.action:
                    if active_obj.animation_data.action.name != action_name:
                        active_obj.animation_data.action.name = action_name
            
            # 创建结果信息
            object_names = ", ".join([obj.name for obj in bake_objects])
            bake_types = []
            if do_pose: bake_types.append("姿态")
            if do_object: bake_types.append("对象")
            
            text_content = self.create_text_content(
                f"已烘焙动画:\n"
                f"对象: {object_names}\n"
                f"帧范围: {frame_start} - {frame_end}, 步长: {step}\n"
                f"烘焙类型: {', '.join(bake_types)}"
                + (f"\n动作名称: {action_name}" if action_name else "")
            )
            
        except Exception as e:
            text_content = self.create_text_content(f"烘焙动画时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
            
        finally:
            # 恢复原始选择状态
            bpy.ops.object.select_all(action='DESELECT')
            for obj in original_selected_objects:
                if obj:
                    obj.select_set(True)
            if original_active_object:
                bpy.context.view_layer.objects.active = original_active_object
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(BakeAnimationHandler())
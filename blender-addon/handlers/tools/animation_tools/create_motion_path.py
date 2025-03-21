"""
创建对象运动路径的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.CreateMotionPath")

class CreateMotionPathHandler(BaseToolHandler):
    """创建运动路径工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_create_motion_path"
        
    @property
    def description(self) -> Optional[str]:
        return "计算并显示对象或骨骼的运动路径"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "要计算运动路径的对象名称"
                },
                "bone_name": {
                    "type": "string",
                    "title": "骨骼名称",
                    "description": "如果是骨架，要计算运动路径的骨骼名称"
                },
                "frame_start": {
                    "type": "integer",
                    "title": "开始帧",
                    "description": "运动路径的开始帧"
                },
                "frame_end": {
                    "type": "integer",
                    "title": "结束帧",
                    "description": "运动路径的结束帧"
                },
                "bake": {
                    "type": "boolean",
                    "title": "烘焙路径",
                    "description": "是否立即烘焙运动路径",
                    "default": True
                },
                "line_thickness": {
                    "type": "integer",
                    "title": "线条粗细",
                    "description": "运动路径线条的粗细",
                    "default": 2
                },
                "show_frame_numbers": {
                    "type": "boolean",
                    "title": "显示帧数",
                    "description": "是否在路径上显示帧数",
                    "default": False
                },
                "use_custom_color": {
                    "type": "boolean",
                    "title": "使用自定义颜色",
                    "description": "是否使用自定义颜色绘制运动路径",
                    "default": False
                },
                "custom_color": {
                    "type": "array",
                    "title": "自定义颜色",
                    "description": "运动路径的自定义颜色 [R, G, B]",
                    "items": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1
                    },
                    "minItems": 3,
                    "maxItems": 3
                },
                "display_baked_paths": {
                    "type": "boolean",
                    "title": "显示路径",
                    "description": "是否显示计算出的运动路径",
                    "default": True
                },
                "with_children": {
                    "type": "boolean", 
                    "title": "包含子物体",
                    "description": "是否也计算所有子物体的运动路径",
                    "default": False
                },
                "clear_existing": {
                    "type": "boolean",
                    "title": "清除现有路径",
                    "description": "是否在计算前清除现有的运动路径",
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
            
        # 检查骨骼名称（如果对象是骨架）
        bone_name = arguments.get("bone_name")
        if bone_name:
            obj = bpy.data.objects[object_name]
            if obj.type != 'ARMATURE':
                return f"对象 '{object_name}' 不是骨架，不能指定骨骼"
                
            if bone_name not in obj.pose.bones:
                return f"在骨架 '{object_name}' 中找不到骨骼: {bone_name}"
        
        # 检查开始帧和结束帧
        frame_start = arguments.get("frame_start")
        frame_end = arguments.get("frame_end")
        
        if frame_start is not None and not isinstance(frame_start, int):
            return "开始帧必须是整数"
            
        if frame_end is not None and not isinstance(frame_end, int):
            return "结束帧必须是整数"
            
        if frame_start is not None and frame_end is not None and frame_start > frame_end:
            return "开始帧必须小于或等于结束帧"
            
        # 检查线条粗细
        line_thickness = arguments.get("line_thickness", 2)
        if not isinstance(line_thickness, int) or line_thickness < 1:
            return "线条粗细必须是大于或等于1的整数"
            
        # 检查自定义颜色
        use_custom_color = arguments.get("use_custom_color", False)
        custom_color = arguments.get("custom_color")
        
        if use_custom_color and (not custom_color or not isinstance(custom_color, list) or len(custom_color) != 3):
            return "启用自定义颜色时，必须提供包含3个0-1之间值的颜色数组 [R, G, B]"
            
        if use_custom_color and custom_color:
            if not all(isinstance(c, (int, float)) and 0 <= c <= 1 for c in custom_color):
                return "自定义颜色值必须在0到1之间"
                
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行创建运动路径操作"""
        logger.info(f"创建运动路径，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._create_motion_path, arguments)
        
    def _create_motion_path(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中创建运动路径"""
        object_name = arguments.get("object_name")
        bone_name = arguments.get("bone_name")
        frame_start = arguments.get("frame_start")
        frame_end = arguments.get("frame_end")
        bake = arguments.get("bake", True)
        line_thickness = arguments.get("line_thickness", 2)
        show_frame_numbers = arguments.get("show_frame_numbers", False)
        use_custom_color = arguments.get("use_custom_color", False)
        custom_color = arguments.get("custom_color")
        
        try:
            # 获取对象
            obj = bpy.data.objects[object_name]
            
            # 保存当前选择状态
            original_active = bpy.context.view_layer.objects.active
            original_selected = [o for o in bpy.context.selected_objects]
            
            # 选择目标对象
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            
            # 如果未指定帧范围，使用场景的帧范围
            if frame_start is None:
                frame_start = bpy.context.scene.frame_start
            if frame_end is None:
                frame_end = bpy.context.scene.frame_end
            
            # 创建或更新运动路径设置
            if obj.type == 'ARMATURE' and bone_name:
                # 为特定骨骼设置运动路径
                pose_bone = obj.pose.bones[bone_name]
                
                # 确保骨骼可见且选中
                original_bone_select = {}
                for b in obj.data.bones:
                    original_bone_select[b.name] = b.select
                    b.select = (b.name == bone_name)
                
                # 设置骨骼的运动路径
                pose_bone.motion_path.type = 'RANGE'
                pose_bone.motion_path.frame_start = frame_start
                pose_bone.motion_path.frame_end = frame_end
                pose_bone.motion_path.lines = show_frame_numbers
                
                # 设置运动路径显示选项
                bpy.context.scene.tool_settings.use_keyframe_insert_auto = False
                bpy.context.scene.tool_settings.motion_path.show_frame_numbers = show_frame_numbers
                bpy.context.scene.tool_settings.motion_path.type = 'RANGE'
                bpy.context.scene.tool_settings.motion_path.frame_start = frame_start
                bpy.context.scene.tool_settings.motion_path.frame_end = frame_end
                bpy.context.scene.tool_settings.motion_path.line_thickness = line_thickness
                
                # 设置自定义颜色
                if use_custom_color and custom_color:
                    pose_bone.motion_path.use_custom_color = True
                    pose_bone.motion_path.color = custom_color
                
                # 烘焙运动路径
                if bake:
                    bpy.ops.pose.paths_calculate(start_frame=frame_start, end_frame=frame_end)
                
                # 恢复原始骨骼选择状态
                for name, select in original_bone_select.items():
                    obj.data.bones[name].select = select
                
                path_type = "骨骼"
                target_name = f"{object_name}.{bone_name}"
                
            else:
                # 为对象设置运动路径
                obj.motion_path.type = 'RANGE'
                obj.motion_path.frame_start = frame_start
                obj.motion_path.frame_end = frame_end
                obj.motion_path.lines = show_frame_numbers
                
                # 设置运动路径显示选项
                bpy.context.scene.tool_settings.use_keyframe_insert_auto = False
                bpy.context.scene.tool_settings.motion_path.show_frame_numbers = show_frame_numbers
                bpy.context.scene.tool_settings.motion_path.type = 'RANGE'
                bpy.context.scene.tool_settings.motion_path.frame_start = frame_start
                bpy.context.scene.tool_settings.motion_path.frame_end = frame_end
                bpy.context.scene.tool_settings.motion_path.line_thickness = line_thickness
                
                # 设置自定义颜色
                if use_custom_color and custom_color:
                    obj.motion_path.use_custom_color = True
                    obj.motion_path.color = custom_color
                
                # 烘焙运动路径
                if bake:
                    bpy.ops.object.paths_calculate(start_frame=frame_start, end_frame=frame_end)
                
                path_type = "对象"
                target_name = object_name
            
            # 创建结果信息
            baked_info = "并已烘焙" if bake else "但未烘焙"
            color_info = f"，使用自定义颜色 RGB{custom_color}" if use_custom_color and custom_color else ""
            
            text_content = self.create_text_content(
                f"已为{path_type} '{target_name}' 创建运动路径{baked_info}\n"
                f"帧范围: {frame_start} - {frame_end}\n"
                f"线条粗细: {line_thickness}{color_info}"
            )
            
        except Exception as e:
            text_content = self.create_text_content(f"创建运动路径时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
            
        finally:
            # 恢复原始选择状态
            bpy.ops.object.select_all(action='DESELECT')
            for obj in original_selected:
                if obj:
                    obj.select_set(True)
            if original_active:
                bpy.context.view_layer.objects.active = original_active
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(CreateMotionPathHandler())
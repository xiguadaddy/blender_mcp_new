"""
创建和管理Blender动画动作的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.CreateAction")

class CreateActionHandler(BaseToolHandler):
    """创建动作工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_create_action"
        
    @property
    def description(self) -> Optional[str]:
        return "创建和管理Blender动画动作"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action_name": {
                    "type": "string",
                    "title": "动作名称",
                    "description": "要创建或管理的动作名称"
                },
                "operation": {
                    "type": "string",
                    "title": "操作",
                    "description": "要执行的操作",
                    "enum": ["create", "assign", "remove", "push", "list"],
                    "default": "create"
                },
                "object_name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "要处理的对象名称"
                },
                "frame_start": {
                    "type": "integer",
                    "title": "开始帧",
                    "description": "动作的开始帧"
                },
                "frame_end": {
                    "type": "integer",
                    "title": "结束帧",
                    "description": "动作的结束帧"
                },
                "from_current_fcurves": {
                    "type": "boolean",
                    "title": "从当前FCurves创建",
                    "description": "是否从对象当前的FCurves创建新动作",
                    "default": False
                }
            }
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        operation = arguments.get("operation", "create")
        valid_operations = ["create", "assign", "remove", "push", "list"]
        if operation not in valid_operations:
            return f"无效的操作: {operation}，有效操作: {', '.join(valid_operations)}"
            
        # 对于除了'list'外的所有操作，都需要动作名称
        if operation != "list" and not arguments.get("action_name"):
            return "必须提供动作名称"
            
        # 对于'assign'、'remove'和'push'操作，需要对象名称
        if operation in ["assign", "remove", "push"] and not arguments.get("object_name"):
            return f"操作 '{operation}' 需要提供对象名称"
            
        # 检查对象是否存在
        object_name = arguments.get("object_name")
        if object_name and object_name not in bpy.data.objects:
            return f"找不到对象: {object_name}"
            
        # 检查开始帧和结束帧
        frame_start = arguments.get("frame_start")
        frame_end = arguments.get("frame_end")
        
        if frame_start is not None and not isinstance(frame_start, int):
            return "开始帧必须是整数"
            
        if frame_end is not None and not isinstance(frame_end, int):
            return "结束帧必须是整数"
            
        if frame_start is not None and frame_end is not None and frame_start > frame_end:
            return "开始帧必须小于或等于结束帧"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行创建动作操作"""
        logger.info(f"创建动作，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._create_action, arguments)
        
    def _create_action(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中创建动作"""
        action_name = arguments.get("action_name")
        operation = arguments.get("operation", "create")
        object_name = arguments.get("object_name")
        frame_start = arguments.get("frame_start")
        frame_end = arguments.get("frame_end")
        from_current_fcurves = arguments.get("from_current_fcurves", False)
        
        try:
            # 列出所有动作
            if operation == "list":
                actions_info = []
                for action in bpy.data.actions:
                    # 提取帧范围
                    if action.frame_range:
                        frame_range = f"{int(action.frame_range[0])} - {int(action.frame_range[1])}"
                    else:
                        frame_range = "未知"
                    
                    # 查找使用该动作的对象
                    users = []
                    for obj in bpy.data.objects:
                        if obj.animation_data and obj.animation_data.action == action:
                            users.append(obj.name)
                    
                    actions_info.append({
                        "name": action.name,
                        "frame_range": frame_range,
                        "users": users,
                        "user_count": action.users
                    })
                
                # 构建动作列表文本
                if actions_info:
                    actions_list = "\n".join([
                        f"- {a['name']} (帧范围: {a['frame_range']}, 用户: {', '.join(a['users']) if a['users'] else '无'})"
                        for a in actions_info
                    ])
                    text_content = self.create_text_content(f"动作列表 ({len(actions_info)} 个):\n{actions_list}")
                else:
                    text_content = self.create_text_content("没有找到动画动作")
                
                return self.create_result([text_content])
            
            # 创建新动作
            if operation == "create":
                # 检查动作是否已存在
                if action_name in bpy.data.actions:
                    # 如果已存在，询问是否要使用现有动作
                    text_content = self.create_text_content(f"动作 '{action_name}' 已存在")
                    return self.create_result([text_content], is_error=True)
                
                # 创建新动作
                action = bpy.data.actions.new(action_name)
                
                # 如果指定了对象且需要从当前FCurves创建
                if object_name and from_current_fcurves:
                    obj = bpy.data.objects[object_name]
                    if obj.animation_data and obj.animation_data.action:
                        # 复制现有动作的FCurves
                        source_action = obj.animation_data.action
                        for fcurve in source_action.fcurves:
                            new_fcurve = action.fcurves.new(
                                data_path=fcurve.data_path,
                                index=fcurve.array_index
                            )
                            # 复制关键帧点
                            for keyframe in fcurve.keyframe_points:
                                new_keyframe = new_fcurve.keyframe_points.insert(
                                    frame=keyframe.co[0],
                                    value=keyframe.co[1]
                                )
                                new_keyframe.interpolation = keyframe.interpolation
                
                # 如果指定了对象，分配新动作
                if object_name:
                    obj = bpy.data.objects[object_name]
                    if not obj.animation_data:
                        obj.animation_data_create()
                    obj.animation_data.action = action
                
                # 设置帧范围（如果提供）
                if frame_start is not None:
                    action.frame_range[0] = frame_start
                if frame_end is not None:
                    action.frame_range[1] = frame_end
                
                text_content = self.create_text_content(
                    f"已创建动作 '{action_name}'"
                    + (f"\n并分配给对象 '{object_name}'" if object_name else "")
                )
                return self.create_result([text_content])
            
            # 分配现有动作
            elif operation == "assign":
                # 检查动作是否存在
                if action_name not in bpy.data.actions:
                    text_content = self.create_text_content(f"动作 '{action_name}' 不存在")
                    return self.create_result([text_content], is_error=True)
                
                # 获取动作和对象
                action = bpy.data.actions[action_name]
                obj = bpy.data.objects[object_name]
                
                # 创建动画数据（如果不存在）
                if not obj.animation_data:
                    obj.animation_data_create()
                
                # 分配动作
                obj.animation_data.action = action
                
                text_content = self.create_text_content(f"已将动作 '{action_name}' 分配给对象 '{object_name}'")
                return self.create_result([text_content])
            
            # 移除对象的动作
            elif operation == "remove":
                obj = bpy.data.objects[object_name]
                
                if not obj.animation_data or not obj.animation_data.action:
                    text_content = self.create_text_content(f"对象 '{object_name}' 没有活动动作")
                    return self.create_result([text_content], is_error=True)
                
                current_action = obj.animation_data.action.name
                obj.animation_data.action = None
                
                text_content = self.create_text_content(f"已从对象 '{object_name}' 移除动作 '{current_action}'")
                return self.create_result([text_content])
            
            # 将当前动作推送到NLA条带
            elif operation == "push":
                obj = bpy.data.objects[object_name]
                
                if not obj.animation_data or not obj.animation_data.action:
                    text_content = self.create_text_content(f"对象 '{object_name}' 没有活动动作")
                    return self.create_result([text_content], is_error=True)
                
                # 获取当前动作
                current_action = obj.animation_data.action
                
                # 推送到NLA
                track = obj.animation_data.nla_tracks.new()
                track.name = action_name or current_action.name
                
                # 创建条带
                strip = track.strips.new(
                    name=action_name or current_action.name,
                    start=frame_start or 1,
                    action=current_action
                )
                
                # 设置条带参数
                if frame_start is not None:
                    strip.frame_start = frame_start
                if frame_end is not None:
                    strip.frame_end = frame_end
                
                # 清除活动动作
                obj.animation_data.action = None
                
                text_content = self.create_text_content(
                    f"已将对象 '{object_name}' 的活动动作 '{current_action.name}' 推送到NLA条带\n"
                    f"条带名称: {strip.name}"
                    + (f"\n帧范围: {strip.frame_start} - {strip.frame_end}" if frame_start is not None or frame_end is not None else "")
                )
                return self.create_result([text_content])
            
        except Exception as e:
            text_content = self.create_text_content(f"处理动作时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
            
        # 默认情况不应该到达这里
        text_content = self.create_text_content(f"未知操作: {operation}")
        return self.create_result([text_content], is_error=True)


# 在导入时自动注册工具实例
register_tool(CreateActionHandler())
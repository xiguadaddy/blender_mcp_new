"""
清除Blender对象动画数据的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.ClearAnimationData")

class ClearAnimationDataHandler(BaseToolHandler):
    """清除动画数据工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_clear_animation_data"
        
    @property
    def description(self) -> Optional[str]:
        return "清除对象的动画数据，如关键帧、NLA轨道等"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "要清除动画数据的对象名称"
                },
                "clear_action": {
                    "type": "boolean",
                    "title": "清除动作",
                    "description": "是否清除对象的当前动作",
                    "default": True
                },
                "clear_nla_tracks": {
                    "type": "boolean",
                    "title": "清除NLA轨道",
                    "description": "是否清除对象的NLA轨道",
                    "default": True
                },
                "clear_drivers": {
                    "type": "boolean",
                    "title": "清除驱动器",
                    "description": "是否清除对象的属性驱动器",
                    "default": True
                },
                "clear_all_animation_data": {
                    "type": "boolean",
                    "title": "清除所有动画数据",
                    "description": "是否完全删除对象的animation_data（包括上述所有内容）",
                    "default": False
                },
                "data_path": {
                    "type": "string",
                    "title": "数据路径",
                    "description": "如果指定，只清除特定数据路径的关键帧"
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
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行清除动画数据操作"""
        logger.info(f"清除动画数据，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._clear_animation_data, arguments)
        
    def _clear_animation_data(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中清除动画数据"""
        object_name = arguments.get("object_name")
        clear_action = arguments.get("clear_action", True)
        clear_nla_tracks = arguments.get("clear_nla_tracks", True)
        clear_drivers = arguments.get("clear_drivers", True)
        clear_all_animation_data = arguments.get("clear_all_animation_data", False)
        data_path = arguments.get("data_path")
        
        # 获取对象
        obj = bpy.data.objects[object_name]
        
        # 如果对象没有动画数据，则返回相应信息
        if not obj.animation_data:
            text_content = self.create_text_content(f"对象 '{object_name}' 没有动画数据")
            return self.create_result([text_content])
        
        # 跟踪清除的项目
        cleared_items = []
        
        try:
            # 如果指定了清除所有动画数据
            if clear_all_animation_data:
                obj.animation_data_clear()
                cleared_items.append("所有动画数据")
            else:
                # 如果指定了数据路径，只清除该路径的关键帧
                if data_path and obj.animation_data.action:
                    fcurves_to_remove = []
                    for fcurve in obj.animation_data.action.fcurves:
                        if fcurve.data_path == data_path:
                            fcurves_to_remove.append(fcurve)
                    
                    # 移除匹配的F曲线
                    for fcurve in fcurves_to_remove:
                        obj.animation_data.action.fcurves.remove(fcurve)
                    
                    if fcurves_to_remove:
                        cleared_items.append(f"数据路径 '{data_path}' 的关键帧")
                
                # 清除动作
                if clear_action and obj.animation_data.action:
                    action_name = obj.animation_data.action.name
                    obj.animation_data.action = None
                    cleared_items.append(f"动作 '{action_name}'")
                
                # 清除NLA轨道
                if clear_nla_tracks and obj.animation_data.nla_tracks:
                    track_count = len(obj.animation_data.nla_tracks)
                    while obj.animation_data.nla_tracks:
                        obj.animation_data.nla_tracks.remove(obj.animation_data.nla_tracks[0])
                    cleared_items.append(f"{track_count} 个NLA轨道")
                
                # 清除驱动器
                if clear_drivers and obj.animation_data.drivers:
                    driver_count = len(obj.animation_data.drivers)
                    while obj.animation_data.drivers:
                        obj.animation_data.drivers.remove(obj.animation_data.drivers[0])
                    cleared_items.append(f"{driver_count} 个驱动器")
            
            # 创建结果信息
            if cleared_items:
                text_content = self.create_text_content(f"已为对象 '{object_name}' 清除: {', '.join(cleared_items)}")
            else:
                text_content = self.create_text_content(f"未清除对象 '{object_name}' 的任何动画数据")
                
        except Exception as e:
            text_content = self.create_text_content(f"清除动画数据时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(ClearAnimationDataHandler())
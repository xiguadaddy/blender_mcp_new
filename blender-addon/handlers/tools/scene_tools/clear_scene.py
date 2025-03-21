"""
清空Blender场景的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.ClearScene")

class ClearSceneHandler(BaseToolHandler):
    """清空场景工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_clear_scene"
        
    @property
    def description(self) -> Optional[str]:
        return "清空Blender场景中的对象"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "scene_name": {
                    "type": "string",
                    "title": "场景名称",
                    "description": "要清空的场景名称（默认为当前活动场景）"
                },
                "clear_objects": {
                    "type": "boolean",
                    "title": "清除对象",
                    "description": "是否清除所有对象",
                    "default": True
                },
                "clear_materials": {
                    "type": "boolean",
                    "title": "清除材质",
                    "description": "是否清除所有未使用的材质",
                    "default": False
                },
                "clear_worlds": {
                    "type": "boolean",
                    "title": "清除世界",
                    "description": "是否清除所有未使用的世界环境",
                    "default": False
                },
                "exclude_cameras": {
                    "type": "boolean",
                    "title": "排除相机",
                    "description": "是否在清除对象时排除相机",
                    "default": False
                },
                "exclude_lights": {
                    "type": "boolean",
                    "title": "排除灯光",
                    "description": "是否在清除对象时排除灯光",
                    "default": False
                }
            }
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查场景名称（如果提供）
        scene_name = arguments.get("scene_name")
        if scene_name and scene_name not in bpy.data.scenes:
            return f"场景 '{scene_name}' 不存在"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行清空场景操作"""
        logger.info(f"清空场景，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._clear_scene, arguments)
        
    def _clear_scene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中清空场景"""
        scene_name = arguments.get("scene_name")
        clear_objects = arguments.get("clear_objects", True)
        clear_materials = arguments.get("clear_materials", False)
        clear_worlds = arguments.get("clear_worlds", False)
        exclude_cameras = arguments.get("exclude_cameras", False)
        exclude_lights = arguments.get("exclude_lights", False)
        
        # 获取场景
        if scene_name:
            scene = bpy.data.scenes[scene_name]
        else:
            scene = bpy.context.scene
            scene_name = scene.name
        
        # 跟踪删除的项目
        deleted_objects = 0
        deleted_materials = 0
        deleted_worlds = 0
        
        # 清除对象
        if clear_objects:
            # 收集要删除的对象
            objects_to_delete = []
            for obj in scene.objects:
                # 根据排除条件过滤对象
                if exclude_cameras and obj.type == 'CAMERA':
                    continue
                if exclude_lights and obj.type == 'LIGHT':
                    continue
                objects_to_delete.append(obj)
            
            # 删除对象
            for obj in objects_to_delete:
                bpy.data.objects.remove(obj)
                deleted_objects += 1
        
        # 清除未使用的材质
        if clear_materials:
            for material in bpy.data.materials:
                if material.users == 0:
                    bpy.data.materials.remove(material)
                    deleted_materials += 1
        
        # 清除未使用的世界环境
        if clear_worlds:
            for world in bpy.data.worlds:
                if world.users == 0:
                    bpy.data.worlds.remove(world)
                    deleted_worlds += 1
        
        # 创建结果信息
        result_parts = []
        if clear_objects:
            exclude_info = ""
            if exclude_cameras or exclude_lights:
                excludes = []
                if exclude_cameras: excludes.append("相机")
                if exclude_lights: excludes.append("灯光")
                exclude_info = f"（排除: {', '.join(excludes)}）"
            result_parts.append(f"已删除 {deleted_objects} 个对象{exclude_info}")
        
        if clear_materials:
            result_parts.append(f"已删除 {deleted_materials} 个未使用的材质")
            
        if clear_worlds:
            result_parts.append(f"已删除 {deleted_worlds} 个未使用的世界环境")
            
        if not result_parts:
            result_text = f"场景 '{scene_name}' 没有执行任何清除操作"
        else:
            result_text = f"场景 '{scene_name}' 已清除: " + "，".join(result_parts)
            
        text_content = self.create_text_content(result_text)
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(ClearSceneHandler())
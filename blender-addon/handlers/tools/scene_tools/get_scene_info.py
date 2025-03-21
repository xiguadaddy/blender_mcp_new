"""
获取Blender场景信息的工具
"""

import bpy
from ..registry import register_tool
import json
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.GetSceneInfo")

class GetSceneInfoHandler(BaseToolHandler):
    """获取场景信息工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_get_scene_info"
        
    @property
    def description(self) -> Optional[str]:
        return "获取Blender场景的详细信息"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "scene_name": {
                    "type": "string",
                    "title": "场景名称",
                    "description": "要获取信息的场景名称（默认为当前活动场景）"
                },
                "include_objects": {
                    "type": "boolean",
                    "title": "包含对象",
                    "description": "是否包含场景中对象的详细信息",
                    "default": True
                },
                "include_materials": {
                    "type": "boolean",
                    "title": "包含材质",
                    "description": "是否包含场景中使用的材质信息",
                    "default": False
                },
                "include_world": {
                    "type": "boolean",
                    "title": "包含世界",
                    "description": "是否包含场景的世界环境信息",
                    "default": True
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
        """执行获取场景信息操作"""
        logger.info(f"获取场景信息，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._get_scene_info, arguments)
        
    def _get_scene_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中获取场景信息"""
        scene_name = arguments.get("scene_name")
        include_objects = arguments.get("include_objects", True)
        include_materials = arguments.get("include_materials", False)
        include_world = arguments.get("include_world", True)
        
        # 获取场景
        if scene_name:
            scene = bpy.data.scenes[scene_name]
        else:
            scene = bpy.context.scene
            scene_name = scene.name
        
        # 收集场景基本信息
        scene_info = {
            "name": scene.name,
            "is_active": (bpy.context.scene == scene),
            "render": {
                "resolution_x": scene.render.resolution_x,
                "resolution_y": scene.render.resolution_y,
                "resolution_percentage": scene.render.resolution_percentage,
                "engine": scene.render.engine,
                "fps": scene.render.fps
            },
            "animation": {
                "frame_start": scene.frame_start,
                "frame_end": scene.frame_end,
                "frame_current": scene.frame_current
            }
        }
        
        # 收集对象信息
        if include_objects:
            objects_info = []
            
            for obj in scene.objects:
                obj_info = {
                    "name": obj.name,
                    "type": obj.type,
                    "location": [obj.location.x, obj.location.y, obj.location.z],
                    "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
                    "scale": [obj.scale.x, obj.scale.y, obj.scale.z],
                    "visible": obj.visible_get()
                }
                
                # 特定类型的附加信息
                if obj.type == 'MESH':
                    obj_info["vertices_count"] = len(obj.data.vertices)
                    obj_info["faces_count"] = len(obj.data.polygons)
                    obj_info["materials"] = [
                        slot.material.name if slot.material else None
                        for slot in obj.material_slots
                    ]
                    
                elif obj.type == 'CAMERA':
                    obj_info["camera"] = {
                        "lens": obj.data.lens,
                        "type": obj.data.type,
                        "is_active": (scene.camera == obj)
                    }
                    
                elif obj.type == 'LIGHT':
                    obj_info["light"] = {
                        "type": obj.data.type,
                        "energy": obj.data.energy,
                        "color": [obj.data.color.r, obj.data.color.g, obj.data.color.b]
                    }
                    
                objects_info.append(obj_info)
                
            scene_info["objects"] = objects_info
            scene_info["objects_count"] = len(objects_info)
        
        # 收集材质信息
        if include_materials:
            # 收集场景中使用的所有材质
            used_materials = set()
            for obj in scene.objects:
                if obj.type == 'MESH':
                    for slot in obj.material_slots:
                        if slot.material:
                            used_materials.add(slot.material.name)
            
            materials_info = []
            for mat_name in used_materials:
                mat = bpy.data.materials[mat_name]
                mat_info = {
                    "name": mat.name,
                    "use_nodes": mat.use_nodes,
                    "users": mat.users
                }
                
                # 收集基本材质属性
                if mat.use_nodes:
                    principled_bsdf = mat.node_tree.nodes.get('Principled BSDF')
                    if principled_bsdf:
                        mat_info["base_color"] = [
                            principled_bsdf.inputs['Base Color'].default_value[0],
                            principled_bsdf.inputs['Base Color'].default_value[1],
                            principled_bsdf.inputs['Base Color'].default_value[2],
                            principled_bsdf.inputs['Base Color'].default_value[3]
                        ]
                        mat_info["metallic"] = principled_bsdf.inputs['Metallic'].default_value
                        mat_info["roughness"] = principled_bsdf.inputs['Roughness'].default_value
                        mat_info["specular"] = principled_bsdf.inputs['Specular'].default_value
                else:
                    mat_info["diffuse_color"] = [
                        mat.diffuse_color[0],
                        mat.diffuse_color[1],
                        mat.diffuse_color[2],
                        mat.diffuse_color[3]
                    ]
                
                materials_info.append(mat_info)
                
            scene_info["materials"] = materials_info
            scene_info["materials_count"] = len(materials_info)
        
        # 收集世界环境信息
        if include_world and scene.world:
            world = scene.world
            world_info = {
                "name": world.name,
                "use_nodes": world.use_nodes
            }
            
            if world.use_nodes:
                # 尝试找到世界节点中的背景节点
                background_node = None
                for node in world.node_tree.nodes:
                    if node.type == 'BACKGROUND':
                        background_node = node
                        break
                        
                if background_node:
                    world_info["background_strength"] = background_node.inputs['Strength'].default_value
                    world_info["background_color"] = [
                        background_node.inputs['Color'].default_value[0],
                        background_node.inputs['Color'].default_value[1],
                        background_node.inputs['Color'].default_value[2]
                    ]
            
            scene_info["world"] = world_info
        
        # 创建结果信息
        scene_json = json.dumps(scene_info, indent=2)
        text_content = self.create_text_content(f"场景 '{scene_name}' 信息:\n{scene_json}")
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(GetSceneInfoHandler())
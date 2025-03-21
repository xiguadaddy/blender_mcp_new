import bpy
import logging
from typing import Any, Dict, List, Optional
from mathutils import Vector

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils
from ..registry import register_tool

# 获取日志器
logger = logging.getLogger("BlenderMCP.CreateObject")

# 在导入时输出日志，用于调试
logger.info("正在加载创建对象工具模块")

class CreateObjectHandler(BaseToolHandler):
    """创建3D对象工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_create_object"
        
    @property
    def description(self) -> Optional[str]:
        return "创建3D对象，如立方体、球体、平面等"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object_type": {
                    "type": "string",
                    "title": "对象类型",
                    "description": "要创建的3D对象类型",
                    "enum": ["cube", "sphere", "plane", "cylinder", "cone", "torus", "empty"]
                },
                "name": {
                    "type": "string",
                    "title": "名称",
                    "description": "新对象的名称"
                },
                "location": {
                    "type": "array",
                    "title": "位置",
                    "description": "对象的位置坐标 [x, y, z]",
                    "items": {
                        "type": "number"
                    }
                },
                "size": {
                    "type": "number",
                    "title": "尺寸",
                    "description": "对象的整体尺寸"
                }
            },
            "required": ["object_type"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查对象类型
        object_type = arguments.get("object_type")
        if not object_type:
            return "缺少对象类型参数"
            
        valid_types = ["cube", "sphere", "plane", "cylinder", "cone", "torus", "empty"]
        if object_type not in valid_types:
            return f"无效的对象类型: {object_type}，有效类型: {', '.join(valid_types)}"
            
        # 检查位置参数
        location = arguments.get("location")
        if location and not (isinstance(location, list) and len(location) == 3 and all(isinstance(v, (int, float)) for v in location)):
            return "位置参数必须是包含3个数字的数组 [x, y, z]"
            
        # 检查尺寸参数
        size = arguments.get("size")
        if size and not isinstance(size, (int, float)):
            return "尺寸参数必须是数字"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行创建对象操作"""
        logger.info(f"创建对象，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._create_object, arguments)
        
    def _create_object(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中创建对象"""
        object_type = arguments.get("object_type")
        name = arguments.get("name", f"新{object_type}")
        location = Vector(arguments.get("location", [0, 0, 0]))
        size = arguments.get("size", 1.0)
        
        # 创建对象
        if object_type == "cube":
            bpy.ops.mesh.primitive_cube_add(size=size, location=location)
        elif object_type == "sphere":
            bpy.ops.mesh.primitive_uv_sphere_add(radius=size/2, location=location)
        elif object_type == "plane":
            bpy.ops.mesh.primitive_plane_add(size=size, location=location)
        elif object_type == "cylinder":
            bpy.ops.mesh.primitive_cylinder_add(radius=size/2, depth=size, location=location)
        elif object_type == "cone":
            bpy.ops.mesh.primitive_cone_add(radius1=size/2, depth=size, location=location)
        elif object_type == "torus":
            bpy.ops.mesh.primitive_torus_add(major_radius=size/2, minor_radius=size/4, location=location)
        elif object_type == "empty":
            bpy.ops.object.empty_add(type='PLAIN_AXES', radius=size, location=location)
        
        # 设置对象名称
        created_object = bpy.context.active_object
        created_object.name = name
        
        # 创建成功响应
        text_content = self.create_text_content(f"已创建 {object_type} 对象: {name}")
        
        # 返回结果
        return self.create_result([text_content])

# 在导入时自动注册工具实例
logger.info("正在注册创建对象工具...")
register_tool(CreateObjectHandler())
logger.info("创建对象工具注册完成") 
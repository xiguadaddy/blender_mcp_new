"""
变换Blender对象的工具
"""

import bpy
from ..registry import register_tool
import logging
import mathutils
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.TransformObject")

class TransformObjectHandler(BaseToolHandler):
    """变换3D对象工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_transform_object"
        
    @property
    def description(self) -> Optional[str]:
        return "变换3D对象的位置、旋转或缩放"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "要变换的对象名称"
                },
                "location": {
                    "type": "array",
                    "title": "位置",
                    "description": "对象的位置坐标 [x, y, z]",
                    "items": {
                        "type": "number"
                    }
                },
                "rotation": {
                    "type": "array",
                    "title": "旋转",
                    "description": "对象的旋转角度（弧度）[x, y, z]",
                    "items": {
                        "type": "number"
                    }
                },
                "scale": {
                    "type": "array",
                    "title": "缩放",
                    "description": "对象的缩放值 [x, y, z]",
                    "items": {
                        "type": "number"
                    }
                },
                "relative": {
                    "type": "boolean",
                    "title": "相对变换",
                    "description": "是否相对于当前变换而不是绝对值",
                    "default": False
                }
            },
            "required": ["name"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查对象名称
        if not arguments.get("name"):
            return "必须提供对象名称"
            
        # 检查变换参数
        location = arguments.get("location")
        if location and not (isinstance(location, list) and len(location) == 3 and all(isinstance(v, (int, float)) for v in location)):
            return "位置参数必须是包含3个数字的数组 [x, y, z]"
            
        rotation = arguments.get("rotation")
        if rotation and not (isinstance(rotation, list) and len(rotation) == 3 and all(isinstance(v, (int, float)) for v in rotation)):
            return "旋转参数必须是包含3个数字的数组 [x, y, z]"
            
        scale = arguments.get("scale")
        if scale and not (isinstance(scale, list) and len(scale) == 3 and all(isinstance(v, (int, float)) for v in scale)):
            return "缩放参数必须是包含3个数字的数组 [x, y, z]"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行变换对象操作"""
        logger.info(f"变换对象，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._transform_object, arguments)
        
    def _transform_object(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中变换对象"""
        obj_name = arguments.get("name")
        location = arguments.get("location")
        rotation = arguments.get("rotation")
        scale = arguments.get("scale")
        relative = arguments.get("relative", False)
        
        # 检查对象是否存在
        if obj_name not in bpy.data.objects:
            text_content = self.create_text_content(f"找不到对象: {obj_name}")
            return self.create_result([text_content], is_error=True)
        
        # 获取对象
        obj = bpy.data.objects[obj_name]
        
        # 应用变换
        if location:
            if relative:
                # 相对位移
                obj.location.x += location[0]
                obj.location.y += location[1]
                obj.location.z += location[2]
            else:
                # 绝对位置
                obj.location = mathutils.Vector(location)
        
        if rotation:
            if relative:
                # 相对旋转
                obj.rotation_euler.x += rotation[0]
                obj.rotation_euler.y += rotation[1]
                obj.rotation_euler.z += rotation[2]
            else:
                # 绝对旋转
                obj.rotation_euler = mathutils.Euler(rotation)
        
        if scale:
            if relative:
                # 相对缩放
                obj.scale.x *= scale[0]
                obj.scale.y *= scale[1]
                obj.scale.z *= scale[2]
            else:
                # 绝对缩放
                obj.scale = mathutils.Vector(scale)
        
        # 更新场景
        bpy.context.view_layer.update()
        
        # 创建结果信息
        text_content = self.create_text_content(f"已变换对象: {obj_name}")
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(TransformObjectHandler())
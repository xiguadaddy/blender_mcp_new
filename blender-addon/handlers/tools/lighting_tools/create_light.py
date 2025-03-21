"""
创建Blender灯光的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.CreateLight")

class CreateLightHandler(BaseToolHandler):
    """创建灯光工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_create_light"
        
    @property
    def description(self) -> Optional[str]:
        return "创建新的灯光并设置其属性"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "title": "灯光名称",
                    "description": "新灯光的名称"
                },
                "light_type": {
                    "type": "string",
                    "title": "灯光类型",
                    "description": "灯光的类型",
                    "enum": ["POINT", "SUN", "SPOT", "AREA"],
                    "default": "POINT"
                },
                "location": {
                    "type": "array",
                    "title": "位置",
                    "description": "灯光的位置坐标 [x, y, z]",
                    "items": {
                        "type": "number"
                    },
                    "default": [0, 0, 3]
                },
                "rotation": {
                    "type": "array",
                    "title": "旋转",
                    "description": "灯光的旋转角度（弧度）[x, y, z]",
                    "items": {
                        "type": "number"
                    },
                    "default": [0, 0, 0]
                },
                "energy": {
                    "type": "number",
                    "title": "强度",
                    "description": "灯光的能量/强度",
                    "default": 1000
                },
                "color": {
                    "type": "array",
                    "title": "颜色",
                    "description": "灯光的RGB颜色 [r, g, b]",
                    "items": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1
                    },
                    "default": [1, 1, 1]
                },
                "size": {
                    "type": "number",
                    "title": "尺寸",
                    "description": "灯光的尺寸 (对点光源是半径，对区域光源是面积尺寸)",
                    "default": 1.0
                },
                "use_shadow": {
                    "type": "boolean",
                    "title": "启用阴影",
                    "description": "灯光是否产生阴影",
                    "default": True
                }
            }
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查灯光类型
        light_type = arguments.get("light_type", "POINT")
        valid_types = ["POINT", "SUN", "SPOT", "AREA"]
        if light_type not in valid_types:
            return f"不支持的灯光类型: {light_type}，有效类型: {', '.join(valid_types)}"
            
        # 检查位置参数
        location = arguments.get("location")
        if location and not (isinstance(location, list) and len(location) == 3 and all(isinstance(v, (int, float)) for v in location)):
            return "位置参数必须是包含3个数字的数组 [x, y, z]"
            
        # 检查旋转参数
        rotation = arguments.get("rotation")
        if rotation and not (isinstance(rotation, list) and len(rotation) == 3 and all(isinstance(v, (int, float)) for v in rotation)):
            return "旋转参数必须是包含3个数字的数组 [x, y, z]"
            
        # 检查颜色参数
        color = arguments.get("color")
        if color and not (isinstance(color, list) and len(color) == 3 and all(isinstance(v, (int, float)) and 0 <= v <= 1 for v in color)):
            return "颜色参数必须是包含3个在0-1范围内的数字的数组 [r, g, b]"
            
        # 检查能量参数
        energy = arguments.get("energy")
        if energy is not None and (not isinstance(energy, (int, float)) or energy < 0):
            return "能量参数必须是非负数"
            
        # 检查尺寸参数
        size = arguments.get("size")
        if size is not None and (not isinstance(size, (int, float)) or size <= 0):
            return "尺寸参数必须是正数"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行创建灯光操作"""
        logger.info(f"创建灯光，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._create_light, arguments)
        
    def _create_light(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中创建灯光"""
        name = arguments.get("name", "新灯光")
        light_type = arguments.get("light_type", "POINT")
        location = arguments.get("location", [0, 0, 3])
        rotation = arguments.get("rotation", [0, 0, 0])
        energy = arguments.get("energy", 1000)
        color = arguments.get("color", [1, 1, 1])
        size = arguments.get("size", 1.0)
        use_shadow = arguments.get("use_shadow", True)
        
        # 创建灯光数据
        light_data = bpy.data.lights.new(name=f"{name}_数据", type=light_type)
        
        # 设置灯光属性
        light_data.energy = energy
        light_data.color = color
        light_data.use_shadow = use_shadow
        
        # 特定灯光类型的设置
        if light_type == "POINT":
            light_data.shadow_soft_size = size
        elif light_type == "SUN":
            light_data.angle = size * 0.01  # 转换为合理的角度
        elif light_type == "SPOT":
            light_data.shadow_soft_size = size * 0.5
            light_data.spot_size = 1.0  # 默认聚光角度
            light_data.spot_blend = 0.15  # 默认边缘柔和度
        elif light_type == "AREA":
            light_data.size = size
            light_data.shape = 'SQUARE'  # 默认形状
        
        # 创建灯光对象
        light_obj = bpy.data.objects.new(name, light_data)
        
        # 设置位置和旋转
        light_obj.location = location
        light_obj.rotation_euler = rotation
        
        # 添加到场景
        bpy.context.collection.objects.link(light_obj)
        
        # 创建结果信息
        text_content = self.create_text_content(
            f"已创建{self._get_light_type_name(light_type)}: {light_obj.name}\n"
            f"位置: {location}\n"
            f"强度: {energy}\n"
            f"颜色: RGB{color}"
        )
        
        # 返回结果
        return self.create_result([text_content])
        
    def _get_light_type_name(self, light_type: str) -> str:
        """获取灯光类型的中文名称"""
        type_names = {
            "POINT": "点光源",
            "SUN": "太阳光",
            "SPOT": "聚光灯",
            "AREA": "面光源"
        }
        return type_names.get(light_type, light_type)


# 在导入时自动注册工具实例
register_tool(CreateLightHandler())
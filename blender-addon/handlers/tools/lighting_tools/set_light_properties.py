"""
设置Blender灯光属性的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.SetLightProperties")

class SetLightPropertiesHandler(BaseToolHandler):
    """设置灯光属性工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_set_light_properties"
        
    @property
    def description(self) -> Optional[str]:
        return "修改灯光的各种属性，如强度、颜色等"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "light_name": {
                    "type": "string",
                    "title": "灯光名称",
                    "description": "要修改的灯光名称"
                },
                "energy": {
                    "type": "number",
                    "title": "强度",
                    "description": "灯光的能量/强度"
                },
                "color": {
                    "type": "array",
                    "title": "颜色",
                    "description": "灯光的RGB颜色 [r, g, b]",
                    "items": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1
                    }
                },
                "size": {
                    "type": "number",
                    "title": "尺寸",
                    "description": "灯光的尺寸 (对点光源是半径，对区域光源是面积尺寸)"
                },
                "use_shadow": {
                    "type": "boolean",
                    "title": "启用阴影",
                    "description": "灯光是否产生阴影"
                },
                "shadow_soft_size": {
                    "type": "number",
                    "title": "阴影柔和度",
                    "description": "灯光的阴影柔和度尺寸"
                },
                "spot_size": {
                    "type": "number",
                    "title": "聚光角度",
                    "description": "聚光灯的光束角度（弧度）",
                    "minimum": 0,
                    "maximum": 3.14159
                },
                "spot_blend": {
                    "type": "number",
                    "title": "聚光混合",
                    "description": "聚光灯的边缘混合因子",
                    "minimum": 0,
                    "maximum": 1
                },
                "area_shape": {
                    "type": "string",
                    "title": "面光源形状",
                    "description": "面光源的形状",
                    "enum": ["SQUARE", "RECTANGLE", "DISK", "ELLIPSE"]
                },
                "area_size_y": {
                    "type": "number",
                    "title": "面光源Y尺寸",
                    "description": "矩形或椭圆面光源的Y尺寸（对于RECTANGLE或ELLIPSE）"
                }
            },
            "required": ["light_name"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查灯光名称
        if not arguments.get("light_name"):
            return "必须提供灯光名称"
            
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
            
        # 检查聚光灯角度
        spot_size = arguments.get("spot_size")
        if spot_size is not None and (not isinstance(spot_size, (int, float)) or spot_size < 0 or spot_size > 3.14159):
            return "聚光角度必须在0到π之间"
            
        # 检查聚光混合
        spot_blend = arguments.get("spot_blend")
        if spot_blend is not None and (not isinstance(spot_blend, (int, float)) or spot_blend < 0 or spot_blend > 1):
            return "聚光混合必须在0到1之间"
            
        # 检查面光源形状
        area_shape = arguments.get("area_shape")
        if area_shape and area_shape not in ["SQUARE", "RECTANGLE", "DISK", "ELLIPSE"]:
            return "面光源形状必须是 'SQUARE'、'RECTANGLE'、'DISK' 或 'ELLIPSE'"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行设置灯光属性操作"""
        logger.info(f"设置灯光属性，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._set_light_properties, arguments)
        
    def _set_light_properties(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中设置灯光属性"""
        light_name = arguments.get("light_name")
        
        # 检查灯光是否存在
        if light_name not in bpy.data.objects:
            text_content = self.create_text_content(f"找不到灯光: {light_name}")
            return self.create_result([text_content], is_error=True)
        
        # 获取灯光对象
        light_obj = bpy.data.objects[light_name]
        
        # 确保对象是灯光类型
        if light_obj.type != 'LIGHT':
            text_content = self.create_text_content(f"对象 '{light_name}' 不是灯光")
            return self.create_result([text_content], is_error=True)
        
        # 获取灯光数据
        light_data = light_obj.data
        light_type = light_data.type  # 获取灯光类型
        
        # 记录修改的属性
        modified_props = []
        
        # 设置灯光属性
        if "energy" in arguments:
            light_data.energy = arguments["energy"]
            modified_props.append(f"强度: {arguments['energy']}")
            
        if "color" in arguments:
            light_data.color = arguments["color"]
            modified_props.append(f"颜色: RGB{arguments['color']}")
            
        if "use_shadow" in arguments:
            light_data.use_shadow = arguments["use_shadow"]
            modified_props.append(f"启用阴影: {'是' if arguments['use_shadow'] else '否'}")
            
        if "shadow_soft_size" in arguments:
            light_data.shadow_soft_size = arguments["shadow_soft_size"]
            modified_props.append(f"阴影柔和度: {arguments['shadow_soft_size']}")
            
        # 特定灯光类型的属性
        if light_type == "SPOT":
            if "spot_size" in arguments:
                light_data.spot_size = arguments["spot_size"]
                modified_props.append(f"聚光角度: {arguments['spot_size']}")
                
            if "spot_blend" in arguments:
                light_data.spot_blend = arguments["spot_blend"]
                modified_props.append(f"聚光混合: {arguments['spot_blend']}")
                
        elif light_type == "AREA":
            if "size" in arguments:
                light_data.size = arguments["size"]
                modified_props.append(f"尺寸: {arguments['size']}")
                
            if "area_shape" in arguments:
                light_data.shape = arguments["area_shape"]
                modified_props.append(f"面光源形状: {arguments['area_shape']}")
                
            if "area_size_y" in arguments and light_data.shape in ['RECTANGLE', 'ELLIPSE']:
                light_data.size_y = arguments["area_size_y"]
                modified_props.append(f"面光源Y尺寸: {arguments['area_size_y']}")
                
        else:  # POINT, SUN
            if "size" in arguments:
                if light_type == "POINT":
                    light_data.shadow_soft_size = arguments["size"]
                    modified_props.append(f"点光源尺寸: {arguments['size']}")
                elif light_type == "SUN":
                    light_data.angle = arguments["size"] * 0.01
                    modified_props.append(f"太阳光角度: {arguments['size'] * 0.01}")
        
        # 创建结果信息
        if modified_props:
            properties_text = "\n".join(modified_props)
            text_content = self.create_text_content(f"已修改{self._get_light_type_name(light_type)} '{light_name}' 的属性:\n{properties_text}")
        else:
            text_content = self.create_text_content(f"未修改灯光 '{light_name}' 的任何属性")
        
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
register_tool(SetLightPropertiesHandler())
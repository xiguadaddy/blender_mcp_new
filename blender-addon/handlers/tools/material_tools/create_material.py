"""
创建Blender材质的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.CreateMaterial")

class CreateMaterialHandler(BaseToolHandler):
    """创建材质工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_create_material"
        
    @property
    def description(self) -> Optional[str]:
        return "创建新的Blender材质"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "title": "材质名称",
                    "description": "新材质的名称"
                },
                "color": {
                    "type": "array",
                    "title": "基础颜色",
                    "description": "RGBA颜色值 [r, g, b, a]",
                    "items": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1
                    },
                    "default": [0.8, 0.8, 0.8, 1.0]
                },
                "metallic": {
                    "type": "number",
                    "title": "金属度",
                    "description": "材质的金属度 (0-1)",
                    "minimum": 0,
                    "maximum": 1,
                    "default": 0.0
                },
                "roughness": {
                    "type": "number",
                    "title": "粗糙度",
                    "description": "材质的粗糙度 (0-1)",
                    "minimum": 0,
                    "maximum": 1,
                    "default": 0.5
                }
            }
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 验证颜色参数
        color = arguments.get("color")
        if color and not (isinstance(color, list) and len(color) == 4 and all(isinstance(v, (int, float)) and 0 <= v <= 1 for v in color)):
            return "颜色参数必须是包含4个在0-1范围内的数字的数组 [r, g, b, a]"
            
        # 验证金属度
        metallic = arguments.get("metallic")
        if metallic is not None and not (isinstance(metallic, (int, float)) and 0 <= metallic <= 1):
            return "金属度必须是0-1范围内的数字"
            
        # 验证粗糙度
        roughness = arguments.get("roughness")
        if roughness is not None and not (isinstance(roughness, (int, float)) and 0 <= roughness <= 1):
            return "粗糙度必须是0-1范围内的数字"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行创建材质操作"""
        logger.info(f"创建材质，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._create_material, arguments)
        
    def _create_material(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中创建材质"""
        name = arguments.get("name", "新材质")
        color = arguments.get("color", [0.8, 0.8, 0.8, 1.0])
        metallic = arguments.get("metallic", 0.0)
        roughness = arguments.get("roughness", 0.5)
        
        # 创建新材质
        mat = bpy.data.materials.new(name=name)
        
        # 启用节点
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        
        # 获取主要着色器节点
        principled_bsdf = nodes.get('Principled BSDF')
        
        if principled_bsdf:
            # 设置基础属性
            principled_bsdf.inputs['Base Color'].default_value = color
            principled_bsdf.inputs['Metallic'].default_value = metallic
            principled_bsdf.inputs['Roughness'].default_value = roughness
        
        # 创建结果信息
        text_content = self.create_text_content(f"已创建材质: {mat.name}")
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(CreateMaterialHandler())
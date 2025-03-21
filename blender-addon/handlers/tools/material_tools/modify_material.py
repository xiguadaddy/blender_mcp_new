"""
修改Blender材质属性的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.ModifyMaterial")

class ModifyMaterialHandler(BaseToolHandler):
    """修改材质属性工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_modify_material"
        
    @property
    def description(self) -> Optional[str]:
        return "修改现有Blender材质的属性"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "title": "材质名称",
                    "description": "要修改的材质名称"
                },
                "new_name": {
                    "type": "string",
                    "title": "新材质名称",
                    "description": "材质的新名称（可选）"
                },
                "color": {
                    "type": "array",
                    "title": "基础颜色",
                    "description": "RGBA颜色值 [r, g, b, a]",
                    "items": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1
                    }
                },
                "metallic": {
                    "type": "number",
                    "title": "金属度",
                    "description": "材质的金属度 (0-1)",
                    "minimum": 0,
                    "maximum": 1
                },
                "roughness": {
                    "type": "number",
                    "title": "粗糙度",
                    "description": "材质的粗糙度 (0-1)",
                    "minimum": 0,
                    "maximum": 1
                },
                "specular": {
                    "type": "number",
                    "title": "高光强度",
                    "description": "材质的高光强度 (0-1)",
                    "minimum": 0,
                    "maximum": 1
                },
                "use_nodes": {
                    "type": "boolean",
                    "title": "使用节点",
                    "description": "是否使用节点材质系统"
                }
            },
            "required": ["name"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查材质名称
        if not arguments.get("name"):
            return "必须提供材质名称"
            
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
            
        # 验证高光
        specular = arguments.get("specular")
        if specular is not None and not (isinstance(specular, (int, float)) and 0 <= specular <= 1):
            return "高光强度必须是0-1范围内的数字"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行修改材质操作"""
        logger.info(f"修改材质，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._modify_material, arguments)
        
    def _modify_material(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中修改材质"""
        name = arguments.get("name")
        new_name = arguments.get("new_name")
        color = arguments.get("color")
        metallic = arguments.get("metallic")
        roughness = arguments.get("roughness")
        specular = arguments.get("specular")
        use_nodes = arguments.get("use_nodes")
        
        # 检查材质是否存在
        if name not in bpy.data.materials:
            text_content = self.create_text_content(f"找不到材质: {name}")
            return self.create_result([text_content], is_error=True)
        
        # 获取材质
        mat = bpy.data.materials[name]
        
        # 如果需要，修改使用节点状态
        if use_nodes is not None:
            mat.use_nodes = use_nodes
        
        # 如果使用节点，修改节点属性
        if mat.use_nodes:
            nodes = mat.node_tree.nodes
            principled_bsdf = nodes.get('Principled BSDF')
            
            if principled_bsdf:
                # 修改基础颜色
                if color:
                    principled_bsdf.inputs['Base Color'].default_value = color
                
                # 修改金属度
                if metallic is not None:
                    principled_bsdf.inputs['Metallic'].default_value = metallic
                
                # 修改粗糙度
                if roughness is not None:
                    principled_bsdf.inputs['Roughness'].default_value = roughness
                
                # 修改高光
                if specular is not None:
                    principled_bsdf.inputs['Specular'].default_value = specular
        else:
            # 非节点材质，使用传统属性
            if color:
                mat.diffuse_color = color
                
            if specular is not None:
                mat.specular_intensity = specular
        
        # 如果需要，重命名材质
        if new_name:
            old_name = mat.name
            mat.name = new_name
            name = mat.name  # 获取实际名称（可能与请求的新名称不同，如果有重名）
        
        # 创建结果信息
        if new_name:
            text_content = self.create_text_content(f"已修改材质并重命名: {name}")
        else:
            text_content = self.create_text_content(f"已修改材质: {name}")
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(ModifyMaterialHandler())
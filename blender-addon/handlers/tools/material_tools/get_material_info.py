"""
获取Blender材质信息的工具
"""

import bpy
from ..registry import register_tool
import logging
import json
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.GetMaterialInfo")

class GetMaterialInfoHandler(BaseToolHandler):
    """获取材质信息工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_get_material_info"
        
    @property
    def description(self) -> Optional[str]:
        return "获取Blender材质的详细信息"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "title": "材质名称",
                    "description": "要获取信息的材质名称"
                },
                "all": {
                    "type": "boolean",
                    "title": "所有材质",
                    "description": "是否获取所有材质的信息",
                    "default": False
                }
            }
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 如果既没有提供材质名称，也没有设置获取全部标志，则返回错误
        if not arguments.get("name") and not arguments.get("all"):
            return "需要提供材质名称或设置获取全部标志"
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行获取材质信息操作"""
        logger.info(f"获取材质信息，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._get_material_info, arguments)
        
    def _get_material_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中获取材质信息"""
        material_name = arguments.get("name")
        get_all = arguments.get("all", False)
        
        # 存储材质信息
        material_infos = []
        
        if get_all:
            # 获取所有材质信息
            for mat in bpy.data.materials:
                material_infos.append(self._extract_material_info(mat))
            
            # 创建结果信息
            materials_json = json.dumps(material_infos, indent=2)
            text_content = self.create_text_content(f"已获取全部材质信息，共 {len(material_infos)} 个:\n{materials_json}")
            
        elif material_name:
            # 获取指定材质的信息
            if material_name in bpy.data.materials:
                mat = bpy.data.materials[material_name]
                material_info = self._extract_material_info(mat)
                material_infos.append(material_info)
                
                # 创建结果信息
                material_json = json.dumps(material_info, indent=2)
                text_content = self.create_text_content(f"材质信息 - {material_name}:\n{material_json}")
            else:
                text_content = self.create_text_content(f"找不到材质: {material_name}")
                return self.create_result([text_content], is_error=True)
        
        else:
            text_content = self.create_text_content("未提供有效的获取材质信息参数")
            return self.create_result([text_content], is_error=True)
        
        # 返回结果
        return self.create_result([text_content])
        
    def _extract_material_info(self, material) -> Dict[str, Any]:
        """从材质中提取信息"""
        info = {
            "name": material.name,
            "use_nodes": material.use_nodes,
            "users": material.users
        }
        
        # 如果使用节点，提取节点信息
        if material.use_nodes:
            try:
                principled_bsdf = material.node_tree.nodes.get('Principled BSDF')
                if principled_bsdf:
                    info["properties"] = {
                        "base_color": [
                            principled_bsdf.inputs['Base Color'].default_value[0],
                            principled_bsdf.inputs['Base Color'].default_value[1],
                            principled_bsdf.inputs['Base Color'].default_value[2],
                            principled_bsdf.inputs['Base Color'].default_value[3]
                        ],
                        "metallic": principled_bsdf.inputs['Metallic'].default_value,
                        "roughness": principled_bsdf.inputs['Roughness'].default_value,
                        "specular": principled_bsdf.inputs['Specular'].default_value,
                    }
            except:
                info["properties"] = {"error": "无法获取节点属性"}
        else:
            # 非节点材质，使用传统属性
            info["properties"] = {
                "diffuse_color": [
                    material.diffuse_color[0],
                    material.diffuse_color[1],
                    material.diffuse_color[2],
                    material.diffuse_color[3]
                ],
                "specular_intensity": material.specular_intensity
            }
        
        # 查找使用此材质的对象
        users = []
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                for slot in obj.material_slots:
                    if slot.material == material:
                        users.append(obj.name)
                        break
        
        info["used_by_objects"] = users
        
        return info


# 在导入时自动注册工具实例
register_tool(GetMaterialInfoHandler())
"""
删除Blender材质的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.DeleteMaterial")

class DeleteMaterialHandler(BaseToolHandler):
    """删除材质工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_delete_material"
        
    @property
    def description(self) -> Optional[str]:
        return "从Blender中删除一个或多个材质"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "title": "材质名称",
                    "description": "要删除的材质名称"
                },
                "all": {
                    "type": "boolean",
                    "title": "删除全部",
                    "description": "是否删除所有材质",
                    "default": False
                },
                "unused": {
                    "type": "boolean",
                    "title": "仅删除未使用的",
                    "description": "是否仅删除未使用的材质",
                    "default": False
                }
            }
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 如果既没有提供材质名称，也没有设置删除全部标志或仅删除未使用标志，则返回错误
        if not arguments.get("name") and not arguments.get("all") and not arguments.get("unused"):
            return "需要提供材质名称、设置删除全部标志或设置仅删除未使用标志"
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行删除材质操作"""
        logger.info(f"删除材质，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._delete_material, arguments)
        
    def _delete_material(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中删除材质"""
        material_name = arguments.get("name", None)
        delete_all = arguments.get("all", False)
        delete_unused = arguments.get("unused", False)
        
        deleted_materials = []
        
        if delete_all:
            # 删除所有材质
            for mat in list(bpy.data.materials):
                mat_name = mat.name
                bpy.data.materials.remove(mat)
                deleted_materials.append(mat_name)
            
            text_content = self.create_text_content(f"已删除所有材质，共 {len(deleted_materials)} 个")
            
        elif delete_unused:
            # 收集所有使用中的材质
            used_materials = set()
            for obj in bpy.data.objects:
                if obj.type == 'MESH':
                    for slot in obj.material_slots:
                        if slot.material:
                            used_materials.add(slot.material.name)
            
            # 删除未使用的材质
            for mat in list(bpy.data.materials):
                if mat.name not in used_materials:
                    mat_name = mat.name
                    bpy.data.materials.remove(mat)
                    deleted_materials.append(mat_name)
            
            text_content = self.create_text_content(f"已删除未使用的材质，共 {len(deleted_materials)} 个")
            
        elif material_name:
            # 删除特定材质
            if material_name in bpy.data.materials:
                mat = bpy.data.materials[material_name]
                bpy.data.materials.remove(mat)
                deleted_materials.append(material_name)
                
                text_content = self.create_text_content(f"已删除材质: {material_name}")
            else:
                text_content = self.create_text_content(f"找不到材质: {material_name}")
                return self.create_result([text_content], is_error=True)
        
        else:
            text_content = self.create_text_content("未提供有效的删除材质参数")
            return self.create_result([text_content], is_error=True)
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(DeleteMaterialHandler())
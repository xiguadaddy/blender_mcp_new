"""
将材质分配给对象的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.AssignMaterial")

class AssignMaterialHandler(BaseToolHandler):
    """将材质分配给对象的工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_assign_material"
        
    @property
    def description(self) -> Optional[str]:
        return "将材质分配给一个或多个3D对象"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "material_name": {
                    "type": "string",
                    "title": "材质名称",
                    "description": "要分配的材质名称"
                },
                "object_name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "要分配材质的对象名称"
                },
                "object_names": {
                    "type": "array",
                    "title": "对象名称列表",
                    "description": "要分配材质的多个对象名称",
                    "items": {
                        "type": "string"
                    }
                },
                "slot_index": {
                    "type": "integer",
                    "title": "材质槽索引",
                    "description": "要分配到的材质槽索引，默认为0",
                    "default": 0
                },
                "create_if_missing": {
                    "type": "boolean",
                    "title": "不存在时创建",
                    "description": "如果材质不存在，是否创建新材质",
                    "default": False
                }
            },
            "required": ["material_name"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查材质名称
        if not arguments.get("material_name"):
            return "必须提供材质名称"
            
        # 检查对象名称
        if not arguments.get("object_name") and not arguments.get("object_names"):
            return "必须提供对象名称或对象名称列表"
            
        # 检查槽索引
        slot_index = arguments.get("slot_index")
        if slot_index is not None and not isinstance(slot_index, int):
            return "材质槽索引必须是整数"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行分配材质操作"""
        logger.info(f"分配材质，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._assign_material, arguments)
        
    def _assign_material(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中分配材质"""
        material_name = arguments.get("material_name")
        object_name = arguments.get("object_name")
        object_names = arguments.get("object_names", [])
        slot_index = arguments.get("slot_index", 0)
        create_if_missing = arguments.get("create_if_missing", False)
        
        # 如果提供了单个对象名称但没有提供列表，将单个名称加入列表
        if object_name and not object_names:
            object_names = [object_name]
        
        # 检查材质是否存在
        if material_name not in bpy.data.materials:
            if create_if_missing:
                # 创建新材质
                mat = bpy.data.materials.new(name=material_name)
                logger.info(f"创建新材质: {material_name}")
            else:
                text_content = self.create_text_content(f"找不到材质: {material_name}")
                return self.create_result([text_content], is_error=True)
        else:
            # 获取现有材质
            mat = bpy.data.materials[material_name]
        
        # 记录成功和失败的对象
        success_objects = []
        failed_objects = []
        
        # 分配材质给指定对象
        for obj_name in object_names:
            if obj_name in bpy.data.objects:
                obj = bpy.data.objects[obj_name]
                
                # 只对网格对象操作
                if obj.type == 'MESH':
                    # 确保有足够的材质槽
                    while len(obj.material_slots) <= slot_index:
                        obj.data.materials.append(None)
                    
                    # 分配材质
                    obj.material_slots[slot_index].material = mat
                    success_objects.append(obj_name)
                else:
                    failed_objects.append(f"{obj_name} (不是网格对象)")
            else:
                failed_objects.append(f"{obj_name} (不存在)")
        
        # 创建结果信息
        if success_objects:
            success_msg = f"已将材质 {material_name} 分配给 {len(success_objects)} 个对象"
            if failed_objects:
                text_content = self.create_text_content(f"{success_msg}，但 {len(failed_objects)} 个对象失败: {', '.join(failed_objects)}")
            else:
                text_content = self.create_text_content(success_msg)
        else:
            text_content = self.create_text_content(f"没有成功分配材质，所有对象都失败: {', '.join(failed_objects)}")
            return self.create_result([text_content], is_error=True)
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(AssignMaterialHandler())
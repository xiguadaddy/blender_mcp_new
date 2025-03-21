"""
列出Blender中的所有材质的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.ListMaterials")

class ListMaterialsHandler(BaseToolHandler):
    """列出材质工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_list_materials"
        
    @property
    def description(self) -> Optional[str]:
        return "列出Blender中的所有材质"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name_filter": {
                    "type": "string",
                    "title": "名称过滤",
                    "description": "可选的名称过滤条件（使用包含匹配）"
                }
            }
        }
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行列出材质操作"""
        logger.info(f"列出材质，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._list_materials, arguments)
        
    def _list_materials(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中列出材质"""
        name_filter = arguments.get("name_filter", "")
        
        # 收集材质信息
        materials_info = []
        for mat in bpy.data.materials:
            # 如果有过滤条件，检查材质名称是否匹配
            if name_filter and name_filter.lower() not in mat.name.lower():
                continue
                
            # 统计使用此材质的对象
            user_objects = []
            for obj in bpy.data.objects:
                if obj.type == 'MESH':
                    for slot in obj.material_slots:
                        if slot.material == mat:
                            user_objects.append(obj.name)
                            break
            
            # 添加材质信息
            materials_info.append({
                "name": mat.name,
                "users": mat.users,
                "used_by_objects": user_objects
            })
        
        # 创建结果文本
        if materials_info:
            materials_list = "\n".join([
                f"- {info['name']} (使用者: {info['users']}, 对象: {', '.join(info['used_by_objects']) if info['used_by_objects'] else '无'})"
                for info in materials_info
            ])
            
            text_content = self.create_text_content(f"找到 {len(materials_info)} 个材质:\n{materials_list}")
        else:
            if name_filter:
                text_content = self.create_text_content(f"没有找到匹配过滤条件 '{name_filter}' 的材质")
            else:
                text_content = self.create_text_content("场景中没有材质")
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(ListMaterialsHandler())
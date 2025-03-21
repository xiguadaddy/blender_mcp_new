"""
设置Blender网格顶点位置的工具
"""

import bpy
from ..registry import register_tool
import bmesh
import logging
from typing import Any, Dict, List, Optional
import mathutils

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.SetVertexPosition")

class SetVertexPositionHandler(BaseToolHandler):
    """设置顶点位置工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_set_vertex_position"
        
    @property
    def description(self) -> Optional[str]:
        return "设置网格对象中顶点的位置"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "要操作的网格对象名称"
                },
                "vertex_indices": {
                    "type": "array",
                    "title": "顶点索引",
                    "description": "要移动的顶点索引数组",
                    "items": {
                        "type": "integer"
                    }
                },
                "position": {
                    "type": "array",
                    "title": "位置",
                    "description": "顶点的新位置 [x, y, z]",
                    "items": {
                        "type": "number"
                    }
                },
                "offset": {
                    "type": "array",
                    "title": "偏移量",
                    "description": "顶点的位置偏移 [dx, dy, dz]",
                    "items": {
                        "type": "number"
                    }
                },
                "relative": {
                    "type": "boolean",
                    "title": "相对移动",
                    "description": "是否为相对于当前位置的移动",
                    "default": False
                }
            },
            "required": ["object_name"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查对象名称
        if not arguments.get("object_name"):
            return "必须提供对象名称"
            
        # 检查顶点索引
        vertex_indices = arguments.get("vertex_indices")
        if not vertex_indices or not isinstance(vertex_indices, list) or len(vertex_indices) == 0:
            return "必须提供至少一个顶点索引"
            
        # 检查位置和偏移参数
        position = arguments.get("position")
        offset = arguments.get("offset")
        
        if not position and not offset:
            return "必须提供位置或偏移参数"
            
        if position and not (isinstance(position, list) and len(position) == 3 and all(isinstance(v, (int, float)) for v in position)):
            return "位置参数必须是包含3个数字的数组 [x, y, z]"
            
        if offset and not (isinstance(offset, list) and len(offset) == 3 and all(isinstance(v, (int, float)) for v in offset)):
            return "偏移参数必须是包含3个数字的数组 [dx, dy, dz]"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行设置顶点位置操作"""
        logger.info(f"设置顶点位置，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._set_vertex_position, arguments)
        
    def _set_vertex_position(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中设置顶点位置"""
        object_name = arguments.get("object_name")
        vertex_indices = arguments.get("vertex_indices", [])
        position = arguments.get("position")
        offset = arguments.get("offset")
        relative = arguments.get("relative", False)
        
        # 检查对象是否存在
        if object_name not in bpy.data.objects:
            text_content = self.create_text_content(f"找不到对象: {object_name}")
            return self.create_result([text_content], is_error=True)
        
        # 获取对象
        obj = bpy.data.objects[object_name]
        
        # 确保对象是网格类型
        if obj.type != 'MESH':
            text_content = self.create_text_content(f"只能对网格对象操作，而 '{object_name}' 是 '{obj.type}' 类型")
            return self.create_result([text_content], is_error=True)
        
        # 获取网格数据
        mesh = obj.data
        
        # 检查顶点索引是否有效
        if any(idx < 0 or idx >= len(mesh.vertices) for idx in vertex_indices):
            text_content = self.create_text_content(f"顶点索引超出范围，对象 '{object_name}' 有 {len(mesh.vertices)} 个顶点")
            return self.create_result([text_content], is_error=True)
        
        # 移动顶点
        try:
            if position:
                # 设置绝对位置
                pos_vector = mathutils.Vector(position)
                for idx in vertex_indices:
                    if relative:
                        mesh.vertices[idx].co += pos_vector
                    else:
                        mesh.vertices[idx].co = pos_vector
            elif offset:
                # 应用偏移
                offset_vector = mathutils.Vector(offset)
                for idx in vertex_indices:
                    mesh.vertices[idx].co += offset_vector
            
            # 更新网格
            mesh.update()
            
            # 描述操作
            if position:
                if relative:
                    op_desc = f"相对移动 {len(vertex_indices)} 个顶点，位移: {position}"
                else:
                    op_desc = f"设置 {len(vertex_indices)} 个顶点的位置为 {position}"
            else:
                op_desc = f"偏移 {len(vertex_indices)} 个顶点，偏移量: {offset}"
            
            text_content = self.create_text_content(f"已在对象 '{object_name}' 上{op_desc}")
        except Exception as e:
            text_content = self.create_text_content(f"设置顶点位置时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(SetVertexPositionHandler())
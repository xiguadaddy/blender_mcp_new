"""
细分Blender网格的工具
"""

import bpy
from ..registry import register_tool
import bmesh
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.SubdivideMesh")

class SubdivideMeshHandler(BaseToolHandler):
    """细分网格工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_subdivide_mesh"
        
    @property
    def description(self) -> Optional[str]:
        return "细分网格对象的选定边或面"
        
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
                "cuts": {
                    "type": "integer",
                    "title": "切割数量",
                    "description": "要创建的切割数量",
                    "default": 1,
                    "minimum": 1,
                    "maximum": 10
                },
                "smoothness": {
                    "type": "number",
                    "title": "平滑度",
                    "description": "细分的平滑度",
                    "default": 0.0,
                    "minimum": 0.0,
                    "maximum": 1.0
                },
                "edge_indices": {
                    "type": "array",
                    "title": "边索引",
                    "description": "要细分的边索引数组",
                    "items": {
                        "type": "integer"
                    }
                },
                "face_indices": {
                    "type": "array",
                    "title": "面索引",
                    "description": "要细分的面索引数组",
                    "items": {
                        "type": "integer"
                    }
                },
                "all": {
                    "type": "boolean",
                    "title": "细分全部",
                    "description": "是否细分所有边或面",
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
            
        # 检查切割数量
        cuts = arguments.get("cuts", 1)
        if not isinstance(cuts, int) or cuts < 1 or cuts > 10:
            return "切割数量必须是1到10之间的整数"
            
        # 检查平滑度
        smoothness = arguments.get("smoothness", 0.0)
        if not isinstance(smoothness, (int, float)) or smoothness < 0.0 or smoothness > 1.0:
            return "平滑度必须是0到1之间的数值"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行细分网格操作"""
        logger.info(f"细分网格，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._subdivide_mesh, arguments)
        
    def _subdivide_mesh(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中细分网格"""
        object_name = arguments.get("object_name")
        cuts = arguments.get("cuts", 1)
        smoothness = arguments.get("smoothness", 0.0)
        edge_indices = arguments.get("edge_indices", [])
        face_indices = arguments.get("face_indices", [])
        use_all = arguments.get("all", False)
        
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
        
        # 确保对象是活动对象
        bpy.context.view_layer.objects.active = obj
        
        # 进入编辑模式
        bpy.ops.object.mode_set(mode='EDIT')
        
        # 创建bmesh实例
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        
        # 取消所有选择
        for edge in bm.edges:
            edge.select = False
        for face in bm.faces:
            face.select = False
        
        # 选择要细分的几何体
        if edge_indices:
            # 选择指定的边
            for idx in edge_indices:
                if idx < len(bm.edges):
                    bm.edges[idx].select = True
        elif face_indices:
            # 选择指定的面
            for idx in face_indices:
                if idx < len(bm.faces):
                    bm.faces[idx].select = True
        elif use_all:
            # 选择所有几何体
            bpy.ops.mesh.select_all(action='SELECT')
        else:
            # 默认选择所有面
            for face in bm.faces:
                face.select = True
        
        # 更新bmesh到网格
        bmesh.update_edit_mesh(me)
        
        # 执行细分操作
        try:
            bpy.ops.mesh.subdivide(number_cuts=cuts, smoothness=smoothness)
            
            # 计算结果信息
            if edge_indices:
                desc = f"{len(edge_indices)} 条边"
            elif face_indices:
                desc = f"{len(face_indices)} 个面"
            elif use_all:
                desc = "所有几何体"
            else:
                desc = "所有面"
            
            text_content = self.create_text_content(f"已细分对象 '{object_name}' 上的 {desc}，切割数: {cuts}，平滑度: {smoothness}")
        except Exception as e:
            text_content = self.create_text_content(f"细分网格时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
        finally:
            # 返回对象模式
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(SubdivideMeshHandler())
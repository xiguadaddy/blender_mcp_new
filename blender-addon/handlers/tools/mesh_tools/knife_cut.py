"""
执行Blender切刀工具操作的工具
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
logger = logging.getLogger("BlenderMCP.KnifeCut")

class KnifeCutHandler(BaseToolHandler):
    """切刀工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_knife_cut"
        
    @property
    def description(self) -> Optional[str]:
        return "在网格上执行切刀操作，创建新的边"
        
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
                "points": {
                    "type": "array",
                    "title": "切刀点",
                    "description": "切刀路径上的点坐标数组，每个点是 [x, y, z]",
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "number"
                        }
                    }
                },
                "cut_through": {
                    "type": "boolean",
                    "title": "穿透切割",
                    "description": "是否穿透整个网格切割",
                    "default": True
                }
            },
            "required": ["object_name", "points"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查对象名称
        if not arguments.get("object_name"):
            return "必须提供对象名称"
            
        # 检查切刀点
        points = arguments.get("points")
        if not points or not isinstance(points, list) or len(points) < 2:
            return "必须提供至少两个切刀点"
            
        # 验证每个点的格式
        for point in points:
            if not isinstance(point, list) or len(point) != 3 or not all(isinstance(v, (int, float)) for v in point):
                return "切刀点必须是 [x, y, z] 格式的坐标"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行切刀操作"""
        logger.info(f"执行切刀操作，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._knife_cut, arguments)
        
    def _knife_cut(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中执行切刀操作"""
        object_name = arguments.get("object_name")
        points = arguments.get("points", [])
        cut_through = arguments.get("cut_through", True)
        
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
        
        # 在对象空间中转换点坐标
        object_points = [mathutils.Vector(point) for point in points]
        
        # 尝试使用自定义的切刀操作
        try:
            # 使用bmesh.ops.bisect_plane替代knife_cut
            # 计算切割平面的法向量和位置
            if len(object_points) >= 3:
                # 如果有三个或更多点，使用前三个点确定平面
                v1 = object_points[0]
                v2 = object_points[1]
                v3 = object_points[2]
                
                # 计算平面法向量
                vec1 = v2 - v1
                vec2 = v3 - v1
                normal = vec1.cross(vec2).normalized()
                
                # 使用平面切割
                result = bmesh.ops.bisect_plane(
                    bm,
                    geom=bm.faces[:] + bm.edges[:] + bm.verts[:],
                    plane_co=v1,
                    plane_no=normal,
                    clear_inner=False,
                    clear_outer=False
                )
                
                # 更新网格
                bmesh.update_edit_mesh(me)
                
                text_content = self.create_text_content(f"已在对象 '{object_name}' 上执行平面切割，使用 {len(points)} 个点确定的平面")
            else:
                # 如果只有两个点，创建一条直线切割
                v1 = object_points[0]
                v2 = object_points[1]
                
                # 创建一个垂直于直线的平面
                direction = (v2 - v1).normalized()
                
                # 寻找一个不与方向平行的向量，用于构建平面法向量
                if abs(direction.x) < 0.5:
                    temp_vec = mathutils.Vector((1, 0, 0))
                else:
                    temp_vec = mathutils.Vector((0, 1, 0))
                
                # 计算平面法向量
                normal = direction.cross(temp_vec).normalized()
                
                # 在每个点位置执行平面切割
                for point in object_points:
                    result = bmesh.ops.bisect_plane(
                        bm,
                        geom=bm.faces[:] + bm.edges[:] + bm.verts[:],
                        plane_co=point,
                        plane_no=normal,
                        clear_inner=False,
                        clear_outer=False
                    )
                
                # 更新网格
                bmesh.update_edit_mesh(me)
                
                text_content = self.create_text_content(f"已在对象 '{object_name}' 上执行线段切割，使用 {len(points)} 个点")
        except Exception as e:
            text_content = self.create_text_content(f"执行切刀操作时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
        finally:
            # 返回对象模式
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(KnifeCutHandler())
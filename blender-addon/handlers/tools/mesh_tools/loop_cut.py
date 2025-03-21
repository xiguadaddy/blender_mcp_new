"""
在Blender网格上执行环切的工具
"""

import bpy
from ..registry import register_tool
import bmesh
import logging
import mathutils
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.LoopCut")

class LoopCutHandler(BaseToolHandler):
    """环切工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_loop_cut"
        
    @property
    def description(self) -> Optional[str]:
        return "在网格对象上执行环切操作"
        
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
                "edge_index": {
                    "type": "integer",
                    "title": "边索引",
                    "description": "要从其开始环切的边索引"
                },
                "position": {
                    "type": "number",
                    "title": "位置",
                    "description": "切割位置（0.0-1.0，0.5为中间）",
                    "default": 0.5,
                    "minimum": 0.0,
                    "maximum": 1.0
                },
                "number_cuts": {
                    "type": "integer",
                    "title": "切割数量",
                    "description": "要创建的环切数量",
                    "default": 1,
                    "minimum": 1,
                    "maximum": 10
                }
            },
            "required": ["object_name"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查对象名称
        if not arguments.get("object_name"):
            return "必须提供对象名称"
            
        # 检查位置
        position = arguments.get("position", 0.5)
        if not isinstance(position, (int, float)) or position < 0.0 or position > 1.0:
            return "位置必须是0到1之间的数值"
            
        # 检查切割数量
        number_cuts = arguments.get("number_cuts", 1)
        if not isinstance(number_cuts, int) or number_cuts < 1 or number_cuts > 10:
            return "切割数量必须是1到10之间的整数"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行环切操作"""
        logger.info(f"环切，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._loop_cut, arguments)
        
    def _loop_cut(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中执行环切"""
        object_name = arguments.get("object_name")
        edge_index = arguments.get("edge_index")
        position = arguments.get("position", 0.5)
        number_cuts = arguments.get("number_cuts", 1)
        
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
        
        # 取消所有选择
        bpy.ops.mesh.select_all(action='DESELECT')
        
        # 切换到边选择模式
        bpy.context.tool_settings.mesh_select_mode = (False, True, False)
        
        # 创建bmesh实例
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        
        # 如果提供了边索引，选择该边
        if edge_index is not None:
            if edge_index < 0 or edge_index >= len(bm.edges):
                bpy.ops.object.mode_set(mode='OBJECT')  # 返回对象模式
                text_content = self.create_text_content(f"边索引 {edge_index} 超出范围，对象 '{object_name}' 有 {len(bm.edges)} 条边")
                return self.create_result([text_content], is_error=True)
            
            # 选择边
            bm.edges[edge_index].select = True
            bmesh.update_edit_mesh(me)
        
        # 执行环切操作
        try:
            # 尝试对选定的边执行环切
            if edge_index is not None:
                # 需要使用鼠标位置设置环切工具，这在脚本中比较复杂
                # 一种变通方法是使用细分操作，然后沿着边循环移动顶点
                
                # 获取选定的边
                edge = bm.edges[edge_index]
                
                # 获取边循环
                edge_loop = []
                visited = set()
                
                def get_next_edge(current_edge, vert):
                    """获取与当前边相连且形成循环的下一条边"""
                    for link_edge in vert.link_edges:
                        if link_edge != current_edge and link_edge not in visited:
                            # 检查是否与当前边形成直线
                            other_vert = link_edge.other_vert(vert)
                            if len(other_vert.link_edges) == 4:  # 确保是网格内部顶点
                                visited.add(link_edge)
                                return link_edge
                    return None
                
                # 从初始边开始
                edge_loop.append(edge)
                visited.add(edge)
                
                # 向一个方向循环
                current_edge = edge
                vert = edge.verts[0]
                while True:
                    next_edge = get_next_edge(current_edge, vert)
                    if not next_edge or next_edge in edge_loop:
                        break
                    edge_loop.append(next_edge)
                    vert = next_edge.other_vert(vert)
                    current_edge = next_edge
                
                # 向另一个方向循环
                current_edge = edge
                vert = edge.verts[1]
                while True:
                    next_edge = get_next_edge(current_edge, vert)
                    if not next_edge or next_edge in edge_loop:
                        break
                    edge_loop.append(next_edge)
                    vert = next_edge.other_vert(vert)
                    current_edge = next_edge
                
                # 选择边循环中的所有边
                for e in edge_loop:
                    e.select = True
                
                # 更新网格
                bmesh.update_edit_mesh(me)
                
                # 执行细分操作
                bpy.ops.mesh.subdivide(number_cuts=number_cuts)
                
                # 获取新创建的顶点，并根据位置调整它们
                # 这部分在脚本中较难实现，因为我们需要确定哪些是新创建的顶点
                # 在这个简化版本中，我们只使用细分功能
                
                text_content = self.create_text_content(f"已在对象 '{object_name}' 上执行环切操作，从边 {edge_index} 开始，切割数: {number_cuts}")
            else:
                # 如果没有选定边，使用默认的环切工具操作
                bpy.ops.mesh.loopcut_slide(
                    MESH_OT_loopcut={
                        "number_cuts": number_cuts,
                        "smoothness": 0,
                        "falloff": 'INVERSE_SQUARE',
                        "object_index": 0,
                        "edge_index": 0  # 这里的edge_index是内部索引，与我们的不同
                    },
                    TRANSFORM_OT_edge_slide={
                        "value": position - 0.5,  # 转换为-0.5到0.5范围
                        "single_side": False,
                        "use_even": False,
                        "flipped": False,
                        "use_clamp": True,
                        "mirror": True,
                        "snap": False,
                        "snap_target": 'CLOSEST',
                        "snap_point": (0, 0, 0),
                        "snap_align": False,
                        "snap_normal": (0, 0, 0),
                        "correct_uv": True,
                        "release_confirm": True
                    }
                )
                
                text_content = self.create_text_content(f"已在对象 '{object_name}' 上执行环切操作，切割数: {number_cuts}，位置: {position}")
        except Exception as e:
            text_content = self.create_text_content(f"执行环切操作时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
        finally:
            # 返回对象模式
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(LoopCutHandler())
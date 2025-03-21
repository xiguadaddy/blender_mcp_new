"""
挤出Blender网格面的工具
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
logger = logging.getLogger("BlenderMCP.ExtrudeFaces")

class ExtrudeFacesHandler(BaseToolHandler):
    """挤出网格面工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_extrude_faces"
        
    @property
    def description(self) -> Optional[str]:
        return "挤出网格对象的选定面"
        
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
                "face_indices": {
                    "type": "array",
                    "title": "面索引",
                    "description": "要挤出的面索引数组",
                    "items": {
                        "type": "integer"
                    }
                },
                "distance": {
                    "type": "number",
                    "title": "挤出距离",
                    "description": "沿法线方向挤出的距离",
                    "default": 1.0
                },
                "direction": {
                    "type": "array",
                    "title": "挤出方向",
                    "description": "自定义挤出方向 [x, y, z]（覆盖法线方向）",
                    "items": {
                        "type": "number"
                    }
                },
                "individual": {
                    "type": "boolean",
                    "title": "单独挤出",
                    "description": "是否单独挤出每个面（而不是作为一个组）",
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
            
        # 检查方向参数
        direction = arguments.get("direction")
        if direction and not (isinstance(direction, list) and len(direction) == 3 and all(isinstance(v, (int, float)) for v in direction)):
            return "方向参数必须是包含3个数字的数组 [x, y, z]"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行挤出面操作"""
        logger.info(f"挤出面，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._extrude_faces, arguments)
        
    def _extrude_faces(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中挤出面"""
        object_name = arguments.get("object_name")
        face_indices = arguments.get("face_indices", [])
        distance = arguments.get("distance", 1.0)
        direction = arguments.get("direction")
        individual = arguments.get("individual", False)
        
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
        for face in bm.faces:
            face.select = False
        
        # 选择指定的面
        selected_faces = []
        
        if face_indices:
            for idx in face_indices:
                if idx < len(bm.faces):
                    face = bm.faces[idx]
                    face.select = True
                    selected_faces.append(face)
        else:
            # 如果没有提供面索引，选择所有面
            for face in bm.faces:
                face.select = True
                selected_faces.append(face)
        
        # 检查是否有选中的面
        if not selected_faces:
            bpy.ops.object.mode_set(mode='OBJECT')  # 返回对象模式
            text_content = self.create_text_content("没有找到要挤出的有效面")
            return self.create_result([text_content], is_error=True)
        
        # 执行挤出
        if individual:
            # 单独挤出每个面
            for face in selected_faces:
                # 取消所有选择
                for f in bm.faces:
                    f.select = False
                
                # 只选择当前面
                face.select = True
                
                # 执行挤出
                ret = bmesh.ops.extrude_face_region(bm, geom=[face])
                extruded_verts = [v for v in ret['geom'] if isinstance(v, bmesh.types.BMVert)]
                
                # 移动挤出的顶点
                if direction:
                    # 使用自定义方向
                    vec = mathutils.Vector(direction).normalized() * distance
                else:
                    # 使用面法线
                    vec = face.normal.normalized() * distance
                
                for v in extruded_verts:
                    v.co += vec
        else:
            # 作为一个组挤出
            ret = bmesh.ops.extrude_face_region(bm, geom=[face for face in selected_faces])
            extruded_verts = [v for v in ret['geom'] if isinstance(v, bmesh.types.BMVert)]
            
            if direction:
                # 使用自定义方向
                vec = mathutils.Vector(direction).normalized() * distance
                for v in extruded_verts:
                    v.co += vec
            else:
                # 使用单独的面法线
                for face in [f for f in ret['geom'] if isinstance(f, bmesh.types.BMFace)]:
                    bmesh.ops.translate(bm, vec=face.normal * distance, verts=face.verts)
        
        # 更新bmesh到网格
        bmesh.update_edit_mesh(me)
        
        # 返回对象模式
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # 创建结果信息
        if face_indices:
            text_content = self.create_text_content(f"已挤出对象 '{object_name}' 上的 {len(selected_faces)} 个面")
        else:
            text_content = self.create_text_content(f"已挤出对象 '{object_name}' 上的所有面")
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(ExtrudeFacesHandler())
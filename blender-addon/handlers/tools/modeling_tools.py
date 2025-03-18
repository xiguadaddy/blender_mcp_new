"""
建模工具模块

包含创建和修改3D网格的各种建模操作，如挤出、细分、布尔运算等。
"""

import bpy
import bmesh
import mathutils
import math
import logging
from mathutils import Vector
from ..tool_handlers import execute_in_main_thread

# 设置日志
logger = logging.getLogger("BlenderMCP.ModelingTools")

# ---------- 网格编辑功能 ----------

def extrude_faces(args):
    """挤出选定的面"""
    logger.debug(f"挤出面: {args}")
    object_name = args.get("object_name")
    face_indices = args.get("face_indices", [])
    direction = args.get("direction")
    distance = args.get("distance", 1.0)
    
    def exec_func():
        try:
            # 获取对象
            obj = bpy.data.objects.get(object_name)
            if not obj or obj.type != 'MESH':
                return {"error": f"无效网格对象: {object_name}"}
            
            # 进入编辑模式
            bpy.context.view_layer.objects.active = obj
            current_mode = bpy.context.object.mode
            bpy.ops.object.mode_set(mode='EDIT')
            
            # 创建bmesh
            bm = bmesh.from_edit_mesh(obj.data)
            bm.faces.ensure_lookup_table()
            
            # 取消选择所有
            for face in bm.faces:
                face.select = False
                
            # 选择指定的面
            for idx in face_indices:
                if idx < len(bm.faces):
                    bm.faces[idx].select = True
                else:
                    logger.warning(f"面索引 {idx} 超出范围")
            
            # 挤出操作
            ret = bmesh.ops.extrude_face_region(bm, geom=[f for f in bm.faces if f.select])
            extruded_verts = [v for v in ret["geom"] if isinstance(v, bmesh.types.BMVert)]
            
            # 移动挤出的顶点
            if direction is None:
                # 使用面法线
                bmesh.ops.translate(bm, 
                                   vec=mathutils.Vector((0, 0, distance)), 
                                   verts=extruded_verts)
            else:
                # 使用指定方向
                bmesh.ops.translate(bm, 
                                   vec=mathutils.Vector(direction) * distance, 
                                   verts=extruded_verts)
            
            # 更新网格
            bmesh.update_edit_mesh(obj.data)
            
            # 恢复之前的模式
            bpy.ops.object.mode_set(mode=current_mode)
            
            return {
                "status": "success",
                "extruded_faces": len(face_indices),
                "object": object_name
            }
            
        except Exception as e:
            logger.error(f"挤出面时出错: {str(e)}")
            if 'current_mode' in locals():
                bpy.ops.object.mode_set(mode=current_mode)
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def subdivide_mesh(args):
    """细分网格"""
    logger.debug(f"细分网格: {args}")
    object_name = args.get("object_name")
    cuts = args.get("cuts", 1)
    smooth = args.get("smooth", 0.0)
    
    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj or obj.type != 'MESH':
                return {"error": f"无效网格对象: {object_name}"}
                
            # 进入编辑模式
            bpy.context.view_layer.objects.active = obj
            current_mode = bpy.context.object.mode
            bpy.ops.object.mode_set(mode='EDIT')
            
            # 选择所有
            bpy.ops.mesh.select_all(action='SELECT')
            
            # 细分
            bpy.ops.mesh.subdivide(number_cuts=cuts, smoothness=smooth)
            
            # 恢复模式
            bpy.ops.object.mode_set(mode=current_mode)
            
            return {
                "status": "success", 
                "object": object_name,
                "cuts": cuts,
                "vertex_count": len(obj.data.vertices)
            }
            
        except Exception as e:
            logger.error(f"细分网格时出错: {str(e)}")
            if 'current_mode' in locals():
                bpy.ops.object.mode_set(mode=current_mode)
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def loop_cut(args):
    """环切操作"""
    logger.debug(f"环切: {args}")
    object_name = args.get("object_name")
    cuts = args.get("cuts", 1)
    edge_index = args.get("edge_index")
    factor = args.get("factor", 0.5)
    
    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj or obj.type != 'MESH':
                return {"error": f"无效网格对象: {object_name}"}
            
            # 使用bmesh进行精确控制
            bpy.context.view_layer.objects.active = obj
            current_mode = bpy.context.object.mode
            bpy.ops.object.mode_set(mode='EDIT')
            
            bm = bmesh.from_edit_mesh(obj.data)
            bm.edges.ensure_lookup_table()
            
            # 选择边
            if edge_index is not None:
                for edge in bm.edges:
                    edge.select = False
                if edge_index < len(bm.edges):
                    bm.edges[edge_index].select = True
                    
                    # 执行环切
                    result = bmesh.ops.subdivide_edges(
                        bm,
                        edges=[e for e in bm.edges if e.select],
                        cuts=cuts,
                        factor=factor
                    )
                    
                    bmesh.update_edit_mesh(obj.data)
                    
                    # 恢复模式
                    bpy.ops.object.mode_set(mode=current_mode)
                    
                    return {
                        "status": "success",
                        "object": object_name,
                        "cuts": cuts,
                        "new_edges": len(result.get('geom_inner', []))
                    }
                else:
                    bpy.ops.object.mode_set(mode=current_mode)
                    return {"error": f"边索引{edge_index}超出范围"}
            else:
                # 如果没有提供边索引，使用Blender的标准环切
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.loopcut_slide(number_cuts=cuts)
                bpy.ops.object.mode_set(mode=current_mode)
                return {
                    "status": "success",
                    "note": "使用了默认的环切操作，需要用户确认位置"
                }
                
        except Exception as e:
            logger.error(f"环切时出错: {str(e)}")
            if 'current_mode' in locals():
                bpy.ops.object.mode_set(mode=current_mode)
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def set_vertex_position(args):
    """设置顶点位置"""
    logger.debug(f"设置顶点位置: {args}")
    object_name = args.get("object_name")
    vertex_indices = args.get("vertex_indices", [])
    positions = args.get("positions", [])
    
    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj or obj.type != 'MESH':
                return {"error": f"无效网格对象: {object_name}"}
            
            if len(vertex_indices) != len(positions):
                return {"error": "顶点索引数量必须与位置数量匹配"}
                
            # 进入对象模式以确保可以修改顶点
            current_mode = bpy.context.object.mode if bpy.context.object else 'OBJECT'
            if bpy.context.object != obj:
                bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # 修改顶点位置
            modified_count = 0
            for i, idx in enumerate(vertex_indices):
                if idx < len(obj.data.vertices):
                    obj.data.vertices[idx].co = positions[i]
                    modified_count += 1
                else:
                    logger.warning(f"顶点索引 {idx} 超出范围")
            
            # 更新网格
            obj.data.update()
            
            # 恢复模式
            bpy.ops.object.mode_set(mode=current_mode)
            
            return {
                "status": "success",
                "object": object_name,
                "modified_vertices": modified_count
            }
            
        except Exception as e:
            logger.error(f"设置顶点位置时出错: {str(e)}")
            if 'current_mode' in locals():
                bpy.ops.object.mode_set(mode=current_mode)
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

# ---------- 布尔操作 ----------

def boolean_operation(args):
    """执行布尔操作"""
    logger.debug(f"布尔操作: {args}")
    object_name = args.get("object_name")  # 目标对象
    tool_object_name = args.get("tool_object_name")  # 工具对象
    operation = args.get("operation", "UNION")  # UNION, INTERSECT, DIFFERENCE
    solver = args.get("solver", "FAST")  # FAST, EXACT
    
    def exec_func():
        try:
            # 获取对象
            obj = bpy.data.objects.get(object_name)
            tool_obj = bpy.data.objects.get(tool_object_name)
            
            if not obj or obj.type != 'MESH':
                return {"error": f"无效目标对象: {object_name}"}
                
            if not tool_obj or tool_obj.type != 'MESH':
                return {"error": f"无效工具对象: {tool_object_name}"}
            
            # 设置活动对象
            bpy.context.view_layer.objects.active = obj
            
            # 添加布尔修改器
            bool_mod = obj.modifiers.new(name="Boolean", type="BOOLEAN")
            bool_mod.operation = operation
            bool_mod.solver = solver
            bool_mod.object = tool_obj
            
            # 应用修改器
            bpy.ops.object.modifier_apply(modifier=bool_mod.name)
            
            # 处理工具对象
            delete_tool = args.get("delete_tool", True)
            if delete_tool:
                bpy.data.objects.remove(tool_obj)
            
            return {
                "status": "success",
                "object": object_name,
                "operation": operation
            }
            
        except Exception as e:
            logger.error(f"布尔操作时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

# ---------- 修改器操作 ----------

def apply_modifier(args):
    """应用修改器到对象"""
    logger.debug(f"应用修改器: {args}")
    object_name = args.get("object_name")
    modifier_type = args.get("modifier_type")
    parameters = args.get("parameters", {})
    apply_immediately = args.get("apply", False)
    
    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"找不到对象: {object_name}"}
                
            # 创建修改器
            mod = obj.modifiers.new(name=f"{modifier_type}_mod", type=modifier_type)
            
            # 应用特定类型修改器的参数
            if modifier_type == "SUBSURF":
                mod.levels = parameters.get("levels", 2)
                mod.render_levels = parameters.get("render_levels", mod.levels)
            
            elif modifier_type == "BEVEL":
                mod.width = parameters.get("width", 0.1)
                mod.segments = parameters.get("segments", 3)
                
            elif modifier_type == "SOLIDIFY":
                mod.thickness = parameters.get("thickness", 0.1)
                
            elif modifier_type == "ARRAY":
                mod.count = parameters.get("count", 2)
                mod.relative_offset_displace[0] = parameters.get("offset_x", 1.0)
                mod.relative_offset_displace[1] = parameters.get("offset_y", 0.0)
                mod.relative_offset_displace[2] = parameters.get("offset_z", 0.0)
                
            elif modifier_type == "MIRROR":
                mod.use_axis[0] = parameters.get("use_x", True)
                mod.use_axis[1] = parameters.get("use_y", False)
                mod.use_axis[2] = parameters.get("use_z", False)
                
            elif modifier_type == "REMESH":
                mod.octree_depth = parameters.get("octree_depth", 4)
                mod.scale = parameters.get("scale", 0.9)
                mod.mode = parameters.get("mode", 'SHARP')
                
            elif modifier_type == "DISPLACE":
                mod.strength = parameters.get("strength", 1.0)
                
                # 如果提供了纹理名称
                texture_name = parameters.get("texture")
                if texture_name and texture_name in bpy.data.textures:
                    mod.texture = bpy.data.textures[texture_name]
            
            # 应用修改器
            if apply_immediately:
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.modifier_apply(modifier=mod.name)
                return {
                    "status": "success", 
                    "object_name": object_name,
                    "modifier_type": modifier_type,
                    "applied": True
                }
            
            return {
                "status": "success", 
                "object_name": object_name,
                "modifier_name": mod.name,
                "modifier_type": modifier_type
            }
        except Exception as e:
            logger.error(f"应用修改器时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def remove_modifier(args):
    """从对象中移除修改器"""
    logger.debug(f"移除修改器: {args}")
    object_name = args.get("object_name")
    modifier_name = args.get("modifier_name")
    
    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"找不到对象: {object_name}"}
            
            # 查找修改器
            if modifier_name not in obj.modifiers:
                return {"error": f"修改器 {modifier_name} 不存在于对象 {object_name}"}
            
            # 移除修改器
            mod = obj.modifiers[modifier_name]
            obj.modifiers.remove(mod)
            
            return {
                "status": "success",
                "object_name": object_name,
                "modifier_name": modifier_name
            }
            
        except Exception as e:
            logger.error(f"移除修改器时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

# ---------- 特殊建模操作 ----------

def knife_cut(args):
    """刀切工具"""
    logger.debug(f"刀切操作: {args}")
    object_name = args.get("object_name")
    cut_points = args.get("cut_points", [])  # 切割点的3D坐标列表
    
    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj or obj.type != 'MESH':
                return {"error": f"无效网格对象: {object_name}"}
            
            if len(cut_points) < 2:
                return {"error": "至少需要两个点来创建切割"}
            
            # 设置活动对象
            bpy.context.view_layer.objects.active = obj
            current_mode = bpy.context.object.mode
            
            # 进入编辑模式
            bpy.ops.object.mode_set(mode='EDIT')
            
            # 创建bmesh
            bm = bmesh.from_edit_mesh(obj.data)
            
            # 执行切割
            # 注意: bmesh不提供直接的knife_cut操作，这里我们使用bmesh.ops.bisect_plane来模拟
            
            # 计算切割平面的法线和原点
            points_3d = [Vector(p) for p in cut_points]
            if len(points_3d) >= 3:
                # 如果有3个或更多点，使用前3个点确定平面
                v1 = points_3d[1] - points_3d[0]
                v2 = points_3d[2] - points_3d[0]
                normal = v1.cross(v2).normalized()
                center = points_3d[0]
            else:
                # 如果只有2个点，使用默认向上的法线
                v1 = points_3d[1] - points_3d[0]
                normal = Vector((0, 0, 1))
                if abs(v1.dot(normal)) > 0.9:  # 如果线段几乎垂直，换一个法线
                    normal = Vector((1, 0, 0))
                center = points_3d[0]
            
            # 执行切割
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(
                bm,
                geom=geom,
                plane_co=center,
                plane_no=normal
            )
            
            # 更新网格
            bmesh.update_edit_mesh(obj.data)
            
            # 恢复模式
            bpy.ops.object.mode_set(mode=current_mode)
            
            return {
                "status": "success",
                "object": object_name,
                "cut_points": len(cut_points)
            }
            
        except Exception as e:
            logger.error(f"刀切操作时出错: {str(e)}")
            if 'current_mode' in locals():
                bpy.ops.object.mode_set(mode=current_mode)
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def create_geometry_nodes(args):
    """创建几何节点修改器"""
    logger.debug(f"创建几何节点: {args}")
    object_name = args.get("object_name")
    node_setup = args.get("node_setup", {})
    
    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"找不到对象: {object_name}"}
            
            # 检查是否支持几何节点
            if not hasattr(bpy.types, 'GeometryNodeTree'):
                return {"error": "当前Blender版本不支持几何节点"}
            
            # 创建几何节点修改器
            mod = obj.modifiers.new(name="GeometryNodes", type='NODES')
            
            # 创建新的节点组
            node_group = bpy.data.node_groups.new(name=f"{object_name}_geometry", type='GeometryNodeTree')
            mod.node_group = node_group
            
            # 添加输入/输出节点
            nodes = node_group.nodes
            input_node = nodes.new('NodeGroupInput')
            output_node = nodes.new('NodeGroupOutput')
            
            input_node.location = (-200, 0)
            output_node.location = (200, 0)
            
            # 设置基本接口
            node_group.inputs.new('NodeSocketGeometry', "Geometry")
            node_group.outputs.new('NodeSocketGeometry', "Geometry")
            
            # 连接输入/输出
            links = node_group.links
            links.new(input_node.outputs["Geometry"], output_node.inputs["Geometry"])
            
            # 添加自定义节点（根据提供的设置）
            added_nodes = []
            for i, node_def in enumerate(node_setup.get("nodes", [])):
                if "type" not in node_def:
                    continue
                    
                node_type = node_def["type"]
                node = None
                
                try:
                    node = nodes.new(node_type)
                    node.location = node_def.get("location", (0, -100 * (i + 1)))
                    
                    # 设置属性
                    for prop, value in node_def.get("properties", {}).items():
                        if hasattr(node, prop):
                            setattr(node, prop, value)
                    
                    added_nodes.append(node)
                except Exception as e:
                    logger.warning(f"创建节点 {node_type} 时出错: {str(e)}")
            
            # 创建连接
            for link_def in node_setup.get("links", []):
                from_idx = link_def.get("from_node")
                to_idx = link_def.get("to_node")
                from_socket = link_def.get("from_socket")
                to_socket = link_def.get("to_socket")
                
                # 特殊处理输入/输出节点
                from_node = None
                to_node = None
                
                if from_idx == -1:
                    from_node = input_node
                elif from_idx == -2:
                    from_node = output_node
                elif 0 <= from_idx < len(added_nodes):
                    from_node = added_nodes[from_idx]
                    
                if to_idx == -1:
                    to_node = input_node
                elif to_idx == -2:
                    to_node = output_node
                elif 0 <= to_idx < len(added_nodes):
                    to_node = added_nodes[to_idx]
                
                # 创建连接
                if from_node and to_node and from_socket in from_node.outputs and to_socket in to_node.inputs:
                    links.new(from_node.outputs[from_socket], to_node.inputs[to_socket])
            
            return {
                "status": "success",
                "object": object_name,
                "modifier": mod.name,
                "node_group": node_group.name,
                "nodes_count": len(added_nodes)
            }
            
        except Exception as e:
            logger.error(f"创建几何节点时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def join_objects(args):
    """连接多个物体"""
    logger.debug(f"连接物体: {args}")
    objects = args.get("objects", [])
    target_object = args.get("target_object")
    
    def exec_func():
        try:
            if not objects:
                return {"error": "未提供要连接的对象列表"}
            
            # 获取目标对象
            target = None
            if target_object:
                target = bpy.data.objects.get(target_object)
                if not target:
                    return {"error": f"目标对象不存在: {target_object}"}
            else:
                # 如果未指定目标，使用第一个对象作为目标
                target = bpy.data.objects.get(objects[0])
                if not target:
                    return {"error": f"对象不存在: {objects[0]}"}
                    
            # 收集要连接的对象
            objs_to_join = []
            for obj_name in objects:
                obj = bpy.data.objects.get(obj_name)
                if obj and obj != target and obj.type == target.type:
                    objs_to_join.append(obj)
            
            if not objs_to_join:
                return {"error": "没有有效的对象可以连接"}
            
            # 取消选择所有对象
            bpy.ops.object.select_all(action='DESELECT')
            
            # 选择目标对象和要连接的对象
            target.select_set(True)
            for obj in objs_to_join:
                obj.select_set(True)
                
            # 设置活动对象
            bpy.context.view_layer.objects.active = target
            
            # 执行连接
            bpy.ops.object.join()
            
            return {
                "status": "success",
                "target_object": target.name,
                "joined_objects": len(objs_to_join)
            }
            
        except Exception as e:
            logger.error(f"连接物体时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def separate_mesh(args):
    """分离网格"""
    logger.debug(f"分离网格: {args}")
    object_name = args.get("object_name")
    selection_method = args.get("selection_method", "SELECTED")
    material_index = args.get("material_index", 0)
    
    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj or obj.type != 'MESH':
                return {"error": f"无效网格对象: {object_name}"}
            
            # 设置活动对象
            bpy.context.view_layer.objects.active = obj
            
            # 存储当前模式
            current_mode = bpy.context.object.mode
            
            # 进入编辑模式
            bpy.ops.object.mode_set(mode='EDIT')
            
            # 根据选择方法进行选择
            bpy.ops.mesh.select_all(action='DESELECT')
            
            if selection_method == "SELECTED":
                # 使用已有选择，不做额外操作
                pass
            elif selection_method == "MATERIAL":
                # 按材质索引选择
                bpy.context.tool_settings.mesh_select_mode = (False, False, True)  # 只选择面
                bm = bmesh.from_edit_mesh(obj.data)
                for face in bm.faces:
                    if face.material_index == material_index:
                        face.select = True
                bmesh.update_edit_mesh(obj.data)
            elif selection_method == "LOOSE":
                # 选择所有松散部分
                bpy.ops.mesh.select_loose()
            
            # 分离选择的网格部分
            bpy.ops.mesh.separate(type='SELECTED')
            
            # 恢复模式
            bpy.ops.object.mode_set(mode=current_mode)
            
            # 获取新创建的对象
            new_objects = []
            for o in bpy.data.objects:
                if o.name.startswith(object_name + ".") and o.type == 'MESH':
                    new_objects.append(o.name)
            
            return {
                "status": "success",
                "original_object": object_name,
                "new_objects": new_objects,
                "selection_method": selection_method
            }
            
        except Exception as e:
            logger.error(f"分离网格时出错: {str(e)}")
            if 'current_mode' in locals():
                bpy.ops.object.mode_set(mode=current_mode)
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

# 注册工具
TOOLS = {
    # 网格编辑功能
    "extrude_faces": extrude_faces,
    "subdivide_mesh": subdivide_mesh,
    "loop_cut": loop_cut,
    "set_vertex_position": set_vertex_position,
    
    # 布尔操作
    "boolean_operation": boolean_operation,
    
    # 修改器操作
    "apply_modifier": apply_modifier,
    "remove_modifier": remove_modifier,
    
    # 特殊建模操作
    "knife_cut": knife_cut,
    "create_geometry_nodes": create_geometry_nodes,
    
    # 对象操作
    "join_objects": join_objects,
    "separate_mesh": separate_mesh
} 
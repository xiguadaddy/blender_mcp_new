"""
对象操作工具模块

包括对象的创建、获取、修改和删除相关功能。
"""

import bpy
import bmesh
from mathutils import Vector, Euler
import json
from ..tool_handlers import execute_in_main_thread
from ...mcp_types import create_text_content, create_image_content
from ...logger import get_logger

# 设置日志
logger = get_logger("BlenderMCP.ObjectTools")

# 对象创建函数
def create_object(args):
    """创建3D对象"""
    logger.debug(f"创建对象: {args}")
    obj_type = args.get("object_type")
    location = args.get("location", [0, 0, 0])
    name = args.get("name", f"New_{obj_type}")
    size = args.get("size", 2.0)
    
    def exec_func():
        try:
            if obj_type == "cube":
                bpy.ops.mesh.primitive_cube_add(size=size, location=location)
            elif obj_type == "sphere":
                bpy.ops.mesh.primitive_uv_sphere_add(radius=size/2, location=location)
            elif obj_type == "plane":
                bpy.ops.mesh.primitive_plane_add(size=size, location=location)
            elif obj_type == "cylinder":
                bpy.ops.mesh.primitive_cylinder_add(radius=size/2, depth=size, location=location)
            elif obj_type == "cone":
                bpy.ops.mesh.primitive_cone_add(radius1=size/2, depth=size, location=location)
            elif obj_type == "torus":
                bpy.ops.mesh.primitive_torus_add(location=location)
            elif obj_type == "empty":
                empty = bpy.data.objects.new(name, None)
                empty.location = location
                empty.empty_display_type = args.get("empty_type", "PLAIN_AXES")
                empty.empty_display_size = size
                bpy.context.collection.objects.link(empty)
                bpy.context.view_layer.objects.active = empty
                message = f"已创建{obj_type}对象 '{empty.name}'"
                return {
                    "status": "success", 
                    "text": message,
                    "object_name": empty.name,
                    "location": list(empty.location)
                }
            else:
                return {"error": f"未知对象类型: {obj_type}"}
                
            # 重命名对象
            obj = bpy.context.active_object
            obj.name = name
            
            message = f"已创建{obj_type}对象 '{obj.name}'"
            return {
                "status": "success", 
                "text": message,
                "object_name": obj.name,
                "location": list(obj.location)
            }
        except Exception as e:
            logger.error(f"创建对象时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def create_text(args):
    """创建3D文本"""
    logger.debug(f"创建文本: {args}")
    text = args.get("text", "Text")
    name = args.get("name")
    location = args.get("location", (0, 0, 0))
    scale = args.get("scale", (1, 1, 1))
    extrude = args.get("extrude", 0.0)
    
    def exec_func():
        try:
            # 添加文本对象
            bpy.ops.object.text_add(location=location)
            text_obj = bpy.context.object
            
            # 设置名称
            if name:
                text_obj.name = name
            
            # 设置文本内容
            text_obj.data.body = text
            
            # 设置挤出
            text_obj.data.extrude = extrude
            
            # 设置缩放
            text_obj.scale = scale
            
            return {
                "status": "success",
                "object": text_obj.name,
                "text": text,
                "location": location,
                "scale": scale,
                "extrude": extrude
            }
            
        except Exception as e:
            logger.error(f"创建文本时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def create_curve(args):
    """创建曲线"""
    logger.debug(f"创建曲线: {args}")
    points = args.get("points", [])
    name = args.get("name")
    curve_type = args.get("type", "POLY")  # POLY, BEZIER, NURBS
    
    def exec_func():
        try:
            if not points or len(points) < 2:
                return {"error": "需要至少两个点来创建曲线"}
            
            # 创建曲线数据
            curve_data = bpy.data.curves.new(name=name if name else "Curve", type='CURVE')
            curve_data.dimensions = '3D'
            curve_data.resolution_u = 12
            
            # 创建样条
            spline = None
            
            if curve_type == "BEZIER":
                spline = curve_data.splines.new(type='BEZIER')
                spline.bezier_points.add(len(points) - 1)
                for i, point in enumerate(points):
                    spline.bezier_points[i].co = point
                    spline.bezier_points[i].handle_left_type = 'AUTO'
                    spline.bezier_points[i].handle_right_type = 'AUTO'
                    
            else:  # POLY 或 NURBS
                spline_type = 'NURBS' if curve_type == "NURBS" else 'POLY'
                spline = curve_data.splines.new(type=spline_type)
                spline.points.add(len(points) - 1)
                
                for i, point in enumerate(points):
                    # NURBS点是4D的 (x, y, z, w)
                    if len(point) == 3:
                        spline.points[i].co = (point[0], point[1], point[2], 1.0)
                    else:
                        spline.points[i].co = point
            
            # 设置NURBS属性
            if curve_type == "NURBS":
                spline.order_u = min(4, len(points))
                spline.use_endpoint_u = True
            
            # 创建对象
            curve_obj = bpy.data.objects.new(name if name else "Curve", curve_data)
            bpy.context.collection.objects.link(curve_obj)
            
            return {
                "status": "success",
                "object": curve_obj.name,
                "type": curve_type,
                "points": len(points)
            }
            
        except Exception as e:
            logger.error(f"创建曲线时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

# 对象修改函数
def transform_object(args):
    """转换对象位置、旋转或缩放"""
    logger.debug(f"转换对象: {args}")
    object_name = args.get("object_name")
    location = args.get("location")
    rotation = args.get("rotation")
    scale = args.get("scale")
    
    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"找不到对象: {object_name}"}
            
            # 应用变换
            if location:
                obj.location = location
            
            if rotation:
                obj.rotation_euler = Euler(rotation, 'XYZ')
            
            if scale:
                obj.scale = scale
            
            return {
                "status": "success", 
                "object_name": object_name,
                "location": list(obj.location),
                "rotation": list(obj.rotation_euler),
                "scale": list(obj.scale)
            }
        except Exception as e:
            logger.error(f"转换对象时出错: {str(e)}")
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

def set_object_parent(args):
    """设置对象的父级对象"""
    logger.debug(f"设置对象父级: {args}")
    object_name = args.get("object_name")
    parent_name = args.get("parent_name")
    keep_transform = args.get("keep_transform", True)
    
    def exec_func():
        try:
            # 获取对象
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"找不到对象: {object_name}"}
                
            # 获取父对象
            parent = bpy.data.objects.get(parent_name) if parent_name else None
            
            # 设置父级关系
            if parent:
                # 清除现有的父级关系
                obj.parent = None
                
                # 存储原始变换（如果需要）
                original_matrix = obj.matrix_world.copy() if keep_transform else None
                
                # 设置新父级
                obj.parent = parent
                
                # 保持世界空间变换（如果需要）
                if keep_transform:
                    obj.matrix_world = original_matrix
                
                return {
                    "status": "success",
                    "object": object_name,
                    "parent": parent_name,
                    "keep_transform": keep_transform
                }
            else:
                # 清除父级关系
                original_matrix = obj.matrix_world.copy() if keep_transform else None
                obj.parent = None
                
                if keep_transform:
                    obj.matrix_world = original_matrix
                
                return {
                    "status": "success",
                    "object": object_name,
                    "parent": None,
                    "message": "已清除父级关系"
                }
                
        except Exception as e:
            logger.error(f"设置对象父级时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def rename_object(args):
    """重命名对象"""
    logger.debug(f"重命名对象: {args}")
    object_name = args.get("object_name")
    new_name = args.get("new_name")
    
    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"找不到对象: {object_name}"}
                
            if not new_name:
                return {"error": "未提供新名称"}
                
            old_name = obj.name
            obj.name = new_name
            
            return {
                "status": "success",
                "old_name": old_name,
                "new_name": obj.name  # 返回实际名称（可能与请求的不同，如果名称已存在）
            }
            
        except Exception as e:
            logger.error(f"重命名对象时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

# 对象获取函数
def get_object_info(args):
    """获取对象的详细信息"""
    logger.debug(f"获取对象信息: {args}")
    object_name = args.get("object_name")
    include_mesh_data = args.get("include_mesh_data", False)
    include_materials = args.get("include_materials", True)
    
    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"找不到对象: {object_name}"}
                
            # 基本信息
            info = {
                "name": obj.name,
                "type": obj.type,
                "location": list(obj.location),
                "rotation": list(obj.rotation_euler),
                "scale": list(obj.scale),
                "dimensions": list(obj.dimensions),
                "visible": obj.visible_get(),
                "parent": obj.parent.name if obj.parent else None,
                "children": [child.name for child in bpy.data.objects if child.parent == obj]
            }
            
            # 根据对象类型获取额外信息
            if obj.type == 'MESH':
                mesh_info = {
                    "vertices_count": len(obj.data.vertices),
                    "edges_count": len(obj.data.edges),
                    "polygons_count": len(obj.data.polygons)
                }
                
                # 包含网格详细数据
                if include_mesh_data:
                    # 顶点数据
                    vertices = []
                    for v in obj.data.vertices:
                        vertices.append({
                            "index": v.index,
                            "co": list(v.co),
                            "normal": list(v.normal)
                        })
                    
                    # 面数据
                    polygons = []
                    for p in obj.data.polygons:
                        polygons.append({
                            "index": p.index,
                            "vertices": [v for v in p.vertices],
                            "normal": list(p.normal),
                            "material_index": p.material_index
                        })
                    
                    mesh_info["vertices"] = vertices
                    mesh_info["polygons"] = polygons
                    
                info["mesh"] = mesh_info
                
                # 材质信息
                if include_materials:
                    materials = []
                    for slot in obj.material_slots:
                        if slot.material:
                            mat = slot.material
                            mat_info = {
                                "name": mat.name,
                                "use_nodes": mat.use_nodes
                            }
                            
                            # 尝试获取基本颜色
                            if mat.use_nodes:
                                principled = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
                                if principled and "Base Color" in principled.inputs:
                                    mat_info["color"] = list(principled.inputs["Base Color"].default_value)
                            
                            materials.append(mat_info)
                    
                    info["materials"] = materials
                    
            elif obj.type == 'CURVE':
                curve_info = {
                    "dimensions": obj.data.dimensions,
                    "splines_count": len(obj.data.splines),
                    "resolution_u": obj.data.resolution_u
                }
                info["curve"] = curve_info
                
            elif obj.type == 'FONT':
                text_info = {
                    "text": obj.data.body,
                    "extrude": obj.data.extrude,
                    "size": obj.data.size
                }
                info["text"] = text_info
                
            elif obj.type == 'EMPTY':
                empty_info = {
                    "display_type": obj.empty_display_type,
                    "display_size": obj.empty_display_size
                }
                info["empty"] = empty_info
                
            return {
                "status": "success",
                "text": f"获取对象 '{object_name}' 的信息",
                "info": info
            }
            
        except Exception as e:
            logger.error(f"获取对象信息时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def list_objects(args):
    """列出场景中的对象"""
    logger.debug(f"列出对象: {args}")
    filter_type = args.get("filter_type")  # 如果提供，按类型过滤
    collection_name = args.get("collection")  # 如果提供，仅返回特定集合中的对象
    
    def exec_func():
        try:
            objects = []
            
            # 确定要迭代的对象集合
            if collection_name:
                collection = bpy.data.collections.get(collection_name)
                if not collection:
                    return {"error": f"找不到集合: {collection_name}"}
                objects_to_iterate = collection.objects
            else:
                objects_to_iterate = bpy.context.scene.objects
            
            # 遍历对象
            for obj in objects_to_iterate:
                # 根据类型筛选
                if filter_type and obj.type != filter_type:
                    continue
                    
                # 添加基本对象信息
                obj_info = {
                    "name": obj.name,
                    "type": obj.type,
                    "location": list(obj.location),
                    "dimensions": list(obj.dimensions),
                    "parent": obj.parent.name if obj.parent else None
                }
                
                objects.append(obj_info)
            
            msg = f"找到 {len(objects)} 个对象"
            if filter_type:
                msg += f" (类型: {filter_type})"
            if collection_name:
                msg += f" (集合: {collection_name})"
                
            return {
                "status": "success",
                "text": msg,
                "count": len(objects),
                "objects": objects
            }
            
        except Exception as e:
            logger.error(f"列出对象时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

# 对象删除函数
def delete_object(args):
    """删除对象"""
    logger.debug(f"删除对象: {args}")
    object_names = args.get("object_names", [])
    object_name = args.get("object_name")
    
    # 确保我们有对象列表
    if object_name and not object_names:
        object_names = [object_name]
    
    def exec_func():
        try:
            if not object_names:
                return {"error": "未提供要删除的对象名称"}
                
            deleted_objects = []
            not_found_objects = []
            
            # 收集需要删除的对象
            objects_to_delete = []
            for name in object_names:
                obj = bpy.data.objects.get(name)
                if obj:
                    objects_to_delete.append(obj)
                    deleted_objects.append(name)
                else:
                    not_found_objects.append(name)
            
            # 删除对象
            if objects_to_delete:
                bpy.ops.object.delete({"selected_objects": objects_to_delete})
            
            result = {
                "status": "success",
                "deleted_count": len(deleted_objects),
                "deleted_objects": deleted_objects
            }
            
            if not_found_objects:
                result["not_found_objects"] = not_found_objects
                result["warnings"] = f"未找到 {len(not_found_objects)} 个对象"
                
            return result
            
        except Exception as e:
            logger.error(f"删除对象时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def duplicate_object(args):
    """复制对象"""
    logger.debug(f"复制对象: {args}")
    object_name = args.get("object_name")
    new_name = args.get("new_name")
    linked = args.get("linked", False)  # 是否为链接复制（共享数据）
    
    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"找不到对象: {object_name}"}
            
            # 选择要复制的对象
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            
            # 执行复制
            if linked:
                bpy.ops.object.duplicate_move_linked()
            else:
                bpy.ops.object.duplicate_move()
            
            # 获取新对象（活动对象应该是新复制的对象）
            new_obj = bpy.context.active_object
            
            # 设置新名称（如果提供）
            if new_name:
                new_obj.name = new_name
            
            return {
                "status": "success",
                "original_object": object_name,
                "new_object": new_obj.name,
                "linked": linked
            }
            
        except Exception as e:
            logger.error(f"复制对象时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

# 注册工具
TOOLS = {
    # 创建类
    "create_object": create_object,
    "create_text": create_text,
    "create_curve": create_curve,
    "duplicate_object": duplicate_object,
    
    # 修改类
    "transform_object": transform_object,
    "set_vertex_position": set_vertex_position,
    "set_object_parent": set_object_parent,
    "rename_object": rename_object,
    
    # 获取类
    "get_object_info": get_object_info,
    "list_objects": list_objects,
    
    # 删除类
    "delete_object": delete_object
}
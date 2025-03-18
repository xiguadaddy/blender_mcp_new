import bpy
import os
import tempfile
import base64
from mathutils import Vector, Euler
import threading
import time
import logging
from ..utils import thread_utils
import bmesh
import mathutils
import math

# 设置日志
logger = logging.getLogger("BlenderMCP.Tools")

# 工具线程锁，确保线程安全
_tool_lock = threading.Lock()

def execute_in_main_thread(func, *args, **kwargs):
    """在Blender主线程中执行函数"""
    # 确保主线程处理器已注册
    thread_utils.register_main_thread_processor()
    
    # 使用线程工具执行函数
    return thread_utils.run_in_main_thread(func, *args, **kwargs)

def execute_tool(tool_name, arguments):
    """执行指定工具"""
    from .tools import register_all_tools
    
    print(f"执行工具: {tool_name}, 参数: {arguments}")
    
    # 执行Python代码
    if tool_name == "execute_python":
        code = arguments.get("code", "")
        if not code:
            return {"error": "未提供Python代码"}
        
        try:
            # 创建局部命名空间执行代码
            namespace = {"bpy": bpy, "result": None}
            exec(code, namespace)
            # 返回代码执行结果
            return namespace.get("result", {"status": "success", "message": "代码执行成功，但未返回结果"})
        except Exception as e:
            return {"error": f"执行Python代码时出错: {str(e)}"}
    
    # 获取所有注册的工具
    tools = register_all_tools()
    
    with _tool_lock:
        try:
            if tool_name in tools:
                return tools[tool_name](arguments)
            else:
                error_msg = f"未知工具: {tool_name}"
                logger.error(error_msg)
                return {"error": error_msg}
        except Exception as e:
            error_msg = f"执行工具时出错: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

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
            else:
                return {"error": f"未知对象类型: {obj_type}"}
                
            # 重命名对象
            obj = bpy.context.active_object
            obj.name = name
            
            return {
                "status": "success", 
                "object_name": obj.name,
                "location": list(obj.location)
            }
        except Exception as e:
            logger.error(f"创建对象时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def set_material(args):
    """为对象设置材质"""
    logger.debug(f"设置材质: {args}")
    object_name = args.get("object_name")
    material_name = args.get("material_name")  # 添加材质名称参数
    color = args.get("color", [0.8, 0.8, 0.8, 1.0])
    metallic = args.get("metallic", 0.0)
    roughness = args.get("roughness", 0.5)
    specular = args.get("specular", 0.5)  # 添加镜面反射参数
    
    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"找不到对象: {object_name}"}
                
            # 确定材质名称 (如果未提供)
            mat_name = material_name or f"{object_name}_material"
            
            # 查找现有材质或创建新材质
            mat = bpy.data.materials.get(mat_name)
            if not mat:
                mat = bpy.data.materials.new(name=mat_name)
                logger.debug(f"创建新材质: {mat_name}")
            else:
                logger.debug(f"使用现有材质: {mat_name}")
            
            # 启用节点编辑
            mat.use_nodes = True
            
            # 获取主要着色器节点
            nodes = mat.node_tree.nodes
            principled_bsdf = nodes.get('Principled BSDF')
            
            # 如果找不到主要着色器节点，创建一个
            if not principled_bsdf:
                principled_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
            
            # 设置颜色和属性
            try:
                # 确保颜色有Alpha通道
                if color and len(color) == 3:
                    color = color + [1.0]
                
                # 设置主要材质属性
                if principled_bsdf:
                    principled_bsdf.inputs["Base Color"].default_value = color
                    principled_bsdf.inputs["Metallic"].default_value = metallic
                    principled_bsdf.inputs["Roughness"].default_value = roughness
                    principled_bsdf.inputs["Specular"].default_value = specular
                
                # 设置老版本Blender材质属性（向后兼容）
                if hasattr(mat, "diffuse_color"):
                    mat.diffuse_color = color
                
                # 确保输出节点连接
                output_node = None
                for node in nodes:
                    if node.type == 'OUTPUT_MATERIAL':
                        output_node = node
                        break
                
                if not output_node:
                    output_node = nodes.new(type='ShaderNodeOutputMaterial')
                
                # 连接着色器到输出
                mat.node_tree.links.new(principled_bsdf.outputs["BSDF"], output_node.inputs["Surface"])
                
            except (AttributeError, KeyError) as e:
                logger.warning(f"设置材质属性时出现非关键错误: {str(e)}")
                # 继续执行，因为这些是非关键错误
                
            # 应用材质到对象
            if len(obj.material_slots) == 0:
                obj.data.materials.append(mat)
            else:
                # 更新现有插槽
                obj.material_slots[0].material = mat
                
            # 确保所有插槽都有材质
            for slot in obj.material_slots:
                if slot.material is None:
                    slot.material = mat
                
            return {
                "status": "success", 
                "material_name": mat.name,
                "object_name": object_name,
                "color": list(color),
                "metallic": metallic,
                "roughness": roughness
            }
        except Exception as e:
            logger.error(f"设置材质时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def add_light(args):
    """添加灯光到场景"""
    logger.debug(f"添加灯光: {args}")
    light_type = args.get("light_type")
    location = args.get("location", [0, 0, 0])
    name = args.get("name", f"New_{light_type}")
    color = args.get("color", [1.0, 1.0, 1.0])
    energy = args.get("energy", 1000.0)
    
    def exec_func():
        try:
            # 创建灯光数据
            light_data = bpy.data.lights.new(name=name, type=light_type)
            light_data.color = color
            light_data.energy = energy
            
            # 创建灯光对象
            light_obj = bpy.data.objects.new(name=name, object_data=light_data)
            light_obj.location = location
            
            # 添加到场景
            bpy.context.collection.objects.link(light_obj)
            
            # 特定灯光类型的额外设置
            if light_type == 'SPOT':
                light_data.spot_size = args.get("spot_size", 1.0)
                light_data.spot_blend = args.get("spot_blend", 0.15)
            
            return {
                "status": "success", 
                "light_name": name,
                "location": list(light_obj.location)
            }
        except Exception as e:
            logger.error(f"添加灯光时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def set_camera(args):
    """设置相机位置和属性"""
    logger.debug(f"设置相机: {args}")
    location = args.get("location")
    rotation = args.get("rotation")
    name = args.get("name", "MCP_Camera")
    lens = args.get("lens", 50.0)
    
    def exec_func():
        try:
            # 查找已有相机或创建新相机
            camera = None
            if name in bpy.data.objects and bpy.data.objects[name].type == 'CAMERA':
                camera = bpy.data.objects[name]
            else:
                # 创建新相机数据
                cam_data = bpy.data.cameras.new(name=name)
                camera = bpy.data.objects.new(name=name, object_data=cam_data)
                bpy.context.collection.objects.link(camera)
            
            # 设置位置和旋转
            camera.location = location
            camera.rotation_euler = Euler(rotation, 'XYZ')
            
            # 设置镜头参数
            camera.data.lens = lens
            
            # 设置为活动相机
            bpy.context.scene.camera = camera
            
            return {
                "status": "success", 
                "camera_name": name,
                "location": list(camera.location),
                "rotation": list(camera.rotation_euler)
            }
        except Exception as e:
            logger.error(f"设置相机时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def render_scene(args):
    """渲染场景并返回结果"""
    logger.debug(f"渲染场景: {args}")
    output_path = args.get("output_path")
    resolution_x = args.get("resolution_x", 1920)
    resolution_y = args.get("resolution_y", 1080)
    samples = args.get("samples", 128)
    
    def exec_func():
        try:
            # 临时文件用于保存渲染结果
            temp_file = None
            if not output_path:
                temp_dir = tempfile.gettempdir()
                temp_file = os.path.join(temp_dir, f"blender_mcp_render_{int(time.time())}.png")
                output_path = temp_file
            
            # 设置渲染参数
            scene = bpy.context.scene
            scene.render.filepath = output_path
            scene.render.resolution_x = resolution_x
            scene.render.resolution_y = resolution_y
            
            # 设置渲染引擎特定参数
            if scene.render.engine == 'CYCLES':
                scene.cycles.samples = samples
            
            # 执行渲染
            bpy.ops.render.render(write_still=True)
            
            result = {
                "status": "success",
                "output_path": output_path
            }
            
            # 如果使用临时文件，读取图像数据
            if temp_file and os.path.exists(temp_file):
                with open(temp_file, "rb") as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')
                    result["image_data"] = image_data
                    
                # 清理临时文件
                try:
                    os.unlink(temp_file)
                except:
                    pass
            
            return result
        except Exception as e:
            logger.error(f"渲染场景时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def apply_modifier(args):
    """向对象应用修改器"""
    logger.debug(f"应用修改器: {args}")
    object_name = args.get("object_name")
    modifier_type = args.get("modifier_type")
    parameters = args.get("parameters", {})
    
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

def import_model(args):
    """导入3D模型文件"""
    logger.debug(f"导入模型: {args}")
    file_path = args.get("file_path")
    import_type = args.get("import_type")
    
    def exec_func():
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return {"error": f"文件不存在: {file_path}"}
            
            # 根据不同格式调用相应的导入函数
            if import_type == "OBJ":
                bpy.ops.import_scene.obj(filepath=file_path)
            elif import_type == "FBX":
                bpy.ops.import_scene.fbx(filepath=file_path)
            elif import_type == "GLB":
                bpy.ops.import_scene.gltf(filepath=file_path)
            elif import_type == "STL":
                bpy.ops.import_mesh.stl(filepath=file_path)
            else:
                return {"error": f"不支持的导入类型: {import_type}"}
            
            # 获取新导入的对象
            imported_objects = [obj.name for obj in bpy.context.selected_objects]
            
            return {
                "status": "success", 
                "imported_objects": imported_objects,
                "file_path": file_path
            }
        except Exception as e:
            logger.error(f"导入模型时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def extrude_faces(args):
    """挤出面"""
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

def create_animation(args):
    """创建物体动画"""
    logger.debug(f"创建动画: {args}")
    object_name = args.get("object_name")
    keyframes = args.get("keyframes", {})
    property_path = args.get("property_path", "location")
    
    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"对象不存在: {object_name}"}
            
            # 清除现有动画曲线
            if obj.animation_data and obj.animation_data.action:
                for fc in obj.animation_data.action.fcurves:
                    if fc.data_path == property_path:
                        obj.animation_data.action.fcurves.remove(fc)
            
            # 确保有animation_data
            if not obj.animation_data:
                obj.animation_data_create()
            
            # 确保有action
            if not obj.animation_data.action:
                action = bpy.data.actions.new(name=f"{object_name}Action")
                obj.animation_data.action = action
            
            # 设置关键帧
            keyframe_count = 0
            for frame_str, value in keyframes.items():
                frame = int(frame_str)
                
                if property_path == "location":
                    obj.location = value
                    obj.keyframe_insert(data_path=property_path, frame=frame)
                    keyframe_count += 1
                    
                elif property_path == "rotation_euler":
                    # 检查是否需要转换为弧度
                    if isinstance(value[0], (int, float)) and value[0] > 6.28:  # 大于2π可能是角度
                        value = [math.radians(v) for v in value]
                    obj.rotation_euler = value
                    obj.keyframe_insert(data_path=property_path, frame=frame)
                    keyframe_count += 1
                    
                elif property_path == "scale":
                    obj.scale = value
                    obj.keyframe_insert(data_path=property_path, frame=frame)
                    keyframe_count += 1
                    
                else:
                    # 通用属性路径
                    parts = property_path.split('.')
                    target = obj
                    for part in parts[:-1]:
                        target = getattr(target, part)
                    setattr(target, parts[-1], value)
                    obj.keyframe_insert(data_path=property_path, frame=frame)
                    keyframe_count += 1
            
            return {
                "status": "success",
                "object": object_name,
                "property": property_path,
                "keyframes": keyframe_count
            }
            
        except Exception as e:
            logger.error(f"创建动画时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def create_node_material(args):
    """创建节点材质"""
    logger.debug(f"创建节点材质: {args}")
    name = args.get("name")
    node_setup = args.get("node_setup", {})
    
    def exec_func():
        try:
            # 创建新材质或获取现有材质
            mat = bpy.data.materials.get(name)
            if not mat:
                mat = bpy.data.materials.new(name=name)
                logger.debug(f"创建新材质: {name}")
            else:
                logger.debug(f"使用现有材质: {name}")
            
            mat.use_nodes = True
            node_tree = mat.node_tree
            
            # 清除现有节点
            for node in node_tree.nodes:
                node_tree.nodes.remove(node)
                
            # 创建节点
            nodes = {}
            nodes_created = 0
            
            for node_id, node_data in node_setup.get("nodes", {}).items():
                node_type = node_data.get("type", "ShaderNodeBsdfPrincipled")
                
                # 必要时添加Shader前缀
                if not node_type.startswith("ShaderNode") and not node_type.startswith("NodeGroup"):
                    node_type = f"ShaderNode{node_type}"
                
                try:
                    node = node_tree.nodes.new(type=node_type)
                    nodes_created += 1
                    
                    # 设置位置
                    location = node_data.get("location", (0, 0))
                    node.location = location
                    
                    # 设置属性
                    for prop, value in node_data.get("properties", {}).items():
                        if hasattr(node, prop):
                            setattr(node, prop, value)
                        elif prop in node.inputs:
                            if isinstance(value, (list, tuple)) and len(value) >= 3:
                                node.inputs[prop].default_value = value
                            else:
                                node.inputs[prop].default_value = value
                    
                    nodes[node_id] = node
                    
                except Exception as e:
                    logger.warning(f"创建节点 {node_type} 时出错: {str(e)}")
            
            # 创建连接
            links_created = 0
            for link_data in node_setup.get("links", []):
                from_node_id = link_data.get("from_node")
                to_node_id = link_data.get("to_node")
                from_socket = link_data.get("from_socket", 0)
                to_socket = link_data.get("to_socket", 0)
                
                if from_node_id in nodes and to_node_id in nodes:
                    from_node = nodes[from_node_id]
                    to_node = nodes[to_node_id]
                    
                    # 处理索引或名称的插槽
                    if isinstance(from_socket, int) and from_socket < len(from_node.outputs):
                        out_socket = from_node.outputs[from_socket]
                    elif isinstance(from_socket, str) and from_socket in from_node.outputs:
                        out_socket = from_node.outputs[from_socket]
                    else:
                        logger.warning(f"输出插槽 {from_socket} 不存在")
                        continue
                        
                    if isinstance(to_socket, int) and to_socket < len(to_node.inputs):
                        in_socket = to_node.inputs[to_socket]
                    elif isinstance(to_socket, str) and to_socket in to_node.inputs:
                        in_socket = to_node.inputs[to_socket]
                    else:
                        logger.warning(f"输入插槽 {to_socket} 不存在")
                        continue
                    
                    # 创建连接
                    node_tree.links.new(out_socket, in_socket)
                    links_created += 1
            
            # 确保有输出节点
            output_node = None
            for node in node_tree.nodes:
                if node.type == 'OUTPUT_MATERIAL':
                    output_node = node
                    break
                    
            if not output_node:
                output_node = node_tree.nodes.new(type='ShaderNodeOutputMaterial')
                
            # 确保有着色器连接到输出
            if len(output_node.inputs['Surface'].links) == 0:
                # 查找Principled BSDF节点
                principled = None
                for node in node_tree.nodes:
                    if node.type == 'BSDF_PRINCIPLED':
                        principled = node
                        break
                        
                if principled:
                    node_tree.links.new(principled.outputs['BSDF'], output_node.inputs['Surface'])
            
            return {
                "status": "success",
                "material": name,
                "nodes_created": nodes_created,
                "links_created": links_created
            }
            
        except Exception as e:
            logger.error(f"创建节点材质时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def set_uv_mapping(args):
    """设置UV映射"""
    logger.debug(f"设置UV映射: {args}")
    object_name = args.get("object_name")
    mapping_type = args.get("mapping_type", "UNWRAP")
    scale = args.get("scale", (1.0, 1.0))
    
    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj or obj.type != 'MESH':
                return {"error": f"无效网格对象: {object_name}"}
            
            # 设置活动对象
            bpy.context.view_layer.objects.active = obj
            
            # 存储当前模式
            current_mode = bpy.context.object.mode
            bpy.ops.object.mode_set(mode='EDIT')
            
            # 选择所有面
            bm = bmesh.from_edit_mesh(obj.data)
            for face in bm.faces:
                face.select = True
            bmesh.update_edit_mesh(obj.data)
            
            # 应用UV映射
            if mapping_type == "UNWRAP":
                bpy.ops.uv.unwrap()
            elif mapping_type == "SMART_PROJECT":
                bpy.ops.uv.smart_project()
            elif mapping_type == "CUBE_PROJECTION":
                bpy.ops.uv.cube_project()
            elif mapping_type == "CYLINDER_PROJECTION":
                bpy.ops.uv.cylinder_project()
            elif mapping_type == "SPHERE_PROJECTION":
                bpy.ops.uv.sphere_project()
            else:
                # 默认展开
                bpy.ops.uv.unwrap()
            
            # 应用比例
            if "uv_layers" in dir(obj.data) and obj.data.uv_layers:
                uv_layer = obj.data.uv_layers.active
                if uv_layer:
                    for polygon in obj.data.polygons:
                        for loop_idx in polygon.loop_indices:
                            uv = uv_layer.data[loop_idx].uv
                            uv.x *= scale[0]
                            uv.y *= scale[1]
            
            # 恢复模式
            bpy.ops.object.mode_set(mode=current_mode)
            
            return {
                "status": "success",
                "object": object_name,
                "mapping_type": mapping_type,
                "scale": scale
            }
            
        except Exception as e:
            logger.error(f"设置UV映射时出错: {str(e)}")
            # 恢复模式
            if 'current_mode' in locals():
                bpy.ops.object.mode_set(mode=current_mode)
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

def create_particle_system(args):
    """创建粒子系统"""
    logger.debug(f"创建粒子系统: {args}")
    object_name = args.get("object_name")
    particles_count = args.get("count", 1000)
    particle_type = args.get("type", "EMITTER")  # EMITTER, HAIR
    settings = args.get("settings", {})
    
    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"对象不存在: {object_name}"}
            
            # 设置活动对象
            bpy.context.view_layer.objects.active = obj
            
            # 创建粒子系统
            if not obj.particle_systems:
                obj.modifiers.new("ParticleSystem", 'PARTICLE_SYSTEM')
                
            particle_system = obj.particle_systems[-1]
            particle_settings = particle_system.settings
            
            # 设置基本参数
            particle_settings.name = settings.get("name", f"{obj.name}_particles")
            particle_settings.type = particle_type
            particle_settings.count = particles_count
            
            # 设置发射参数
            if particle_type == "EMITTER":
                particle_settings.frame_start = settings.get("frame_start", 1)
                particle_settings.frame_end = settings.get("frame_end", 200)
                particle_settings.lifetime = settings.get("lifetime", 100)
                particle_settings.emit_from = settings.get("emit_from", 'FACE')
                
                # 速度设置
                if "velocity_factor" in settings:
                    particle_settings.normal_factor = settings["velocity_factor"]
                    
                # 物理设置
                if "physics_type" in settings:
                    particle_settings.physics_type = settings["physics_type"]
                    
                # 渲染设置
                if "render_type" in settings:
                    particle_settings.render_type = settings["render_type"]
                    
                    # 对象渲染
                    if settings["render_type"] == 'OBJECT' and "instance_object" in settings:
                        instance_obj = bpy.data.objects.get(settings["instance_object"])
                        if instance_obj:
                            particle_settings.instance_object = instance_obj
                            
                    # 集合渲染
                    elif settings["render_type"] == 'COLLECTION' and "instance_collection" in settings:
                        instance_col = bpy.data.collections.get(settings["instance_collection"])
                        if instance_col:
                            particle_settings.instance_collection = instance_col
            
            # 设置毛发参数            
            elif particle_type == "HAIR":
                particle_settings.hair_length = settings.get("hair_length", 4.0)
                particle_settings.render_step = settings.get("render_step", 3)
                
                # 动力学设置
                if "use_dynamic_hair" in settings:
                    particle_settings.use_dynamic_hair = settings["use_dynamic_hair"]
                    
            # 更新场景
            bpy.context.view_layer.update()
            
            return {
                "status": "success",
                "object": object_name,
                "particles_count": particles_count,
                "particle_type": particle_type,
                "system_name": particle_settings.name
            }
            
        except Exception as e:
            logger.error(f"创建粒子系统时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def advanced_lighting(args):
    """高级照明设置"""
    logger.debug(f"高级照明设置: {args}")
    light_type = args.get("light_type", "AREA")
    name = args.get("name")
    location = args.get("location", (0, 0, 4))
    rotation = args.get("rotation", (0, 0, 0))
    color = args.get("color", (1, 1, 1))
    energy = args.get("energy", 100)
    settings = args.get("settings", {})
    
    def exec_func():
        try:
            # 创建灯光对象
            bpy.ops.object.light_add(type=light_type, location=location, rotation=rotation)
            light_obj = bpy.context.object
            
            # 设置名称
            if name:
                light_obj.name = name
            
            # 获取灯光数据
            light_data = light_obj.data
            
            # 设置基本参数
            light_data.color = color
            light_data.energy = energy
            
            # 根据灯光类型设置特定参数
            if light_type == "POINT":
                light_data.shadow_soft_size = settings.get("shadow_soft_size", 0.1)
                
            elif light_type == "SUN":
                light_data.angle = settings.get("angle", 0.1)
                
            elif light_type == "SPOT":
                light_data.spot_size = settings.get("spot_size", math.radians(45))
                light_data.spot_blend = settings.get("spot_blend", 0.15)
                light_data.shadow_soft_size = settings.get("shadow_soft_size", 0.1)
                
            elif light_type == "AREA":
                light_data.shape = settings.get("shape", 'SQUARE')
                light_data.size = settings.get("size", 1.0)
                if light_data.shape in ('RECTANGLE', 'ELLIPSE'):
                    light_data.size_y = settings.get("size_y", 1.0)
            
            # 阴影设置
            light_data.use_shadow = settings.get("use_shadow", True)
            if hasattr(light_data, "shadow_buffer_clip_start"):
                light_data.shadow_buffer_clip_start = settings.get("shadow_clip_start", 0.1)
                light_data.shadow_buffer_clip_end = settings.get("shadow_clip_end", 100.0)
            
            # 创建节点材质（如果需要）
            if settings.get("use_nodes", False):
                light_data.use_nodes = True
                
                # 获取节点树
                node_tree = light_data.node_tree
                
                # 清除现有节点
                for node in node_tree.nodes:
                    node_tree.nodes.remove(node)
                
                # 创建发射节点
                emission_node = node_tree.nodes.new(type='ShaderNodeEmission')
                emission_node.inputs['Color'].default_value = color + (1.0,)  # RGBA
                emission_node.inputs['Strength'].default_value = energy
                
                # 创建输出节点
                output_node = node_tree.nodes.new(type='ShaderNodeOutputLight')
                
                # 连接节点
                node_tree.links.new(emission_node.outputs[0], output_node.inputs[0])
            
            return {
                "status": "success",
                "object": light_obj.name,
                "type": light_type,
                "energy": energy,
                "location": location
            }
            
        except Exception as e:
            logger.error(f"高级照明设置时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def list_tools():
    """返回可用工具列表"""
    from .tools import register_all_tools
    
    logger.debug("列出可用工具")
    
    # 获取所有注册的工具
    tools_dict = register_all_tools()
    
    tools = []
    for tool_name, tool_func in tools_dict.items():
        # 获取工具的docstring作为描述
        description = tool_func.__doc__ or f"执行{tool_name}操作"
        
        # 构建工具信息
        tool_info = {
            "name": tool_name,
            "description": description.strip(),
            "version": "1.0"
        }
        
        # 针对特定工具添加额外信息
        if tool_name == "create_object":
            tool_info["input_schema"] = {
                "type": "object",
                "properties": {
                    "object_type": {
                        "type": "string",
                        "enum": ["cube", "sphere", "plane", "cylinder", "cone", "torus", "empty"],
                        "description": "要创建的对象类型"
                    },
                    "location": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "对象位置坐标 [x, y, z]"
                    },
                    "name": {
                        "type": "string",
                        "description": "对象名称"
                    },
                    "size": {
                        "type": "number",
                        "description": "对象大小"
                    }
                },
                "required": ["object_type"]
            }
        elif tool_name == "set_material":
            tool_info["input_schema"] = {
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "目标对象名称"},
                    "material_name": {"type": "string", "description": "材质名称"},
                    "color": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "RGBA颜色值 [r, g, b, a]"
                    },
                    "metallic": {"type": "number", "description": "金属度(0-1)"},
                    "roughness": {"type": "number", "description": "粗糙度(0-1)"}
                },
                "required": ["object_name"]
            }
        elif tool_name == "add_light":
            tool_info["input_schema"] = {
                "type": "object",
                "properties": {
                    "light_type": {
                        "type": "string",
                        "enum": ["POINT", "SUN", "SPOT", "AREA"],
                        "description": "灯光类型"
                    },
                    "location": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "灯光位置 [x, y, z]"
                    },
                    "name": {"type": "string", "description": "灯光名称"},
                    "color": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "RGB颜色值 [r, g, b]"
                    },
                    "energy": {"type": "number", "description": "灯光强度"}
                },
                "required": ["light_type"]
            }
        
        tools.append(tool_info)
    
    return tools

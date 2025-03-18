import bpy
import os
import tempfile
import base64
from mathutils import Vector, Euler
import threading
import time
import logging
from ..utils import thread_utils

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
    
    with _tool_lock:
        try:
            if tool_name in TOOLS:
                return TOOLS[tool_name](arguments)
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
    color = args.get("color", [0.8, 0.8, 0.8, 1.0])
    metallic = args.get("metallic", 0.0)
    roughness = args.get("roughness", 0.5)
    
    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"找不到对象: {object_name}"}
                
            # 创建新材质
            mat_name = f"{object_name}_material"
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True
            
            # 设置颜色和属性
            principled_bsdf = mat.node_tree.nodes.get('Principled BSDF')
            if principled_bsdf:
                principled_bsdf.inputs["Base Color"].default_value = color
                principled_bsdf.inputs["Metallic"].default_value = metallic
                principled_bsdf.inputs["Roughness"].default_value = roughness
                
            # 应用材质到对象
            if obj.data.materials:
                obj.data.materials[0] = mat
            else:
                obj.data.materials.append(mat)
                
            return {
                "status": "success", 
                "material_name": mat_name,
                "object_name": object_name
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

# TOOLS字典定义...
TOOLS = {
    "create_object": create_object,
    "set_material": set_material,
    "add_light": add_light,
    "set_camera": set_camera,
    "render_scene": render_scene,
    "apply_modifier": apply_modifier,
    "transform_object": transform_object,
    "import_model": import_model
}

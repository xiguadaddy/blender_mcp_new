import bpy
import json
import bmesh
from mathutils import Vector
import base64
import logging
import os
import tempfile
from ..utils import thread_utils

# 设置日志
logger = logging.getLogger("BlenderMCP.Resources")
# 配置日志格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# 添加控制台处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# 添加文件处理器
log_file = os.path.join(tempfile.gettempdir(), "blender_mcp_resources.log")
file_handler = logging.FileHandler(log_file, mode='a')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

logger.setLevel(logging.DEBUG)

# 资源变更跟踪变量
resource_state = {
    "objects": {},       # 对象状态
    "materials": {},     # 材质状态
    "lights": {},        # 灯光状态
    "cameras": {},       # 相机状态
    "scene": {           # 场景状态
        "frame": 0,      # 当前帧
    }
}

def execute_in_main_thread(func, *args, **kwargs):
    """在Blender主线程中执行函数"""
    # 确保主线程处理器已注册
    thread_utils.register_main_thread_processor()
    
    logger.debug(f"在主线程中执行函数: {func.__name__}")
    # 使用线程工具执行函数
    return thread_utils.run_in_main_thread(func, *args, **kwargs)

def update_resource_state():
    """更新资源状态，检测变化，并返回变化的资源URI列表"""
    changed_resources = []
    
    logger.debug("更新资源状态...")
    
    try:
        # 检查对象变化
        for obj in bpy.context.scene.objects:
            obj_id = obj.name
            obj_type = obj.type.lower()
            
            # 对象位置和旋转的哈希
            obj_state = f"{obj.location}|{obj.rotation_euler}|{obj.scale}"
            
            # 检查这个对象是否是新的或已更改
            if obj_type not in resource_state["objects"]:
                resource_state["objects"][obj_type] = {}
                
            if obj_id not in resource_state["objects"][obj_type] or resource_state["objects"][obj_type][obj_id] != obj_state:
                resource_state["objects"][obj_type][obj_id] = obj_state
                changed_uri = f"blender://{obj_type}/{obj_id}"
                changed_resources.append(changed_uri)
                logger.debug(f"资源变化: {changed_uri}")
        
        # 检查材质变化
        for mat in bpy.data.materials:
            mat_id = mat.name
            
            # 简单地使用修改时间作为状态
            if mat.use_nodes and mat.node_tree:
                mat_state = str(mat.node_tree.nodes.values())
            else:
                mat_state = str(mat.diffuse_color)
                
            if mat_id not in resource_state["materials"] or resource_state["materials"][mat_id] != mat_state:
                resource_state["materials"][mat_id] = mat_state
                changed_uri = f"blender://material/{mat_id}"
                changed_resources.append(changed_uri)
                logger.debug(f"资源变化: {changed_uri}")
        
        # 检查灯光变化
        for light in [obj for obj in bpy.context.scene.objects if obj.type == 'LIGHT']:
            light_id = light.name
            light_data = light.data
            
            # 灯光状态包括位置、颜色和能量
            light_state = f"{light.location}|{light_data.color}|{light_data.energy}"
            
            if light_id not in resource_state["lights"] or resource_state["lights"][light_id] != light_state:
                resource_state["lights"][light_id] = light_state
                changed_uri = f"blender://light/{light_id}"
                changed_resources.append(changed_uri)
                logger.debug(f"资源变化: {changed_uri}")
                
        # 检查相机变化
        for camera in [obj for obj in bpy.context.scene.objects if obj.type == 'CAMERA']:
            camera_id = camera.name
            camera_data = camera.data
            
            # 相机状态包括位置、旋转和镜头参数
            camera_state = f"{camera.location}|{camera.rotation_euler}|{camera_data.lens}"
            
            if camera_id not in resource_state["cameras"] or resource_state["cameras"][camera_id] != camera_state:
                resource_state["cameras"][camera_id] = camera_state
                changed_uri = f"blender://camera/{camera_id}"
                changed_resources.append(changed_uri)
                logger.debug(f"资源变化: {changed_uri}")
                
        # 检查场景变化（例如当前帧）
        current_frame = bpy.context.scene.frame_current
        if resource_state["scene"]["frame"] != current_frame:
            resource_state["scene"]["frame"] = current_frame
            changed_uri = f"blender://scene/current"
            changed_resources.append(changed_uri)
            logger.debug(f"资源变化: {changed_uri}")
            
        if changed_resources:
            logger.info(f"检测到 {len(changed_resources)} 个资源变化")
        
        return changed_resources
        
    except Exception as e:
        logger.error(f"更新资源状态时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def check_object_exists(object_name):
    """检查对象是否存在"""
    logger.debug(f"检查对象是否存在: {object_name}")
    return {"exists": object_name in bpy.data.objects}

def handle_list_resources():
    """列出所有可用资源"""
    logger.debug("处理list_resources请求")
    
    # 创建一个简化版本的资源列表函数，避免死锁
    def simple_get_resources():
        try:
            resources = []
            max_items = 100  # 限制资源数量，避免过多处理
            counter = 0
            
            # 收集场景中的对象，带计数限制
            for obj in bpy.context.scene.objects:
                if counter >= max_items:
                    break
                resources.append({
                    "type": obj.type.lower(),
                    "id": obj.name,
                    "name": obj.name,
                    "uri": f"blender://{obj.type.lower()}/{obj.name}"
                })
                counter += 1
                
            # 如果还有配额，收集材质
            if counter < max_items:
                material_limit = max_items - counter
                for i, mat in enumerate(bpy.data.materials):
                    if i >= material_limit:
                        break
                    resources.append({
                        "type": "material",
                        "id": mat.name,
                        "name": mat.name,
                        "uri": f"blender://material/{mat.name}"
                    })
                    counter += 1
            
            # 添加场景资源
            if counter < max_items:
                resources.append({
                    "type": "scene",
                    "id": "current",
                    "name": bpy.context.scene.name if hasattr(bpy.context, "scene") and bpy.context.scene else "未知场景",
                    "uri": "blender://scene/current"
                })
                
            logger.info(f"简化模式：找到 {len(resources)} 个资源")
            return resources
            
        except Exception as e:
            logger.error(f"获取简化资源列表时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    # 尝试使用主线程执行，但带有超时保护
    try:
        # 使用一个简单的线程安全标记来检测超时
        result_holder = {"result": None, "completed": False}
        
        def exec_func():
            try:
                resources = []
                
                # 收集场景中的对象
                for obj in bpy.context.scene.objects:
                    resources.append({
                        "type": obj.type.lower(),
                        "id": obj.name,
                        "name": obj.name,
                        "uri": f"blender://{obj.type.lower()}/{obj.name}"
                    })
                    
                # 收集材质
                for mat in bpy.data.materials:
                    resources.append({
                        "type": "material",
                        "id": mat.name,
                        "name": mat.name,
                        "uri": f"blender://material/{mat.name}"
                    })
                    
                # 收集灯光
                for light in [obj for obj in bpy.context.scene.objects if obj.type == 'LIGHT']:
                    resources.append({
                        "type": "light",
                        "id": light.name,
                        "name": light.name,
                        "uri": f"blender://light/{light.name}"
                    })
                    
                # 收集相机
                for camera in [obj for obj in bpy.context.scene.objects if obj.type == 'CAMERA']:
                    resources.append({
                        "type": "camera",
                        "id": camera.name,
                        "name": camera.name,
                        "uri": f"blender://camera/{camera.name}"
                    })
                    
                # 添加场景资源
                resources.append({
                    "type": "scene",
                    "id": "current",
                    "name": bpy.context.scene.name,
                    "uri": "blender://scene/current"
                })
                
                logger.info(f"找到 {len(resources)} 个资源")
                result_holder["result"] = resources
                result_holder["completed"] = True
                return resources
                
            except Exception as e:
                logger.error(f"列出资源时出错: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                result_holder["result"] = []
                result_holder["completed"] = True
                return []
        
        # 启动一个线程在主线程中执行资源获取
        import threading
        thread = threading.Thread(target=lambda: execute_in_main_thread(exec_func))
        thread.daemon = True
        thread.start()
        
        # 等待结果，但有超时保护（2秒）
        import time
        start_time = time.time()
        max_wait_time = 2.0  # 最多等待2秒
        
        while time.time() - start_time < max_wait_time:
            if result_holder["completed"]:
                logger.debug(f"成功获取资源列表，用时: {time.time() - start_time:.2f}秒")
                return result_holder["result"]
            time.sleep(0.05)  # 短暂睡眠，避免CPU过载
            
        # 如果超时，使用简化版本获取
        logger.warning(f"获取资源列表超时，使用简化模式获取")
        return simple_get_resources()
        
    except Exception as e:
        logger.error(f"列出资源处理时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # 出错时也使用简化版本获取
        logger.warning("由于错误使用简化模式获取资源列表")
        return simple_get_resources()

def handle_read_resource(resource_type, resource_id):
    """读取指定资源的详细信息"""
    logger.debug(f"处理read_resource请求: type={resource_type}, id={resource_id}")
    
    try:
        if resource_type == "mesh":
            return extract_mesh_data(resource_id)
        elif resource_type == "material":
            return extract_material_data(resource_id)
        elif resource_type == "light":
            return extract_light_data(resource_id)
        elif resource_type == "camera":
            return extract_camera_data(resource_id)
        elif resource_type == "scene":
            return extract_scene_data(resource_id)
        else:
            error_msg = f"未知资源类型: {resource_type}"
            logger.warning(error_msg)
            return {"error": error_msg}
            
    except Exception as e:
        error_msg = f"读取资源时出错: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return {"error": error_msg}

def extract_mesh_data(mesh_name):
    """提取网格对象数据"""
    obj = bpy.data.objects.get(mesh_name)
    if not obj or obj.type != 'MESH':
        return {"error": f"找不到网格对象: {mesh_name}"}
        
    # 获取网格数据
    mesh = obj.data
    
    # 创建bmesh以获取更详细的信息
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    
    # 提取顶点
    vertices = []
    for v in bm.verts:
        vertices.append({
            "co": [v.co.x, v.co.y, v.co.z],
            "normal": [v.normal.x, v.normal.y, v.normal.z]
        })
    
    # 提取面
    faces = []
    for f in bm.faces:
        face_verts = [v.index for v in f.verts]
        faces.append({
            "verts": face_verts,
            "normal": [f.normal.x, f.normal.y, f.normal.z]
        })
    
    # 释放bmesh
    bm.free()
    
    # 收集材质信息
    materials = []
    for mat in obj.material_slots:
        if mat.material:
            materials.append(mat.material.name)
    
    return {
        "name": obj.name,
        "vertices_count": len(vertices),
        "faces_count": len(faces),
        "location": [obj.location.x, obj.location.y, obj.location.z],
        "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
        "scale": [obj.scale.x, obj.scale.y, obj.scale.z],
        "materials": materials,
        "vertices": vertices[:100],  # 限制数据量
        "faces": faces[:100],  # 限制数据量
    }

def extract_material_data(material_name):
    """提取材质数据"""
    mat = bpy.data.materials.get(material_name)
    if not mat:
        return {"error": f"找不到材质: {material_name}"}
    
    # 基本材质信息
    material_data = {
        "name": mat.name,
        "use_nodes": mat.use_nodes,
    }
    
    # 如果使用节点，提取一些基本属性
    if mat.use_nodes:
        principled = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if principled:
            material_data["base_color"] = [
                principled.inputs["Base Color"].default_value[0],
                principled.inputs["Base Color"].default_value[1],
                principled.inputs["Base Color"].default_value[2],
                principled.inputs["Base Color"].default_value[3]
            ]
            material_data["metallic"] = principled.inputs["Metallic"].default_value
            material_data["roughness"] = principled.inputs["Roughness"].default_value
    else:
        # 旧式材质系统
        material_data["diffuse_color"] = [
            mat.diffuse_color[0],
            mat.diffuse_color[1],
            mat.diffuse_color[2],
            mat.diffuse_color[3]
        ]
    
    return material_data

def extract_light_data(light_name):
    """提取灯光数据"""
    obj = bpy.data.objects.get(light_name)
    if not obj or obj.type != 'LIGHT':
        return {"error": f"找不到灯光对象: {light_name}"}
    
    light = obj.data
    light_data = {
        "name": obj.name,
        "type": light.type,
        "color": [light.color[0], light.color[1], light.color[2]],
        "energy": light.energy,
        "location": [obj.location.x, obj.location.y, obj.location.z],
    }
    
    # 特定类型的灯光属性
    if light.type == 'SPOT':
        light_data["spot_size"] = light.spot_size
        light_data["spot_blend"] = light.spot_blend
    elif light.type == 'SUN':
        light_data["angle"] = light.angle
    
    return light_data

def extract_camera_data(camera_name):
    """提取相机数据"""
    obj = bpy.data.objects.get(camera_name)
    if not obj or obj.type != 'CAMERA':
        return {"error": f"找不到相机对象: {camera_name}"}
    
    camera = obj.data
    camera_data = {
        "name": obj.name,
        "location": [obj.location.x, obj.location.y, obj.location.z],
        "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
        "lens": camera.lens,
        "sensor_width": camera.sensor_width,
        "sensor_height": camera.sensor_height,
        "clip_start": camera.clip_start,
        "clip_end": camera.clip_end,
    }
    
    return camera_data

def extract_scene_data(scene_id):
    """提取场景数据"""
    logger.debug(f"提取场景数据: {scene_id}")
    
    try:
        if scene_id != "current":
            return {"error": "只支持当前场景"}
            
        scene = bpy.context.scene
        
        # 收集基本场景数据
        scene_data = {
            "name": scene.name,
            "frame_current": scene.frame_current,
            "frame_start": scene.frame_start,
            "frame_end": scene.frame_end,
            "fps": scene.render.fps,
            "objects_count": len(scene.objects),
            "render_engine": scene.render.engine,
            "background_color": [c for c in scene.world.color] if scene.world else [0, 0, 0],
            "resolution": [scene.render.resolution_x, scene.render.resolution_y],
            "active_camera": scene.camera.name if scene.camera else None,
        }
        
        # 收集对象列表
        scene_data["objects"] = [obj.name for obj in scene.objects]
        
        # 收集灯光列表
        scene_data["lights"] = [obj.name for obj in scene.objects if obj.type == 'LIGHT']
        
        # 收集相机列表
        scene_data["cameras"] = [obj.name for obj in scene.objects if obj.type == 'CAMERA']
        
        logger.debug(f"场景数据提取完成: {scene.name}")
        return scene_data
        
    except Exception as e:
        error_msg = f"提取场景数据时出错: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return {"error": error_msg}

import bpy
import json
import bmesh
from mathutils import Vector
import base64
import logging

# 设置日志
logger = logging.getLogger("BlenderMCP.Resources")

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

def update_resource_state():
    """更新资源状态，检测变化，并返回变化的资源URI列表"""
    changed_resources = []
    
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
            changed_resources.append(f"blender://{obj_type}/{obj_id}")
    
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
            changed_resources.append(f"blender://material/{mat_id}")
    
    # 检查灯光变化
    for light in [obj for obj in bpy.context.scene.objects if obj.type == 'LIGHT']:
        light_id = light.name
        light_data = light.data
        
        # 灯光状态包括位置、颜色和能量
        light_state = f"{light.location}|{light_data.color}|{light_data.energy}"
        
        if light_id not in resource_state["lights"] or resource_state["lights"][light_id] != light_state:
            resource_state["lights"][light_id] = light_state
            changed_resources.append(f"blender://light/{light_id}")
    
    # 检查相机变化
    for camera in [obj for obj in bpy.context.scene.objects if obj.type == 'CAMERA']:
        camera_id = camera.name
        camera_data = camera.data
        
        # 相机状态包括位置、旋转和视场
        camera_state = f"{camera.location}|{camera.rotation_euler}|{camera_data.lens}"
        
        if camera_id not in resource_state["cameras"] or resource_state["cameras"][camera_id] != camera_state:
            resource_state["cameras"][camera_id] = camera_state
            changed_resources.append(f"blender://camera/{camera_id}")
    
    # 检查场景变化
    if bpy.context.scene.frame_current != resource_state["scene"]["frame"]:
        resource_state["scene"]["frame"] = bpy.context.scene.frame_current
        changed_resources.append("blender://scene/current")
    
    return changed_resources

def check_object_exists(object_name):
    """检查对象是否存在"""
    exists = object_name in bpy.data.objects
    logger.debug(f"检查对象 '{object_name}' 是否存在: {exists}")
    return {"exists": exists}

def handle_list_resources():
    """列出所有可用资源"""
    logger.debug("列出资源")
    resources = []
    
    # 收集场景中的对象
    for obj in bpy.context.scene.objects:
        resources.append({
            "type": obj.type.lower(),
            "id": obj.name,
            "name": obj.name
        })
        
    # 收集材质
    for mat in bpy.data.materials:
        resources.append({
            "type": "material",
            "id": mat.name,
            "name": mat.name
        })
        
    # 收集灯光
    for light in [obj for obj in bpy.context.scene.objects if obj.type == 'LIGHT']:
        resources.append({
            "type": "light",
            "id": light.name,
            "name": light.name
        })
        
    # 收集相机
    for camera in [obj for obj in bpy.context.scene.objects if obj.type == 'CAMERA']:
        resources.append({
            "type": "camera",
            "id": camera.name,
            "name": camera.name
        })
    
    # 添加场景本身
    resources.append({
        "type": "scene",
        "id": "current",
        "name": bpy.context.scene.name
    })
        
    logger.debug(f"找到 {len(resources)} 个资源")
    return resources

def handle_read_resource(resource_type, resource_id):
    """读取指定资源的详细信息"""
    logger.debug(f"读取资源: {resource_type}/{resource_id}")
    
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
            logger.error(error_msg)
            return {"error": error_msg}
    except Exception as e:
        error_msg = f"获取资源数据时出错: {str(e)}"
        logger.error(error_msg)
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
    if scene_id != "current":
        return {"error": f"只支持获取当前场景(current)，不支持: {scene_id}"}
    
    scene = bpy.context.scene
    
    # 收集基本场景信息
    scene_data = {
        "name": scene.name,
        "frame_current": scene.frame_current,
        "frame_start": scene.frame_start,
        "frame_end": scene.frame_end,
        "objects": [],
        "render_settings": {
            "engine": scene.render.engine,
            "resolution_x": scene.render.resolution_x,
            "resolution_y": scene.render.resolution_y,
            "resolution_percentage": scene.render.resolution_percentage,
            "fps": scene.render.fps,
        }
    }
    
    # 收集场景中的对象信息
    for obj in scene.objects:
        scene_data["objects"].append({
            "name": obj.name,
            "type": obj.type,
            "visible": obj.visible_get(),
            "location": [obj.location.x, obj.location.y, obj.location.z]
        })
    
    return scene_data

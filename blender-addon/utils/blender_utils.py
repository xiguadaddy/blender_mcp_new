import bpy
import os
import json

def get_blender_version():
    """获取Blender版本信息"""
    major, minor, patch = bpy.app.version
    return {
        "version": f"{major}.{minor}.{patch}",
        "version_tuple": (major, minor, patch),
        "build_date": bpy.app.build_date,
        "platform": bpy.app.platform
    }

def get_active_object():
    """获取活动对象信息"""
    obj = bpy.context.active_object
    if not obj:
        return None
        
    result = {
        "name": obj.name,
        "type": obj.type,
        "location": list(obj.location),
        "rotation": list(obj.rotation_euler),
        "scale": list(obj.scale)
    }
    
    # 添加类型特定信息
    if obj.type == 'MESH':
        result["vertices_count"] = len(obj.data.vertices)
        result["faces_count"] = len(obj.data.polygons)
        
    return result

def get_scene_stats():
    """获取当前场景统计信息"""
    scene = bpy.context.scene
    stats = {
        "name": scene.name,
        "objects": {
            "total": len(scene.objects),
            "by_type": {}
        },
        "frame_current": scene.frame_current,
        "frame_start": scene.frame_start,
        "frame_end": scene.frame_end,
        "render": {
            "engine": scene.render.engine,
            "resolution": (scene.render.resolution_x, scene.render.resolution_y)
        }
    }
    
    # 按类型统计对象
    for obj in scene.objects:
        if obj.type not in stats["objects"]["by_type"]:
            stats["objects"]["by_type"][obj.type] = 0
        stats["objects"]["by_type"][obj.type] += 1
        
    return stats

def export_scene_json(filepath):
    """将场景信息导出为JSON"""
    scene_data = {
        "name": bpy.context.scene.name,
        "objects": [],
        "materials": [],
        "cameras": [],
        "lights": []
    }
    
    # 收集对象信息
    for obj in bpy.context.scene.objects:
        obj_data = {
            "name": obj.name,
            "type": obj.type,
            "location": list(obj.location),
            "rotation": list(obj.rotation_euler),
            "scale": list(obj.scale),
            "visible": obj.visible_get()
        }
        scene_data["objects"].append(obj_data)
        
        # 收集相机信息
        if obj.type == 'CAMERA':
            cam_data = {
                "name": obj.name,
                "lens": obj.data.lens,
                "sensor_width": obj.data.sensor_width,
                "is_active": (obj == bpy.context.scene.camera)
            }
            scene_data["cameras"].append(cam_data)
            
        # 收集灯光信息
        elif obj.type == 'LIGHT':
            light_data = {
                "name": obj.name,
                "type": obj.data.type,
                "color": list(obj.data.color),
                "energy": obj.data.energy
            }
            scene_data["lights"].append(light_data)
    
    # 收集材质信息
    for mat in bpy.data.materials:
        mat_data = {
            "name": mat.name,
            "use_nodes": mat.use_nodes
        }
        scene_data["materials"].append(mat_data)
    
    # 导出到JSON文件
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(scene_data, f, indent=2)
        
    return filepath

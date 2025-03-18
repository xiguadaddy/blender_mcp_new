"""
相机操作工具模块

包括相机的创建、获取、修改和删除相关功能。
"""

import bpy
import logging
import math
from mathutils import Vector, Euler
from ..tool_handlers import execute_in_main_thread

# 设置日志
logger = logging.getLogger("BlenderMCP.CameraTools")

# 相机创建函数
def add_camera(args):
    """添加相机到场景"""
    logger.debug(f"添加相机: {args}")
    name = args.get("name", "New_Camera")
    location = args.get("location", [0, 0, 0])
    rotation = args.get("rotation", [0, 0, 0])
    lens = args.get("lens", 50.0)
    
    def exec_func():
        try:
            # 创建相机数据
            camera_data = bpy.data.cameras.new(name=name)
            
            # 设置镜头参数
            camera_data.lens = lens
            
            # 创建相机对象
            camera_obj = bpy.data.objects.new(name=name, object_data=camera_data)
            camera_obj.location = location
            camera_obj.rotation_euler = Euler(rotation, 'XYZ')
            
            # 添加到场景
            bpy.context.collection.objects.link(camera_obj)
            
            return {
                "status": "success", 
                "camera_name": name,
                "location": list(camera_obj.location),
                "rotation": list(camera_obj.rotation_euler),
                "lens": camera_data.lens
            }
        except Exception as e:
            logger.error(f"添加相机时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def set_camera(args):
    """设置场景活动相机并配置其参数"""
    logger.debug(f"设置活动相机: {args}")
    name = args.get("name")
    location = args.get("location")
    rotation = args.get("rotation")
    target = args.get("target")
    lens = args.get("lens")
    depth_of_field = args.get("depth_of_field", {})
    
    def exec_func():
        try:
            camera_obj = None
            
            # 检查是否需要创建新相机
            if not name or name not in bpy.data.objects:
                # 创建新相机
                bpy.ops.object.camera_add()
                camera_obj = bpy.context.object
                if name:
                    camera_obj.name = name
            else:
                # 使用现有相机
                camera_obj = bpy.data.objects[name]
            
            # 确保对象是相机
            if camera_obj.type != 'CAMERA':
                return {"error": f"对象 '{name}' 不是相机"}
            
            # 设置场景的活动相机
            bpy.context.scene.camera = camera_obj
            
            # 设置位置和旋转
            if location:
                camera_obj.location = location
            
            # 如果提供了目标，让相机看向目标
            if target:
                # 计算相机应该面向的方向
                direction = Vector(target) - camera_obj.location
                # 使用 track_to 约束让相机看向目标
                track_to = None
                for constraint in camera_obj.constraints:
                    if constraint.type == 'TRACK_TO':
                        track_to = constraint
                        break
                
                if not track_to:
                    track_to = camera_obj.constraints.new('TRACK_TO')
                
                # 如果有空物体作为目标，使用它，否则创建一个
                empty_name = f"{camera_obj.name}_target"
                target_obj = bpy.data.objects.get(empty_name)
                
                if not target_obj:
                    # 创建空物体作为目标
                    bpy.ops.object.empty_add(type='PLAIN_AXES', location=target)
                    target_obj = bpy.context.object
                    target_obj.name = empty_name
                else:
                    # 更新现有目标的位置
                    target_obj.location = target
                
                # 设置track_to约束的目标
                track_to.target = target_obj
                track_to.track_axis = 'TRACK_NEGATIVE_Z'
                track_to.up_axis = 'UP_Y'
            elif rotation:
                # 如果没有目标但有旋转，直接设置旋转
                # 清除可能存在的track_to约束
                for constraint in camera_obj.constraints:
                    if constraint.type == 'TRACK_TO':
                        camera_obj.constraints.remove(constraint)
                
                camera_obj.rotation_euler = Euler(rotation, 'XYZ')
            
            # 设置相机参数
            camera_data = camera_obj.data
            
            if lens:
                camera_data.lens = lens
            
            # 设置景深参数
            if depth_of_field:
                camera_data.dof.use_dof = True
                
                # 焦距
                if "focus_distance" in depth_of_field:
                    camera_data.dof.focus_distance = depth_of_field["focus_distance"]
                
                # 光圈F值
                if "aperture_fstop" in depth_of_field:
                    camera_data.dof.aperture_fstop = depth_of_field["aperture_fstop"]
                
                # 光圈叶片数
                if "aperture_blades" in depth_of_field:
                    camera_data.dof.aperture_blades = depth_of_field["aperture_blades"]
                
                # 光圈旋转
                if "aperture_rotation" in depth_of_field:
                    camera_data.dof.aperture_rotation = depth_of_field["aperture_rotation"]
                
                # 光圈比率
                if "aperture_ratio" in depth_of_field:
                    camera_data.dof.aperture_ratio = depth_of_field["aperture_ratio"]
            
            return {
                "status": "success",
                "camera": camera_obj.name,
                "location": list(camera_obj.location),
                "lens": camera_data.lens,
                "is_active": (bpy.context.scene.camera == camera_obj)
            }
            
        except Exception as e:
            logger.error(f"设置相机时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

# 相机修改函数
def update_camera(args):
    """更新相机属性"""
    logger.debug(f"更新相机属性: {args}")
    camera_name = args.get("camera_name")
    location = args.get("location")
    rotation = args.get("rotation")
    lens = args.get("lens")
    depth_of_field = args.get("depth_of_field")
    
    def exec_func():
        try:
            # 获取相机对象
            camera_obj = bpy.data.objects.get(camera_name)
            if not camera_obj or camera_obj.type != 'CAMERA':
                return {"error": f"找不到相机对象: {camera_name}"}
            
            # 获取相机数据
            camera_data = camera_obj.data
            
            # 更新各项属性
            if location is not None:
                camera_obj.location = location
                
            if rotation is not None:
                # 清除可能存在的track_to约束
                for constraint in camera_obj.constraints:
                    if constraint.type == 'TRACK_TO':
                        camera_obj.constraints.remove(constraint)
                
                camera_obj.rotation_euler = Euler(rotation, 'XYZ')
                
            if lens is not None:
                camera_data.lens = lens
                
            # 设置景深参数
            if depth_of_field is not None:
                camera_data.dof.use_dof = True
                
                # 焦距
                if "focus_distance" in depth_of_field:
                    camera_data.dof.focus_distance = depth_of_field["focus_distance"]
                
                # 光圈F值
                if "aperture_fstop" in depth_of_field:
                    camera_data.dof.aperture_fstop = depth_of_field["aperture_fstop"]
                
                # 光圈叶片数
                if "aperture_blades" in depth_of_field:
                    camera_data.dof.aperture_blades = depth_of_field["aperture_blades"]
                
                # 光圈旋转
                if "aperture_rotation" in depth_of_field:
                    camera_data.dof.aperture_rotation = depth_of_field["aperture_rotation"]
                
                # 光圈比率
                if "aperture_ratio" in depth_of_field:
                    camera_data.dof.aperture_ratio = depth_of_field["aperture_ratio"]
            
            return {
                "status": "success",
                "camera": camera_name,
                "location": list(camera_obj.location),
                "rotation": list(camera_obj.rotation_euler),
                "lens": camera_data.lens
            }
            
        except Exception as e:
            logger.error(f"更新相机属性时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

# 相机获取函数
def get_camera_info(args):
    """获取相机信息"""
    logger.debug(f"获取相机信息: {args}")
    camera_name = args.get("camera_name")
    
    def exec_func():
        try:
            # 获取相机对象
            camera_obj = bpy.data.objects.get(camera_name)
            if not camera_obj or camera_obj.type != 'CAMERA':
                return {"error": f"找不到相机对象: {camera_name}"}
            
            # 获取相机数据
            camera_data = camera_obj.data
            
            # 基本相机信息
            camera_info = {
                "name": camera_obj.name,
                "location": list(camera_obj.location),
                "rotation": list(camera_obj.rotation_euler),
                "lens": camera_data.lens,
                "is_active": (bpy.context.scene.camera == camera_obj),
                "type": camera_data.type,  # 'PERSP', 'ORTHO', or 'PANO'
                "sensor_width": camera_data.sensor_width,
                "sensor_height": camera_data.sensor_height
            }
            
            # 景深信息
            camera_info["depth_of_field"] = {
                "use_dof": camera_data.dof.use_dof,
                "focus_distance": camera_data.dof.focus_distance,
                "aperture_fstop": camera_data.dof.aperture_fstop,
                "aperture_blades": camera_data.dof.aperture_blades,
                "aperture_rotation": camera_data.dof.aperture_rotation,
                "aperture_ratio": camera_data.dof.aperture_ratio
            }
            
            # 检查约束
            constraints = []
            for constraint in camera_obj.constraints:
                constraint_info = {
                    "type": constraint.type,
                    "name": constraint.name
                }
                
                if constraint.type == 'TRACK_TO' and constraint.target:
                    constraint_info["target"] = constraint.target.name
                    constraint_info["target_location"] = list(constraint.target.location)
                
                constraints.append(constraint_info)
            
            camera_info["constraints"] = constraints
            
            return {
                "status": "success",
                "camera_info": camera_info
            }
            
        except Exception as e:
            logger.error(f"获取相机信息时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def list_cameras(args):
    """列出场景中的所有相机"""
    logger.debug(f"列出相机: {args}")
    
    def exec_func():
        try:
            cameras = []
            active_camera = bpy.context.scene.camera
            
            # 遍历场景中的所有对象
            for obj in bpy.context.scene.objects:
                if obj.type == 'CAMERA':
                    camera_data = obj.data
                    
                    # 基本相机信息
                    camera_info = {
                        "name": obj.name,
                        "location": list(obj.location),
                        "lens": camera_data.lens,
                        "is_active": (obj == active_camera)
                    }
                    
                    cameras.append(camera_info)
            
            return {
                "status": "success",
                "count": len(cameras),
                "cameras": cameras
            }
            
        except Exception as e:
            logger.error(f"列出相机时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

# 相机删除函数
def delete_camera(args):
    """删除相机"""
    logger.debug(f"删除相机: {args}")
    camera_names = args.get("camera_names", [])
    camera_name = args.get("camera_name")
    
    # 确保我们有相机列表
    if camera_name and not camera_names:
        camera_names = [camera_name]
        
    def exec_func():
        try:
            if not camera_names:
                return {"error": "未提供要删除的相机名称"}
                
            deleted_cameras = []
            not_found_cameras = []
            
            # 收集需要删除的相机对象
            cameras_to_delete = []
            for name in camera_names:
                obj = bpy.data.objects.get(name)
                if obj and obj.type == 'CAMERA':
                    # 检查是否为活动相机
                    if obj == bpy.context.scene.camera:
                        # 清除活动相机设置
                        bpy.context.scene.camera = None
                    
                    cameras_to_delete.append(obj)
                    deleted_cameras.append(name)
                else:
                    not_found_cameras.append(name)
            
            # 删除相机对象
            if cameras_to_delete:
                # 取消选择所有对象
                bpy.ops.object.select_all(action='DESELECT')
                
                # 选择要删除的相机
                for obj in cameras_to_delete:
                    obj.select_set(True)
                    
                # 删除选定的对象
                bpy.ops.object.delete()
            
            result = {
                "status": "success",
                "deleted_count": len(deleted_cameras),
                "deleted_cameras": deleted_cameras
            }
            
            if not_found_cameras:
                result["not_found_cameras"] = not_found_cameras
                result["warnings"] = f"未找到 {len(not_found_cameras)} 个相机"
                
            return result
            
        except Exception as e:
            logger.error(f"删除相机时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

# 注册工具
TOOLS = {
    # 创建类
    "add_camera": add_camera,
    "set_camera": set_camera,
    
    # 修改类
    "update_camera": update_camera,
    
    # 获取类
    "get_camera_info": get_camera_info,
    "list_cameras": list_cameras,
    
    # 删除类
    "delete_camera": delete_camera
} 
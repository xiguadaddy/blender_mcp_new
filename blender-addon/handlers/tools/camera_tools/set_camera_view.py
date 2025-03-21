"""
设置Blender相机视角的工具
"""

import bpy
from ..registry import register_tool
import logging
import math
import mathutils
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.SetCameraView")

class SetCameraViewHandler(BaseToolHandler):
    """设置相机视角工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_set_camera_view"
        
    @property
    def description(self) -> Optional[str]:
        return "设置相机的位置、旋转和视角"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "camera_name": {
                    "type": "string",
                    "title": "相机名称",
                    "description": "要调整的相机名称"
                },
                "location": {
                    "type": "array",
                    "title": "位置",
                    "description": "相机的位置坐标 [x, y, z]",
                    "items": {
                        "type": "number"
                    }
                },
                "rotation": {
                    "type": "array",
                    "title": "旋转",
                    "description": "相机的旋转角度（弧度）[x, y, z]",
                    "items": {
                        "type": "number"
                    }
                },
                "target": {
                    "type": "array",
                    "title": "目标点",
                    "description": "相机看向的目标点坐标 [x, y, z]",
                    "items": {
                        "type": "number"
                    }
                },
                "target_object": {
                    "type": "string",
                    "title": "目标对象",
                    "description": "相机要对准的对象名称"
                },
                "distance": {
                    "type": "number",
                    "title": "距离",
                    "description": "相机与目标的距离"
                },
                "angle": {
                    "type": "number",
                    "title": "角度",
                    "description": "相机俯视角度（度）"
                },
                "roll": {
                    "type": "number",
                    "title": "侧倾角",
                    "description": "相机的侧倾角度（度）"
                }
            },
            "required": ["camera_name"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查相机名称
        if not arguments.get("camera_name"):
            return "必须提供相机名称"
            
        # 检查位置参数
        location = arguments.get("location")
        if location and not (isinstance(location, list) and len(location) == 3 and all(isinstance(v, (int, float)) for v in location)):
            return "位置参数必须是包含3个数字的数组 [x, y, z]"
            
        # 检查旋转参数
        rotation = arguments.get("rotation")
        if rotation and not (isinstance(rotation, list) and len(rotation) == 3 and all(isinstance(v, (int, float)) for v in rotation)):
            return "旋转参数必须是包含3个数字的数组 [x, y, z]"
            
        # 检查目标点参数
        target = arguments.get("target")
        if target and not (isinstance(target, list) and len(target) == 3 and all(isinstance(v, (int, float)) for v in target)):
            return "目标点参数必须是包含3个数字的数组 [x, y, z]"
            
        # 检查兼容性
        if target and rotation:
            return "不能同时指定目标点和旋转，因为它们会相互冲突"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行设置相机视角操作"""
        logger.info(f"设置相机视角，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._set_camera_view, arguments)
        
    def _set_camera_view(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中设置相机视角"""
        camera_name = arguments.get("camera_name")
        location = arguments.get("location")
        rotation = arguments.get("rotation")
        target = arguments.get("target")
        target_object = arguments.get("target_object")
        distance = arguments.get("distance")
        angle = arguments.get("angle")
        roll = arguments.get("roll", 0)
        
        # 检查相机是否存在
        if camera_name not in bpy.data.objects:
            text_content = self.create_text_content(f"找不到相机: {camera_name}")
            return self.create_result([text_content], is_error=True)
        
        # 获取相机对象
        camera_obj = bpy.data.objects[camera_name]
        
        # 确保对象是相机类型
        if camera_obj.type != 'CAMERA':
            text_content = self.create_text_content(f"对象 '{camera_name}' 不是相机")
            return self.create_result([text_content], is_error=True)
        
        # 记录修改的属性
        modified_props = []
        
        # 设置相机位置
        if location:
            camera_obj.location = location
            modified_props.append(f"位置: {location}")
            
        # 设置相机旋转
        if rotation:
            camera_obj.rotation_euler = rotation
            modified_props.append(f"旋转: {rotation}")
            
        # 如果提供了目标对象，获取其位置
        if target_object:
            if target_object in bpy.data.objects:
                target_obj = bpy.data.objects[target_object]
                target = [target_obj.location.x, target_obj.location.y, target_obj.location.z]
                modified_props.append(f"目标对象: {target_object}")
            else:
                text_content = self.create_text_content(f"找不到目标对象: {target_object}")
                return self.create_result([text_content], is_error=True)
        
        # 如果提供了目标点，计算相机旋转
        if target:
            # 计算从相机到目标的方向向量
            cam_loc = mathutils.Vector(location) if location else camera_obj.location
            target_vec = mathutils.Vector(target)
            direction = target_vec - cam_loc
            
            # 计算旋转
            rot_quat = direction.to_track_quat('-Z', 'Y')
            
            # 应用侧倾角
            if roll:
                roll_rad = math.radians(roll)
                roll_mat = mathutils.Matrix.Rotation(roll_rad, 4, 'Z')
                rot_quat = rot_quat @ roll_mat.to_quaternion()
            
            # 应用旋转
            camera_obj.rotation_euler = rot_quat.to_euler()
            modified_props.append(f"朝向目标点: {target}")
            
            # 如果提供了距离，调整相机位置
            if distance:
                # 规范化方向向量并调整距离
                dir_norm = direction.normalized()
                camera_obj.location = target_vec - dir_norm * distance
                modified_props.append(f"距离: {distance}")
                
        # 如果提供了俯视角度和距离，根据角度调整相机位置
        elif angle is not None and target and distance:
            # 将角度转换为弧度
            angle_rad = math.radians(angle)
            
            # 计算相机的位置（简化为仅在yz平面内工作）
            cam_x = target[0]
            cam_y = target[1] - distance * math.cos(angle_rad)
            cam_z = target[2] + distance * math.sin(angle_rad)
            
            camera_obj.location = [cam_x, cam_y, cam_z]
            
            # 计算朝向目标的旋转
            direction = mathutils.Vector(target) - camera_obj.location
            rot_quat = direction.to_track_quat('-Z', 'Y')
            
            # 应用侧倾角
            if roll:
                roll_rad = math.radians(roll)
                roll_mat = mathutils.Matrix.Rotation(roll_rad, 4, 'Z')
                rot_quat = rot_quat @ roll_mat.to_quaternion()
            
            camera_obj.rotation_euler = rot_quat.to_euler()
            
            modified_props.append(f"角度: {angle}°")
            modified_props.append(f"距离: {distance}")
        
        # 创建结果信息
        if modified_props:
            properties_text = "\n".join(modified_props)
            text_content = self.create_text_content(f"已设置相机 '{camera_name}' 的视角:\n{properties_text}")
        else:
            text_content = self.create_text_content(f"未修改相机 '{camera_name}' 的任何视角属性")
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(SetCameraViewHandler())
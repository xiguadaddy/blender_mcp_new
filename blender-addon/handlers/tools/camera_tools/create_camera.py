"""
创建Blender相机的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional
import mathutils

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.CreateCamera")

class CreateCameraHandler(BaseToolHandler):
    """创建相机工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_create_camera"
        
    @property
    def description(self) -> Optional[str]:
        return "创建新的相机并设置其属性"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "title": "相机名称",
                    "description": "新相机的名称"
                },
                "location": {
                    "type": "array",
                    "title": "位置",
                    "description": "相机的位置坐标 [x, y, z]",
                    "items": {
                        "type": "number"
                    },
                    "default": [0, 0, 5]
                },
                "rotation": {
                    "type": "array",
                    "title": "旋转",
                    "description": "相机的旋转角度（弧度）[x, y, z]",
                    "items": {
                        "type": "number"
                    },
                    "default": [0, 0, 0]
                },
                "lens": {
                    "type": "number",
                    "title": "焦距",
                    "description": "相机的焦距（mm）",
                    "default": 50
                },
                "sensor_width": {
                    "type": "number",
                    "title": "传感器宽度",
                    "description": "相机传感器宽度（mm）",
                    "default": 36
                },
                "set_active": {
                    "type": "boolean",
                    "title": "设为活动相机",
                    "description": "是否将新相机设为活动相机",
                    "default": True
                }
            }
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查位置参数
        location = arguments.get("location")
        if location and not (isinstance(location, list) and len(location) == 3 and all(isinstance(v, (int, float)) for v in location)):
            return "位置参数必须是包含3个数字的数组 [x, y, z]"
            
        # 检查旋转参数
        rotation = arguments.get("rotation")
        if rotation and not (isinstance(rotation, list) and len(rotation) == 3 and all(isinstance(v, (int, float)) for v in rotation)):
            return "旋转参数必须是包含3个数字的数组 [x, y, z]"
            
        # 检查焦距
        lens = arguments.get("lens")
        if lens is not None and (not isinstance(lens, (int, float)) or lens <= 0):
            return "焦距必须是正数"
            
        # 检查传感器宽度
        sensor_width = arguments.get("sensor_width")
        if sensor_width is not None and (not isinstance(sensor_width, (int, float)) or sensor_width <= 0):
            return "传感器宽度必须是正数"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行创建相机操作"""
        logger.info(f"创建相机，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._create_camera, arguments)
        
    def _create_camera(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中创建相机"""
        name = arguments.get("name", "新相机")
        location = arguments.get("location", [0, 0, 5])
        rotation = arguments.get("rotation", [0, 0, 0])
        lens = arguments.get("lens", 50)
        sensor_width = arguments.get("sensor_width", 36)
        set_active = arguments.get("set_active", True)
        
        # 创建相机数据
        camera_data = bpy.data.cameras.new(name=f"{name}_数据")
        
        # 设置相机属性
        camera_data.lens = lens
        camera_data.sensor_width = sensor_width
        
        # 创建相机对象
        camera_obj = bpy.data.objects.new(name, camera_data)
        
        # 设置位置和旋转
        camera_obj.location = location
        camera_obj.rotation_euler = rotation
        
        # 添加到场景
        bpy.context.collection.objects.link(camera_obj)
        
        # 设置为活动相机
        if set_active:
            bpy.context.scene.camera = camera_obj
        
        # 创建结果信息
        text_content = self.create_text_content(
            f"已创建相机: {camera_obj.name}\n"
            f"位置: {location}\n"
            f"旋转: {rotation}\n"
            f"焦距: {lens}mm\n"
            f"传感器宽度: {sensor_width}mm"
        )
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(CreateCameraHandler())
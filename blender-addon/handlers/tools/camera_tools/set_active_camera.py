"""
设置Blender活动相机的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.SetActiveCamera")

class SetActiveCameraHandler(BaseToolHandler):
    """设置活动相机工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_set_active_camera"
        
    @property
    def description(self) -> Optional[str]:
        return "设置场景的活动相机"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "camera_name": {
                    "type": "string",
                    "title": "相机名称",
                    "description": "要设为活动相机的相机名称"
                },
                "list_cameras": {
                    "type": "boolean",
                    "title": "列出所有相机",
                    "description": "是否列出场景中的所有相机",
                    "default": False
                }
            }
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 如果既没有提供相机名称，也没有设置列出所有相机标志，则返回错误
        if not arguments.get("camera_name") and not arguments.get("list_cameras"):
            return "需要提供相机名称或设置列出所有相机标志"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行设置活动相机操作"""
        logger.info(f"设置活动相机，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._set_active_camera, arguments)
        
    def _set_active_camera(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中设置活动相机"""
        camera_name = arguments.get("camera_name")
        list_cameras = arguments.get("list_cameras", False)
        
        # 如果设置了列出所有相机标志，收集并返回相机列表
        if list_cameras:
            cameras = []
            
            for obj in bpy.data.objects:
                if obj.type == 'CAMERA':
                    cameras.append({
                        "name": obj.name,
                        "active": (bpy.context.scene.camera == obj)
                    })
            
            if cameras:
                camera_list = "\n".join([
                    f"- {cam['name']} {'(活动)' if cam['active'] else ''}"
                    for cam in cameras
                ])
                
                text_content = self.create_text_content(f"场景中的相机:\n{camera_list}")
            else:
                text_content = self.create_text_content("场景中没有相机")
                
            return self.create_result([text_content])
        
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
        
        # 设置为活动相机
        bpy.context.scene.camera = camera_obj
        
        # 创建结果信息
        text_content = self.create_text_content(f"已将 '{camera_name}' 设为活动相机")
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(SetActiveCameraHandler())
"""
设置Blender相机属性的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.SetCameraProperties")

class SetCameraPropertiesHandler(BaseToolHandler):
    """设置相机属性工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_set_camera_properties"
        
    @property
    def description(self) -> Optional[str]:
        return "设置相机的各种属性，如焦距、景深等"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "camera_name": {
                    "type": "string",
                    "title": "相机名称",
                    "description": "要修改的相机名称"
                },
                "lens": {
                    "type": "number",
                    "title": "焦距",
                    "description": "相机的焦距（mm）"
                },
                "sensor_width": {
                    "type": "number",
                    "title": "传感器宽度",
                    "description": "相机传感器宽度（mm）"
                },
                "sensor_height": {
                    "type": "number",
                    "title": "传感器高度",
                    "description": "相机传感器高度（mm）"
                },
                "dof_distance": {
                    "type": "number",
                    "title": "景深距离",
                    "description": "景深焦点距离"
                },
                "use_dof": {
                    "type": "boolean",
                    "title": "启用景深",
                    "description": "是否启用景深效果"
                },
                "fstop": {
                    "type": "number",
                    "title": "光圈值",
                    "description": "光圈F值"
                },
                "clip_start": {
                    "type": "number",
                    "title": "开始裁剪距离",
                    "description": "相机的开始裁剪距离"
                },
                "clip_end": {
                    "type": "number",
                    "title": "结束裁剪距离",
                    "description": "相机的结束裁剪距离"
                },
                "type": {
                    "type": "string",
                    "title": "相机类型",
                    "description": "相机的类型",
                    "enum": ["PERSP", "ORTHO", "PANO"],
                    "default": "PERSP"
                }
            },
            "required": ["camera_name"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查相机名称
        if not arguments.get("camera_name"):
            return "必须提供相机名称"
            
        # 检查相机类型
        camera_type = arguments.get("type")
        if camera_type and camera_type not in ["PERSP", "ORTHO", "PANO"]:
            return "相机类型必须是 'PERSP'、'ORTHO' 或 'PANO'"
            
        # 检查正值参数
        for param_name in ["lens", "sensor_width", "sensor_height", "fstop", "clip_start", "clip_end"]:
            value = arguments.get(param_name)
            if value is not None and (not isinstance(value, (int, float)) or value <= 0):
                return f"{param_name} 必须是正数"
                
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行设置相机属性操作"""
        logger.info(f"设置相机属性，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._set_camera_properties, arguments)
        
    def _set_camera_properties(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中设置相机属性"""
        camera_name = arguments.get("camera_name")
        
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
        
        # 获取相机数据
        camera_data = camera_obj.data
        
        # 记录修改的属性
        modified_props = []
        
        # 设置相机属性
        if "lens" in arguments:
            camera_data.lens = arguments["lens"]
            modified_props.append(f"焦距: {arguments['lens']}mm")
            
        if "sensor_width" in arguments:
            camera_data.sensor_width = arguments["sensor_width"]
            modified_props.append(f"传感器宽度: {arguments['sensor_width']}mm")
            
        if "sensor_height" in arguments:
            camera_data.sensor_height = arguments["sensor_height"]
            modified_props.append(f"传感器高度: {arguments['sensor_height']}mm")
            
        if "dof_distance" in arguments:
            camera_data.dof.focus_distance = arguments["dof_distance"]
            modified_props.append(f"景深距离: {arguments['dof_distance']}")
            
        if "use_dof" in arguments:
            camera_data.dof.use_dof = arguments["use_dof"]
            modified_props.append(f"启用景深: {'是' if arguments['use_dof'] else '否'}")
            
        if "fstop" in arguments:
            camera_data.dof.aperture_fstop = arguments["fstop"]
            modified_props.append(f"光圈值: f/{arguments['fstop']}")
            
        if "clip_start" in arguments:
            camera_data.clip_start = arguments["clip_start"]
            modified_props.append(f"开始裁剪距离: {arguments['clip_start']}")
            
        if "clip_end" in arguments:
            camera_data.clip_end = arguments["clip_end"]
            modified_props.append(f"结束裁剪距离: {arguments['clip_end']}")
            
        if "type" in arguments:
            camera_data.type = arguments["type"]
            modified_props.append(f"相机类型: {arguments['type']}")
        
        # 创建结果信息
        if modified_props:
            properties_text = "\n".join(modified_props)
            text_content = self.create_text_content(f"已修改相机 '{camera_name}' 的属性:\n{properties_text}")
        else:
            text_content = self.create_text_content(f"未修改相机 '{camera_name}' 的任何属性")
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(SetCameraPropertiesHandler())
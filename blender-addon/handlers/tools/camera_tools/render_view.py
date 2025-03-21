"""
渲染Blender相机视图的工具
"""

import bpy
from ..registry import register_tool
import logging
import os
import tempfile
import base64
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.RenderView")

class RenderViewHandler(BaseToolHandler):
    """渲染相机视图工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_render_view"
        
    @property
    def description(self) -> Optional[str]:
        return "渲染相机的视图并返回结果图像"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "camera_name": {
                    "type": "string",
                    "title": "相机名称",
                    "description": "要渲染视图的相机名称"
                },
                "resolution_x": {
                    "type": "integer",
                    "title": "宽度分辨率",
                    "description": "渲染图像的宽度分辨率",
                    "default": 1920
                },
                "resolution_y": {
                    "type": "integer",
                    "title": "高度分辨率",
                    "description": "渲染图像的高度分辨率",
                    "default": 1080
                },
                "samples": {
                    "type": "integer",
                    "title": "采样数",
                    "description": "渲染的采样数量",
                    "default": 32
                },
                "file_format": {
                    "type": "string",
                    "title": "文件格式",
                    "description": "渲染结果的文件格式",
                    "enum": ["PNG", "JPEG", "BMP"],
                    "default": "PNG"
                },
                "save_path": {
                    "type": "string",
                    "title": "保存路径",
                    "description": "渲染结果的保存路径"
                },
                "engine": {
                    "type": "string",
                    "title": "渲染引擎",
                    "description": "使用的渲染引擎",
                    "enum": ["CYCLES", "BLENDER_EEVEE"],
                    "default": "BLENDER_EEVEE"
                }
            }
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查正整数参数
        for param_name in ["resolution_x", "resolution_y", "samples"]:
            value = arguments.get(param_name)
            if value is not None and (not isinstance(value, int) or value <= 0):
                return f"{param_name} 必须是正整数"
                
        # 检查文件格式
        file_format = arguments.get("file_format", "PNG")
        if file_format not in ["PNG", "JPEG", "BMP"]:
            return "文件格式必须是 'PNG'、'JPEG' 或 'BMP'"
            
        # 检查渲染引擎
        engine = arguments.get("engine", "BLENDER_EEVEE")
        if engine not in ["CYCLES", "BLENDER_EEVEE"]:
            return "渲染引擎必须是 'CYCLES' 或 'BLENDER_EEVEE'"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行渲染相机视图操作"""
        logger.info(f"渲染相机视图，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._render_view, arguments)
        
    def _render_view(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中渲染相机视图"""
        camera_name = arguments.get("camera_name")
        resolution_x = arguments.get("resolution_x", 1920)
        resolution_y = arguments.get("resolution_y", 1080)
        samples = arguments.get("samples", 32)
        file_format = arguments.get("file_format", "PNG")
        save_path = arguments.get("save_path")
        engine = arguments.get("engine", "BLENDER_EEVEE")
        
        # 检查相机（如果提供了相机名称）
        if camera_name:
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
        
        # 如果没有活动相机
        if not bpy.context.scene.camera:
            text_content = self.create_text_content("没有活动相机可以渲染")
            return self.create_result([text_content], is_error=True)
        
        # 保存当前渲染设置
        original_settings = {
            "resolution_x": bpy.context.scene.render.resolution_x,
            "resolution_y": bpy.context.scene.render.resolution_y,
            "resolution_percentage": bpy.context.scene.render.resolution_percentage,
            "film_transparent": bpy.context.scene.render.film_transparent,
            "engine": bpy.context.scene.render.engine,
            "samples": None,
            "file_format": bpy.context.scene.render.image_settings.file_format
        }
        
        if engine == "CYCLES":
            original_settings["samples"] = bpy.context.scene.cycles.samples
        else:  # BLENDER_EEVEE
            original_settings["samples"] = bpy.context.scene.eevee.taa_render_samples
        
        try:
            # 设置渲染参数
            bpy.context.scene.render.resolution_x = resolution_x
            bpy.context.scene.render.resolution_y = resolution_y
            bpy.context.scene.render.resolution_percentage = 100
            bpy.context.scene.render.film_transparent = True
            bpy.context.scene.render.engine = engine
            
            # 设置采样数
            if engine == "CYCLES":
                bpy.context.scene.cycles.samples = samples
            else:  # BLENDER_EEVEE
                bpy.context.scene.eevee.taa_render_samples = samples
            
            # 设置输出格式
            bpy.context.scene.render.image_settings.file_format = file_format
            
            # 创建临时文件
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, f"blender_render_temp.{file_format.lower()}")
            
            # 设置输出路径
            output_path = save_path if save_path else temp_file
            bpy.context.scene.render.filepath = output_path
            
            # 渲染图像
            bpy.ops.render.render(write_still=True)
            
            # 读取渲染结果
            with open(output_path, 'rb') as f:
                image_data = f.read()
            
            # 转换为base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # 创建图片内容
            mime_type = {
                "PNG": "image/png",
                "JPEG": "image/jpeg",
                "BMP": "image/bmp"
            }[file_format]
            
            image_content = self.create_image_content(image_base64, mime_type)
            
            # 创建文本内容
            active_camera_name = bpy.context.scene.camera.name
            text_content = self.create_text_content(
                f"已渲染相机 '{active_camera_name}' 的视图\n"
                f"分辨率: {resolution_x}x{resolution_y}\n"
                f"引擎: {engine}, 采样数: {samples}"
            )
            
            # 如果保存到指定路径，添加路径信息
            if save_path:
                text_content.text += f"\n保存路径: {save_path}"
            
            # 返回结果
            return self.create_result([text_content, image_content])
            
        except Exception as e:
            text_content = self.create_text_content(f"渲染相机视图时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
            
        finally:
            # 恢复原始渲染设置
            bpy.context.scene.render.resolution_x = original_settings["resolution_x"]
            bpy.context.scene.render.resolution_y = original_settings["resolution_y"]
            bpy.context.scene.render.resolution_percentage = original_settings["resolution_percentage"]
            bpy.context.scene.render.film_transparent = original_settings["film_transparent"]
            bpy.context.scene.render.engine = original_settings["engine"]
            bpy.context.scene.render.image_settings.file_format = original_settings["file_format"]
            
            if original_settings["engine"] == "CYCLES":
                bpy.context.scene.cycles.samples = original_settings["samples"]
            else:  # BLENDER_EEVEE
                bpy.context.scene.eevee.taa_render_samples = original_settings["samples"]


# 在导入时自动注册工具实例
register_tool(RenderViewHandler())
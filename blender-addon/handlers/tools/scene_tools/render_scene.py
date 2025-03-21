"""
渲染Blender场景的工具
"""

import bpy
from ..registry import register_tool
import os
import tempfile
import base64
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.RenderScene")

class RenderSceneHandler(BaseToolHandler):
    """渲染场景工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_render_scene"
        
    @property
    def description(self) -> Optional[str]:
        return "渲染Blender场景并保存结果"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "scene_name": {
                    "type": "string",
                    "title": "场景名称",
                    "description": "要渲染的场景名称（默认为当前活动场景）"
                },
                "camera_name": {
                    "type": "string",
                    "title": "相机名称",
                    "description": "用于渲染的相机名称（默认为场景活动相机）"
                },
                "resolution_x": {
                    "type": "integer",
                    "title": "宽度分辨率",
                    "description": "渲染图像的宽度分辨率"
                },
                "resolution_y": {
                    "type": "integer",
                    "title": "高度分辨率",
                    "description": "渲染图像的高度分辨率"
                },
                "resolution_percentage": {
                    "type": "integer",
                    "title": "分辨率百分比",
                    "description": "渲染分辨率百分比",
                    "minimum": 1,
                    "maximum": 100
                },
                "samples": {
                    "type": "integer",
                    "title": "采样数",
                    "description": "渲染的采样数量"
                },
                "file_format": {
                    "type": "string",
                    "title": "文件格式",
                    "description": "渲染结果的文件格式",
                    "enum": ["PNG", "JPEG", "BMP", "OPEN_EXR"],
                    "default": "PNG"
                },
                "save_path": {
                    "type": "string",
                    "title": "保存路径",
                    "description": "渲染结果的保存路径（如果为空则只渲染不保存）"
                },
                "engine": {
                    "type": "string",
                    "title": "渲染引擎",
                    "description": "使用的渲染引擎",
                    "enum": ["CYCLES", "BLENDER_EEVEE", "BLENDER_WORKBENCH"],
                    "default": "BLENDER_EEVEE"
                },
                "animation": {
                    "type": "boolean",
                    "title": "渲染动画",
                    "description": "是否渲染整个动画序列而不是单帧",
                    "default": False
                },
                "start_frame": {
                    "type": "integer",
                    "title": "开始帧",
                    "description": "动画渲染的开始帧（仅当渲染动画时有效）"
                },
                "end_frame": {
                    "type": "integer",
                    "title": "结束帧",
                    "description": "动画渲染的结束帧（仅当渲染动画时有效）"
                },
                "frame_step": {
                    "type": "integer",
                    "title": "帧步长",
                    "description": "动画渲染的帧步长（仅当渲染动画时有效）",
                    "default": 1
                }
            }
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查场景名称（如果提供）
        scene_name = arguments.get("scene_name")
        if scene_name and scene_name not in bpy.data.scenes:
            return f"场景 '{scene_name}' 不存在"
            
        # 检查相机名称（如果提供）
        camera_name = arguments.get("camera_name")
        if camera_name:
            if camera_name not in bpy.data.objects:
                return f"相机 '{camera_name}' 不存在"
            
            camera_obj = bpy.data.objects[camera_name]
            if camera_obj.type != 'CAMERA':
                return f"对象 '{camera_name}' 不是相机"
        
        # 检查分辨率
        resolution_x = arguments.get("resolution_x")
        if resolution_x is not None and (not isinstance(resolution_x, int) or resolution_x <= 0):
            return "宽度分辨率必须是正整数"
            
        resolution_y = arguments.get("resolution_y")
        if resolution_y is not None and (not isinstance(resolution_y, int) or resolution_y <= 0):
            return "高度分辨率必须是正整数"
            
        resolution_percentage = arguments.get("resolution_percentage")
        if resolution_percentage is not None and (not isinstance(resolution_percentage, int) or resolution_percentage < 1 or resolution_percentage > 100):
            return "分辨率百分比必须是1到100之间的整数"
        
        # 检查采样数
        samples = arguments.get("samples")
        if samples is not None and (not isinstance(samples, int) or samples < 1):
            return "采样数必须是正整数"
        
        # 检查文件格式
        file_format = arguments.get("file_format", "PNG")
        if file_format not in ["PNG", "JPEG", "BMP", "OPEN_EXR"]:
            return "文件格式必须是 'PNG'、'JPEG'、'BMP' 或 'OPEN_EXR'"
        
        # 检查保存路径目录
        save_path = arguments.get("save_path")
        if save_path:
            dir_path = os.path.dirname(save_path)
            if dir_path and not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path)
                except:
                    return f"无法创建目录: {dir_path}"
        
        # 检查引擎
        engine = arguments.get("engine", "BLENDER_EEVEE")
        if engine not in ["CYCLES", "BLENDER_EEVEE", "BLENDER_WORKBENCH"]:
            return "渲染引擎必须是 'CYCLES'、'BLENDER_EEVEE' 或 'BLENDER_WORKBENCH'"
        
        # 检查动画参数
        animation = arguments.get("animation", False)
        if animation:
            start_frame = arguments.get("start_frame")
            if start_frame is not None and not isinstance(start_frame, int):
                return "开始帧必须是整数"
                
            end_frame = arguments.get("end_frame")
            if end_frame is not None and not isinstance(end_frame, int):
                return "结束帧必须是整数"
                
            if start_frame is not None and end_frame is not None and start_frame > end_frame:
                return "开始帧必须小于或等于结束帧"
                
            frame_step = arguments.get("frame_step", 1)
            if not isinstance(frame_step, int) or frame_step < 1:
                return "帧步长必须是正整数"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行渲染场景操作"""
        logger.info(f"渲染场景，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._render_scene, arguments)
        
    def _render_scene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中渲染场景"""
        scene_name = arguments.get("scene_name")
        camera_name = arguments.get("camera_name")
        resolution_x = arguments.get("resolution_x")
        resolution_y = arguments.get("resolution_y")
        resolution_percentage = arguments.get("resolution_percentage")
        samples = arguments.get("samples")
        file_format = arguments.get("file_format", "PNG")
        save_path = arguments.get("save_path")
        engine = arguments.get("engine", "BLENDER_EEVEE")
        animation = arguments.get("animation", False)
        start_frame = arguments.get("start_frame")
        end_frame = arguments.get("end_frame")
        frame_step = arguments.get("frame_step", 1)
        
        # 获取场景
        if scene_name:
            scene = bpy.data.scenes[scene_name]
        else:
            scene = bpy.context.scene
            scene_name = scene.name
        
        # 确保该场景是活动场景
        original_scene = bpy.context.scene
        bpy.context.window.scene = scene
        
        # 设置相机（如果提供）
        original_camera = scene.camera
        if camera_name:
            camera_obj = bpy.data.objects[camera_name]
            scene.camera = camera_obj
        
        # 检查场景是否有相机
        if not scene.camera:
            # 恢复原始场景
            bpy.context.window.scene = original_scene
            
            text_content = self.create_text_content(f"场景 '{scene_name}' 没有活动相机")
            return self.create_result([text_content], is_error=True)
        
        # 保存当前渲染设置
        original_settings = {
            "resolution_x": scene.render.resolution_x,
            "resolution_y": scene.render.resolution_y,
            "resolution_percentage": scene.render.resolution_percentage,
            "engine": scene.render.engine,
            "film_transparent": scene.render.film_transparent,
            "file_format": scene.render.image_settings.file_format,
            "frame_start": scene.frame_start,
            "frame_end": scene.frame_end,
            "frame_step": scene.frame_step,
            "frame_current": scene.frame_current,
            "cycles_samples": scene.cycles.samples if hasattr(scene, "cycles") else None,
            "eevee_samples": scene.eevee.taa_render_samples if hasattr(scene, "eevee") else None
        }
        
        # 设置临时文件路径
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f"blender_render_temp.{file_format.lower()}")
        
        try:
            # 设置渲染参数
            if resolution_x is not None:
                scene.render.resolution_x = resolution_x
            if resolution_y is not None:
                scene.render.resolution_y = resolution_y
            if resolution_percentage is not None:
                scene.render.resolution_percentage = resolution_percentage
            
            scene.render.film_transparent = True
            scene.render.engine = engine
            
            # 设置采样数
            if samples is not None:
                if engine == "CYCLES":
                    scene.cycles.samples = samples
                elif engine == "BLENDER_EEVEE":
                    scene.eevee.taa_render_samples = samples
            
            # 设置输出格式
            scene.render.image_settings.file_format = file_format
            
            # 设置输出路径
            output_path = save_path if save_path else temp_file
            scene.render.filepath = output_path
            
            # 执行渲染
            if animation:
                # 设置动画帧范围
                if start_frame is not None:
                    scene.frame_start = start_frame
                if end_frame is not None:
                    scene.frame_end = end_frame
                scene.frame_step = frame_step
                
                # 渲染动画
                bpy.ops.render.render(animation=True)
                
                # 创建结果信息
                text_content = self.create_text_content(
                    f"已渲染场景 '{scene_name}' 的动画\n"
                    f"帧范围: {scene.frame_start} - {scene.frame_end}, 步长: {scene.frame_step}\n"
                    f"分辨率: {scene.render.resolution_x}x{scene.render.resolution_y} @{scene.render.resolution_percentage}%\n"
                    f"引擎: {engine}\n"
                    f"保存路径: {output_path}"
                )
                
                # 返回结果，不包含图像（因为是动画）
                return self.create_result([text_content])
                
            else:
                # 渲染单帧
                bpy.ops.render.render(write_still=True)
                
                # 如果设置了保存路径，则已经保存了渲染结果
                # 否则，需要从临时文件读取结果
                if not save_path:
                    output_path = temp_file
                
                # 读取渲染结果图像
                with open(output_path, 'rb') as f:
                    image_data = f.read()
                
                # 转换为base64
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                
                # 创建图片内容
                mime_type = {
                    "PNG": "image/png",
                    "JPEG": "image/jpeg",
                    "BMP": "image/bmp",
                    "OPEN_EXR": "image/x-exr"
                }[file_format]
                
                image_content = self.create_image_content(image_base64, mime_type)
                
                # 创建文本内容
                text_content = self.create_text_content(
                    f"已渲染场景 '{scene_name}' 的图像\n"
                    f"相机: {scene.camera.name}\n"
                    f"分辨率: {scene.render.resolution_x}x{scene.render.resolution_y} @{scene.render.resolution_percentage}%\n"
                    f"引擎: {engine}"
                )
                
                # 如果保存到指定路径，添加路径信息
                if save_path:
                    text_content.text += f"\n保存路径: {save_path}"
                
                # 返回结果
                return self.create_result([text_content, image_content])
                
        except Exception as e:
            text_content = self.create_text_content(f"渲染场景时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
            
        finally:
            # 恢复原始设置
            scene.render.resolution_x = original_settings["resolution_x"]
            scene.render.resolution_y = original_settings["resolution_y"]
            scene.render.resolution_percentage = original_settings["resolution_percentage"]
            scene.render.engine = original_settings["engine"]
            scene.render.film_transparent = original_settings["film_transparent"]
            scene.render.image_settings.file_format = original_settings["file_format"]
            scene.frame_start = original_settings["frame_start"]
            scene.frame_end = original_settings["frame_end"]
            scene.frame_step = original_settings["frame_step"]
            scene.frame_current = original_settings["frame_current"]
            
            if original_settings["cycles_samples"] is not None:
                scene.cycles.samples = original_settings["cycles_samples"]
            if original_settings["eevee_samples"] is not None:
                scene.eevee.taa_render_samples = original_settings["eevee_samples"]
            
            # 恢复原始相机
            scene.camera = original_camera
            
            # 恢复原始场景
            bpy.context.window.scene = original_scene


# 在导入时自动注册工具实例
register_tool(RenderSceneHandler())
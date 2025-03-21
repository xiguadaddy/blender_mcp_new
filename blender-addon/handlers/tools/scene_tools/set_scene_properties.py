"""
设置Blender场景属性的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.SetSceneProperties")

class SetScenePropertiesHandler(BaseToolHandler):
    """设置场景属性工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_set_scene_properties"
        
    @property
    def description(self) -> Optional[str]:
        return "设置Blender场景的各种属性"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "scene_name": {
                    "type": "string",
                    "title": "场景名称",
                    "description": "要设置属性的场景名称（默认为当前活动场景）"
                },
                "resolution_x": {
                    "type": "integer",
                    "title": "分辨率X",
                    "description": "渲染分辨率宽度"
                },
                "resolution_y": {
                    "type": "integer",
                    "title": "分辨率Y",
                    "description": "渲染分辨率高度"
                },
                "resolution_percentage": {
                    "type": "integer",
                    "title": "分辨率百分比",
                    "description": "渲染分辨率百分比",
                    "minimum": 1,
                    "maximum": 100
                },
                "fps": {
                    "type": "number",
                    "title": "帧率",
                    "description": "场景帧率"
                },
                "frame_start": {
                    "type": "integer",
                    "title": "开始帧",
                    "description": "动画开始帧"
                },
                "frame_end": {
                    "type": "integer",
                    "title": "结束帧",
                    "description": "动画结束帧"
                },
                "frame_current": {
                    "type": "integer",
                    "title": "当前帧",
                    "description": "设置当前帧"
                },
                "render_engine": {
                    "type": "string",
                    "title": "渲染引擎",
                    "description": "设置渲染引擎",
                    "enum": ["BLENDER_EEVEE", "CYCLES", "BLENDER_WORKBENCH"]
                },
                "cycles_samples": {
                    "type": "integer",
                    "title": "Cycles采样数",
                    "description": "Cycles渲染引擎的采样数",
                    "minimum": 1
                },
                "eevee_samples": {
                    "type": "integer",
                    "title": "Eevee采样数",
                    "description": "Eevee渲染引擎的采样数",
                    "minimum": 1
                }
            }
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查场景名称（如果提供）
        scene_name = arguments.get("scene_name")
        if scene_name and scene_name not in bpy.data.scenes:
            return f"场景 '{scene_name}' 不存在"
            
        # 检查分辨率
        resolution_x = arguments.get("resolution_x")
        if resolution_x is not None and (not isinstance(resolution_x, int) or resolution_x <= 0):
            return "分辨率X必须是正整数"
            
        resolution_y = arguments.get("resolution_y")
        if resolution_y is not None and (not isinstance(resolution_y, int) or resolution_y <= 0):
            return "分辨率Y必须是正整数"
            
        # 检查分辨率百分比
        resolution_percentage = arguments.get("resolution_percentage")
        if resolution_percentage is not None and (not isinstance(resolution_percentage, int) or resolution_percentage < 1 or resolution_percentage > 100):
            return "分辨率百分比必须是1到100之间的整数"
            
        # 检查帧率
        fps = arguments.get("fps")
        if fps is not None and (not isinstance(fps, (int, float)) or fps <= 0):
            return "帧率必须是正数"
            
        # 检查采样数
        cycles_samples = arguments.get("cycles_samples")
        if cycles_samples is not None and (not isinstance(cycles_samples, int) or cycles_samples < 1):
            return "Cycles采样数必须是正整数"
            
        eevee_samples = arguments.get("eevee_samples")
        if eevee_samples is not None and (not isinstance(eevee_samples, int) or eevee_samples < 1):
            return "Eevee采样数必须是正整数"
            
        # 检查渲染引擎
        render_engine = arguments.get("render_engine")
        if render_engine and render_engine not in ["BLENDER_EEVEE", "CYCLES", "BLENDER_WORKBENCH"]:
            return "渲染引擎必须是 'BLENDER_EEVEE'、'CYCLES' 或 'BLENDER_WORKBENCH'"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行设置场景属性操作"""
        logger.info(f"设置场景属性，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._set_scene_properties, arguments)
        
    def _set_scene_properties(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中设置场景属性"""
        scene_name = arguments.get("scene_name")
        
        # 获取场景
        if scene_name:
            scene = bpy.data.scenes[scene_name]
        else:
            scene = bpy.context.scene
            scene_name = scene.name
        
        # 跟踪修改的属性
        modified_props = []
        
        # 设置渲染分辨率
        if "resolution_x" in arguments:
            scene.render.resolution_x = arguments["resolution_x"]
            modified_props.append(f"分辨率X: {arguments['resolution_x']}")
            
        if "resolution_y" in arguments:
            scene.render.resolution_y = arguments["resolution_y"]
            modified_props.append(f"分辨率Y: {arguments['resolution_y']}")
            
        if "resolution_percentage" in arguments:
            scene.render.resolution_percentage = arguments["resolution_percentage"]
            modified_props.append(f"分辨率百分比: {arguments['resolution_percentage']}%")
        
        # 设置帧率
        if "fps" in arguments:
            scene.render.fps = arguments["fps"]
            modified_props.append(f"帧率: {arguments['fps']}")
            
        # 设置帧范围
        if "frame_start" in arguments:
            scene.frame_start = arguments["frame_start"]
            modified_props.append(f"开始帧: {arguments['frame_start']}")
            
        if "frame_end" in arguments:
            scene.frame_end = arguments["frame_end"]
            modified_props.append(f"结束帧: {arguments['frame_end']}")
            
        if "frame_current" in arguments:
            scene.frame_current = arguments["frame_current"]
            modified_props.append(f"当前帧: {arguments['frame_current']}")
        
        # 设置渲染引擎
        if "render_engine" in arguments:
            scene.render.engine = arguments["render_engine"]
            modified_props.append(f"渲染引擎: {arguments['render_engine']}")
        
        # 设置采样数
        if "cycles_samples" in arguments:
            scene.cycles.samples = arguments["cycles_samples"]
            modified_props.append(f"Cycles采样数: {arguments['cycles_samples']}")
            
        if "eevee_samples" in arguments:
            scene.eevee.taa_render_samples = arguments["eevee_samples"]
            modified_props.append(f"Eevee采样数: {arguments['eevee_samples']}")
        
        # 创建结果信息
        if modified_props:
            properties_text = "\n".join(modified_props)
            text_content = self.create_text_content(f"已设置场景 '{scene_name}' 的属性:\n{properties_text}")
        else:
            text_content = self.create_text_content(f"未修改场景 '{scene_name}' 的任何属性")
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(SetScenePropertiesHandler())
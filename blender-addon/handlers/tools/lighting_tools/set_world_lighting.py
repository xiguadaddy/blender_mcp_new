"""
设置Blender世界环境光照的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.SetWorldLighting")

class SetWorldLightingHandler(BaseToolHandler):
    """设置世界环境光照工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_set_world_lighting"
        
    @property
    def description(self) -> Optional[str]:
        return "设置场景的世界环境光照和背景"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "world_name": {
                    "type": "string",
                    "title": "世界名称",
                    "description": "世界环境的名称",
                    "default": "世界"
                },
                "background_color": {
                    "type": "array",
                    "title": "背景颜色",
                    "description": "背景颜色RGB值 [r, g, b]",
                    "items": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1
                    }
                },
                "background_energy": {
                    "type": "number",
                    "title": "背景强度",
                    "description": "背景的能量/强度",
                    "default": 1.0
                },
                "use_nodes": {
                    "type": "boolean",
                    "title": "使用节点",
                    "description": "是否使用节点系统设置世界环境",
                    "default": True
                },
                "use_nishita_sky": {
                    "type": "boolean",
                    "title": "使用物理天空",
                    "description": "是否使用Nishita物理天空模型",
                    "default": False
                },
                "sun_elevation": {
                    "type": "number",
                    "title": "太阳高度",
                    "description": "太阳高度角度（弧度）",
                    "minimum": -1.5708,
                    "maximum": 1.5708
                },
                "sun_rotation": {
                    "type": "number",
                    "title": "太阳旋转",
                    "description": "太阳方位角（弧度）",
                    "minimum": 0,
                    "maximum": 6.2832
                }
            }
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 验证背景颜色
        background_color = arguments.get("background_color")
        if background_color and not (isinstance(background_color, list) and len(background_color) == 3 and all(isinstance(v, (int, float)) and 0 <= v <= 1 for v in background_color)):
            return "背景颜色必须是包含3个在0-1范围内的数字的数组 [r, g, b]"
            
        # 验证背景强度
        background_energy = arguments.get("background_energy")
        if background_energy is not None and (not isinstance(background_energy, (int, float)) or background_energy < 0):
            return "背景强度必须是非负数"
            
        # 验证太阳高度
        sun_elevation = arguments.get("sun_elevation")
        if sun_elevation is not None and (not isinstance(sun_elevation, (int, float)) or sun_elevation < -1.5708 or sun_elevation > 1.5708):
            return "太阳高度必须在-π/2到π/2之间"
            
        # 验证太阳旋转
        sun_rotation = arguments.get("sun_rotation")
        if sun_rotation is not None and (not isinstance(sun_rotation, (int, float)) or sun_rotation < 0 or sun_rotation > 6.2832):
            return "太阳旋转必须在0到2π之间"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行设置世界环境光照操作"""
        logger.info(f"设置世界环境光照，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._set_world_lighting, arguments)
        
    def _set_world_lighting(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中设置世界环境光照"""
        world_name = arguments.get("world_name", "世界")
        background_color = arguments.get("background_color")
        background_energy = arguments.get("background_energy", 1.0)
        use_nodes = arguments.get("use_nodes", True)
        use_nishita_sky = arguments.get("use_nishita_sky", False)
        sun_elevation = arguments.get("sun_elevation")
        sun_rotation = arguments.get("sun_rotation")
        
        # 获取或创建世界环境
        if world_name in bpy.data.worlds:
            world = bpy.data.worlds[world_name]
        else:
            world = bpy.data.worlds.new(world_name)
        
        # 设置活动世界
        bpy.context.scene.world = world
        
        # 记录修改的属性
        modified_props = []
        
        # 是否使用节点
        world.use_nodes = use_nodes
        
        if use_nodes:
            # 确保节点存在
            if not world.node_tree:
                world.use_nodes = True
                
            nodes = world.node_tree.nodes
            links = world.node_tree.links
            
            # 清除所有现有节点
            nodes.clear()
            
            if use_nishita_sky:
                # 创建物理天空节点
                sky_texture = nodes.new('ShaderNodeTexSky')
                sky_texture.location = (-300, 0)
                sky_texture.sky_type = 'NISHITA'  # 使用Nishita模型
                
                # 设置太阳位置
                if sun_elevation is not None:
                    sky_texture.sun_elevation = sun_elevation
                    modified_props.append(f"太阳高度: {sun_elevation}")
                    
                if sun_rotation is not None:
                    sky_texture.sun_rotation = sun_rotation
                    modified_props.append(f"太阳旋转: {sun_rotation}")
                
                modified_props.append("使用物理天空: 是")
                
                # 创建并连接背景输出节点
                background = nodes.new('ShaderNodeBackground')
                background.location = (0, 0)
                
                # 设置背景强度
                background.inputs['Strength'].default_value = background_energy
                modified_props.append(f"背景强度: {background_energy}")
                
                # 连接天空纹理到背景
                links.new(sky_texture.outputs['Color'], background.inputs['Color'])
                
                # 创建并连接输出节点
                output = nodes.new('ShaderNodeOutputWorld')
                output.location = (300, 0)
                links.new(background.outputs['Background'], output.inputs['Surface'])
                
            else:
                # 创建背景节点
                background = nodes.new('ShaderNodeBackground')
                background.location = (0, 0)
                
                # 设置背景颜色
                if background_color:
                    # 转换为RGBA
                    rgba_color = background_color + [1.0]
                    background.inputs['Color'].default_value = rgba_color
                    modified_props.append(f"背景颜色: RGB{background_color}")
                
                # 设置背景强度
                background.inputs['Strength'].default_value = background_energy
                modified_props.append(f"背景强度: {background_energy}")
                
                # 创建并连接输出节点
                output = nodes.new('ShaderNodeOutputWorld')
                output.location = (300, 0)
                links.new(background.outputs['Background'], output.inputs['Surface'])
            
            modified_props.append("使用节点: 是")
        else:
            # 不使用节点，直接设置背景颜色
            if background_color:
                # 转换为RGBA
                rgba_color = background_color + [1.0]
                world.color = rgba_color
                modified_props.append(f"背景颜色: RGB{background_color}")
                
            modified_props.append("使用节点: 否")
        
        # 创建结果信息
        if modified_props:
            properties_text = "\n".join(modified_props)
            text_content = self.create_text_content(f"已设置世界环境 '{world_name}' 的属性:\n{properties_text}")
        else:
            text_content = self.create_text_content(f"未修改世界环境 '{world_name}' 的任何属性")
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(SetWorldLightingHandler())
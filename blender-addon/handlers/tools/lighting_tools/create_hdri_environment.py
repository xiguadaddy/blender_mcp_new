"""
创建HDRI环境光照的工具
"""

import bpy
from ..registry import register_tool
import os
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.CreateHDRIEnvironment")

class CreateHDRIEnvironmentHandler(BaseToolHandler):
    """创建HDRI环境光照工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_create_hdri_environment"
        
    @property
    def description(self) -> Optional[str]:
        return "创建基于HDRI图像的环境光照"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "hdri_path": {
                    "type": "string",
                    "title": "HDRI路径",
                    "description": "HDRI图像文件的路径"
                },
                "world_name": {
                    "type": "string",
                    "title": "世界名称",
                    "description": "世界环境的名称",
                    "default": "HDRI环境"
                },
                "strength": {
                    "type": "number",
                    "title": "强度",
                    "description": "HDRI环境的强度",
                    "default": 1.0
                },
                "rotation": {
                    "type": "number",
                    "title": "旋转",
                    "description": "HDRI环境的Z轴旋转（弧度）",
                    "default": 0.0
                }
            },
            "required": ["hdri_path"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查HDRI路径
        hdri_path = arguments.get("hdri_path")
        if not hdri_path:
            return "必须提供HDRI图像路径"
            
        # 检查强度
        strength = arguments.get("strength")
        if strength is not None and (not isinstance(strength, (int, float)) or strength < 0):
            return "强度必须是非负数"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行创建HDRI环境操作"""
        logger.info(f"创建HDRI环境，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._create_hdri_environment, arguments)
        
    def _create_hdri_environment(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中创建HDRI环境"""
        hdri_path = arguments.get("hdri_path")
        world_name = arguments.get("world_name", "HDRI环境")
        strength = arguments.get("strength", 1.0)
        rotation = arguments.get("rotation", 0.0)
        
        # 检查文件是否存在
        if not os.path.isfile(hdri_path):
            text_content = self.create_text_content(f"找不到HDRI文件: {hdri_path}")
            return self.create_result([text_content], is_error=True)
            
        # 获取或创建世界环境
        if world_name in bpy.data.worlds:
            world = bpy.data.worlds[world_name]
        else:
            world = bpy.data.worlds.new(world_name)
        
        # 设置活动世界
        bpy.context.scene.world = world
        
        # 启用节点
        world.use_nodes = True
        nodes = world.node_tree.nodes
        links = world.node_tree.links
        
        # 清除所有现有节点
        nodes.clear()
        
        # 创建环境纹理节点
        env_tex = nodes.new('ShaderNodeTexEnvironment')
        env_tex.location = (-600, 0)
        
        # 加载HDRI图像
        try:
            # 检查图像是否已加载
            image_name = os.path.basename(hdri_path)
            if image_name in bpy.data.images:
                image = bpy.data.images[image_name]
            else:
                image = bpy.data.images.load(hdri_path)
                
            env_tex.image = image
        except Exception as e:
            text_content = self.create_text_content(f"加载HDRI图像时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
        
        # 创建映射节点（用于旋转HDRI）
        mapping = nodes.new('ShaderNodeMapping')
        mapping.location = (-800, 0)
        mapping.inputs['Rotation'].default_value[2] = rotation
        
        # 创建纹理坐标节点
        tex_coord = nodes.new('ShaderNodeTexCoord')
        tex_coord.location = (-1000, 0)
        
        # 创建背景节点
        background = nodes.new('ShaderNodeBackground')
        background.location = (-300, 0)
        background.inputs['Strength'].default_value = strength
        
        # 创建输出节点
        output = nodes.new('ShaderNodeOutputWorld')
        output.location = (0, 0)
        
        # 连接节点
        links.new(tex_coord.outputs['Generated'], mapping.inputs['Vector'])
        links.new(mapping.outputs['Vector'], env_tex.inputs['Vector'])
        links.new(env_tex.outputs['Color'], background.inputs['Color'])
        links.new(background.outputs['Background'], output.inputs['Surface'])
        
        # 创建结果信息
        text_content = self.create_text_content(
            f"已创建HDRI环境:\n"
            f"世界名称: {world_name}\n"
            f"HDRI文件: {os.path.basename(hdri_path)}\n"
            f"强度: {strength}\n"
            f"旋转: {rotation} 弧度"
        )
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(CreateHDRIEnvironmentHandler())
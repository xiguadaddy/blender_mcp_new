"""
为Blender对象创建几何节点设置的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.CreateGeometryNodes")

class CreateGeometryNodesHandler(BaseToolHandler):
    """创建几何节点工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_create_geometry_nodes"
        
    @property
    def description(self) -> Optional[str]:
        return "为对象创建基本的几何节点修改器和节点组"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "要添加几何节点的对象名称"
                },
                "node_type": {
                    "type": "string",
                    "title": "节点类型",
                    "description": "要创建的几何节点类型",
                    "enum": [
                        "simple", "array", "instance", "distribute", "transform"
                    ],
                    "default": "simple"
                },
                "node_group_name": {
                    "type": "string",
                    "title": "节点组名称",
                    "description": "创建的节点组名称（可选）"
                },
                "parameters": {
                    "type": "object",
                    "title": "节点参数",
                    "description": "节点特定的参数"
                }
            },
            "required": ["object_name"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查对象名称
        if not arguments.get("object_name"):
            return "必须提供对象名称"
            
        # 检查节点类型
        node_type = arguments.get("node_type", "simple")
        valid_types = ["simple", "array", "instance", "distribute", "transform"]
        if node_type not in valid_types:
            return f"不支持的节点类型: {node_type}，有效类型: {', '.join(valid_types)}"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行创建几何节点操作"""
        logger.info(f"创建几何节点，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._create_geometry_nodes, arguments)
        
    def _create_geometry_nodes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中创建几何节点"""
        object_name = arguments.get("object_name")
        node_type = arguments.get("node_type", "simple")
        node_group_name = arguments.get("node_group_name", f"{object_name}_GeometryNodes")
        parameters = arguments.get("parameters", {})
        
        # 检查对象是否存在
        if object_name not in bpy.data.objects:
            text_content = self.create_text_content(f"找不到对象: {object_name}")
            return self.create_result([text_content], is_error=True)
        
        # 获取对象
        obj = bpy.data.objects[object_name]
        
        # 确保Blender版本支持几何节点
        if bpy.app.version < (2, 92, 0):
            text_content = self.create_text_content("几何节点功能需要Blender 2.92或更高版本")
            return self.create_result([text_content], is_error=True)
        
        try:
            # 创建新的几何节点修改器
            gn_modifier = obj.modifiers.new(name="GeometryNodes", type='NODES')
            
            # 创建新的节点组
            node_group = bpy.data.node_groups.new(name=node_group_name, type='GeometryNodeTree')
            
            # 设置修改器使用新节点组
            gn_modifier.node_group = node_group
            
            # 为节点组创建输入和输出节点
            input_node = node_group.nodes.new('NodeGroupInput')
            output_node = node_group.nodes.new('NodeGroupOutput')
            
            # 设置节点位置
            input_node.location = (-200, 0)
            output_node.location = (200, 0)
            
            # 根据节点类型添加特定节点
            if node_type == "simple":
                # 简单节点组，只连接输入到输出
                node_group.links.new(input_node.outputs[0], output_node.inputs[0])
                
            elif node_type == "array":
                # 创建阵列节点
                array_node = node_group.nodes.new('GeometryNodeInstanceOnPoints')
                array_node.location = (0, 0)
                
                # 创建网格线节点来生成点
                point_node = node_group.nodes.new('GeometryNodeMeshLine')
                point_node.location = (-100, -100)
                
                # 设置点数量参数
                count = parameters.get("count", 5)
                point_node.inputs[0].default_value = count
                
                # 连接节点
                node_group.links.new(input_node.outputs[0], array_node.inputs[0])  # 实例化对象
                node_group.links.new(point_node.outputs[0], array_node.inputs[2])  # 点阵列
                node_group.links.new(array_node.outputs[0], output_node.inputs[0])  # 输出
                
            elif node_type == "instance":
                # 创建实例化节点
                instance_node = node_group.nodes.new('GeometryNodeInstanceOnPoints')
                instance_node.location = (0, 0)
                
                # 创建点分布节点
                point_node = node_group.nodes.new('GeometryNodeDistributePointsOnFaces')
                point_node.location = (-100, -100)
                
                # 设置点数量参数
                density = parameters.get("density", 10.0)
                point_node.inputs[2].default_value = density
                
                # 连接节点
                node_group.links.new(input_node.outputs[0], point_node.inputs[0])  # 输入几何体到点分布
                node_group.links.new(input_node.outputs[0], instance_node.inputs[0])  # 输入几何体到实例化
                node_group.links.new(point_node.outputs[0], instance_node.inputs[2])  # 分布的点到实例化
                node_group.links.new(instance_node.outputs[0], output_node.inputs[0])  # 输出
                
            elif node_type == "distribute":
                # 创建点分布节点
                point_node = node_group.nodes.new('GeometryNodeDistributePointsOnFaces')
                point_node.location = (0, 0)
                
                # 设置点数量参数
                density = parameters.get("density", 10.0)
                point_node.inputs[2].default_value = density
                
                # 连接节点
                node_group.links.new(input_node.outputs[0], point_node.inputs[0])  # 输入几何体到点分布
                node_group.links.new(point_node.outputs[0], output_node.inputs[0])  # 点到输出
                
            elif node_type == "transform":
                # 创建变换节点
                transform_node = node_group.nodes.new('GeometryNodeTransform')
                transform_node.location = (0, 0)
                
                # 设置变换参数
                translation = parameters.get("translation", [0, 0, 0])
                rotation = parameters.get("rotation", [0, 0, 0])
                scale = parameters.get("scale", [1, 1, 1])
                
                transform_node.inputs[1].default_value[0] = translation[0]
                transform_node.inputs[1].default_value[1] = translation[1]
                transform_node.inputs[1].default_value[2] = translation[2]
                
                transform_node.inputs[2].default_value[0] = rotation[0]
                transform_node.inputs[2].default_value[1] = rotation[1]
                transform_node.inputs[2].default_value[2] = rotation[2]
                
                transform_node.inputs[3].default_value[0] = scale[0]
                transform_node.inputs[3].default_value[1] = scale[1]
                transform_node.inputs[3].default_value[2] = scale[2]
                
                # 连接节点
                node_group.links.new(input_node.outputs[0], transform_node.inputs[0])  # 输入几何体到变换
                node_group.links.new(transform_node.outputs[0], output_node.inputs[0])  # 变换到输出
            
            text_content = self.create_text_content(f"已为对象 '{object_name}' 创建 '{node_type}' 类型的几何节点修改器")
        except Exception as e:
            text_content = self.create_text_content(f"创建几何节点时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(CreateGeometryNodesHandler())
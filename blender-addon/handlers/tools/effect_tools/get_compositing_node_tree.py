from ..registry import register_tool
import bpy
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils
from ....mcp_types import create_text_content

# 获取日志器
logger = logging.getLogger("BlenderMCP.GetCompositingNodeTree")

class GetCompositingNodeTreeHandler(BaseToolHandler):
    """获取合成节点树工具处理器"""
    
    @property
    def name(self) -> str:
        return "get_compositing_node_tree"
        
    @property
    def description(self) -> Optional[str]:
        return "获取场景的合成节点树信息"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "include_sockets": {
                    "type": "boolean",
                    "title": "包含接口",
                    "description": "是否包含节点接口信息",
                    "default": False
                },
                "include_links": {
                    "type": "boolean",
                    "title": "包含连接",
                    "description": "是否包含节点连接信息",
                    "default": False
                }
            }
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        return None  # 没有必填参数
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行获取合成节点树操作"""
        logger.debug(f"获取合成节点树: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._get_compositing_node_tree, arguments)
        
    def _get_compositing_node_tree(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中获取合成节点树"""
        try:
            include_sockets = args.get("include_sockets", False)
            include_links = args.get("include_links", False)
            
            # 获取当前场景
            scene = bpy.context.scene
            
            # 确保合成节点已启用
            if not scene.use_nodes:
                scene.use_nodes = True
                
            node_tree = scene.node_tree
            
            # 序列化节点树
            nodes_data = []
            for node in node_tree.nodes:
                node_data = {
                    "name": node.name,
                    "type": node.type,
                    "location": [node.location.x, node.location.y],
                    "width": node.width,
                    "height": node.height,
                    "mute": node.mute,
                    "hide": node.hide
                }
                
                # 添加特定节点类型的属性
                if node.type == 'VIEWER':
                    node_data["use_alpha"] = node.use_alpha
                elif node.type == 'COMPOSITE':
                    node_data["use_alpha"] = node.use_alpha
                elif node.type == 'BLUR':
                    node_data["size_x"] = node.size_x
                    node_data["size_y"] = node.size_y
                    node_data["use_relative"] = node.use_relative
                    node_data["aspect_correction"] = node.aspect_correction
                    node_data["filter_type"] = node.filter_type
                elif node.type == 'COLOR_CORRECTION':
                    node_data["red"] = node.red
                    node_data["green"] = node.green
                    node_data["blue"] = node.blue
                    node_data["midtones_start"] = node.midtones_start
                    node_data["midtones_end"] = node.midtones_end
                
                # 如果需要，添加插槽信息
                if include_sockets:
                    # 输入插槽
                    node_data["inputs"] = []
                    for input_socket in node.inputs:
                        socket_data = {
                            "name": input_socket.name,
                            "type": input_socket.type
                        }
                        # 尝试获取默认值（如果存在）
                        if hasattr(input_socket, "default_value"):
                            if isinstance(input_socket.default_value, float):
                                socket_data["default_value"] = input_socket.default_value
                            elif hasattr(input_socket.default_value, "__len__"):
                                # 处理颜色等复杂类型
                                socket_data["default_value"] = list(input_socket.default_value)
                        node_data["inputs"].append(socket_data)
                    
                    # 输出插槽
                    node_data["outputs"] = []
                    for output_socket in node.outputs:
                        socket_data = {
                            "name": output_socket.name,
                            "type": output_socket.type
                        }
                        node_data["outputs"].append(socket_data)
                
                nodes_data.append(node_data)
            
            # 如果需要，添加连接信息
            links_data = []
            if include_links:
                for link in node_tree.links:
                    links_data.append({
                        "from_node": link.from_node.name,
                        "from_socket": link.from_socket.name,
                        "to_node": link.to_node.name,
                        "to_socket": link.to_socket.name
                    })
            
            # 返回节点树信息
            result_data = {
                "node_tree_name": node_tree.name,
                "nodes_count": len(node_tree.nodes),
                "links_count": len(node_tree.links),
                "nodes": nodes_data
            }
            
            if include_links:
                result_data["links"] = links_data
            
            text_content = create_text_content(f"已获取合成节点树信息，包含 {len(node_tree.nodes)} 个节点和 {len(node_tree.links)} 个连接")
            
            return self.create_result([text_content], result_data)
        except Exception as e:
            logger.error(f"获取合成节点树出错: {str(e)}")
            return {"error": str(e)}


# 在导入时自动注册工具实例
register_tool(GetCompositingNodeTreeHandler())
from ..registry import register_tool
import bpy
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils
from ....mcp_types import create_text_content

# 获取日志器
logger = logging.getLogger("BlenderMCP.ConnectCompositingNodes")

class ConnectCompositingNodesHandler(BaseToolHandler):
    """连接合成节点工具处理器"""
    
    @property
    def name(self) -> str:
        return "connect_compositing_nodes"
        
    @property
    def description(self) -> Optional[str]:
        return "连接两个合成节点的插槽"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "from_node_name": {
                    "type": "string",
                    "title": "源节点名称",
                    "description": "连接起点的节点名称"
                },
                "from_socket_name": {
                    "type": "string",
                    "title": "源插槽名称",
                    "description": "连接起点的输出插槽名称"
                },
                "to_node_name": {
                    "type": "string",
                    "title": "目标节点名称",
                    "description": "连接终点的节点名称"
                },
                "to_socket_name": {
                    "type": "string",
                    "title": "目标插槽名称",
                    "description": "连接终点的输入插槽名称"
                }
            },
            "required": ["from_node_name", "from_socket_name", "to_node_name", "to_socket_name"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        if not arguments.get("from_node_name"):
            return "必须提供源节点名称"
            
        if not arguments.get("from_socket_name"):
            return "必须提供源插槽名称"
            
        if not arguments.get("to_node_name"):
            return "必须提供目标节点名称"
            
        if not arguments.get("to_socket_name"):
            return "必须提供目标插槽名称"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行连接合成节点操作"""
        logger.debug(f"连接合成节点: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._connect_compositing_nodes, arguments)
        
    def _connect_compositing_nodes(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中连接合成节点"""
        try:
            from_node_name = args.get("from_node_name")
            from_socket_name = args.get("from_socket_name")
            to_node_name = args.get("to_node_name")
            to_socket_name = args.get("to_socket_name")
            
            # 获取当前场景
            scene = bpy.context.scene
            
            # 确保合成节点已启用
            if not scene.use_nodes:
                scene.use_nodes = True
                
            node_tree = scene.node_tree
            
            # 获取节点
            from_node = node_tree.nodes.get(from_node_name)
            if not from_node:
                return {"error": f"找不到源节点: {from_node_name}"}
                
            to_node = node_tree.nodes.get(to_node_name)
            if not to_node:
                return {"error": f"找不到目标节点: {to_node_name}"}
                
            # 获取插槽
            from_socket = None
            for socket in from_node.outputs:
                if socket.name == from_socket_name:
                    from_socket = socket
                    break
                    
            if not from_socket:
                return {"error": f"在节点 '{from_node_name}' 中找不到输出插槽: {from_socket_name}"}
                
            to_socket = None
            for socket in to_node.inputs:
                if socket.name == to_socket_name:
                    to_socket = socket
                    break
                    
            if not to_socket:
                return {"error": f"在节点 '{to_node_name}' 中找不到输入插槽: {to_socket_name}"}
                
            # 创建连接
            new_link = node_tree.links.new(from_socket, to_socket)
            if not new_link:
                return {"error": f"无法连接插槽: 从 {from_node_name}.{from_socket_name} 到 {to_node_name}.{to_socket_name}"}
                
            text_content = create_text_content(f"已连接 {from_node_name}.{from_socket_name} 到 {to_node_name}.{to_socket_name}")
            
            return self.create_result([text_content], {
                "from_node": from_node_name,
                "from_socket": from_socket_name,
                "to_node": to_node_name,
                "to_socket": to_socket_name
            })
        except Exception as e:
            logger.error(f"连接合成节点出错: {str(e)}")
            return {"error": str(e)}


# 在导入时自动注册工具实例
register_tool(ConnectCompositingNodesHandler())
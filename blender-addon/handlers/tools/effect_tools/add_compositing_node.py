from ..registry import register_tool
import bpy
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils
from ....mcp_types import create_text_content

# 获取日志器
logger = logging.getLogger("BlenderMCP.AddCompositingNode")

class AddCompositingNodeHandler(BaseToolHandler):
    """添加合成节点工具处理器"""
    
    @property
    def name(self) -> str:
        return "add_compositing_node"
        
    @property
    def description(self) -> Optional[str]:
        return "添加新的合成节点到节点树"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "node_type": {
                    "type": "string",
                    "title": "节点类型",
                    "description": "要添加的合成节点类型",
                    "enum": ["COMPOSITE", "VIEWER", "RGB", "VALUE", "MIX", "BLUR", "FILTER", 
                             "COLOR_CORRECTION", "HUE_SAT", "BRIGHTCONTRAST", "GAMMA", "INVERT",
                             "NORMAL", "CURVE", "MAP_VALUE", "VIGNETTE", "GLARE", "TONEMAP",
                             "LENSDIST", "DEFOCUS", "TRANSLATE", "ROTATE", "SCALE", "IMAGE",
                             "MASK", "MOVIE_CLIP", "RENDER_LAYERS"]
                },
                "node_name": {
                    "type": "string",
                    "title": "节点名称",
                    "description": "自定义节点名称"
                },
                "location": {
                    "type": "array",
                    "title": "位置",
                    "description": "节点在编辑器中的位置 [X, Y]",
                    "items": {
                        "type": "number"
                    }
                },
                "settings": {
                    "type": "object",
                    "title": "节点设置",
                    "description": "节点的附加设置",
                    "additionalProperties": True    
                }
            },
            "required": ["node_type"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        if not arguments.get("node_type"):
            return "必须提供节点类型"
            
        location = arguments.get("location")
        if location and (not isinstance(location, list) or len(location) != 2 or 
                         not all(isinstance(v, (int, float)) for v in location)):
            return "位置必须是包含2个数字的数组 [X, Y]"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行添加合成节点操作"""
        logger.debug(f"添加合成节点: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._add_compositing_node, arguments)
        
    def _add_compositing_node(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中添加合成节点"""
        try:
            node_type = args.get("node_type")
            node_name = args.get("node_name")
            location = args.get("location", [0, 0])
            settings = args.get("settings", {})
            
            # 获取当前场景
            scene = bpy.context.scene
            
            # 确保合成节点已启用
            if not scene.use_nodes:
                scene.use_nodes = True
                
            node_tree = scene.node_tree
            
            # 添加节点
            new_node = node_tree.nodes.new(type=f'CompositorNode{node_type}')
            
            # 设置节点名称（如果提供）
            if node_name:
                new_node.name = node_name
                
            # 设置节点位置
            new_node.location = (location[0], location[1])
            
            # 应用节点特定设置
            for key, value in settings.items():
                if hasattr(new_node, key):
                    try:
                        setattr(new_node, key, value)
                    except:
                        logger.warning(f"无法设置属性 {key}={value}")
            
            # 特定节点类型的设置
            self._apply_specific_settings(new_node, settings)
            
            text_content = create_text_content(f"已添加类型为 {node_type} 的合成节点: {new_node.name}")
            
            return self.create_result([text_content], {
                "node_name": new_node.name,
                "node_type": node_type,
                "location": [new_node.location.x, new_node.location.y]
            })
        except Exception as e:
            logger.error(f"添加合成节点出错: {str(e)}")
            return {"error": str(e)}
            
    def _apply_specific_settings(self, node, settings):
        """应用特定节点类型的设置"""
        # 根据节点类型应用特定设置
        node_type = node.type
        
        if node_type == 'BLUR':
            if "size_x" in settings:
                node.size_x = settings["size_x"]
            if "size_y" in settings:
                node.size_y = settings["size_y"]
            if "filter_type" in settings:
                node.filter_type = settings["filter_type"]
                
        elif node_type == 'HUE_SAT':
            if "hue" in settings:
                node.inputs['Hue'].default_value = settings["hue"]
            if "saturation" in settings:
                node.inputs['Saturation'].default_value = settings["saturation"]
            if "value" in settings:
                node.inputs['Value'].default_value = settings["value"]
                
        elif node_type == 'MIX':
            if "blend_type" in settings:
                node.blend_type = settings["blend_type"]
            if "use_alpha" in settings:
                node.use_alpha = settings["use_alpha"]
            if "fac" in settings:
                node.inputs[0].default_value = settings["fac"]
                
        elif node_type == 'RGB':
            if "color" in settings:
                color = settings["color"]
                if len(color) >= 3:
                    node.outputs[0].default_value[0] = color[0]
                    node.outputs[0].default_value[1] = color[1]
                    node.outputs[0].default_value[2] = color[2]
                    if len(color) >= 4:
                        node.outputs[0].default_value[3] = color[3]
                        
        elif node_type == 'VALUE':
            if "value" in settings:
                node.outputs[0].default_value = settings["value"]
                
        # 可以添加更多节点类型的特定设置


# 在导入时自动注册工具实例
register_tool(AddCompositingNodeHandler())
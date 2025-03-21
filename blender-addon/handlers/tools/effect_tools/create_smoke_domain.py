from ..registry import register_tool
import bpy
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils
from ....mcp_types import create_text_content

# 获取日志器
logger = logging.getLogger("BlenderMCP.CreateSmokeDomain")

class CreateSmokeDomainHandler(BaseToolHandler):
    """创建烟雾域工具处理器"""
    
    @property
    def name(self) -> str:
        return "create_smoke_domain"
        
    @property
    def description(self) -> Optional[str]:
        return "创建烟雾模拟域、流体或碰撞体"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "要设置为烟雾域的对象名称"
                },
                "smoke_type": {
                    "type": "string",
                    "title": "烟雾类型",
                    "description": "烟雾模拟类型",
                    "enum": ["DOMAIN", "FLOW", "COLLISION"],
                    "default": "DOMAIN"
                },
                "settings": {
                    "type": "object",
                    "title": "烟雾设置",
                    "description": "烟雾模拟的附加设置",
                    "properties": {
                        "resolution_factor": {
                            "type": "integer",
                            "title": "分辨率因子",
                            "description": "烟雾域分辨率倍数"
                        },
                        "domain_type": {
                            "type": "string",
                            "title": "域类型",
                            "description": "烟雾域的类型",
                            "enum": ["GAS", "LIQUID"]
                        },
                        "flow_type": {
                            "type": "string",
                            "title": "流体类型",
                            "description": "流体类型",
                            "enum": ["SMOKE", "BOTH", "FIRE"]
                        },
                        "smoke_color": {
                            "type": "array",
                            "title": "烟雾颜色",
                            "description": "烟雾颜色 [R, G, B]",
                            "items": {
                                "type": "number"
                            }
                        }
                    }
                }
            },
            "required": ["object_name"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        if not arguments.get("object_name"):
            return "必须提供对象名称"
            
        smoke_type = arguments.get("smoke_type")
        if smoke_type and smoke_type not in ["DOMAIN", "FLOW", "COLLISION"]:
            return "烟雾类型必须是 'DOMAIN', 'FLOW' 或 'COLLISION'"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行创建烟雾域操作"""
        logger.debug(f"创建烟雾域: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._create_smoke_domain, arguments)
        
    def _create_smoke_domain(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中创建烟雾域"""
        try:
            object_name = args.get("object_name")
            smoke_type = args.get("smoke_type", 'DOMAIN')
            settings = args.get("settings", {})

            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"找不到对象: {object_name}"}

            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.modifier_add(type='SMOKE')
            smoke_modifier = obj.modifiers["Smoke"]
            smoke_modifier.smoke_type = smoke_type

            if smoke_type == 'DOMAIN':
                smoke_settings = smoke_modifier.domain_settings
                if "resolution_factor" in settings:
                    smoke_settings.resolution_factor = settings["resolution_factor"]
                if "domain_type" in settings:
                    smoke_settings.domain_type = settings["domain_type"]
                # 可以添加更多域设置

            elif smoke_type == 'FLOW':
                flow_settings = smoke_modifier.flow_settings
                if "flow_type" in settings:
                    flow_settings.flow_type = settings["flow_type"]
                if "smoke_color" in settings:
                    color = settings["smoke_color"]
                    if len(color) >= 3:
                        flow_settings.smoke_color[0] = color[0]
                        flow_settings.smoke_color[1] = color[1]
                        flow_settings.smoke_color[2] = color[2]
                # 可以添加更多流体设置

            # 更新场景
            bpy.context.view_layer.update()

            text_content = create_text_content(f"已将对象 '{object_name}' 设置为类型为 {smoke_type} 的烟雾模拟")
            
            return self.create_result([text_content], {
                "object_name": object_name,
                "smoke_type": smoke_type
            })
        except Exception as e:
            logger.error(f"创建烟雾域出错: {str(e)}")
            return {"error": str(e)}


# 在导入时自动注册工具实例
register_tool(CreateSmokeDomainHandler())
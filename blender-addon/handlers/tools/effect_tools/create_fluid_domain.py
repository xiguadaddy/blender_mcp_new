from ..registry import register_tool
import bpy
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils
from ....mcp_types import create_text_content

# 获取日志器
logger = logging.getLogger("BlenderMCP.CreateFluidDomain")

class CreateFluidDomainHandler(BaseToolHandler):
    """创建流体域工具处理器"""
    
    @property
    def name(self) -> str:
        return "create_fluid_domain"
        
    @property
    def description(self) -> Optional[str]:
        return "创建流体模拟域、流体或障碍物"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "要设置为流体域的对象名称"
                },
                "fluid_type": {
                    "type": "string",
                    "title": "流体类型",
                    "description": "流体模拟类型",
                    "enum": ["DOMAIN", "FLOW", "EFFECTOR"],
                    "default": "DOMAIN"
                },
                "settings": {
                    "type": "object",
                    "title": "流体设置",
                    "description": "流体模拟的附加设置",
                    "properties": {
                        "resolution_divisions": {
                            "type": "integer",
                            "title": "分辨率",
                            "description": "流体域分辨率",
                            "default": 32
                        },
                        "domain_type": {
                            "type": "string",
                            "title": "域类型",
                            "description": "流体域的类型",
                            "enum": ["GAS", "LIQUID"]
                        },
                        "flow_type": {
                            "type": "string",
                            "title": "流体流类型",
                            "description": "流体类型",
                            "enum": ["SMOKE", "BOTH", "FIRE", "LIQUID"]
                        },
                        "effector_type": {
                            "type": "string",
                            "title": "效应器类型",
                            "description": "效应器类型",
                            "enum": ["COLLISION", "GUIDE"]
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
            
        fluid_type = arguments.get("fluid_type")
        if fluid_type and fluid_type not in ["DOMAIN", "FLOW", "EFFECTOR"]:
            return "流体类型必须是 'DOMAIN', 'FLOW' 或 'EFFECTOR'"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行创建流体域操作"""
        logger.debug(f"创建流体域: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._create_fluid_domain, arguments)
        
    def _create_fluid_domain(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中创建流体域"""
        try:
            object_name = args.get("object_name")
            fluid_type = args.get("fluid_type", 'DOMAIN')
            settings = args.get("settings", {})

            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"找不到对象: {object_name}"}

            bpy.context.view_layer.objects.active = obj
            
            # 使用流体模拟修改器
            bpy.ops.object.modifier_add(type='FLUID')
            fluid_modifier = obj.modifiers[-1]  # 获取新添加的修改器
            
            # 设置流体类型
            fluid_modifier.fluid_type = fluid_type
            
            # 根据流体类型设置特定属性
            if fluid_type == 'DOMAIN':
                domain_settings = fluid_modifier.domain_settings
                
                # 设置域类型（气体或液体）
                if "domain_type" in settings:
                    domain_settings.domain_type = settings["domain_type"]
                
                # 设置分辨率
                if "resolution_divisions" in settings:
                    domain_settings.resolution_divisions = settings["resolution_divisions"]
                else:
                    domain_settings.resolution_divisions = 32  # 默认值
                
            elif fluid_type == 'FLOW':
                flow_settings = fluid_modifier.flow_settings
                
                # 设置流体类型
                if "flow_type" in settings:
                    flow_settings.flow_type = settings["flow_type"]
                
            elif fluid_type == 'EFFECTOR':
                effector_settings = fluid_modifier.effector_settings
                
                # 设置效应器类型
                if "effector_type" in settings:
                    effector_settings.effector_type = settings["effector_type"]
            
            # 更新场景
            bpy.context.view_layer.update()

            text_content = create_text_content(f"已将对象 '{object_name}' 设置为类型为 {fluid_type} 的流体模拟")
            
            return self.create_result([text_content], {
                "object_name": object_name,
                "fluid_type": fluid_type
            })
        except Exception as e:
            logger.error(f"创建流体域出错: {str(e)}")
            return {"error": str(e)}


# 在导入时自动注册工具实例
register_tool(CreateFluidDomainHandler())
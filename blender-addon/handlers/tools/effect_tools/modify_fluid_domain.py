from ..registry import register_tool
import bpy
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils
from ....mcp_types import create_text_content

# 获取日志器
logger = logging.getLogger("BlenderMCP.ModifyFluidDomain")

class ModifyFluidDomainHandler(BaseToolHandler):
    """修改流体域工具处理器"""
    
    @property
    def name(self) -> str:
        return "modify_fluid_domain"
        
    @property
    def description(self) -> Optional[str]:
        return "修改现有流体域的属性"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "包含流体域的对象名称"
                },
                "settings": {
                    "type": "object",
                    "title": "域设置",
                    "description": "要修改的流体域设置",
                    "properties": {
                        "resolution_divisions": {
                            "type": "integer",
                            "title": "分辨率",
                            "description": "流体域分辨率"
                        },
                        "time_scale": {
                            "type": "number",
                            "title": "时间缩放",
                            "description": "流体模拟时间缩放因子"
                        },
                        "use_adaptive_domain": {
                            "type": "boolean",
                            "title": "自适应域",
                            "description": "使用自适应域调整大小"
                        },
                        "viscosity_base": {
                            "type": "number",
                            "title": "基础粘度",
                            "description": "液体粘度基础值"
                        },
                        "gravity": {
                            "type": "array",
                            "title": "重力",
                            "description": "流体域的重力向量 [X, Y, Z]",
                            "items": {
                                "type": "number"
                            }
                        }
                    }
                }
            },
            "required": ["object_name", "settings"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        if not arguments.get("object_name"):
            return "必须提供对象名称"
            
        if not arguments.get("settings"):
            return "必须提供至少一个要修改的设置"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行修改流体域操作"""
        logger.debug(f"修改流体域属性: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._modify_fluid_domain, arguments)
        
    def _modify_fluid_domain(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中修改流体域"""
        try:
            object_name = args.get("object_name")
            settings = args.get("settings", {})

            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"找不到对象: {object_name}"}

            # 查找流体修改器
            fluid_modifier = None
            for mod in obj.modifiers:
                if mod.type == 'FLUID' and mod.fluid_type == 'DOMAIN':
                    fluid_modifier = mod
                    break
                    
            if not fluid_modifier:
                return {"error": f"对象上找不到流体域修改器: {object_name}"}

            domain_settings = fluid_modifier.domain_settings
            
            # 修改设置
            modified_settings = []
            
            if "resolution_divisions" in settings:
                domain_settings.resolution_divisions = settings["resolution_divisions"]
                modified_settings.append("resolution_divisions")
                
            if "time_scale" in settings:
                domain_settings.time_scale = settings["time_scale"]
                modified_settings.append("time_scale")
                
            if "use_adaptive_domain" in settings:
                domain_settings.use_adaptive_domain = settings["use_adaptive_domain"]
                modified_settings.append("use_adaptive_domain")
                
            if "viscosity_base" in settings:
                domain_settings.viscosity_base = settings["viscosity_base"]
                modified_settings.append("viscosity_base")
                
            if "gravity" in settings:
                gravity = settings["gravity"]
                if len(gravity) >= 3:
                    domain_settings.gravity[0] = gravity[0]
                    domain_settings.gravity[1] = gravity[1]
                    domain_settings.gravity[2] = gravity[2]
                    modified_settings.append("gravity")

            # 更新场景
            bpy.context.view_layer.update()

            text_content = create_text_content(f"已修改对象 '{object_name}' 上的流体域属性，修改了: {', '.join(modified_settings)}")
            
            return self.create_result([text_content], {
                "object_name": object_name,
                "modified_settings": modified_settings
            })
        except Exception as e:
            logger.error(f"修改流体域属性出错: {str(e)}")
            return {"error": str(e)}


# 在导入时自动注册工具实例
register_tool(ModifyFluidDomainHandler())
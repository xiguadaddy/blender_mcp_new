from ..registry import register_tool
import bpy
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils
from ....mcp_types import create_text_content

# 获取日志器
logger = logging.getLogger("BlenderMCP.ModifySmokeDomain")

class ModifySmokeDomainHandler(BaseToolHandler):
    """修改烟雾域工具处理器"""
    
    @property
    def name(self) -> str:
        return "modify_smoke_domain"
        
    @property
    def description(self) -> Optional[str]:
        return "修改现有烟雾域的属性"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "包含烟雾域的对象名称"
                },
                "settings": {
                    "type": "object",
                    "title": "域设置",
                    "description": "要修改的烟雾域设置",
                    "properties": {
                        "resolution_factor": {
                            "type": "integer",
                            "title": "分辨率因子",
                            "description": "烟雾域分辨率倍数"
                        },
                        "time_scale": {
                            "type": "number",
                            "title": "时间缩放",
                            "description": "烟雾模拟时间缩放因子"
                        },
                        "vorticity": {
                            "type": "number",
                            "title": "涡度",
                            "description": "烟雾模拟涡度强度"
                        },
                        "use_high_resolution": {
                            "type": "boolean",
                            "title": "高分辨率",
                            "description": "使用高分辨率模拟"
                        },
                        "collision_collection": {
                            "type": "string",
                            "title": "碰撞集合",
                            "description": "用于碰撞的集合名称"
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
        """执行修改烟雾域操作"""
        logger.debug(f"修改烟雾域属性: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._modify_smoke_domain, arguments)
        
    def _modify_smoke_domain(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中修改烟雾域"""
        try:
            object_name = args.get("object_name")
            settings = args.get("settings", {})

            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"找不到对象: {object_name}"}

            smoke_modifier = obj.modifiers.get("Smoke")
            if not smoke_modifier or smoke_modifier.type != 'SMOKE' or smoke_modifier.smoke_type != 'DOMAIN':
                return {"error": f"对象上找不到烟雾域修改器: {object_name}"}

            smoke_domain_settings = smoke_modifier.domain_settings
            
            # 修改设置
            modified_settings = []
            
            if "resolution_factor" in settings:
                smoke_domain_settings.resolution_factor = settings["resolution_factor"]
                modified_settings.append("resolution_factor")
                
            if "time_scale" in settings:
                smoke_domain_settings.time_scale = settings["time_scale"]
                modified_settings.append("time_scale")
                
            if "vorticity" in settings:
                smoke_domain_settings.vorticity = settings["vorticity"]
                modified_settings.append("vorticity")
                
            if "use_high_resolution" in settings:
                smoke_domain_settings.use_high_resolution = settings["use_high_resolution"]
                modified_settings.append("use_high_resolution")
                
            if "collision_collection" in settings:
                coll_name = settings["collision_collection"]
                coll = bpy.data.collections.get(coll_name)
                if coll:
                    smoke_domain_settings.collision_collection = coll
                    modified_settings.append("collision_collection")

            # 更新场景
            bpy.context.view_layer.update()

            text_content = create_text_content(f"已修改对象 '{object_name}' 上的烟雾域属性，修改了: {', '.join(modified_settings)}")
            
            return self.create_result([text_content], {
                "object_name": object_name,
                "modified_settings": modified_settings
            })
        except Exception as e:
            logger.error(f"修改烟雾域属性出错: {str(e)}")
            return {"error": str(e)}


# 在导入时自动注册工具实例
register_tool(ModifySmokeDomainHandler())
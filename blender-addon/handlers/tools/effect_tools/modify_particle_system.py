from ..registry import register_tool
import bpy
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils
from ....mcp_types import create_text_content

# 获取日志器
logger = logging.getLogger("BlenderMCP.ModifyParticleSystem")

class ModifyParticleSystemHandler(BaseToolHandler):
    """修改粒子系统工具处理器"""
    
    @property
    def name(self) -> str:
        return "modify_particle_system"
        
    @property
    def description(self) -> Optional[str]:
        return "修改现有粒子系统的属性"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "包含粒子系统的对象名称"
                },
                "system_name": {
                    "type": "string",
                    "title": "系统名称",
                    "description": "要修改的粒子系统名称"
                },
                "settings": {
                    "type": "object",
                    "title": "粒子设置",
                    "description": "要修改的粒子系统设置",
                    "properties": {
                        "count": {
                            "type": "integer",
                            "title": "粒子数量",
                            "description": "粒子系统的粒子数量"
                        },
                        "seed": {
                            "type": "integer",
                            "title": "随机种子",
                            "description": "粒子系统的随机种子"
                        },
                        "frame_start": {
                            "type": "integer",
                            "title": "起始帧",
                            "description": "放射开始的帧"
                        },
                        "frame_end": {
                            "type": "integer",
                            "title": "结束帧",
                            "description": "放射结束的帧"
                        },
                        "lifetime": {
                            "type": "integer",
                            "title": "生命周期",
                            "description": "粒子的生命周期长度"
                        },
                        "normal_factor": {
                            "type": "number",
                            "title": "法线因子",
                            "description": "粒子沿法线方向的速度因子"
                        },
                        "object_align_factor": {
                            "type": "array",
                            "title": "对象对齐因子",
                            "description": "沿对象X, Y, Z轴的速度因子",
                            "items": {
                                "type": "number"
                            }
                        }
                    }
                }
            },
            "required": ["object_name", "system_name", "settings"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        if not arguments.get("object_name"):
            return "必须提供对象名称"
            
        if not arguments.get("system_name"):
            return "必须提供粒子系统名称"
            
        if not arguments.get("settings"):
            return "必须提供至少一个要修改的设置"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行修改粒子系统操作"""
        logger.debug(f"修改粒子系统属性: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._modify_particle_system, arguments)
        
    def _modify_particle_system(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中修改粒子系统"""
        try:
            object_name = args.get("object_name")
            system_name = args.get("system_name")
            settings = args.get("settings", {})

            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"找不到对象: {object_name}"}

            particle_system = obj.particle_systems.get(system_name)
            if not particle_system:
                return {"error": f"找不到粒子系统: {system_name}"}

            particle_settings = particle_system.settings
            
            # 修改设置
            modified_settings = []
            
            if "count" in settings:
                particle_settings.count = settings["count"]
                modified_settings.append("count")
                
            if "seed" in settings:
                particle_settings.seed = settings["seed"]
                modified_settings.append("seed")
                
            if "frame_start" in settings:
                particle_settings.frame_start = settings["frame_start"]
                modified_settings.append("frame_start")
                
            if "frame_end" in settings:
                particle_settings.frame_end = settings["frame_end"]
                modified_settings.append("frame_end")
                
            if "lifetime" in settings:
                particle_settings.lifetime = settings["lifetime"]
                modified_settings.append("lifetime")
                
            if "normal_factor" in settings:
                particle_settings.normal_factor = settings["normal_factor"]
                modified_settings.append("normal_factor")
                
            if "object_align_factor" in settings:
                values = settings["object_align_factor"]
                if len(values) >= 3:
                    particle_settings.object_align_factor[0] = values[0]
                    particle_settings.object_align_factor[1] = values[1]
                    particle_settings.object_align_factor[2] = values[2]
                    modified_settings.append("object_align_factor")

            # 更新场景
            bpy.context.view_layer.update()

            text_content = create_text_content(f"已修改对象 '{object_name}' 上的粒子系统 '{system_name}'，修改了: {', '.join(modified_settings)}")
            
            return self.create_result([text_content], {
                "object_name": object_name,
                "system_name": system_name,
                "modified_settings": modified_settings
            })
        except Exception as e:
            logger.error(f"修改粒子系统属性出错: {str(e)}")
            return {"error": str(e)}


# 在导入时自动注册工具实例
register_tool(ModifyParticleSystemHandler())
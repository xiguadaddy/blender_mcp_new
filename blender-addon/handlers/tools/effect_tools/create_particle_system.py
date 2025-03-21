from ..registry import register_tool
import bpy
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils
from ....mcp_types import create_text_content

# 获取日志器
logger = logging.getLogger("BlenderMCP.CreateParticleSystem")

class CreateParticleSystemHandler(BaseToolHandler):
    """创建粒子系统工具处理器"""
    
    @property
    def name(self) -> str:
        return "create_particle_system"
        
    @property
    def description(self) -> Optional[str]:
        return "创建粒子系统，可以是放射粒子或毛发粒子"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "要添加粒子系统的对象名称"
                },
                "count": {
                    "type": "integer",
                    "title": "粒子数量",
                    "description": "粒子系统的粒子数量",
                    "default": 1000
                },
                "type": {
                    "type": "string",
                    "title": "粒子类型",
                    "description": "粒子系统类型",
                    "enum": ["EMITTER", "HAIR"],
                    "default": "EMITTER"
                },
                "settings": {
                    "type": "object",
                    "title": "粒子设置",
                    "description": "粒子系统的附加设置",
                    "properties": {
                        "name": {
                            "type": "string",
                            "title": "系统名称",
                            "description": "粒子系统的名称"
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
                        "emit_from": {
                            "type": "string",
                            "title": "放射源",
                            "description": "粒子放射的源位置",
                            "enum": ["FACE", "VOLUME", "VERT"]
                        },
                        "velocity_factor": {
                            "type": "number",
                            "title": "速度因子",
                            "description": "粒子法线速度因子"
                        },
                        "physics_type": {
                            "type": "string",
                            "title": "物理类型",
                            "description": "粒子物理模拟类型"
                        },
                        "render_type": {
                            "type": "string",
                            "title": "渲染类型",
                            "description": "粒子渲染的类型"
                        },
                        "instance_object": {
                            "type": "string",
                            "title": "实例对象",
                            "description": "用于实例的对象名称"
                        },
                        "instance_collection": {
                            "type": "string",
                            "title": "实例集合",
                            "description": "用于实例的集合名称"
                        },
                        "hair_length": {
                            "type": "number",
                            "title": "毛发长度",
                            "description": "毛发粒子的长度"
                        },
                        "render_step": {
                            "type": "integer",
                            "title": "渲染步骤",
                            "description": "毛发渲染分段数"
                        },
                        "use_dynamic_hair": {
                            "type": "boolean",
                            "title": "动态毛发",
                            "description": "启用动态毛发物理"
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
        
        particle_type = arguments.get("type")
        if particle_type and particle_type not in ["EMITTER", "HAIR"]:
            return "粒子类型必须是 'EMITTER' 或 'HAIR'"
            
        count = arguments.get("count")
        if count is not None and (not isinstance(count, int) or count <= 0):
            return "粒子数量必须是正整数"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行创建粒子系统操作"""
        logger.debug(f"创建粒子系统: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._create_particle_system, arguments)
        
    def _create_particle_system(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中创建粒子系统"""
        try:
            object_name = args.get("object_name")
            particles_count = args.get("count", 1000)
            particle_type = args.get("type", "EMITTER")
            settings = args.get("settings", {})
            
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"对象不存在: {object_name}"}

            # 设置活动对象
            bpy.context.view_layer.objects.active = obj

            # 创建粒子系统
            if not obj.particle_systems:
                obj.modifiers.new("ParticleSystem", 'PARTICLE_SYSTEM')

            particle_system = obj.particle_systems[-1]
            particle_settings = particle_system.settings

            # 设置基本参数
            particle_settings.name = settings.get("name", f"{obj.name}_particles")
            particle_settings.type = particle_type
            particle_settings.count = particles_count

            # 设置发射参数
            if particle_type == "EMITTER":
                particle_settings.frame_start = settings.get("frame_start", 1)
                particle_settings.frame_end = settings.get("frame_end", 200)
                particle_settings.lifetime = settings.get("lifetime", 100)
                particle_settings.emit_from = settings.get("emit_from", 'FACE')

                # 速度设置
                if "velocity_factor" in settings:
                    particle_settings.normal_factor = settings["velocity_factor"]

                # 物理设置
                if "physics_type" in settings:
                    particle_settings.physics_type = settings["physics_type"]

                # 渲染设置
                if "render_type" in settings:
                    particle_settings.render_type = settings["render_type"]

                    # 对象渲染
                    if settings["render_type"] == 'OBJECT' and "instance_object" in settings:
                        instance_obj = bpy.data.objects.get(settings["instance_object"])
                        if instance_obj:
                            particle_settings.instance_object = instance_obj

                    # 集合渲染
                    elif settings["render_type"] == 'COLLECTION' and "instance_collection" in settings:
                        instance_col = bpy.data.collections.get(settings["instance_collection"])
                        if instance_col:
                            particle_settings.instance_collection = instance_col

            # 设置毛发参数
            elif particle_type == "HAIR":
                particle_settings.hair_length = settings.get("hair_length", 4.0)
                particle_settings.render_step = settings.get("render_step", 3)

                # 动力学设置
                if "use_dynamic_hair" in settings:
                    particle_settings.use_dynamic_hair = settings["use_dynamic_hair"]

            # 更新场景
            bpy.context.view_layer.update()

            text_content = create_text_content(f"已为对象 '{object_name}' 创建含 {particles_count} 个粒子的 {particle_type} 粒子系统")
            
            return self.create_result([text_content], {
                "object_name": object_name,
                "particles_count": particles_count,
                "particle_type": particle_type,
                "system_name": particle_settings.name
            })
        except Exception as e:
            logger.error(f"创建粒子系统时出错: {str(e)}")
            return {"error": str(e)}


# 在导入时自动注册工具实例
register_tool(CreateParticleSystemHandler())
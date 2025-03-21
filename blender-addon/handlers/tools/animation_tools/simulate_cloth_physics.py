"""
模拟布料物理的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.SimulateClothPhysics")

class SimulateClothPhysicsHandler(BaseToolHandler):
    """模拟布料物理工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_simulate_cloth_physics"
        
    @property
    def description(self) -> Optional[str]:
        return "为网格对象添加并配置布料物理模拟"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "要添加布料物理的网格对象名称"
                },
                "preset": {
                    "type": "string",
                    "title": "预设",
                    "description": "使用的布料预设类型",
                    "enum": ["silk", "cotton", "leather", "denim", "rubber", "custom"],
                    "default": "cotton"
                },
                "quality": {
                    "type": "integer",
                    "title": "质量步数",
                    "description": "布料模拟的质量步数",
                    "minimum": 1,
                    "default": 5
                },
                "mass": {
                    "type": "number",
                    "title": "质量",
                    "description": "布料的质量",
                    "minimum": 0,
                    "default": 0.3
                },
                "tension_stiffness": {
                    "type": "number",
                    "title": "张力刚度",
                    "description": "布料的张力刚度",
                    "minimum": 0,
                    "default": 15
                },
                "compression_stiffness": {
                    "type": "number",
                    "title": "压缩刚度",
                    "description": "布料的压缩刚度",
                    "minimum": 0,
                    "default": 15
                },
                "shear_stiffness": {
                    "type": "number",
                    "title": "剪切刚度",
                    "description": "布料的剪切刚度",
                    "minimum": 0,
                    "default": 15
                },
                "bending_stiffness": {
                    "type": "number",
                    "title": "弯曲刚度",
                    "description": "布料的弯曲刚度",
                    "minimum": 0,
                    "default": 15
                },
                "pin_vertex_group": {
                    "type": "string",
                    "title": "固定顶点组",
                    "description": "指定要固定的顶点组名称"
                },
                "collision_objects": {
                    "type": "array",
                    "title": "碰撞对象",
                    "description": "与布料交互的碰撞对象名称列表",
                    "items": {
                        "type": "string"
                    }
                },
                "use_self_collision": {
                    "type": "boolean",
                    "title": "使用自碰撞",
                    "description": "是否启用布料自碰撞",
                    "default": False
                },
                "frame_start": {
                    "type": "integer",
                    "title": "开始帧",
                    "description": "模拟的开始帧"
                },
                "frame_end": {
                    "type": "integer",
                    "title": "结束帧",
                    "description": "模拟的结束帧"
                },
                "bake_simulation": {
                    "type": "boolean",
                    "title": "烘焙模拟",
                    "description": "是否立即烘焙模拟",
                    "default": False
                }
            },
            "required": ["object_name"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查对象名称
        object_name = arguments.get("object_name")
        if not object_name:
            return "必须提供对象名称"
            
        # 检查对象是否存在
        if object_name not in bpy.data.objects:
            return f"找不到对象: {object_name}"
            
        # 检查对象是否是网格
        obj = bpy.data.objects[object_name]
        if obj.type != 'MESH':
            return f"对象 '{object_name}' 不是网格，无法应用布料物理"
            
        # 检查质量步数
        quality = arguments.get("quality", 5)
        if not isinstance(quality, int) or quality < 1:
            return "质量步数必须是大于等于1的整数"
            
        # 检查质量
        mass = arguments.get("mass", 0.3)
        if not isinstance(mass, (int, float)) or mass < 0:
            return "质量必须是非负数"
            
        # 检查张力刚度
        tension_stiffness = arguments.get("tension_stiffness", 15)
        if not isinstance(tension_stiffness, (int, float)) or tension_stiffness < 0:
            return "张力刚度必须是非负数"
            
        # 检查压缩刚度
        compression_stiffness = arguments.get("compression_stiffness", 15)
        if not isinstance(compression_stiffness, (int, float)) or compression_stiffness < 0:
            return "压缩刚度必须是非负数"
            
        # 检查剪切刚度
        shear_stiffness = arguments.get("shear_stiffness", 15)
        if not isinstance(shear_stiffness, (int, float)) or shear_stiffness < 0:
            return "剪切刚度必须是非负数"
            
        # 检查弯曲刚度
        bending_stiffness = arguments.get("bending_stiffness", 15)
        if not isinstance(bending_stiffness, (int, float)) or bending_stiffness < 0:
            return "弯曲刚度必须是非负数"
            
        # 检查固定顶点组
        pin_vertex_group = arguments.get("pin_vertex_group")
        if pin_vertex_group and obj.vertex_groups and pin_vertex_group not in [vg.name for vg in obj.vertex_groups]:
            return f"对象上找不到顶点组: '{pin_vertex_group}'"
            
        # 检查碰撞对象
        collision_objects = arguments.get("collision_objects", [])
        if collision_objects:
            missing_objects = [name for name in collision_objects if name not in bpy.data.objects]
            if missing_objects:
                return f"找不到以下碰撞对象: {', '.join(missing_objects)}"
                
        # 检查开始帧和结束帧
        frame_start = arguments.get("frame_start")
        frame_end = arguments.get("frame_end")
        
        if frame_start is not None and not isinstance(frame_start, int):
            return "开始帧必须是整数"
            
        if frame_end is not None and not isinstance(frame_end, int):
            return "结束帧必须是整数"
            
        if frame_start is not None and frame_end is not None and frame_start >= frame_end:
            return "开始帧必须小于结束帧"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行模拟布料物理操作"""
        logger.info(f"模拟布料物理，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._simulate_cloth_physics, arguments)
        
    def _simulate_cloth_physics(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中模拟布料物理"""
        object_name = arguments.get("object_name")
        preset = arguments.get("preset", "cotton")
        quality = arguments.get("quality", 5)
        mass = arguments.get("mass", 0.3)
        tension_stiffness = arguments.get("tension_stiffness", 15)
        compression_stiffness = arguments.get("compression_stiffness", 15)
        shear_stiffness = arguments.get("shear_stiffness", 15)
        bending_stiffness = arguments.get("bending_stiffness", 15)
        pin_vertex_group = arguments.get("pin_vertex_group")
        collision_objects = arguments.get("collision_objects", [])
        use_self_collision = arguments.get("use_self_collision", False)
        frame_start = arguments.get("frame_start")
        frame_end = arguments.get("frame_end")
        bake_simulation = arguments.get("bake_simulation", False)
        
        # 获取对象
        obj = bpy.data.objects[object_name]
        
        # 保存当前选择状态
        original_active = bpy.context.view_layer.objects.active
        original_selected = [o for o in bpy.context.selected_objects]
        
        try:
            # 选择目标对象
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            
            # 获取或添加布料修改器
            cloth_modifier = None
            for mod in obj.modifiers:
                if mod.type == 'CLOTH':
                    cloth_modifier = mod
                    break
                    
            if not cloth_modifier:
                cloth_modifier = obj.modifiers.new(name="Cloth", type='CLOTH')
            
            # 配置布料修改器
            cloth_settings = cloth_modifier.settings
            
            # 应用预设
            if preset != "custom":
                # 根据预设设置属性
                if preset == "silk":
                    cloth_settings.quality = 10
                    cloth_settings.mass = 0.15
                    cloth_settings.tension_stiffness = 5
                    cloth_settings.compression_stiffness = 5
                    cloth_settings.shear_stiffness = 5
                    cloth_settings.bending_stiffness = 0.5
                elif preset == "cotton":
                    cloth_settings.quality = 7
                    cloth_settings.mass = 0.3
                    cloth_settings.tension_stiffness = 15
                    cloth_settings.compression_stiffness = 15
                    cloth_settings.shear_stiffness = 15
                    cloth_settings.bending_stiffness = 5
                elif preset == "leather":
                    cloth_settings.quality = 5
                    cloth_settings.mass = 0.4
                    cloth_settings.tension_stiffness = 25
                    cloth_settings.compression_stiffness = 25
                    cloth_settings.shear_stiffness = 25
                    cloth_settings.bending_stiffness = 15
                elif preset == "denim":
                    cloth_settings.quality = 5
                    cloth_settings.mass = 0.5
                    cloth_settings.tension_stiffness = 50
                    cloth_settings.compression_stiffness = 50
                    cloth_settings.shear_stiffness = 50
                    cloth_settings.bending_stiffness = 25
                elif preset == "rubber":
                    cloth_settings.quality = 5
                    cloth_settings.mass = 0.3
                    cloth_settings.tension_stiffness = 80
                    cloth_settings.compression_stiffness = 80
                    cloth_settings.shear_stiffness = 80
                    cloth_settings.bending_stiffness = 40
            else:
                # 使用自定义设置
                cloth_settings.quality = quality
                cloth_settings.mass = mass
                cloth_settings.tension_stiffness = tension_stiffness
                cloth_settings.compression_stiffness = compression_stiffness
                cloth_settings.shear_stiffness = shear_stiffness
                cloth_settings.bending_stiffness = bending_stiffness
            
            # 设置固定顶点组
            if pin_vertex_group:
                cloth_settings.vertex_group_mass = pin_vertex_group
            
            # 设置自碰撞
            cloth_settings.use_self_collision = use_self_collision
            
            # 设置碰撞对象
            for coll_name in collision_objects:
                coll_obj = bpy.data.objects[coll_name]
                
                # 检查并添加碰撞修改器
                has_collision = False
                for mod in coll_obj.modifiers:
                    if mod.type == 'COLLISION':
                        has_collision = True
                        break
                        
                if not has_collision:
                    coll_obj.modifiers.new(name="Collision", type='COLLISION')
            
            # 设置开始帧和结束帧
            if frame_start is not None:
                cloth_settings.frame_start = frame_start
            else:
                frame_start = cloth_settings.frame_start
                
            if frame_end is not None:
                cloth_settings.frame_end = frame_end
            else:
                frame_end = cloth_settings.frame_end
            
            # 如果需要烘焙模拟
            if bake_simulation:
                # 清除现有的烘焙点缓存
                if hasattr(cloth_modifier, "point_cache"):
                    bpy.ops.ptcache.free_bake_all()
                
                # 烘焙模拟
                override = bpy.context.copy()
                override["point_cache"] = cloth_modifier.point_cache
                bpy.ops.ptcache.bake(override, bake=True)
                
                bake_info = "并已烘焙模拟"
            else:
                bake_info = "（未烘焙）"
            
            # 创建结果信息
            collision_info = f"已设置 {len(collision_objects)} 个碰撞对象" if collision_objects else "无碰撞对象"
            pin_info = f"固定顶点组: {pin_vertex_group}" if pin_vertex_group else "无固定顶点"
            
            text_content = self.create_text_content(
                f"已为对象 '{object_name}' 添加布料物理{bake_info}\n"
                f"预设: {preset}\n"
                f"帧范围: {frame_start} - {frame_end}\n"
                f"{collision_info}\n"
                f"{pin_info}\n"
                f"自碰撞: {'启用' if use_self_collision else '禁用'}"
            )
            
        except Exception as e:
            text_content = self.create_text_content(f"设置布料物理时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
            
        finally:
            # 恢复原始选择状态
            bpy.ops.object.select_all(action='DESELECT')
            for obj in original_selected:
                if obj:
                    obj.select_set(True)
            if original_active:
                bpy.context.view_layer.objects.active = original_active
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(SimulateClothPhysicsHandler())
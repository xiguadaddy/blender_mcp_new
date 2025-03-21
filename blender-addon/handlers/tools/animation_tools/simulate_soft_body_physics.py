"""
模拟软体物理的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.SimulateSoftBodyPhysics")

class SimulateSoftBodyPhysicsHandler(BaseToolHandler):
    """模拟软体物理工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_simulate_soft_body_physics"
        
    @property
    def description(self) -> Optional[str]:
        return "为网格对象添加并配置软体物理模拟"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "要添加软体物理的网格对象名称"
                },
                "preset": {
                    "type": "string",
                    "title": "预设",
                    "description": "使用的软体预设类型",
                    "enum": ["jelly", "balloon", "cloth", "rubber", "custom"],
                    "default": "jelly"
                },
                "goal_strength": {
                    "type": "number",
                    "title": "目标强度",
                    "description": "保持原始形状的强度",
                    "minimum": 0,
                    "maximum": 1,
                    "default": 0.5
                },
                "goal_friction": {
                    "type": "number",
                    "title": "目标摩擦力",
                    "description": "目标位置的摩擦力",
                    "minimum": 0,
                    "maximum": 1,
                    "default": 0.5
                },
                "mass": {
                    "type": "number",
                    "title": "质量",
                    "description": "软体的质量",
                    "minimum": 0.001,
                    "default": 1.0
                },
                "edge_stiffness": {
                    "type": "number",
                    "title": "边缘刚度",
                    "description": "边缘弹簧的刚度",
                    "minimum": 0,
                    "default": 0.5
                },
                "damping": {
                    "type": "number",
                    "title": "阻尼",
                    "description": "弹簧的阻尼",
                    "minimum": 0,
                    "maximum": 1,
                    "default": 0.5
                },
                "collision_margin": {
                    "type": "number",
                    "title": "碰撞边距",
                    "description": "碰撞检测的边距",
                    "minimum": 0,
                    "default": 0.01
                },
                "use_goal": {
                    "type": "boolean",
                    "title": "使用目标",
                    "description": "是否使用目标（控制还原到原始形状的程度）",
                    "default": True
                },
                "use_edges": {
                    "type": "boolean",
                    "title": "使用边缘",
                    "description": "是否使用边缘弹簧",
                    "default": True
                },
                "use_self_collision": {
                    "type": "boolean",
                    "title": "使用自碰撞",
                    "description": "是否启用自碰撞",
                    "default": False
                },
                "pin_vertex_group": {
                    "type": "string",
                    "title": "固定顶点组",
                    "description": "指定固定在原始位置的顶点组"
                },
                "collision_objects": {
                    "type": "array",
                    "title": "碰撞对象",
                    "description": "与软体交互的碰撞对象名称列表",
                    "items": {
                        "type": "string"
                    }
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
            return f"对象 '{object_name}' 不是网格，无法应用软体物理"
            
        # 检查预设
        preset = arguments.get("preset", "jelly")
        valid_presets = ["jelly", "balloon", "cloth", "rubber", "custom"]
        if preset not in valid_presets:
            return f"无效的预设，有效预设: {', '.join(valid_presets)}"
            
        # 检查目标强度
        goal_strength = arguments.get("goal_strength", 0.5)
        if not isinstance(goal_strength, (int, float)) or goal_strength < 0 or goal_strength > 1:
            return "目标强度必须是0到1之间的数值"
            
        # 检查目标摩擦力
        goal_friction = arguments.get("goal_friction", 0.5)
        if not isinstance(goal_friction, (int, float)) or goal_friction < 0 or goal_friction > 1:
            return "目标摩擦力必须是0到1之间的数值"
            
        # 检查质量
        mass = arguments.get("mass", 1.0)
        if not isinstance(mass, (int, float)) or mass <= 0:
            return "质量必须是正数"
            
        # 检查边缘刚度
        edge_stiffness = arguments.get("edge_stiffness", 0.5)
        if not isinstance(edge_stiffness, (int, float)) or edge_stiffness < 0:
            return "边缘刚度必须是非负数"
            
        # 检查阻尼
        damping = arguments.get("damping", 0.5)
        if not isinstance(damping, (int, float)) or damping < 0 or damping > 1:
            return "阻尼必须是0到1之间的数值"
            
        # 检查碰撞边距
        collision_margin = arguments.get("collision_margin", 0.01)
        if not isinstance(collision_margin, (int, float)) or collision_margin < 0:
            return "碰撞边距必须是非负数"
            
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
        """执行模拟软体物理操作"""
        logger.info(f"模拟软体物理，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._simulate_soft_body_physics, arguments)
        
    def _simulate_soft_body_physics(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中模拟软体物理"""
        object_name = arguments.get("object_name")
        preset = arguments.get("preset", "jelly")
        goal_strength = arguments.get("goal_strength", 0.5)
        goal_friction = arguments.get("goal_friction", 0.5)
        mass = arguments.get("mass", 1.0)
        edge_stiffness = arguments.get("edge_stiffness", 0.5)
        damping = arguments.get("damping", 0.5)
        collision_margin = arguments.get("collision_margin", 0.01)
        use_goal = arguments.get("use_goal", True)
        use_edges = arguments.get("use_edges", True)
        use_self_collision = arguments.get("use_self_collision", False)
        pin_vertex_group = arguments.get("pin_vertex_group")
        collision_objects = arguments.get("collision_objects", [])
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
            
            # 获取或添加软体修改器
            softbody_modifier = None
            for mod in obj.modifiers:
                if mod.type == 'SOFT_BODY':
                    softbody_modifier = mod
                    break
                    
            if not softbody_modifier:
                softbody_modifier = obj.modifiers.new(name="Softbody", type='SOFT_BODY')
            
            # 配置软体修改器
            sb = softbody_modifier.settings
            
            # 应用预设
            if preset != "custom":
                # 根据预设设置属性
                if preset == "jelly":
                    sb.mass = 1.0
                    sb.goal_spring = 0.9
                    sb.goal_friction = 0.9
                    sb.edge_stiffness = 0.1
                    sb.edge_damp = 0.8
                    sb.use_goal = True
                    sb.use_edges = True
                    sb.use_self_collision = False
                elif preset == "balloon":
                    sb.mass = 0.3
                    sb.goal_spring = 0.05
                    sb.goal_friction = 0.5
                    sb.edge_stiffness = 0.8
                    sb.edge_damp = 0.1
                    sb.use_goal = True
                    sb.use_edges = True
                    sb.use_self_collision = True
                elif preset == "cloth":
                    sb.mass = 0.3
                    sb.goal_spring = 0.0
                    sb.goal_friction = 0.0
                    sb.edge_stiffness = 0.5
                    sb.edge_damp = 0.5
                    sb.use_goal = False
                    sb.use_edges = True
                    sb.use_self_collision = True
                elif preset == "rubber":
                    sb.mass = 5.0
                    sb.goal_spring = 0.1
                    sb.goal_friction = 0.1
                    sb.edge_stiffness = 0.9
                    sb.edge_damp = 0.1
                    sb.use_goal = True
                    sb.use_edges = True
                    sb.use_self_collision = False
            else:
                # 使用自定义设置
                sb.mass = mass
                sb.goal_spring = goal_strength
                sb.goal_friction = goal_friction
                sb.edge_stiffness = edge_stiffness
                sb.edge_damp = damping
                sb.use_goal = use_goal
                sb.use_edges = use_edges
                sb.use_self_collision = use_self_collision
            
            # 设置碰撞边距
            sb.collision_type = 'MANUAL'
            sb.collision_margin = collision_margin
            
            # 设置固定顶点组
            if pin_vertex_group:
                sb.vertex_group_goal = pin_vertex_group
            
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
                sb.point_cache.frame_start = frame_start
            else:
                frame_start = sb.point_cache.frame_start
                
            if frame_end is not None:
                sb.point_cache.frame_end = frame_end
            else:
                frame_end = sb.point_cache.frame_end
            
            # 如果需要烘焙模拟
            if bake_simulation:
                # 清除现有的烘焙点缓存
                bpy.ops.ptcache.free_bake_all()
                
                # 烘焙模拟
                override = bpy.context.copy()
                override["point_cache"] = softbody_modifier.point_cache
                bpy.ops.ptcache.bake(override, bake=True)
                
                bake_info = "并已烘焙模拟"
            else:
                bake_info = "（未烘焙）"
            
            # 创建结果信息
            collision_info = f"已设置 {len(collision_objects)} 个碰撞对象" if collision_objects else "无碰撞对象"
            pin_info = f"固定顶点组: {pin_vertex_group}" if pin_vertex_group else "无固定顶点组"
            
            text_content = self.create_text_content(
                f"已为对象 '{object_name}' 添加软体物理{bake_info}\n"
                f"预设: {preset}\n"
                f"质量: {sb.mass}\n"
                f"目标强度: {sb.goal_spring}, 目标摩擦力: {sb.goal_friction}\n"
                f"边缘刚度: {sb.edge_stiffness}, 阻尼: {sb.edge_damp}\n"
                f"帧范围: {frame_start} - {frame_end}\n"
                f"{collision_info}\n"
                f"{pin_info}\n"
                f"自碰撞: {'启用' if sb.use_self_collision else '禁用'}"
            )
            
        except Exception as e:
            text_content = self.create_text_content(f"设置软体物理时出错: {str(e)}")
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
register_tool(SimulateSoftBodyPhysicsHandler())
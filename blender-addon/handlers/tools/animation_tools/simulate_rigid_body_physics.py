"""
模拟刚体物理的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.SimulateRigidBodyPhysics")

class SimulateRigidBodyPhysicsHandler(BaseToolHandler):
    """模拟刚体物理工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_simulate_rigid_body_physics"
        
    @property
    def description(self) -> Optional[str]:
        return "为对象添加并配置刚体物理模拟"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object_names": {
                    "type": "array",
                    "title": "对象名称",
                    "description": "要添加刚体物理的对象名称列表",
                    "items": {
                        "type": "string"
                    }
                },
                "body_type": {
                    "type": "string",
                    "title": "刚体类型",
                    "description": "刚体的类型",
                    "enum": ["ACTIVE", "PASSIVE"],
                    "default": "ACTIVE"
                },
                "shape": {
                    "type": "string",
                    "title": "碰撞形状",
                    "description": "刚体的碰撞形状",
                    "enum": ["BOX", "SPHERE", "CAPSULE", "CYLINDER", "CONE", "CONVEX_HULL", "MESH"],
                    "default": "CONVEX_HULL"
                },
                "mass": {
                    "type": "number",
                    "title": "质量",
                    "description": "刚体的质量",
                    "minimum": 0.001,
                    "default": 1.0
                },
                "friction": {
                    "type": "number",
                    "title": "摩擦力",
                    "description": "表面摩擦力",
                    "minimum": 0,
                    "maximum": 1,
                    "default": 0.5
                },
                "restitution": {
                    "type": "number",
                    "title": "弹性",
                    "description": "碰撞弹性（反弹度）",
                    "minimum": 0,
                    "maximum": 1,
                    "default": 0
                },
                "use_deform": {
                    "type": "boolean",
                    "title": "允许变形",
                    "description": "是否允许网格在模拟中变形",
                    "default": False
                },
                "linear_damping": {
                    "type": "number",
                    "title": "线性阻尼",
                    "description": "线性速度阻尼",
                    "minimum": 0,
                    "maximum": 1,
                    "default": 0.04
                },
                "angular_damping": {
                    "type": "number",
                    "title": "角度阻尼",
                    "description": "角速度阻尼",
                    "minimum": 0,
                    "maximum": 1,
                    "default": 0.1
                },
                "enable_collision": {
                    "type": "boolean",
                    "title": "启用碰撞",
                    "description": "是否启用碰撞检测",
                    "default": True
                },
                "use_margin": {
                    "type": "boolean",
                    "title": "使用碰撞边距",
                    "description": "是否为碰撞检测使用边距",
                    "default": False
                },
                "collision_margin": {
                    "type": "number",
                    "title": "碰撞边距",
                    "description": "碰撞检测边距",
                    "minimum": 0,
                    "default": 0.04
                },
                "create_world": {
                    "type": "boolean",
                    "title": "创建物理世界",
                    "description": "是否创建刚体世界（如果不存在）",
                    "default": True
                },
                "gravity": {
                    "type": "array",
                    "title": "重力",
                    "description": "物理世界的重力向量[x, y, z]",
                    "items": {
                        "type": "number"
                    },
                    "minItems": 3,
                    "maxItems": 3,
                    "default": [0, 0, -9.81]
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
            "required": ["object_names"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查对象名称
        object_names = arguments.get("object_names")
        if not object_names:
            return "必须提供至少一个对象名称"
            
        # 检查对象是否存在
        missing_objects = [name for name in object_names if name not in bpy.data.objects]
        if missing_objects:
            return f"找不到以下对象: {', '.join(missing_objects)}"
            
        # 检查质量
        mass = arguments.get("mass", 1.0)
        if not isinstance(mass, (int, float)) or mass <= 0:
            return "质量必须是正数"
            
        # 检查摩擦力
        friction = arguments.get("friction", 0.5)
        if not isinstance(friction, (int, float)) or friction < 0 or friction > 1:
            return "摩擦力必须是0到1之间的数值"
            
        # 检查弹性
        restitution = arguments.get("restitution", 0)
        if not isinstance(restitution, (int, float)) or restitution < 0 or restitution > 1:
            return "弹性必须是0到1之间的数值"
            
        # 检查线性阻尼
        linear_damping = arguments.get("linear_damping", 0.04)
        if not isinstance(linear_damping, (int, float)) or linear_damping < 0 or linear_damping > 1:
            return "线性阻尼必须是0到1之间的数值"
            
        # 检查角度阻尼
        angular_damping = arguments.get("angular_damping", 0.1)
        if not isinstance(angular_damping, (int, float)) or angular_damping < 0 or angular_damping > 1:
            return "角度阻尼必须是0到1之间的数值"
            
        # 检查碰撞边距
        collision_margin = arguments.get("collision_margin", 0.04)
        if not isinstance(collision_margin, (int, float)) or collision_margin < 0:
            return "碰撞边距必须是非负数"
            
        # 检查重力
        gravity = arguments.get("gravity", [0, 0, -9.81])
        if not isinstance(gravity, list) or len(gravity) != 3:
            return "重力必须是包含三个数值的数组 [x, y, z]"
            
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
        """执行模拟刚体物理操作"""
        logger.info(f"模拟刚体物理，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._simulate_rigid_body_physics, arguments)
        
    def _simulate_rigid_body_physics(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中模拟刚体物理"""
        object_names = arguments.get("object_names", [])
        body_type = arguments.get("body_type", "ACTIVE")
        shape = arguments.get("shape", "CONVEX_HULL")
        mass = arguments.get("mass", 1.0)
        friction = arguments.get("friction", 0.5)
        restitution = arguments.get("restitution", 0)
        use_deform = arguments.get("use_deform", False)
        linear_damping = arguments.get("linear_damping", 0.04)
        angular_damping = arguments.get("angular_damping", 0.1)
        enable_collision = arguments.get("enable_collision", True)
        use_margin = arguments.get("use_margin", False)
        collision_margin = arguments.get("collision_margin", 0.04)
        create_world = arguments.get("create_world", True)
        gravity = arguments.get("gravity", [0, 0, -9.81])
        frame_start = arguments.get("frame_start")
        frame_end = arguments.get("frame_end")
        bake_simulation = arguments.get("bake_simulation", False)
        
        # 保存当前选择状态
        original_active = bpy.context.view_layer.objects.active
        original_selected = [o for o in bpy.context.selected_objects]
        
        try:
            # 创建刚体世界（如果需要）
            if create_world:
                # 检查是否已存在刚体世界
                if not bpy.context.scene.rigidbody_world:
                    bpy.ops.rigidbody.world_add()
                
                # 配置刚体世界
                rb_world = bpy.context.scene.rigidbody_world
                rb_world.gravity = gravity
                
                if frame_start is not None:
                    rb_world.point_cache.frame_start = frame_start
                else:
                    frame_start = rb_world.point_cache.frame_start
                    
                if frame_end is not None:
                    rb_world.point_cache.frame_end = frame_end
                else:
                    frame_end = rb_world.point_cache.frame_end
            
            # 选择并配置对象
            objects_added = []
            for obj_name in object_names:
                obj = bpy.data.objects[obj_name]
                
                # 选择对象
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                
                # 检查对象是否已有刚体设置
                has_rigid_body = hasattr(obj, "rigid_body") and obj.rigid_body is not None
                
                # 添加刚体
                if not has_rigid_body:
                    bpy.ops.rigidbody.object_add()
                
                # 配置刚体属性
                rb = obj.rigid_body
                rb.type = body_type
                rb.collision_shape = shape
                rb.mass = mass
                rb.friction = friction
                rb.restitution = restitution
                rb.use_deform = use_deform
                rb.linear_damping = linear_damping
                rb.angular_damping = angular_damping
                rb.collision_collections[0] = enable_collision
                rb.use_margin = use_margin
                rb.collision_margin = collision_margin
                
                objects_added.append(obj_name)
            
            # 如果需要烘焙模拟
            if bake_simulation and bpy.context.scene.rigidbody_world:
                rb_world = bpy.context.scene.rigidbody_world
                
                # 清除现有的烘焙
                bpy.ops.ptcache.free_bake_all()
                
                # 烘焙模拟
                override = bpy.context.copy()
                override["point_cache"] = rb_world.point_cache
                bpy.ops.ptcache.bake(override, bake=True)
                
                bake_info = "并已烘焙模拟"
            else:
                bake_info = "（未烘焙）"
            
            # 创建结果信息
            text_content = self.create_text_content(
                f"已为 {len(objects_added)} 个对象添加刚体物理{bake_info}:\n"
                f"{', '.join(objects_added)}\n"
                f"刚体类型: {body_type}, 碰撞形状: {shape}\n"
                f"质量: {mass}, 摩擦力: {friction}, 弹性: {restitution}\n"
                f"帧范围: {frame_start} - {frame_end}\n"
                f"重力: [{gravity[0]}, {gravity[1]}, {gravity[2]}]"
            )
            
        except Exception as e:
            text_content = self.create_text_content(f"设置刚体物理时出错: {str(e)}")
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
register_tool(SimulateRigidBodyPhysicsHandler())
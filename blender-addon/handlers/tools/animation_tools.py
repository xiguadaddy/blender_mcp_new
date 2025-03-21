"""
动画操作工具模块

包括动画关键帧、曲线、骨骼绑定、物理效果等功能。
"""

import bpy
from ..tool_handlers import execute_in_main_thread
from ...mcp_types import create_text_content, create_image_content
from ...logger import get_logger

# 设置日志
logger = get_logger("BlenderMCP.AnimationTools")

# ---------- 基础动画功能 ----------

def create_keyframe_animation(args):
    """创建关键帧动画"""
    logger.debug(f"创建关键帧动画: {args}")
    object_name = args.get("object_name")
    property_path = args.get("property_path")
    frame = args.get("frame")
    value = args.get("value")

    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"找不到对象: {object_name}"}

            # 插入关键帧
            obj.keyframe_insert(data_path=property_path, frame=frame, index=-1, values=value)

            return {
                "status": "success",
                "text": f"已为对象 '{object_name}' 在第 {frame} 帧创建关键帧（属性: {property_path}）",
                "object_name": object_name,
                "property_path": property_path,
                "frame": frame
            }
        except Exception as e:
            logger.error(f"创建关键帧动画时出错: {str(e)}")
            return {"error": str(e)}

    return execute_in_main_thread(exec_func)

def clear_animation_data(args):
    """清除动画数据"""
    logger.debug(f"清除动画数据: {args}")
    object_name = args.get("object_name")

    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"找不到对象: {object_name}"}

            obj.animation_data_clear()

            return {
                "status": "success",
                "object_name": object_name
            }
        except Exception as e:
            logger.error(f"清除动画数据时出错: {str(e)}")
            return {"error": str(e)}

    return execute_in_main_thread(exec_func)

def set_keyframe_interpolation(args):
    """设置关键帧插值方式"""
    logger.debug(f"设置关键帧插值方式: {args}")
    object_name = args.get("object_name")
    property_path = args.get("property_path")
    frame = args.get("frame")
    interpolation = args.get("interpolation") # 例如 'LINEAR', 'BEZIER', 'CONSTANT'

    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"找不到对象: {object_name}"}

            action = obj.animation_data.action
            if not action:
                return {"error": f"对象没有动画数据: {object_name}"}

            fcurve = action.fcurves.find(property_path)
            if not fcurve:
                return {"error": f"找不到属性路径的动画曲线: {property_path}"}

            keyframe_points = fcurve.keyframe_points
            keyframe_point = keyframe_points.find(frame)
            if keyframe_point:
                keyframe_point.interpolation = interpolation
            else:
                return {"error": f"在帧 {frame} 找不到关键帧"}

            return {
                "status": "success",
                "object_name": object_name,
                "property_path": property_path,
                "frame": frame,
                "interpolation": interpolation
            }
        except Exception as e:
            logger.error(f"设置关键帧插值方式时出错: {str(e)}")
            return {"error": str(e)}

    return execute_in_main_thread(exec_func)

def set_frame_range(args):
    """设置和获取帧范围"""
    logger.debug(f"设置帧范围: {args}")
    start_frame = args.get("start_frame")
    end_frame = args.get("end_frame")

    def exec_func():
        try:
            scene = bpy.context.scene
            if start_frame is not None:
                scene.frame_start = start_frame
            if end_frame is not None:
                scene.frame_end = end_frame

            return {
                "status": "success",
                "start_frame": scene.frame_start,
                "end_frame": scene.frame_end
            }
        except Exception as e:
            logger.error(f"设置帧范围时出错: {str(e)}")
            return {"error": str(e)}

    return execute_in_main_thread(exec_func)

def get_frame_range(args):
    """获取帧范围"""
    logger.debug(f"获取帧范围: {args}")

    def exec_func():
        try:
            scene = bpy.context.scene
            return create_text_content(f"当前动画范围: {scene.frame_start}-{scene.frame_end}")
        except Exception as e:
            logger.error(f"获取帧范围时出错: {str(e)}")
            return {"error": str(e)}

    return execute_in_main_thread(exec_func)

# ---------- 骨骼和装备 ----------

def create_armature(args):
    """创建骨骼"""
    logger.debug(f"创建骨骼: {args}")
    armature_name = args.get("armature_name", "NewArmature")
    location = args.get("location", [0, 0, 0])

    def exec_func():
        try:
            # 创建骨架数据
            armature_data = bpy.data.armatures.new(name=armature_name + "Data")
            armature_obj = bpy.data.objects.new(armature_name, armature_data)
            bpy.context.collection.objects.link(armature_obj)
            armature_obj.location = location

            # 进入编辑模式添加骨骼
            bpy.context.view_layer.objects.active = armature_obj
            bpy.ops.object.mode_set(mode='EDIT')
            armature_edit_bones = armature_obj.data.edit_bones
            bone = armature_edit_bones.new('Bone')
            bone.head = (0, 0, 0)
            bone.tail = (0, 0, 1)

            # 退出编辑模式
            bpy.ops.object.mode_set(mode='OBJECT')

            return {
                "status": "success",
                "armature_name": armature_name,
                "location": list(armature_obj.location)
            }
        except Exception as e:
            logger.error(f"创建骨骼时出错: {str(e)}")
            return {"error": str(e)}

    return execute_in_main_thread(exec_func)

def create_rig(args):
    """创建装备 (简易方法，可以扩展为更复杂的自动绑定)"""
    # 简易方法可以是指添加一个骨架并将其父级设置为物体，或者使用更高级的自动绑定脚本
    logger.debug(f"创建装备: {args}")
    armature_name = args.get("armature_name")
    object_name = args.get("object_name")

    def exec_func():
        try:
            arm_obj = bpy.data.objects.get(armature_name)
            obj = bpy.data.objects.get(object_name)

            if not arm_obj:
                return {"error": f"找不到骨架: {armature_name}"}
            if not obj:
                return {"error": f"找不到对象: {object_name}"}

            # 设置父级关系为骨骼形变
            obj.parent = arm_obj
            obj.parent_type = 'ARMATURE_DEFORM'

            return {
                "status": "success",
                "armature_name": armature_name,
                "object_name": object_name
            }
        except Exception as e:
            logger.error(f"创建装备时出错: {str(e)}")
            return {"error": str(e)}

    return execute_in_main_thread(exec_func)

def add_ik_constraint(args):
    """添加IK约束"""
    logger.debug(f"添加IK约束: {args}")
    bone_name = args.get("bone_name")
    target_object_name = args.get("target_object_name")
    chain_count = args.get("chain_count", 0)

    def exec_func():
        try:
            arm_obj = bpy.context.object
            if arm_obj.type != 'ARMATURE' or bpy.context.mode != 'POSE':
                return {"error": "请在姿态模式下选择骨架"}

            pose_bone = arm_obj.pose.bones.get(bone_name)
            if not pose_bone:
                return {"error": f"找不到姿态骨骼: {bone_name}"}

            target_obj = bpy.data.objects.get(target_object_name)
            if not target_obj:
                return {"error": f"找不到目标对象: {target_object_name}"}

            ik_constraint = pose_bone.constraints.new('IK')
            ik_constraint.target = target_obj
            ik_constraint.chain_count = chain_count

            return {
                "status": "success",
                "bone_name": bone_name,
                "target_object_name": target_object_name,
                "chain_count": chain_count
            }
        except Exception as e:
            logger.error(f"添加IK约束时出错: {str(e)}")
            return {"error": str(e)}

    return execute_in_main_thread(exec_func)

def set_pose_library(args):
    """设置姿态库 (占位符，具体实现姿态库操作会更复杂)"""
    logger.debug(f"设置姿态库: {args}")
    library_name = args.get("library_name")

    def exec_func():
        try:
            # 姿态库的设置和应用通常涉及更复杂的用户交互和文件处理
            # 这里可以是一个占位符，返回成功状态
            return {
                "status": "success",
                "message": "姿态库功能待完善，当前为占位符",
                "library_name": library_name
            }
        except Exception as e:
            logger.error(f"设置姿态库时出错: {str(e)}")
            return {"error": str(e)}

    return execute_in_main_thread(exec_func)

# ---------- 运动路径 ----------

def create_motion_path(args):
    """创建运动路径"""
    logger.debug(f"创建运动路径: {args}")
    object_name = args.get("object_name")

    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"找不到对象: {object_name}"}

            bpy.ops.object.paths_calculate(object=object_name)

            return {
                "status": "success",
                "object_name": object_name
            }
        except Exception as e:
            logger.error(f"创建运动路径时出错: {str(e)}")
            return {"error": str(e)}

    return execute_in_main_thread(exec_func)

def set_object_follow_path(args):
    """设置物体跟随路径 (使用约束)"""
    logger.debug(f"设置物体跟随路径: {args}")
    object_name = args.get("object_name")
    curve_object_name = args.get("curve_object_name")

    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            curve_obj = bpy.data.objects.get(curve_object_name)

            if not obj:
                return {"error": f"找不到对象: {object_name}"}
            if not curve_obj:
                return {"error": f"找不到曲线对象: {curve_object_name}"}

            # 添加“路径跟随”约束
            follow_path_constraint = obj.constraints.new('FOLLOW_PATH')
            follow_path_constraint.target = curve_obj
            follow_path_constraint.use_fixed_location = True # 默认启用固定位置，可以根据需要调整参数

            return {
                "status": "success",
                "object_name": object_name,
                "curve_object_name": curve_object_name
            }
        except Exception as e:
            logger.error(f"设置物体跟随路径时出错: {str(e)}")
            return {"error": str(e)}

    return execute_in_main_thread(exec_func)

# ---------- 物理动画 ----------

def simulate_cloth_physics(args):
    """布料模拟 (简易方法，直接添加布料修改器)"""
    logger.debug(f"布料模拟: {args}")
    object_name = args.get("object_name")
    settings = args.get("settings", {})

    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"找不到对象: {object_name}"}

            # 添加布料修改器
            cloth_modifier = obj.modifiers.new(name="Cloth", type='CLOTH')

            # 应用设置参数
            cloth_settings = cloth_modifier.settings
            if "quality" in settings:
                cloth_settings.quality = settings["quality"] # 质量
            if "mass" in settings:
                cloth_settings.mass = settings["mass"] # 质量
            # ... 可以添加更多布料属性设置

            return {
                "status": "success",
                "object_name": object_name,
                "modifier_name": cloth_modifier.name
            }
        except Exception as e:
            logger.error(f"布料模拟出错: {str(e)}")
            return {"error": str(e)}

    return execute_in_main_thread(exec_func)

def simulate_rigid_body_physics(args):
    """刚体动画"""
    logger.debug(f"刚体动画: {args}")
    object_name = args.get("object_name")
    rigid_body_type = args.get("rigid_body_type", 'ACTIVE') # 'ACTIVE', 'PASSIVE', 'NONE'
    settings = args.get("settings", {})

    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"找不到对象: {object_name}"}

            bpy.ops.rigidbody.object_add(type=rigid_body_type)
            rigid_body = obj.rigid_body

            if rigid_body:
                if "mass" in settings:
                    rigid_body.mass = settings["mass"]
                if "friction" in settings:
                    rigid_body.friction = settings["friction"]
                if "restitution" in settings:
                    rigid_body.restitution = settings["restitution"]
                # ... 更多刚体属性

            return {
                "status": "success",
                "object_name": object_name,
                "rigid_body_type": rigid_body_type
            }
        except Exception as e:
            logger.error(f"刚体动画出错: {str(e)}")
            return {"error": str(e)}

    return execute_in_main_thread(exec_func)

def simulate_soft_body_physics(args):
    """柔体动画 (简易方法，直接添加柔体修改器)"""
    logger.debug(f"柔体动画: {args}")
    object_name = args.get("object_name")
    settings = args.get("settings", {})

    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"找不到对象: {object_name}"}

            # 添加柔体修改器
            soft_body_modifier = obj.modifiers.new(name="SoftBody", type='SOFT_BODY')

            # 应用设置参数
            soft_body_settings = soft_body_modifier.settings
            if "mass" in settings:
                soft_body_settings.mass = settings["mass"]
            if "friction" in settings:
                soft_body_settings.friction = settings["friction"]
            # ... 更多柔体属性

            return {
                "status": "success",
                "object_name": object_name,
                "modifier_name": soft_body_modifier.name
            }
        except Exception as e:
            logger.error(f"柔体动画出错: {str(e)}")
            return {"error": str(e)}

    return execute_in_main_thread(exec_func)

# ---------- 特殊动画功能 ----------

def create_shape_key_animation(args):
    """形态键动画 (基础功能，可以扩展为更精细的控制)"""
    logger.debug(f"形态键动画: {args}")
    object_name = args.get("object_name")
    shape_key_name = args.get("shape_key_name")
    frame = args.get("frame")
    value = args.get("value") # 形态键的值 (0.0 to 1.0)

    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj or obj.type != 'MESH':
                return {"error": f"找不到网格对象: {object_name}"}

            # 确保对象有形态键
            if not obj.data.shape_keys:
                obj.shape_key_add(name='Basis') # 添加基础形态键
            shape_key = obj.data.shape_keys.key_blocks.get(shape_key_name)
            if not shape_key:
                # 如果形态键不存在，则添加
                shape_key = obj.shape_key_add(name=shape_key_name)

            # 设置关键帧
            shape_key.value = value
            shape_key.keyframe_insert("value", frame=frame)

            return {
                "status": "success",
                "object_name": object_name,
                "shape_key_name": shape_key_name,
                "frame": frame,
                "value": value
            }
        except Exception as e:
            logger.error(f"形态键动画出错: {str(e)}")
            return {"error": str(e)}

    return execute_in_main_thread(exec_func)

def create_sound_driven_animation(args):
    """声音驱动动画 (占位符, 声音驱动动画通常需要更复杂的设置)"""
    logger.debug(f"声音驱动动画: {args}")
    object_name = args.get("object_name")
    sound_file_path = args.get("sound_file_path")
    property_path = args.get("property_path") #  例如 "location.z"

    def exec_func():
        try:
            # 声音驱动动画的设置较为复杂，通常涉及驱动器和音频频谱
            # 这里可以是一个占位符，返回成功状态
            return {
                "status": "success",
                "message": "声音驱动动画功能待完善，当前为占位符",
                "object_name": object_name,
                "sound_file_path": sound_file_path,
                "property_path": property_path
            }
        except Exception as e:
            logger.error(f"声音驱动动画出错: {str(e)}")
            return {"error": str(e)}

    return execute_in_main_thread(exec_func)

# ---------- NLA 编辑器控制 ----------

def control_nla_editor(args):
    """NLA编辑器控制 (占位符, NLA编辑器的控制涉及复杂的strip操作)"""
    logger.debug(f"NLA编辑器控制: {args}")
    action = args.get("action") # 例如 "CREATE_STRIP", "DELETE_STRIP", "MOVE_STRIP"
    strip_name = args.get("strip_name")
    track_index = args.get("track_index")

    def exec_func():
        try:
            # NLA编辑器的控制通常需要更精细的操作
            # 这里可以是一个占位符，返回成功状态
            return {
                "status": "success",
                "message": "NLA编辑器控制功能待完善，当前为占位符",
                "action": action,
                "strip_name": strip_name,
                "track_index": track_index
            }
        except Exception as e:
            logger.error(f"NLA编辑器控制出错: {str(e)}")
            return {"error": str(e)}

    return execute_in_main_thread(exec_func)


# 注册工具
TOOLS = {
    # 基础功能
    "create_keyframe_animation": create_keyframe_animation,
    "clear_animation_data": clear_animation_data,
    "set_keyframe_interpolation": set_keyframe_interpolation,
    "set_frame_range": set_frame_range,
    "get_frame_range": get_frame_range,

    # 骨骼和装备
    "create_armature": create_armature,
    "create_rig": create_rig,
    "add_ik_constraint": add_ik_constraint,
    "set_pose_library": set_pose_library, # 占位符

    # 运动路径
    "create_motion_path": create_motion_path,
    "set_object_follow_path": set_object_follow_path,

    # 物理动画
    "simulate_cloth_physics": simulate_cloth_physics,
    "simulate_rigid_body_physics": simulate_rigid_body_physics,
    "simulate_soft_body_physics": simulate_soft_body_physics,

    # 特殊动画功能
    "create_shape_key_animation": create_shape_key_animation,
    "create_sound_driven_animation": create_sound_driven_animation, # 占位符

    # NLA编辑器控制
    "control_nla_editor": control_nla_editor, # 占位符
}

"""
创建预设绑定的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.CreateRig")

class CreateRigHandler(BaseToolHandler):
    """创建绑定工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_create_rig"
        
    @property
    def description(self) -> Optional[str]:
        return "创建常见类型的预设骨架绑定(rig)"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "rig_type": {
                    "type": "string",
                    "title": "绑定类型",
                    "description": "要创建的绑定类型",
                    "enum": ["HUMAN", "QUADRUPED", "SIMPLE", "CUSTOM"],
                    "default": "HUMAN"
                },
                "name": {
                    "type": "string",
                    "title": "绑定名称",
                    "description": "绑定的名称",
                    "default": "Rig"
                },
                "location": {
                    "type": "array",
                    "title": "位置",
                    "description": "绑定的位置 [x, y, z]",
                    "items": {
                        "type": "number"
                    },
                    "minItems": 3,
                    "maxItems": 3,
                    "default": [0, 0, 0]
                },
                "scale": {
                    "type": "number",
                    "title": "缩放",
                    "description": "绑定的缩放系数",
                    "minimum": 0.001,
                    "default": 1.0
                },
                "use_meta_rig": {
                    "type": "boolean",
                    "title": "使用元绑定",
                    "description": "是否使用Blender的Rigify扩展创建可自定义的元绑定",
                    "default": True
                },
                "generate": {
                    "type": "boolean",
                    "title": "生成控制器",
                    "description": "是否立即生成控制器（仅当use_meta_rig为true时有效）",
                    "default": False
                }
            },
            "required": ["rig_type"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查绑定类型
        rig_type = arguments.get("rig_type")
        valid_types = ["HUMAN", "QUADRUPED", "SIMPLE", "CUSTOM"]
        if rig_type not in valid_types:
            return f"无效的绑定类型，有效类型: {', '.join(valid_types)}"
            
        # 检查名称
        name = arguments.get("name")
        if not name:
            return "必须提供绑定名称"
            
        # 检查位置
        location = arguments.get("location")
        if location and (not isinstance(location, list) or len(location) != 3):
            return "位置必须是包含三个数字的数组 [x, y, z]"
            
        # 检查缩放
        scale = arguments.get("scale")
        if scale is not None and (not isinstance(scale, (int, float)) or scale <= 0):
            return "缩放必须是正数"
            
        # 检查是否安装了Rigify
        if arguments.get("use_meta_rig", True):
            try:
                import_result = bpy.ops.preferences.addon_find(name="rigify")
                if not hasattr(bpy.ops, "pose") or not hasattr(bpy.ops.pose, "rigify_generate"):
                    return "Rigify插件未启用，无法创建元绑定。请启用Rigify插件或将use_meta_rig设置为false"
            except:
                return "Rigify插件未安装，无法创建元绑定。请安装Rigify插件或将use_meta_rig设置为false"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行创建绑定操作"""
        logger.info(f"创建绑定，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._create_rig, arguments)
        
    def _create_rig(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中创建绑定"""
        rig_type = arguments.get("rig_type")
        name = arguments.get("name", "Rig")
        location = arguments.get("location", [0, 0, 0])
        scale = arguments.get("scale", 1.0)
        use_meta_rig = arguments.get("use_meta_rig", True)
        generate = arguments.get("generate", False)
        
        try:
            # 检查rigify是否可用
            if use_meta_rig:
                try:
                    # 确保rigify已加载
                    if not bpy.context.preferences.addons.get("rigify"):
                        raise ImportError("Rigify插件未启用")
                except Exception as e:
                    text_content = self.create_text_content(f"无法使用元绑定: {str(e)}，将创建基础骨架")
                    use_meta_rig = False
            
            # 创建适当类型的绑定
            if use_meta_rig:
                # 使用Rigify创建元绑定
                bpy.ops.object.armature_human_metarig_add()
                
                # 获取创建的元绑定对象
                meta_rig = bpy.context.active_object
                meta_rig.name = name
                meta_rig.location = location
                meta_rig.scale = [scale, scale, scale]
                
                # 如果需要立即生成控制器
                if generate:
                    # 选择元绑定
                    bpy.ops.object.mode_set(mode='OBJECT')
                    bpy.ops.object.select_all(action='DESELECT')
                    meta_rig.select_set(True)
                    bpy.context.view_layer.objects.active = meta_rig
                    
                    # 生成控制器
                    bpy.ops.pose.rigify_generate()
                    
                    # 获取生成的控制器
                    generated_rig = bpy.context.active_object
                    generated_rig.name = f"{name}_generated"
                    
                    text_content = self.create_text_content(
                        f"已使用Rigify创建元绑定 '{name}' 并生成控制器 '{generated_rig.name}'\n"
                        f"位置: [{location[0]}, {location[1]}, {location[2]}]\n"
                        f"缩放: {scale}"
                    )
                else:
                    text_content = self.create_text_content(
                        f"已使用Rigify创建元绑定 '{name}'\n"
                        f"位置: [{location[0]}, {location[1]}, {location[2]}]\n"
                        f"缩放: {scale}\n"
                        f"提示: 您可以在姿态模式下使用 'Rigify 生成' 按钮生成控制器"
                    )
            else:
                # 创建基本骨架
                if rig_type == "HUMAN":
                    # 创建基本人形骨架
                    self._create_human_armature(name, location, scale)
                elif rig_type == "QUADRUPED":
                    # 创建四足动物骨架
                    self._create_quadruped_armature(name, location, scale)
                elif rig_type == "SIMPLE":
                    # 创建简单骨架
                    self._create_simple_armature(name, location, scale)
                else:  # CUSTOM
                    # 创建自定义骨架（由用户后续编辑）
                    armature_data = bpy.data.armatures.new(name)
                    armature_obj = bpy.data.objects.new(name, armature_data)
                    armature_obj.location = location
                    armature_obj.scale = [scale, scale, scale]
                    bpy.context.collection.objects.link(armature_obj)
                
                text_content = self.create_text_content(
                    f"已创建 {rig_type} 类型绑定 '{name}'\n"
                    f"位置: [{location[0]}, {location[1]}, {location[2]}]\n"
                    f"缩放: {scale}"
                )
            
            return self.create_result([text_content])
            
        except Exception as e:
            text_content = self.create_text_content(f"创建绑定时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
    
    def _create_human_armature(self, name: str, location: List[float], scale: float) -> None:
        """创建基本人形骨架"""
        # 创建骨架数据
        armature_data = bpy.data.armatures.new(name)
        armature_obj = bpy.data.objects.new(name, armature_data)
        armature_obj.location = location
        armature_obj.scale = [scale, scale, scale]
        bpy.context.collection.objects.link(armature_obj)
        
        # 设置为活动对象
        bpy.context.view_layer.objects.active = armature_obj
        
        # 进入编辑模式
        bpy.ops.object.mode_set(mode='EDIT')
        
        # 创建骨骼
        bones_data = [
            # 躯干
            {"name": "spine", "head": [0, 0, 1], "tail": [0, 0, 1.2], "parent": None},
            {"name": "spine.001", "head": [0, 0, 1.2], "tail": [0, 0, 1.4], "parent": "spine"},
            {"name": "spine.002", "head": [0, 0, 1.4], "tail": [0, 0, 1.6], "parent": "spine.001"},
            {"name": "spine.003", "head": [0, 0, 1.6], "tail": [0, 0, 1.8], "parent": "spine.002"},
            
            # 头部
            {"name": "neck", "head": [0, 0, 1.8], "tail": [0, 0, 1.9], "parent": "spine.003"},
            {"name": "head", "head": [0, 0, 1.9], "tail": [0, 0.1, 2.0], "parent": "neck"},
            
            # 左臂
            {"name": "shoulder.L", "head": [0, 0, 1.8], "tail": [0.2, 0, 1.8], "parent": "spine.003"},
            {"name": "upper_arm.L", "head": [0.2, 0, 1.8], "tail": [0.5, 0, 1.6], "parent": "shoulder.L"},
            {"name": "forearm.L", "head": [0.5, 0, 1.6], "tail": [0.8, 0, 1.4], "parent": "upper_arm.L"},
            {"name": "hand.L", "head": [0.8, 0, 1.4], "tail": [0.9, 0, 1.3], "parent": "forearm.L"},
            
            # 右臂
            {"name": "shoulder.R", "head": [0, 0, 1.8], "tail": [-0.2, 0, 1.8], "parent": "spine.003"},
            {"name": "upper_arm.R", "head": [-0.2, 0, 1.8], "tail": [-0.5, 0, 1.6], "parent": "shoulder.R"},
            {"name": "forearm.R", "head": [-0.5, 0, 1.6], "tail": [-0.8, 0, 1.4], "parent": "forearm.R"},
            {"name": "hand.R", "head": [-0.8, 0, 1.4], "tail": [-0.9, 0, 1.3], "parent": "forearm.R"},
            
            # 左腿
            {"name": "thigh.L", "head": [0.1, 0, 1], "tail": [0.1, 0, 0.5], "parent": "spine"},
            {"name": "shin.L", "head": [0.1, 0, 0.5], "tail": [0.1, 0.1, 0.1], "parent": "thigh.L"},
            {"name": "foot.L", "head": [0.1, 0.1, 0.1], "tail": [0.1, 0.3, 0], "parent": "shin.L"},
            {"name": "toe.L", "head": [0.1, 0.3, 0], "tail": [0.1, 0.4, 0], "parent": "foot.L"},
            
            # 右腿
            {"name": "thigh.R", "head": [-0.1, 0, 1], "tail": [-0.1, 0, 0.5], "parent": "spine"},
            {"name": "shin.R", "head": [-0.1, 0, 0.5], "tail": [-0.1, 0.1, 0.1], "parent": "thigh.R"},
            {"name": "foot.R", "head": [-0.1, 0.1, 0.1], "tail": [-0.1, 0.3, 0], "parent": "shin.R"},
            {"name": "toe.R", "head": [-0.1, 0.3, 0], "tail": [-0.1, 0.4, 0], "parent": "foot.R"},
        ]
        
        # 添加骨骼
        for bone_data in bones_data:
            bone = armature_data.edit_bones.new(bone_data["name"])
            bone.head = bone_data["head"]
            bone.tail = bone_data["tail"]
            
            if bone_data["parent"]:
                bone.parent = armature_data.edit_bones[bone_data["parent"]]
        
        # 返回对象模式
        bpy.ops.object.mode_set(mode='OBJECT')
    
    def _create_quadruped_armature(self, name: str, location: List[float], scale: float) -> None:
        """创建四足动物骨架"""
        # 创建骨架数据
        armature_data = bpy.data.armatures.new(name)
        armature_obj = bpy.data.objects.new(name, armature_data)
        armature_obj.location = location
        armature_obj.scale = [scale, scale, scale]
        bpy.context.collection.objects.link(armature_obj)
        
        # 设置为活动对象
        bpy.context.view_layer.objects.active = armature_obj
        
        # 进入编辑模式
        bpy.ops.object.mode_set(mode='EDIT')
        
        # 创建骨骼
        bones_data = [
            # 躯干
            {"name": "spine", "head": [0, 0, 0.5], "tail": [0, -0.3, 0.6], "parent": None},
            {"name": "spine.001", "head": [0, -0.3, 0.6], "tail": [0, -0.6, 0.7], "parent": "spine"},
            {"name": "spine.002", "head": [0, -0.6, 0.7], "tail": [0, -0.9, 0.7], "parent": "spine.001"},
            
            # 头部
            {"name": "neck", "head": [0, -0.9, 0.7], "tail": [0, -1.2, 0.8], "parent": "spine.002"},
            {"name": "head", "head": [0, -1.2, 0.8], "tail": [0, -1.4, 0.9], "parent": "neck"},
            
            # 尾巴
            {"name": "tail", "head": [0, 0.3, 0.5], "tail": [0, 0.6, 0.6], "parent": "spine"},
            {"name": "tail.001", "head": [0, 0.6, 0.6], "tail": [0, 0.9, 0.5], "parent": "tail"},
            
            # 前腿（左）
            {"name": "front_thigh.L", "head": [0.2, -0.7, 0.6], "tail": [0.3, -0.7, 0.3], "parent": "spine.002"},
            {"name": "front_shin.L", "head": [0.3, -0.7, 0.3], "tail": [0.3, -0.7, 0.1], "parent": "front_thigh.L"},
            {"name": "front_foot.L", "head": [0.3, -0.7, 0.1], "tail": [0.3, -0.8, 0], "parent": "front_shin.L"},
            
            # 前腿（右）
            {"name": "front_thigh.R", "head": [-0.2, -0.7, 0.6], "tail": [-0.3, -0.7, 0.3], "parent": "spine.002"},
            {"name": "front_shin.R", "head": [-0.3, -0.7, 0.3], "tail": [-0.3, -0.7, 0.1], "parent": "front_thigh.R"},
            {"name": "front_foot.R", "head": [-0.3, -0.7, 0.1], "tail": [-0.3, -0.8, 0], "parent": "front_shin.R"},
            
            # 后腿（左）
            {"name": "thigh.L", "head": [0.2, 0.1, 0.5], "tail": [0.3, 0.1, 0.3], "parent": "spine"},
            {"name": "shin.L", "head": [0.3, 0.1, 0.3], "tail": [0.3, 0.1, 0.1], "parent": "thigh.L"},
            {"name": "foot.L", "head": [0.3, 0.1, 0.1], "tail": [0.3, 0, 0], "parent": "shin.L"},
            
            # 后腿（右）
            {"name": "thigh.R", "head": [-0.2, 0.1, 0.5], "tail": [-0.3, 0.1, 0.3], "parent": "spine"},
            {"name": "shin.R", "head": [-0.3, 0.1, 0.3], "tail": [-0.3, 0.1, 0.1], "parent": "thigh.R"},
            {"name": "foot.R", "head": [-0.3, 0.1, 0.1], "tail": [-0.3, 0, 0], "parent": "shin.R"},
        ]
        
        # 添加骨骼
        for bone_data in bones_data:
            bone = armature_data.edit_bones.new(bone_data["name"])
            bone.head = bone_data["head"]
            bone.tail = bone_data["tail"]
            
            if bone_data["parent"]:
                bone.parent = armature_data.edit_bones[bone_data["parent"]]
        
        # 返回对象模式
        bpy.ops.object.mode_set(mode='OBJECT')
    
    def _create_simple_armature(self, name: str, location: List[float], scale: float) -> None:
        """创建简单骨架"""
        # 创建骨架数据
        armature_data = bpy.data.armatures.new(name)
        armature_obj = bpy.data.objects.new(name, armature_data)
        armature_obj.location = location
        armature_obj.scale = [scale, scale, scale]
        bpy.context.collection.objects.link(armature_obj)
        
        # 设置为活动对象
        bpy.context.view_layer.objects.active = armature_obj
        
        # 进入编辑模式
        bpy.ops.object.mode_set(mode='EDIT')
        
        # 创建骨骼
        bones_data = [
            # 主要骨骼
            {"name": "root", "head": [0, 0, 0], "tail": [0, 0, 0.5], "parent": None},
            {"name": "spine", "head": [0, 0, 0.5], "tail": [0, 0, 1.0], "parent": "root"},
            {"name": "spine.001", "head": [0, 0, 1.0], "tail": [0, 0, 1.5], "parent": "spine"},
            {"name": "head", "head": [0, 0, 1.5], "tail": [0, 0.2, 1.7], "parent": "spine.001"},
            
            # 左臂
            {"name": "arm.L", "head": [0.2, 0, 1.5], "tail": [0.5, 0, 1.3], "parent": "spine.001"},
            {"name": "forearm.L", "head": [0.5, 0, 1.3], "tail": [0.8, 0, 1.1], "parent": "arm.L"},
            
            # 右臂
            {"name": "arm.R", "head": [-0.2, 0, 1.5], "tail": [-0.5, 0, 1.3], "parent": "spine.001"},
            {"name": "forearm.R", "head": [-0.5, 0, 1.3], "tail": [-0.8, 0, 1.1], "parent": "arm.R"},
            
            # 左腿
            {"name": "leg.L", "head": [0.1, 0, 0.5], "tail": [0.1, 0, 0.2], "parent": "root"},
            {"name": "foot.L", "head": [0.1, 0, 0.2], "tail": [0.1, 0.2, 0], "parent": "leg.L"},
            
            # 右腿
            {"name": "leg.R", "head": [-0.1, 0, 0.5], "tail": [-0.1, 0, 0.2], "parent": "root"},
            {"name": "foot.R", "head": [-0.1, 0, 0.2], "tail": [-0.1, 0.2, 0], "parent": "leg.R"},
        ]
        
        # 添加骨骼
        for bone_data in bones_data:
            bone = armature_data.edit_bones.new(bone_data["name"])
            bone.head = bone_data["head"]
            bone.tail = bone_data["tail"]
            
            if bone_data["parent"]:
                bone.parent = armature_data.edit_bones[bone_data["parent"]]
        
        # 返回对象模式
        bpy.ops.object.mode_set(mode='OBJECT')


# 在导入时自动注册工具实例
register_tool(CreateRigHandler())
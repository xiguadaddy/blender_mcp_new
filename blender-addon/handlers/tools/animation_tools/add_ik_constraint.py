"""
为骨骼添加IK约束的工具
"""

import bpy
import json
import mathutils
from bpy import context
import logging
from typing import Any, Dict, List, Optional

from ..registry import register_tool
from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.AddIKConstraint")

class AddIKConstraintHandler(BaseToolHandler):
    """添加IK约束工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_add_ik_constraint"
        
    @property
    def description(self) -> Optional[str]:
        return "为骨架中的骨骼添加反向动力学(IK)约束"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "armature_name": {
                    "type": "string",
                    "title": "骨架名称",
                    "description": "骨架对象的名称"
                },
                "bone_name": {
                    "type": "string",
                    "title": "骨骼名称",
                    "description": "要添加IK约束的骨骼名称"
                },
                "target_name": {
                    "type": "string",
                    "title": "目标名称",
                    "description": "IK约束的目标对象名称（如果为空则创建一个新的空对象作为目标）"
                },
                "target_bone": {
                    "type": "string",
                    "title": "目标骨骼",
                    "description": "目标对象上的骨骼名称（如果目标是骨架）"
                },
                "chain_length": {
                    "type": "integer",
                    "title": "链长度",
                    "description": "IK链的长度（骨骼数量）",
                    "default": 2
                },
                "iterations": {
                    "type": "integer",
                    "title": "迭代次数",
                    "description": "IK求解的迭代次数",
                    "default": 10
                },
                "pole_target_name": {
                    "type": "string",
                    "title": "极点目标名称",
                    "description": "IK约束的极点目标对象名称（如果为空则不使用极点目标）"
                },
                "pole_subtarget": {
                    "type": "string",
                    "title": "极点子目标",
                    "description": "极点目标对象上的骨骼名称（如果极点目标是骨架）"
                },
                "pole_angle": {
                    "type": "number",
                    "title": "极点角度",
                    "description": "极点角度（弧度）",
                    "default": 0.0
                },
                "weight": {
                    "type": "number",
                    "title": "权重",
                    "description": "IK约束的影响权重",
                    "minimum": 0,
                    "maximum": 1,
                    "default": 1.0
                },
                "use_tail": {
                    "type": "boolean",
                    "title": "使用尾部",
                    "description": "是否使用骨骼的尾部作为IK目标",
                    "default": False
                },
                "create_target_at_bone": {
                    "type": "boolean",
                    "title": "在骨骼位置创建目标",
                    "description": "是否在骨骼的位置创建IK目标",
                    "default": True
                }
            },
            "required": ["armature_name", "bone_name"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查骨架名称
        armature_name = arguments.get("armature_name")
        if not armature_name:
            return "必须提供骨架名称"
            
        # 检查骨架是否存在
        if armature_name not in bpy.data.objects:
            return f"找不到骨架对象: {armature_name}"
            
        # 检查对象是否是骨架
        armature_obj = bpy.data.objects[armature_name]
        if armature_obj.type != 'ARMATURE':
            return f"对象 '{armature_name}' 不是骨架"
            
        # 检查骨骼名称
        bone_name = arguments.get("bone_name")
        if not bone_name:
            return "必须提供骨骼名称"
            
        # 检查骨骼是否存在
        if armature_obj.pose.bones and bone_name not in armature_obj.pose.bones:
            return f"在骨架 '{armature_name}' 中找不到骨骼: {bone_name}"
            
        # 检查目标（如果提供）
        target_name = arguments.get("target_name")
        if target_name and target_name not in bpy.data.objects:
            return f"找不到目标对象: {target_name}"
            
        # 检查目标骨骼（如果提供）
        target_bone = arguments.get("target_bone")
        if target_name and target_bone:
            target_obj = bpy.data.objects[target_name]
            if target_obj.type == 'ARMATURE' and target_bone not in target_obj.pose.bones:
                return f"在目标骨架 '{target_name}' 中找不到骨骼: {target_bone}"
                
        # 检查极点目标（如果提供）
        pole_target_name = arguments.get("pole_target_name")
        if pole_target_name and pole_target_name not in bpy.data.objects:
            return f"找不到极点目标对象: {pole_target_name}"
            
        # 检查极点子目标（如果提供）
        pole_subtarget = arguments.get("pole_subtarget")
        if pole_target_name and pole_subtarget:
            pole_target_obj = bpy.data.objects[pole_target_name]
            if pole_target_obj.type == 'ARMATURE' and pole_subtarget not in pole_target_obj.pose.bones:
                return f"在极点目标骨架 '{pole_target_name}' 中找不到骨骼: {pole_subtarget}"
                
        # 检查链长度
        chain_length = arguments.get("chain_length", 2)
        if not isinstance(chain_length, int) or chain_length < 1:
            return "链长度必须是大于或等于1的整数"
            
        # 检查迭代次数
        iterations = arguments.get("iterations", 10)
        if not isinstance(iterations, int) or iterations < 1:
            return "迭代次数必须是大于或等于1的整数"
            
        # 检查权重
        weight = arguments.get("weight", 1.0)
        if not isinstance(weight, (int, float)) or weight < 0 or weight > 1:
            return "权重必须是0到1之间的数值"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行添加IK约束操作"""
        logger.info(f"添加IK约束，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._add_ik_constraint, arguments)
        
    def _add_ik_constraint(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中添加IK约束"""
        armature_name = arguments.get("armature_name")
        bone_name = arguments.get("bone_name")
        target_name = arguments.get("target_name")
        target_bone = arguments.get("target_bone")
        chain_length = arguments.get("chain_length", 2)
        iterations = arguments.get("iterations", 10)
        pole_target_name = arguments.get("pole_target_name")
        pole_subtarget = arguments.get("pole_subtarget")
        pole_angle = arguments.get("pole_angle", 0.0)
        weight = arguments.get("weight", 1.0)
        use_tail = arguments.get("use_tail", False)
        create_target_at_bone = arguments.get("create_target_at_bone", True)
        
        try:
            # 获取骨架和骨骼
            armature_obj = bpy.data.objects[armature_name]
            pose_bone = armature_obj.pose.bones[bone_name]
            
            # 获取或创建目标对象
            if not target_name:
                # 创建一个空对象作为目标
                target_obj = bpy.data.objects.new(f"{bone_name}_IK_Target", None)
                bpy.context.collection.objects.link(target_obj)
                
                # 设置目标位置
                if create_target_at_bone:
                    # 计算骨骼的世界空间位置
                    if use_tail:
                        # 使用骨骼的尾部位置
                        bone_pos = armature_obj.matrix_world @ armature_obj.data.bones[bone_name].tail_local
                    else:
                        # 使用骨骼的头部位置
                        bone_pos = armature_obj.matrix_world @ armature_obj.data.bones[bone_name].head_local
                        
                    target_obj.location = bone_pos
            else:
                # 使用指定的目标对象
                target_obj = bpy.data.objects[target_name]
            
            # 获取极点目标对象（如果提供）
            pole_target_obj = None
            if pole_target_name:
                pole_target_obj = bpy.data.objects[pole_target_name]
            
            # 添加IK约束
            ik_constraint = pose_bone.constraints.new('IK')
            ik_constraint.name = f"{bone_name}_IK"
            ik_constraint.target = target_obj
            ik_constraint.subtarget = target_bone if target_bone else ""
            ik_constraint.chain_count = chain_length
            ik_constraint.iterations = iterations
            ik_constraint.use_tail = use_tail
            ik_constraint.weight = weight
            
            # 设置极点目标
            if pole_target_obj:
                ik_constraint.pole_target = pole_target_obj
                ik_constraint.pole_subtarget = pole_subtarget if pole_subtarget else ""
                ik_constraint.pole_angle = pole_angle
            
            # 创建结果信息
            target_info = f"目标: {target_obj.name}" + (f", 骨骼: {target_bone}" if target_bone else "")
            pole_info = f", 极点目标: {pole_target_obj.name}" if pole_target_obj else ""
            
            text_content = self.create_text_content(
                f"已为骨架 '{armature_name}' 的骨骼 '{bone_name}' 添加IK约束\n"
                f"{target_info}{pole_info}\n"
                f"链长度: {chain_length}, 迭代次数: {iterations}"
            )
                
        except Exception as e:
            text_content = self.create_text_content(f"添加IK约束时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(AddIKConstraintHandler())
"""
创建Blender骨架的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional, Tuple

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.CreateArmature")

class CreateArmatureHandler(BaseToolHandler):
    """创建骨架工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_create_armature"
        
    @property
    def description(self) -> Optional[str]:
        return "创建骨架对象和骨骼"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "title": "骨架名称",
                    "description": "新骨架的名称",
                    "default": "Armature"
                },
                "bones": {
                    "type": "array",
                    "title": "骨骼",
                    "description": "要创建的骨骼列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "title": "骨骼名称",
                                "description": "骨骼的名称"
                            },
                            "head": {
                                "type": "array",
                                "title": "骨骼头部",
                                "description": "骨骼头部的位置[x, y, z]",
                                "items": {
                                    "type": "number"
                                },
                                "minItems": 3,
                                "maxItems": 3
                            },
                            "tail": {
                                "type": "array",
                                "title": "骨骼尾部",
                                "description": "骨骼尾部的位置[x, y, z]",
                                "items": {
                                    "type": "number"
                                },
                                "minItems": 3,
                                "maxItems": 3
                            },
                            "parent": {
                                "type": "string",
                                "title": "父骨骼",
                                "description": "父骨骼的名称（如果有）"
                            },
                            "connect": {
                                "type": "boolean",
                                "title": "连接到父骨骼",
                                "description": "是否连接到父骨骼的尾部",
                                "default": False
                            }
                        },
                        "required": ["name", "head", "tail"]
                    }
                },
                "location": {
                    "type": "array",
                    "title": "位置",
                    "description": "骨架对象的位置[x, y, z]",
                    "items": {
                        "type": "number"
                    },
                    "minItems": 3,
                    "maxItems": 3,
                    "default": [0, 0, 0]
                },
                "show_in_front": {
                    "type": "boolean",
                    "title": "显示在前面",
                    "description": "是否在3D视图中始终将骨架显示在几何体前面",
                    "default": True
                },
                "enter_edit_mode": {
                    "type": "boolean",
                    "title": "进入编辑模式",
                    "description": "创建后是否立即进入编辑模式",
                    "default": False
                }
            },
            "required": ["name"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查骨架名称
        name = arguments.get("name")
        if not name:
            return "必须提供骨架名称"
            
        # 检查骨骼列表
        bones = arguments.get("bones", [])
        if bones:
            # 检查每个骨骼
            bone_names = set()
            for i, bone in enumerate(bones):
                # 检查必填字段
                if not bone.get("name"):
                    return f"第 {i+1} 个骨骼必须有名称"
                    
                # 检查骨骼名称是否重复
                if bone.get("name") in bone_names:
                    return f"骨骼名称 '{bone.get('name')}' 重复"
                bone_names.add(bone.get("name"))
                
                # 检查头部和尾部坐标
                head = bone.get("head")
                if not head or not isinstance(head, list) or len(head) != 3:
                    return f"骨骼 '{bone.get('name')}' 必须有正确的头部坐标 [x, y, z]"
                
                tail = bone.get("tail")
                if not tail or not isinstance(tail, list) or len(tail) != 3:
                    return f"骨骼 '{bone.get('name')}' 必须有正确的尾部坐标 [x, y, z]"
                
                # 检查父骨骼名称是否存在于之前定义的骨骼中
                parent = bone.get("parent")
                if parent and parent not in bone_names:
                    return f"骨骼 '{bone.get('name')}' 的父骨骼 '{parent}' 不存在或在该骨骼之后定义"
        
        # 检查位置
        location = arguments.get("location")
        if location and (not isinstance(location, list) or len(location) != 3):
            return "位置必须是包含三个数字的数组 [x, y, z]"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行创建骨架操作"""
        logger.info(f"创建骨架，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._create_armature, arguments)
        
    def _create_armature(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中创建骨架"""
        name = arguments.get("name", "Armature")
        bones_data = arguments.get("bones", [])
        location = arguments.get("location", [0, 0, 0])
        show_in_front = arguments.get("show_in_front", True)
        enter_edit_mode = arguments.get("enter_edit_mode", False)
        
        try:
            # 创建骨架数据
            armature_data = bpy.data.armatures.new(name)
            
            # 创建骨架对象
            armature_obj = bpy.data.objects.new(name, armature_data)
            
            # 设置位置
            armature_obj.location = location
            
            # 设置显示选项
            armature_obj.show_in_front = show_in_front
            
            # 添加到当前集合
            bpy.context.collection.objects.link(armature_obj)
            
            # 设置为活动对象
            bpy.context.view_layer.objects.active = armature_obj
            
            # 进入编辑模式添加骨骼
            bpy.ops.object.mode_set(mode='EDIT')
            
            # 跟踪创建的骨骼
            created_bones = []
            connected_parents = []
            
            # 添加骨骼
            for bone_data in bones_data:
                bone_name = bone_data.get("name")
                head = bone_data.get("head")
                tail = bone_data.get("tail")
                parent = bone_data.get("parent")
                connect = bone_data.get("connect", False)
                
                # 创建新骨骼
                bone = armature_data.edit_bones.new(bone_name)
                bone.head = head
                bone.tail = tail
                
                # 如果指定了父骨骼，设置父子关系
                if parent:
                    bone.parent = armature_data.edit_bones[parent]
                    
                    # 如果需要连接到父骨骼，记录下来
                    if connect:
                        connected_parents.append((bone_name, parent))
                
                created_bones.append(bone_name)
            
            # 处理连接的骨骼
            for child, parent in connected_parents:
                # 连接到父骨骼
                armature_data.edit_bones[child].use_connect = True
            
            # 返回到对象模式
            if not enter_edit_mode:
                bpy.ops.object.mode_set(mode='OBJECT')
            
            # 创建结果信息
            if created_bones:
                text_content = self.create_text_content(
                    f"已创建骨架 '{name}' 并添加了 {len(created_bones)} 个骨骼:\n"
                    f"{', '.join(created_bones)}"
                )
            else:
                text_content = self.create_text_content(f"已创建骨架 '{name}' （没有添加骨骼）")
                
        except Exception as e:
            text_content = self.create_text_content(f"创建骨架时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(CreateArmatureHandler())
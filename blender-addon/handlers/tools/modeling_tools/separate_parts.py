"""
分离Blender对象的工具
"""

import bpy
from ..registry import register_tool
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.SeparateParts")

class SeparatePartsHandler(BaseToolHandler):
    """分离对象工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_separate_parts"
        
    @property
    def description(self) -> Optional[str]:
        return "将3D对象分离为多个部分"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "要分离的对象名称"
                },
                "method": {
                    "type": "string",
                    "title": "分离方法",
                    "description": "分离对象的方法",
                    "enum": ["LOOSE", "MATERIAL", "SELECTED"],
                    "default": "LOOSE"
                },
                "prefix": {
                    "type": "string",
                    "title": "名称前缀",
                    "description": "分离后的对象名称前缀（可选）"
                }
            },
            "required": ["object_name"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查对象名称
        if not arguments.get("object_name"):
            return "必须提供对象名称"
            
        # 检查分离方法
        method = arguments.get("method", "LOOSE")
        valid_methods = ["LOOSE", "MATERIAL", "SELECTED"]
        if method not in valid_methods:
            return f"不支持的分离方法: {method}，有效方法: {', '.join(valid_methods)}"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行分离对象操作"""
        logger.info(f"分离对象，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._separate_parts, arguments)
        
    def _separate_parts(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中分离对象"""
        object_name = arguments.get("object_name")
        method = arguments.get("method", "LOOSE")
        prefix = arguments.get("prefix", "")
        
        # 检查对象是否存在
        if object_name not in bpy.data.objects:
            text_content = self.create_text_content(f"找不到对象: {object_name}")
            return self.create_result([text_content], is_error=True)
        
        # 获取对象
        obj = bpy.data.objects[object_name]
        
        # 确保对象是网格类型
        if obj.type != 'MESH':
            text_content = self.create_text_content(f"只能分离网格对象，而 '{object_name}' 是 '{obj.type}' 类型")
            return self.create_result([text_content], is_error=True)
        
        # 记录原始对象计数
        original_object_count = len(bpy.data.objects)
        
        # 确保目标对象是活动对象且处于编辑模式
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        
        # 根据方法执行不同的选择
        if method == "LOOSE":
            # 选择所有顶点
            bpy.ops.mesh.select_all(action='SELECT')
            # 分离松散部分
            bpy.ops.mesh.separate(type='LOOSE')
            
        elif method == "MATERIAL":
            # 选择所有顶点
            bpy.ops.mesh.select_all(action='SELECT')
            # 按材质分离
            bpy.ops.mesh.separate(type='MATERIAL')
            
        elif method == "SELECTED":
            # 如果是按选择分离，确保有选中的顶点
            bpy.ops.mesh.select_all(action='SELECT')
            # 按选择分离
            bpy.ops.mesh.separate(type='SELECTED')
        
        # 返回对象模式
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # 计算新创建的对象数量
        new_objects = []
        for new_obj in bpy.data.objects:
            if new_obj.name.startswith(object_name + "."):
                new_objects.append(new_obj)
                # 如果提供了前缀，重命名对象
                if prefix:
                    new_obj.name = prefix + new_obj.name.split(".", 1)[1]
        
        # 创建结果信息
        if len(new_objects) > 0:
            new_obj_names = ", ".join([obj.name for obj in new_objects])
            text_content = self.create_text_content(f"已将对象 '{object_name}' 分离为 {len(new_objects) + 1} 个部分: {object_name}, {new_obj_names}")
        else:
            text_content = self.create_text_content(f"对象 '{object_name}' 没有可分离的部分")
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(SeparatePartsHandler())
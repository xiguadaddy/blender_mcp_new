from ..registry import register_tool
import bpy
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.SetMaterial")

class SetMaterialHandler(BaseToolHandler):
    """设置材质工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_set_material"
        
    @property
    def description(self) -> Optional[str]:
        return "为对象设置或创建材质"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "要应用材质的对象名称"
                },
                "material_name": {
                    "type": "string",
                    "title": "材质名称",
                    "description": "要使用或创建的材质名称"
                },
                "color": {
                    "type": "array",
                    "title": "颜色",
                    "description": "RGBA颜色值 [r, g, b, a]",
                    "items": {
                        "type": "number"
                    }
                },
                "metallic": {
                    "type": "number",
                    "title": "金属度",
                    "description": "材质的金属度 (0-1)"
                },
                "roughness": {
                    "type": "number",
                    "title": "粗糙度",
                    "description": "材质的粗糙度 (0-1)"
                }
            },
            "required": ["object_name"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查对象名称
        object_name = arguments.get("object_name")
        if not object_name:
            return "缺少对象名称参数"
            
        # 检查颜色参数
        color = arguments.get("color")
        if color and not (isinstance(color, list) and (len(color) == 3 or len(color) == 4) and all(isinstance(c, (int, float)) for c in color)):
            return "颜色参数必须是包含3或4个数字的数组 [r, g, b] 或 [r, g, b, a]"
            
        # 检查金属度
        metallic = arguments.get("metallic")
        if metallic is not None and not (isinstance(metallic, (int, float)) and 0 <= metallic <= 1):
            return "金属度参数必须是0到1之间的数字"
            
        # 检查粗糙度
        roughness = arguments.get("roughness")
        if roughness is not None and not (isinstance(roughness, (int, float)) and 0 <= roughness <= 1):
            return "粗糙度参数必须是0到1之间的数字"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行设置材质操作"""
        logger.info(f"设置材质，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._set_material, arguments)
        
    def _set_material(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中设置材质"""
        object_name = arguments.get("object_name")
        material_name = arguments.get("material_name", f"{object_name}_材质")
        color = arguments.get("color", [0.8, 0.8, 0.8, 1.0])
        metallic = arguments.get("metallic", 0.0)
        roughness = arguments.get("roughness", 0.5)
        
        # 如果颜色只有RGB，添加Alpha通道
        if len(color) == 3:
            color.append(1.0)
            
        # 获取对象
        if object_name not in bpy.data.objects:
            error_msg = f"找不到对象: {object_name}"
            logger.error(error_msg)
            error_content = self.create_text_content(error_msg)
            return self.create_result([error_content], is_error=True)
            
        obj = bpy.data.objects[object_name]
        
        # 获取或创建材质
        if material_name in bpy.data.materials:
            mat = bpy.data.materials[material_name]
        else:
            mat = bpy.data.materials.new(name=material_name)
            
        # 确保材质使用节点
        mat.use_nodes = True
        
        # 清除所有节点
        nodes = mat.node_tree.nodes
        nodes.clear()
        
        # 创建Principled BSDF节点
        bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
        bsdf.location = (0, 0)
        
        # 创建输出节点
        output = nodes.new(type="ShaderNodeOutputMaterial")
        output.location = (300, 0)
        
        # 连接节点
        links = mat.node_tree.links
        links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
        
        # 设置材质属性
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        
        # 应用材质到对象
        if obj.data.materials:
            # 如果对象已有材质，替换第一个材质
            obj.data.materials[0] = mat
        else:
            # 否则添加新材质
            obj.data.materials.append(mat)
            
        # 创建成功响应
        text_content = self.create_text_content(f"已为对象 {object_name} 设置材质: {material_name}")
        
        # 返回结果
        return self.create_result([text_content]) 

# 在导入时自动注册工具实例
register_tool(SetMaterialHandler())
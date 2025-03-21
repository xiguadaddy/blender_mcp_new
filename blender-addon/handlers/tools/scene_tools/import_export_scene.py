"""
导入导出Blender场景或对象的工具
"""

import bpy
from ..registry import register_tool
import os
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.ImportExportScene")

class ImportSceneHandler(BaseToolHandler):
    """导入场景工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_import_scene"
        
    @property
    def description(self) -> Optional[str]:
        return "导入外部格式的3D场景或对象到Blender"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "title": "文件路径",
                    "description": "要导入的3D文件路径"
                },
                "import_type": {
                    "type": "string",
                    "title": "导入类型",
                    "description": "要导入的文件类型",
                    "enum": ["OBJ", "FBX", "GLB", "3DS", "STL", "PLY"],
                    "default": "OBJ"
                },
                "scene_name": {
                    "type": "string",
                    "title": "场景名称",
                    "description": "要导入到的场景（默认为当前活动场景）"
                },
                "scale": {
                    "type": "number",
                    "title": "缩放",
                    "description": "导入时的缩放系数",
                    "default": 1.0
                },
                "use_custom_normals": {
                    "type": "boolean",
                    "title": "使用自定义法线",
                    "description": "是否使用文件中的自定义法线",
                    "default": True
                }
            },
            "required": ["filepath"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查文件路径
        filepath = arguments.get("filepath")
        if not filepath:
            return "必须提供文件路径"
            
        # 检查文件是否存在
        if not os.path.exists(filepath):
            return f"文件不存在: {filepath}"
            
        # 检查文件扩展名与导入类型是否匹配
        import_type = arguments.get("import_type", "OBJ").lower()
        file_ext = os.path.splitext(filepath)[1].lower()[1:]  # 移除点并转为小写
        
        if file_ext != import_type.lower():
            return f"文件扩展名 '{file_ext}' 与导入类型 '{import_type}' 不匹配"
            
        # 检查场景名称（如果提供）
        scene_name = arguments.get("scene_name")
        if scene_name and scene_name not in bpy.data.scenes:
            return f"场景 '{scene_name}' 不存在"
            
        # 检查缩放
        scale = arguments.get("scale")
        if scale is not None and (not isinstance(scale, (int, float)) or scale <= 0):
            return "缩放必须是正数"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行导入场景操作"""
        logger.info(f"导入场景，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._import_scene, arguments)
        
    def _import_scene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中导入场景"""
        filepath = arguments.get("filepath")
        import_type = arguments.get("import_type", "OBJ").upper()
        scene_name = arguments.get("scene_name")
        scale = arguments.get("scale", 1.0)
        use_custom_normals = arguments.get("use_custom_normals", True)
        
        # 获取场景
        if scene_name:
            scene = bpy.data.scenes[scene_name]
        else:
            scene = bpy.context.scene
            scene_name = scene.name
        
        # 确保该场景是活动场景
        original_scene = bpy.context.scene
        bpy.context.window.scene = scene
        
        # 记录导入前的对象数量
        pre_import_objects = set(bpy.data.objects)
        
        try:
            # 根据不同的文件类型执行相应的导入操作
            if import_type == "OBJ":
                bpy.ops.import_scene.obj(
                    filepath=filepath,
                    axis_forward='-Z',
                    axis_up='Y',
                    use_edges=True,
                    use_smooth_groups=True,
                    use_split_objects=True,
                    use_split_groups=True,
                    use_image_search=True,
                    global_scale=scale
                )
                
            elif import_type == "FBX":
                bpy.ops.import_scene.fbx(
                    filepath=filepath,
                    use_custom_normals=use_custom_normals,
                    global_scale=scale
                )
                
            elif import_type == "GLB" or import_type == "GLTF":
                bpy.ops.import_scene.gltf(
                    filepath=filepath,
                    import_pack_images=True,
                    bone_heuristic='BLENDER'
                )
                
            elif import_type == "3DS":
                bpy.ops.import_scene.autodesk_3ds(
                    filepath=filepath,
                    constrain_size=10.0,
                    use_image_search=True,
                    use_apply_transform=True,
                    global_scale=scale
                )
                
            elif import_type == "STL":
                bpy.ops.import_mesh.stl(
                    filepath=filepath,
                    global_scale=scale
                )
                
            elif import_type == "PLY":
                bpy.ops.import_mesh.ply(
                    filepath=filepath
                )
                
            else:
                text_content = self.create_text_content(f"不支持的导入类型: {import_type}")
                return self.create_result([text_content], is_error=True)
            
            # 计算导入后的新对象
            post_import_objects = set(bpy.data.objects)
            imported_objects = post_import_objects - pre_import_objects
            
            # 创建结果信息
            if imported_objects:
                imported_names = ", ".join([obj.name for obj in imported_objects])
                text_content = self.create_text_content(
                    f"已导入 {len(imported_objects)} 个对象到场景 '{scene_name}':\n{imported_names}\n"
                    f"文件: {filepath}\n"
                    f"类型: {import_type}\n"
                    f"缩放: {scale}"
                )
            else:
                text_content = self.create_text_content(f"导入操作完成，但没有新对象被添加: {filepath}")
                
        except Exception as e:
            text_content = self.create_text_content(f"导入文件时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
            
        finally:
            # 恢复原始场景
            bpy.context.window.scene = original_scene
        
        # 返回结果
        return self.create_result([text_content])



# 在导入时自动注册工具实例
register_tool(ImportSceneHandler())

class ExportSceneHandler(BaseToolHandler):
    """导出场景工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_export_scene"
        
    @property
    def description(self) -> Optional[str]:
        return "导出Blender场景或对象到外部3D格式"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "title": "文件路径",
                    "description": "导出的目标文件路径"
                },
                "export_type": {
                    "type": "string",
                    "title": "导出类型",
                    "description": "要导出的文件类型",
                    "enum": ["OBJ", "FBX", "GLB", "STL", "PLY"],
                    "default": "OBJ"
                },
                "scene_name": {
                    "type": "string",
                    "title": "场景名称",
                    "description": "要导出的场景（默认为当前活动场景）"
                },
                "selected_only": {
                    "type": "boolean",
                    "title": "仅选中对象",
                    "description": "是否只导出选中的对象",
                    "default": False
                },
                "object_names": {
                    "type": "array",
                    "title": "对象名称",
                    "description": "要导出的特定对象名称列表",
                    "items": {
                        "type": "string"
                    }
                },
                "scale": {
                    "type": "number",
                    "title": "缩放",
                    "description": "导出时的缩放系数",
                    "default": 1.0
                },
                "apply_modifiers": {
                    "type": "boolean",
                    "title": "应用修改器",
                    "description": "是否在导出时应用修改器",
                    "default": True
                }
            },
            "required": ["filepath"]
        }
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数"""
        # 检查文件路径
        filepath = arguments.get("filepath")
        if not filepath:
            return "必须提供文件路径"
            
        # 检查导出类型
        export_type = arguments.get("export_type", "OBJ").upper()
        valid_types = ["OBJ", "FBX", "GLB", "STL", "PLY"]
        if export_type not in valid_types:
            return f"不支持的导出类型: {export_type}，有效类型: {', '.join(valid_types)}"
            
        # 确保文件扩展名与导出类型匹配
        file_ext = os.path.splitext(filepath)[1].lower()[1:]  # 移除点并转为小写
        if not file_ext:
            # 如果没有扩展名，自动添加
            filepath = f"{filepath}.{export_type.lower()}"
            arguments["filepath"] = filepath
        elif file_ext != export_type.lower():
            return f"文件扩展名 '{file_ext}' 与导出类型 '{export_type}' 不匹配"
            
        # 检查场景名称（如果提供）
        scene_name = arguments.get("scene_name")
        if scene_name and scene_name not in bpy.data.scenes:
            return f"场景 '{scene_name}' 不存在"
            
        # 检查对象名称（如果提供）
        object_names = arguments.get("object_names", [])
        if object_names:
            missing_objects = [name for name in object_names if name not in bpy.data.objects]
            if missing_objects:
                return f"找不到以下对象: {', '.join(missing_objects)}"
                
        # 检查缩放
        scale = arguments.get("scale")
        if scale is not None and (not isinstance(scale, (int, float)) or scale <= 0):
            return "缩放必须是正数"
            
        # 检查文件目录是否存在并可写
        file_dir = os.path.dirname(filepath)
        if file_dir and not os.path.exists(file_dir):
            try:
                os.makedirs(file_dir)
            except:
                return f"无法创建目录: {file_dir}"
                
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行导出场景操作"""
        logger.info(f"导出场景，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._export_scene, arguments)
        
    def _export_scene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中导出场景"""
        filepath = arguments.get("filepath")
        export_type = arguments.get("export_type", "OBJ").upper()
        scene_name = arguments.get("scene_name")
        selected_only = arguments.get("selected_only", False)
        object_names = arguments.get("object_names", [])
        scale = arguments.get("scale", 1.0)
        apply_modifiers = arguments.get("apply_modifiers", True)
        
        # 获取场景
        if scene_name:
            scene = bpy.data.scenes[scene_name]
        else:
            scene = bpy.context.scene
            scene_name = scene.name
        
        # 确保该场景是活动场景
        original_scene = bpy.context.scene
        bpy.context.window.scene = scene
        
        # 保存当前选择状态
        original_selected = [obj for obj in bpy.data.objects if obj.select_get()]
        
        try:
            # 准备要导出的对象
            export_objects = []
            
            if object_names:
                # 使用指定的对象
                export_objects = [bpy.data.objects[name] for name in object_names if name in bpy.data.objects]
            elif selected_only:
                # 使用当前选中的对象
                export_objects = [obj for obj in bpy.context.selected_objects]
            else:
                # 使用场景中的所有对象
                export_objects = [obj for obj in scene.objects]
            
            # 如果没有要导出的对象，返回错误
            if not export_objects:
                text_content = self.create_text_content("没有找到要导出的对象")
                return self.create_result([text_content], is_error=True)
            
            # 取消当前选择
            bpy.ops.object.select_all(action='DESELECT')
            
            # 选择要导出的对象
            for obj in export_objects:
                obj.select_set(True)
            
            # 根据不同的文件类型执行相应的导出操作
            if export_type == "OBJ":
                bpy.ops.export_scene.obj(
                    filepath=filepath,
                    use_selection=True,
                    axis_forward='-Z',
                    axis_up='Y',
                    global_scale=scale
                )
                
            elif export_type == "FBX":
                bpy.ops.export_scene.fbx(
                    filepath=filepath,
                    use_selection=True,
                    apply_scale_options='FBX_SCALE_ALL',
                    global_scale=scale,
                    apply_unit_scale=True,
                    bake_space_transform=True,
                    mesh_smooth_type='FACE',
                    use_mesh_modifiers=apply_modifiers
                )
                
            elif export_type == "GLB" or export_type == "GLTF":
                bpy.ops.export_scene.gltf(
                    filepath=filepath,
                    export_format='GLB',
                    use_selection=True
                )
                
            elif export_type == "STL":
                bpy.ops.export_mesh.stl(
                    filepath=filepath,
                    use_selection=True,
                    global_scale=scale
                )
                
            elif export_type == "PLY":
                bpy.ops.export_mesh.ply(
                    filepath=filepath,
                    use_selection=True
                )
                
            # 创建结果信息
            object_count = len(export_objects)
            object_names_text = ", ".join([obj.name for obj in export_objects[:10]])
            if len(export_objects) > 10:
                object_names_text += f" 等{len(export_objects)}个对象"
                
            text_content = self.create_text_content(
                f"已将 {object_count} 个对象从场景 '{scene_name}' 导出为 {export_type} 格式\n"
                f"对象: {object_names_text}\n"
                f"文件: {filepath}\n"
                f"缩放: {scale}"
            )
                
        except Exception as e:
            text_content = self.create_text_content(f"导出文件时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
            
        finally:
            # 恢复原始选择状态
            bpy.ops.object.select_all(action='DESELECT')
            for obj in original_selected:
                if obj:
                    obj.select_set(True)
            
            # 恢复原始场景
            bpy.context.window.scene = original_scene
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(ExportSceneHandler())
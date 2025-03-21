"""
保存和加载Blender场景的工具
"""

import bpy
from ..registry import register_tool
import os
import logging
from typing import Any, Dict, List, Optional

from ..base_tool_handler import BaseToolHandler
from ....utils import thread_utils

# 获取日志器
logger = logging.getLogger("BlenderMCP.SaveLoadScene")

class SaveSceneHandler(BaseToolHandler):
    """保存场景工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_save_scene"
        
    @property
    def description(self) -> Optional[str]:
        return "保存Blender场景到文件"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "title": "文件路径",
                    "description": "保存场景的文件路径（.blend后缀）"
                },
                "scene_name": {
                    "type": "string",
                    "title": "场景名称",
                    "description": "要保存的场景名称（默认为当前活动场景）"
                },
                "compress": {
                    "type": "boolean",
                    "title": "压缩文件",
                    "description": "是否压缩.blend文件",
                    "default": True
                },
                "relative_paths": {
                    "type": "boolean",
                    "title": "相对路径",
                    "description": "是否使用相对路径保存",
                    "default": True
                },
                "copy_images": {
                    "type": "boolean",
                    "title": "复制图像",
                    "description": "是否将链接的图像文件保存到.blend文件中",
                    "default": False
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
            
        # 检查文件扩展名
        if not filepath.lower().endswith('.blend'):
            return "文件路径必须以.blend结尾"
            
        # 检查场景名称（如果提供）
        scene_name = arguments.get("scene_name")
        if scene_name and scene_name not in bpy.data.scenes:
            return f"场景 '{scene_name}' 不存在"
            
        # 检查文件目录是否存在并可写
        file_dir = os.path.dirname(filepath)
        if file_dir and not os.path.exists(file_dir):
            try:
                os.makedirs(file_dir)
            except:
                return f"无法创建目录: {file_dir}"
                
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行保存场景操作"""
        logger.info(f"保存场景，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._save_scene, arguments)
        
    def _save_scene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中保存场景"""
        filepath = arguments.get("filepath")
        scene_name = arguments.get("scene_name")
        compress = arguments.get("compress", True)
        relative_paths = arguments.get("relative_paths", True)
        copy_images = arguments.get("copy_images", False)
        
        # 获取场景
        if scene_name:
            scene = bpy.data.scenes[scene_name]
            # 将指定场景设为活动场景，因为保存单个场景需要其为活动场景
            original_scene = bpy.context.scene
            bpy.context.window.scene = scene
        else:
            scene = bpy.context.scene
            scene_name = scene.name
            original_scene = scene
        
        # 设置保存选项
        bpy.data.use_autopack = copy_images
        
        try:
            # 保存场景
            bpy.ops.wm.save_as_mainfile(
                filepath=filepath,
                compress=compress,
                relative_paths=relative_paths
            )
            
            # 创建结果信息
            text_content = self.create_text_content(f"场景 '{scene_name}' 已保存到 {filepath}")
            
        except Exception as e:
            text_content = self.create_text_content(f"保存场景时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
            
        finally:
            # 恢复原始活动场景
            if scene_name and original_scene != scene:
                bpy.context.window.scene = original_scene
            
            # 重置打包选项
            bpy.data.use_autopack = False
        
        # 返回结果
        return self.create_result([text_content])



# 在导入时自动注册工具实例
register_tool(SaveSceneHandler())

class LoadSceneHandler(BaseToolHandler):
    """加载场景工具处理器"""
    
    @property
    def name(self) -> str:
        return "mcp_blender_load_scene"
        
    @property
    def description(self) -> Optional[str]:
        return "从文件加载Blender场景"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "title": "文件路径",
                    "description": "要加载的.blend文件路径"
                },
                "append": {
                    "type": "boolean",
                    "title": "追加到当前文件",
                    "description": "是否将场景追加到当前文件，而不是替换",
                    "default": False
                },
                "scene_name": {
                    "type": "string",
                    "title": "场景名称",
                    "description": "要追加的特定场景名称（仅在追加模式下有效）"
                },
                "set_active": {
                    "type": "boolean",
                    "title": "设为活动场景",
                    "description": "是否将加载/追加的场景设为活动场景",
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
            
        # 检查文件扩展名
        if not filepath.lower().endswith('.blend'):
            return "文件路径必须是.blend文件"
            
        return None
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行加载场景操作"""
        logger.info(f"加载场景，参数: {arguments}")
        
        # 在主线程中执行Blender操作
        return thread_utils.run_in_main_thread(self._load_scene, arguments)
        
    def _load_scene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """在主线程中加载场景"""
        filepath = arguments.get("filepath")
        append = arguments.get("append", False)
        scene_name = arguments.get("scene_name")
        set_active = arguments.get("set_active", True)
        
        try:
            if append:
                # 追加场景
                with bpy.data.libraries.load(filepath) as (data_from, data_to):
                    # 如果指定了场景名称，只追加该场景
                    if scene_name and scene_name in data_from.scenes:
                        data_to.scenes = [scene_name]
                    # 否则追加所有场景
                    else:
                        data_to.scenes = data_from.scenes
                
                # 获取追加的场景
                appended_scenes = data_to.scenes
                
                if not appended_scenes:
                    text_content = self.create_text_content(f"未能从文件中追加任何场景: {filepath}")
                    return self.create_result([text_content], is_error=True)
                
                # 设置活动场景
                if set_active and appended_scenes:
                    scene_to_set = None
                    # 如果指定了场景名，尝试找到它
                    if scene_name:
                        for scene in appended_scenes:
                            if scene.name.startswith(scene_name):
                                scene_to_set = scene
                                break
                    
                    # 如果没有找到指定场景或没有指定场景，使用第一个追加的场景
                    if not scene_to_set:
                        scene_to_set = appended_scenes[0]
                        
                    bpy.context.window.scene = scene_to_set
                    
                # 创建结果信息
                scene_names = [scene.name for scene in appended_scenes]
                text_content = self.create_text_content(f"已从 {filepath} 追加 {len(scene_names)} 个场景: {', '.join(scene_names)}")
                
            else:
                # 记录当前场景的数量，用于后续判断加载了多少新场景
                original_scene_count = len(bpy.data.scenes)
                
                # 加载整个文件
                bpy.ops.wm.open_mainfile(filepath=filepath)
                
                # 计算加载了多少场景
                loaded_scenes = len(bpy.data.scenes) - original_scene_count
                
                # 创建结果信息
                scene_names = [scene.name for scene in bpy.data.scenes]
                text_content = self.create_text_content(f"已加载文件 {filepath}，包含 {len(scene_names)} 个场景")
                
        except Exception as e:
            text_content = self.create_text_content(f"加载场景时出错: {str(e)}")
            return self.create_result([text_content], is_error=True)
        
        # 返回结果
        return self.create_result([text_content])


# 在导入时自动注册工具实例
register_tool(LoadSceneHandler())
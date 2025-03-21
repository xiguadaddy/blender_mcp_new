import bpy
import os
import tempfile
import base64
from mathutils import Vector, Euler
import threading
import time
import logging
import json
import traceback
from ..utils import thread_utils
import bmesh
import mathutils
import math
import concurrent.futures
from ..mcp_types import (
    create_text_content,
    create_image_content,
    create_error_data,
    CallToolResult,
    TextContent,
    Tool,
    ListToolsResult,
    ImageContent,
    ErrorData
)
from ..logger import get_logger

# 获取日志器
logger = get_logger("BlenderMCP.Tools")

# 工具线程锁，确保线程安全
_tool_lock = threading.Lock()

def execute_in_main_thread(func, *args, **kwargs):
    """在Blender主线程中执行函数"""
    # 确保主线程处理器已注册
    thread_utils.register_main_thread_processor()
    
    logger.debug(f"在主线程中执行函数: {func.__name__}")
    # 使用线程工具执行函数
    return thread_utils.run_in_main_thread(func, *args, **kwargs)

def execute_tool(tool_name, arguments):
    """执行指定工具"""
    logger.info(f"执行工具: {tool_name}, 参数: {arguments}")
    
    try:
        # 确保工具名称有统一前缀
        if not tool_name.startswith("mcp_blender_"):
            prefixed_name = f"mcp_blender_{tool_name}"
            logger.info(f"工具名称统一化: {tool_name} -> {prefixed_name}")
            tool_name = prefixed_name
            
        # 使用新的工具系统执行工具
        from .tools import execute_tool as new_execute_tool
        result = new_execute_tool(tool_name, arguments)
        
        # 使用序列化工具处理可能的元组格式结果
        from .tools.serializer import MCPSerializer
        formatted_result = MCPSerializer.fix_tuple_format(result)
        
        logger.debug(f"工具执行结果: {formatted_result}")
        return formatted_result
    except Exception as e:
        logger.error(f"执行工具时出错: {str(e)}")
        logger.error(traceback.format_exc())
        
        # 创建标准格式的错误响应
        from .tools.serializer import MCPSerializer
        error_content = MCPSerializer.create_text_content(f"执行工具时出错: {str(e)}")
        error_result = MCPSerializer.create_tool_result([error_content], is_error=True)
        return error_result

# 添加处理工具结果的函数
def process_tool_result(tool_result, result_obj):
    """处理工具执行结果，转换为标准MCP类型"""
    if tool_result is None:
        # 空结果处理
        content = create_text_content("工具执行成功，但没有返回结果")
        result_obj.content.append(content)
        return
        
    # 如果结果已经是MCP类型，直接添加
    if isinstance(tool_result, (TextContent, ImageContent)):
        result_obj.content.append(tool_result)
        return
        
    # 处理列表结果
    if isinstance(tool_result, list):
        for item in tool_result:
            process_tool_result(item, result_obj)
        return
        
    # 处理字典结果
    if isinstance(tool_result, dict):
        # 检查是否包含图像数据
        if "image_data" in tool_result and "mime_type" in tool_result:
            # 创建图像内容
            image_content = create_image_content(
                tool_result["image_data"], 
                tool_result["mime_type"]
            )
            result_obj.content.append(image_content)
            return
            
        # 检查是否包含文本数据
        if "text" in tool_result:
            content = create_text_content(tool_result["text"])
            result_obj.content.append(content)
            return
            
        # 一般字典，转为文本
        content = create_text_content(json.dumps(tool_result, indent=2))
        result_obj.content.append(content)
        return
        
    # 默认处理：转为文本
    content = create_text_content(str(tool_result))
    result_obj.content.append(content)

def _execute_tool_worker(tools, tool_name, arguments):
    """在工作线程中执行工具（无需锁）"""
    try:
        if tool_name in tools:
            logger.debug(f"执行工具处理函数: {tool_name}")
            start_time = time.time()
            result = tools[tool_name](arguments)
            execution_time = time.time() - start_time
            logger.debug(f"工具执行完成，耗时: {execution_time:.3f}秒")
            return result
        else:
            error_msg = f"未知工具: {tool_name}"
            logger.error(error_msg)
            logger.debug(f"可用工具列表: {list(tools.keys())}")
            return {"error": error_msg}
    except Exception as e:
        error_msg = f"执行工具时出错: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return {"error": error_msg}

def execute_python_tool(code):
    """执行Python代码工具"""
    try:
        # 创建局部命名空间执行代码
        namespace = {"bpy": bpy, "result": None, "create_text_content": create_text_content, 
                    "create_image_content": create_image_content}
        exec(code, namespace)
        # 返回代码执行结果
        return namespace.get("result", {"status": "success", "text": "代码执行成功，但未返回结果"})
    except Exception as e:
        return {"error": f"执行Python代码时出错: {str(e)}"}

def import_model(args):
    """导入3D模型文件"""
    logger.debug(f"导入模型: {args}")
    file_path = args.get("file_path")
    import_type = args.get("import_type")
    
    def exec_func():
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return {"error": f"文件不存在: {file_path}"}
            
            # 根据不同格式调用相应的导入函数
            if import_type == "OBJ":
                bpy.ops.import_scene.obj(filepath=file_path)
            elif import_type == "FBX":
                bpy.ops.import_scene.fbx(filepath=file_path)
            elif import_type == "GLB":
                bpy.ops.import_scene.gltf(filepath=file_path)
            elif import_type == "STL":
                bpy.ops.import_mesh.stl(filepath=file_path)
            else:
                return {"error": f"不支持的导入类型: {import_type}"}
            
            # 获取新导入的对象
            imported_objects = [obj.name for obj in bpy.context.selected_objects]
            
            return {
                "status": "success", 
                "text": f"成功导入{len(imported_objects)}个对象",
                "imported_objects": imported_objects,
                "file_path": file_path
            }
        except Exception as e:
            logger.error(f"导入模型时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)


def set_uv_mapping(args):
    """设置UV映射"""
    logger.debug(f"设置UV映射: {args}")
    object_name = args.get("object_name")
    mapping_type = args.get("mapping_type", "UNWRAP")
    scale = args.get("scale", (1.0, 1.0))
    
    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj or obj.type != 'MESH':
                return {"error": f"无效网格对象: {object_name}"}
            
            # 设置活动对象
            bpy.context.view_layer.objects.active = obj
            
            # 存储当前模式
            current_mode = bpy.context.object.mode
            bpy.ops.object.mode_set(mode='EDIT')
            
            # 选择所有面
            bm = bmesh.from_edit_mesh(obj.data)
            for face in bm.faces:
                face.select = True
            bmesh.update_edit_mesh(obj.data)
            
            # 应用UV映射
            if mapping_type == "UNWRAP":
                bpy.ops.uv.unwrap()
            elif mapping_type == "SMART_PROJECT":
                bpy.ops.uv.smart_project()
            elif mapping_type == "CUBE_PROJECTION":
                bpy.ops.uv.cube_project()
            elif mapping_type == "CYLINDER_PROJECTION":
                bpy.ops.uv.cylinder_project()
            elif mapping_type == "SPHERE_PROJECTION":
                bpy.ops.uv.sphere_project()
            else:
                # 默认展开
                bpy.ops.uv.unwrap()
            
            # 应用比例
            if "uv_layers" in dir(obj.data) and obj.data.uv_layers:
                uv_layer = obj.data.uv_layers.active
                if uv_layer:
                    for polygon in obj.data.polygons:
                        for loop_idx in polygon.loop_indices:
                            uv = uv_layer.data[loop_idx].uv
                            uv.x *= scale[0]
                            uv.y *= scale[1]
            
            # 恢复模式
            bpy.ops.object.mode_set(mode=current_mode)
            
            return {
                "status": "success",
                "text": f"成功为对象 {object_name} 设置 {mapping_type} UV映射",
                "object": object_name,
                "mapping_type": mapping_type,
                "scale": scale
            }
            
        except Exception as e:
            logger.error(f"设置UV映射时出错: {str(e)}")
            # 恢复模式
            if 'current_mode' in locals():
                bpy.ops.object.mode_set(mode=current_mode)
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)


def list_tools():
    """获取所有工具列表"""
    try:
        # 导入工具模块以确保所有工具都已注册
        import importlib
        from . import tools
        
        # 重新加载工具模块以确保所有工具都被加载
        importlib.reload(tools)
        
        # 获取工具列表
        from .tools import list_tools as new_list_tools
        tools_list = new_list_tools()
        tool_count = len(tools_list)
        logger.info(f"返回 {tool_count} 个工具")
        
        if tool_count == 0:
            # 如果没有找到工具，尝试手动初始化工具系统
            logger.warning("没有找到已注册的工具，尝试强制初始化...")
            from .tools.registry import get_tool_registry
            registry = get_tool_registry()
            
            # 手动导入所有工具包
            from .tools import object_tools, material_tools, lighting_tools
            from .tools import camera_tools, scene_tools, mesh_tools
            from .tools import effect_tools, animation_tools, modeling_tools
            
            # 再次尝试获取工具列表
            tools_list = new_list_tools()
            logger.info(f"强制初始化后返回 {len(tools_list)} 个工具")
        
        return {"tools": tools_list}
    except Exception as e:
        logger.error(f"获取工具列表时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {"tools": [], "error": str(e)}

# 添加工具处理器类，用于在场景中注册
class MCPToolsHandler:
    """MCP工具处理器类，提供工具执行接口"""
    
    def __init__(self):
        logger.debug("初始化MCP工具处理器")
    
    def execute_tool(self, tool_name, arguments):
        """执行工具，返回结果"""
        logger.debug(f"MCPToolsHandler执行工具: {tool_name}")
        return execute_tool(tool_name, arguments)
    
    def list_tools(self):
        """获取可用工具列表"""
        logger.debug("MCPToolsHandler获取工具列表")
        return list_tools()

# 全局工具处理器实例
_tools_handler_instance = None
        
# 注册工具处理器到场景
def register_tools_handler():
    """在场景中注册工具处理器"""
    try:
        # 创建一个全局工具处理器实例
        global _tools_handler_instance
        if _tools_handler_instance is None:
            logger.debug("创建全局工具处理器实例")
            _tools_handler_instance = MCPToolsHandler()
        
        # 使用bpy.app.driver_namespace来存储工具处理器
        # 这是一个全局字典，可以用来存储跨Blender会话的数据
        bpy.app.driver_namespace["mcp_tools_handler"] = _tools_handler_instance
        
        # 为所有场景添加工具处理器访问函数
        def get_mcp_tools_handler(self):
            """获取MCP工具处理器实例"""
            if "mcp_tools_handler" in bpy.app.driver_namespace:
                return bpy.app.driver_namespace["mcp_tools_handler"]
            return None
            
        # 注册访问函数到Scene类
        if not hasattr(bpy.types.Scene, "mcp_tools_handler"):
            logger.debug("为Scene类型注册mcp_tools_handler属性")
            bpy.types.Scene.mcp_tools_handler = property(get_mcp_tools_handler)
            
        logger.info("MCP工具处理器已注册")
        return True
    except Exception as e:
        logger.error(f"注册工具处理器时出错: {e}")
        return False

# 注销工具处理器
def unregister_tools_handler():
    """从场景中移除工具处理器"""
    try:
        # 从driver_namespace中删除工具处理器实例
        if "mcp_tools_handler" in bpy.app.driver_namespace:
            del bpy.app.driver_namespace["mcp_tools_handler"]
            
        # 从类型中移除属性
        if hasattr(bpy.types.Scene, "mcp_tools_handler"):
            delattr(bpy.types.Scene, "mcp_tools_handler")
            
        logger.info("MCP工具处理器已注销")
    except Exception as e:
        logger.error(f"注销工具处理器时出错: {e}")

# 更新场景中的工具处理器
def update_tools_handler():
    """确保工具处理器可用"""
    # 确保全局实例存在
    register_tools_handler()
    logger.debug("已更新工具处理器")


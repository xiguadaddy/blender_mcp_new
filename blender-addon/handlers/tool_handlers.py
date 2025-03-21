import bpy
import os
import tempfile
import base64
from mathutils import Vector, Euler
import threading
import time
import logging
import json
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
    from .tools import register_all_tools
    
    logger.info(f"执行工具: {tool_name}, 参数: {arguments}")
    
    # 创建工具结果对象
    result = CallToolResult()
    
    try:
        # 检查是否在主线程中执行
        is_main_thread = threading.current_thread() is threading.main_thread()
        logger.debug(f"执行工具 {tool_name} 在{'主' if is_main_thread else '后台'}线程")
        
        # 执行Python代码
        if tool_name == "execute_python":
            code = arguments.get("code", "")
            if not code:
                logger.warning("未提供Python代码")
                # 创建错误内容
                content = create_text_content("未提供Python代码")
                result.content.append(content)
                result.isError = True
                return result.to_dict()
                
            tool_result = execute_python_tool(code)
            
            if isinstance(tool_result, dict) and "error" in tool_result:
                # 创建错误内容
                content = create_text_content(f"执行Python代码出错: {tool_result['error']}")
                result.content.append(content)
                result.isError = True
            else:
                # 处理可能的复杂返回结果
                process_tool_result(tool_result, result)
                
            return result.to_dict()
        
        # 列出可用工具
        elif tool_name == "list_tools":
            logger.debug("调用list_tools函数")
            return list_tools()
        
        # 获取所有注册的工具
        tools = register_all_tools()
        
        # 在主线程中使用线程池执行，避免阻塞
        if is_main_thread and tool_name not in ["list_tools", "execute_python"]:
            logger.debug(f"检测到在主线程中调用工具{tool_name}，转移到后台线程执行")
            
            # 使用线程池异步执行工具
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_execute_tool_worker, tools, tool_name, arguments)
                
                try:
                    # 等待最多3秒
                    tool_result = future.result(timeout=3.0)
                    
                    # 处理工具执行结果
                    if isinstance(tool_result, dict) and "error" in tool_result:
                        # 创建错误内容
                        error_msg = f"工具执行错误: {tool_result['error']}"
                        content = create_text_content(error_msg)
                        result.content.append(content)
                        result.isError = True
                    else:
                        # 处理工具结果
                        process_tool_result(tool_result, result)
                        
                    return result.to_dict()
                except concurrent.futures.TimeoutError:
                    logger.warning(f"工具{tool_name}执行超时（>3秒），返回超时错误")
                    # 创建超时错误内容
                    content = create_text_content(f"工具执行超时（>3秒）")
                    result.content.append(content)
                    result.isError = True
                    return result.to_dict()
                except Exception as e:
                    logger.error(f"工具{tool_name}异步执行出错: {e}")
                    # 创建异步执行错误内容
                    content = create_text_content(f"工具执行错误: {str(e)}")
                    result.content.append(content)
                    result.isError = True
                    return result.to_dict()
        
        # 在非主线程中直接执行
        tool_result = _execute_tool_worker(tools, tool_name, arguments)
        
        # 处理工具执行结果
        if isinstance(tool_result, dict) and "error" in tool_result:
            # 创建错误内容
            error_msg = f"工具执行错误: {tool_result['error']}"
            content = create_text_content(error_msg)
            result.content.append(content)
            result.isError = True
        else:
            # 处理工具结果
            process_tool_result(tool_result, result)
            
        return result.to_dict()
    except Exception as e:
        import traceback
        error_msg = f"执行工具时出错: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        # 创建异常错误内容
        content = create_text_content(error_msg)
        result.content.append(content)
        result.isError = True
        return result.to_dict()

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
        import traceback
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
    """列出所有可用工具"""
    from .tools import register_all_tools
    
    logger.debug("列出所有可用工具")
    
    # 创建工具列表结果
    result = ListToolsResult()
    
    try:
        # 获取所有工具
        tools_dict = register_all_tools()
        
        for tool_name, tool_func in tools_dict.items():
            # 创建工具对象
            tool = Tool()
            tool.name = tool_name
            
            # 从文档字符串中提取描述
            if tool_func.__doc__:
                tool.description = tool_func.__doc__.strip()
            else:
                tool.description = f"Blender工具: {tool_name}"
                
            # 构建输入模式，为特定工具提供更详细的模式
            if tool_name == "create_object":
                tool.inputSchema = {
                    "type": "object",
                    "properties": {
                        "object_type": {
                            "type": "string",
                            "enum": ["cube", "sphere", "plane", "cylinder", "cone", "torus", "empty"],
                            "description": "要创建的对象类型"
                        },
                        "location": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "对象位置坐标 [x, y, z]"
                        },
                        "name": {
                            "type": "string",
                            "description": "对象名称"
                        },
                        "size": {
                            "type": "number",
                            "description": "对象大小"
                        }
                    },
                    "required": ["object_type"]
                }
            elif tool_name == "set_material":
                tool.inputSchema = {
                    "type": "object",
                    "properties": {
                        "object_name": {"type": "string", "description": "目标对象名称"},
                        "material_name": {"type": "string", "description": "材质名称"},
                        "color": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "RGBA颜色值 [r, g, b, a]"
                        },
                        "metallic": {"type": "number", "description": "金属度(0-1)"},
                        "roughness": {"type": "number", "description": "粗糙度(0-1)"}
                    },
                    "required": ["object_name"]
                }
            elif tool_name == "add_light":
                tool.inputSchema = {
                    "type": "object",
                    "properties": {
                        "light_type": {
                            "type": "string",
                            "enum": ["POINT", "SUN", "SPOT", "AREA"],
                            "description": "灯光类型"
                        },
                        "location": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "灯光位置 [x, y, z]"
                        },
                        "name": {"type": "string", "description": "灯光名称"},
                        "color": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "RGB颜色值 [r, g, b]"
                        },
                        "energy": {"type": "number", "description": "灯光强度"}
                    },
                    "required": ["light_type"]
                }
            else:
                # 默认输入模式
                tool.inputSchema = {
                    "type": "object",
                    "properties": {}
                }
            
            # 添加到工具列表
            result.tools.append(tool)
            
        logger.info(f"找到 {len(result.tools)} 个可用工具")
        return result.to_dict()
    except Exception as e:
        import traceback
        logger.error(f"列出工具时出错: {str(e)}")
        logger.error(traceback.format_exc())
        
        # 返回空的工具列表
        return result.to_dict()

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


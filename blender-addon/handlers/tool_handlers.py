import bpy
import os
import tempfile
import base64
from mathutils import Vector, Euler
import threading
import time
import logging
from ..utils import thread_utils
import bmesh
import mathutils
import math
import concurrent.futures

# 设置日志
logger = logging.getLogger("BlenderMCP.Tools")
# 配置日志格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# 添加控制台处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# 添加文件处理器
log_file = os.path.join(tempfile.gettempdir(), "blender_mcp_tools.log")
file_handler = logging.FileHandler(log_file, mode='a')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

logger.setLevel(logging.DEBUG)

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
    
    # 检查是否在主线程中执行
    is_main_thread = threading.current_thread() is threading.main_thread()
    logger.debug(f"执行工具 {tool_name} 在{'主' if is_main_thread else '后台'}线程")
    
    # 执行Python代码
    if tool_name == "execute_python":
        code = arguments.get("code", "")
        if not code:
            logger.warning("未提供Python代码")
            return {"error": "未提供Python代码"}
        return execute_python_tool(code)
    
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
                return future.result(timeout=3.0)
            except concurrent.futures.TimeoutError:
                logger.warning(f"工具{tool_name}执行超时（>3秒），返回超时错误")
                return {"error": f"工具执行超时（>3秒）"}
            except Exception as e:
                logger.error(f"工具{tool_name}异步执行出错: {e}")
                return {"error": f"工具执行错误: {e}"}
    
    # 在非主线程中直接执行
    return _execute_tool_worker(tools, tool_name, arguments)

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
        namespace = {"bpy": bpy, "result": None}
        exec(code, namespace)
        # 返回代码执行结果
        return namespace.get("result", {"status": "success", "message": "代码执行成功，但未返回结果"})
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
    """获取所有可用工具列表的详细信息"""
    logger.debug("获取工具列表")
    
    try:
        from .tools import register_all_tools
        
        # 获取工具处理函数
        tools_funcs = register_all_tools()
        logger.debug(f"找到 {len(tools_funcs)} 个工具函数")
        
        # 预定义的工具信息
        tools = [
            {
                "name": "create_object",
                "description": "在Blender中创建一个对象",
                "version": "1.0",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "object_type": {
                            "type": "string", 
                            "enum": ["cube", "sphere", "cylinder", "plane", "cone", "torus"],
                            "description": "要创建的对象类型"
                        },
                        "name": {
                            "type": "string",
                            "description": "对象名称(可选)"
                        },
                        "location": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "对象位置坐标 [x, y, z]"
                        },
                        "size": {
                            "type": "number",
                            "description": "对象大小"
                        }
                    },
                    "required": ["object_type"]
                }
            },
            {
                "name": "set_material",
                "description": "为对象设置材质",
                "version": "1.0",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "object_name": {
                            "type": "string",
                            "description": "目标对象名称"
                        },
                        "material_name": {
                            "type": "string",
                            "description": "材质名称（如果不提供则自动生成）"
                        },
                        "color": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "RGBA颜色值 [r, g, b, a]，或RGB颜色值 [r, g, b]"
                        },
                        "metallic": {
                            "type": "number",
                            "description": "金属度(0-1)"
                        },
                        "roughness": {
                            "type": "number",
                            "description": "粗糙度(0-1)"
                        }
                    },
                    "required": ["object_name"]
                }
            },
            {
                "name": "add_light",
                "description": "添加灯光到场景",
                "version": "1.0",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "light_type": {
                            "type": "string",
                            "enum": ["POINT", "SUN", "SPOT", "AREA"],
                            "description": "灯光类型"
                        },
                        "name": {
                            "type": "string",
                            "description": "灯光名称(可选)"
                        },
                        "location": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "灯光位置 [x, y, z]"
                        },
                        "color": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "RGB颜色值 [r, g, b]"
                        },
                        "energy": {
                            "type": "number",
                            "description": "灯光强度"
                        }
                    },
                    "required": ["light_type"]
                }
            },
            {
                "name": "set_camera",
                "description": "设置相机参数",
                "version": "1.0",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "camera_name": {
                            "type": "string",
                            "description": "相机名称(如果不存在则创建)"
                        },
                        "location": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "相机位置 [x, y, z]"
                        },
                        "rotation": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "相机旋转 [x, y, z] (弧度)"
                        },
                        "target": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "相机目标点 [x, y, z]"
                        },
                        "lens": {
                            "type": "number",
                            "description": "镜头焦距(mm)"
                        }
                    },
                    "required": ["camera_name"]
                }
            },
            {
                "name": "render_scene",
                "description": "渲染当前场景",
                "version": "1.0",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "output_path": {
                            "type": "string",
                            "description": "输出文件路径"
                        },
                        "resolution_x": {
                            "type": "number",
                            "description": "水平分辨率"
                        },
                        "resolution_y": {
                            "type": "number",
                            "description": "垂直分辨率"
                        },
                        "engine": {
                            "type": "string",
                            "enum": ["CYCLES", "BLENDER_EEVEE", "WORKBENCH"],
                            "description": "渲染引擎"
                        }
                    },
                    "required": ["output_path"]
                }
            },
            {
                "name": "execute_python",
                "description": "执行Python代码",
                "version": "1.0",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "要执行的Python代码"
                        }
                    },
                    "required": ["code"]
                }
            },
            # 添加更多工具...
        ]
        
        # 根据工具函数列表添加额外的工具
        # 这样可以自动将新添加的工具函数转换为工具信息
        for tool_name in tools_funcs:
            # 跳过已存在的工具
            if any(tool["name"] == tool_name for tool in tools):
                continue
                
            # 创建新工具定义
            tool_info = {
                "name": tool_name,
                "description": f"执行 {tool_name} 操作",
                "version": "1.0",
                # 默认模式，如果工具函数没有docstring，则假设它接受一个空字典
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
            
            # 如果函数有文档字符串，尝试从中提取更多信息
            func = tools_funcs[tool_name]
            if func.__doc__:
                # 尝试从docstring中提取描述信息
                tool_info["description"] = func.__doc__.strip().split('\n')[0]
                
            tools.append(tool_info)
        
        # 记录工具列表
        logger.info(f"返回 {len(tools)} 个工具定义")
        for tool in tools:
            logger.debug(f"工具: {tool['name']} - {tool['description']}")
            
        return tools
        
    except Exception as e:
        import traceback
        logger.error(f"获取工具列表时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return []

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

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

# 设置日志
logger = logging.getLogger("BlenderMCP.Tools")

# 工具线程锁，确保线程安全
_tool_lock = threading.Lock()

def execute_in_main_thread(func, *args, **kwargs):
    """在Blender主线程中执行函数"""
    # 确保主线程处理器已注册
    thread_utils.register_main_thread_processor()
    
    # 使用线程工具执行函数
    return thread_utils.run_in_main_thread(func, *args, **kwargs)

def execute_tool(tool_name, arguments):
    """执行指定工具"""
    from blender_addon.handlers.tools import register_all_tools
    
    print(f"执行工具: {tool_name}, 参数: {arguments}")
    
    # 执行Python代码
    if tool_name == "execute_python":
        code = arguments.get("code", "")
        if not code:
            return {"error": "未提供Python代码"}
        return execute_python_tool(code)
    
    # 列出可用工具
    elif tool_name == "list_tools":
        return list_tools()
    
    # 获取所有注册的工具
    tools = register_all_tools()
    
    with _tool_lock:
        try:
            if tool_name in tools:
                return tools[tool_name](arguments)
            else:
                error_msg = f"未知工具: {tool_name}"
                logger.error(error_msg)
                return {"error": error_msg}
        except Exception as e:
            error_msg = f"执行工具时出错: {str(e)}"
            logger.error(error_msg)
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
    """返回可用工具列表"""
    from .tools import register_all_tools
    
    logger.debug("列出可用工具")
    
    # 获取所有注册的工具
    tools_dict = register_all_tools()
    
    tools = []
    for tool_name, tool_func in tools_dict.items():
        # 获取工具的docstring作为描述
        description = tool_func.__doc__ or f"执行{tool_name}操作"
        
        # 构建工具信息
        tool_info = {
            "name": tool_name,
            "description": description.strip(),
            "version": "1.0"
        }
        
        # 针对特定工具添加额外信息
        if tool_name == "create_object":
            tool_info["input_schema"] = {
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
            tool_info["input_schema"] = {
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
            tool_info["input_schema"] = {
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
        
        tools.append(tool_info)
    
    return tools

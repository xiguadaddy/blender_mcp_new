import mcp.types as types
from .schemas import *
import json

def register_tool_handlers(server, ipc_client):
    """注册所有Blender工具处理程序"""
    
    @server.list_tools()
    async def handle_list_tools():
        """列出可用的Blender工具"""
        print("MCP服务器：处理list_tools请求")
        tools = [
            # 1. 基础对象创建工具
            types.Tool(
                name="创建立方体",
                description="在Blender中创建一个立方体",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "object",
                            "properties": {
                                "x": {"type": "number", "description": "X坐标"},
                                "y": {"type": "number", "description": "Y坐标"},
                                "z": {"type": "number", "description": "Z坐标"}
                            }
                        },
                        "size": {"type": "number", "description": "立方体大小"},
                        "name": {"type": "string", "description": "对象名称"}
                    }
                }
            ),
            types.Tool(
                name="创建球体",
                description="在Blender中创建一个球体",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "object",
                            "properties": {
                                "x": {"type": "number", "description": "X坐标"},
                                "y": {"type": "number", "description": "Y坐标"},
                                "z": {"type": "number", "description": "Z坐标"}
                            }
                        },
                        "radius": {"type": "number", "description": "球体半径"},
                        "name": {"type": "string", "description": "对象名称"}
                    }
                }
            ),
            types.Tool(
                name="创建圆柱体",
                description="在Blender中创建一个圆柱体",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "object",
                            "properties": {
                                "x": {"type": "number", "description": "X坐标"},
                                "y": {"type": "number", "description": "Y坐标"},
                                "z": {"type": "number", "description": "Z坐标"}
                            }
                        },
                        "radius": {"type": "number", "description": "圆柱体半径"},
                        "depth": {"type": "number", "description": "圆柱体高度"},
                        "name": {"type": "string", "description": "对象名称"}
                    }
                }
            ),
            types.Tool(
                name="创建平面",
                description="在Blender中创建一个平面",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "object",
                            "properties": {
                                "x": {"type": "number", "description": "X坐标"},
                                "y": {"type": "number", "description": "Y坐标"},
                                "z": {"type": "number", "description": "Z坐标"}
                            }
                        },
                        "size": {"type": "number", "description": "平面大小"},
                        "name": {"type": "string", "description": "对象名称"}
                    }
                }
            ),
            
            # 2. 对象操作工具
            types.Tool(
                name="移动对象",
                description="移动Blender中的对象",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "object_name": {"type": "string", "description": "对象名称"},
                        "location": {
                            "type": "object",
                            "properties": {
                                "x": {"type": "number", "description": "X坐标"},
                                "y": {"type": "number", "description": "Y坐标"},
                                "z": {"type": "number", "description": "Z坐标"}
                            }
                        }
                    },
                    "required": ["object_name"]
                }
            ),
            types.Tool(
                name="旋转对象",
                description="旋转Blender中的对象",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "object_name": {"type": "string", "description": "对象名称"},
                        "rotation": {
                            "type": "object",
                            "properties": {
                                "x": {"type": "number", "description": "X轴旋转(弧度)"},
                                "y": {"type": "number", "description": "Y轴旋转(弧度)"},
                                "z": {"type": "number", "description": "Z轴旋转(弧度)"}
                            }
                        }
                    },
                    "required": ["object_name"]
                }
            ),
            types.Tool(
                name="缩放对象",
                description="缩放Blender中的对象",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "object_name": {"type": "string", "description": "对象名称"},
                        "scale": {
                            "type": "object",
                            "properties": {
                                "x": {"type": "number", "description": "X轴缩放"},
                                "y": {"type": "number", "description": "Y轴缩放"},
                                "z": {"type": "number", "description": "Z轴缩放"}
                            }
                        }
                    },
                    "required": ["object_name"]
                }
            ),
            types.Tool(
                name="复制对象",
                description="复制Blender中的对象",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "source_name": {"type": "string", "description": "源对象名称"},
                        "new_name": {"type": "string", "description": "新对象名称"},
                        "location": {
                            "type": "object",
                            "properties": {
                                "x": {"type": "number", "description": "X坐标"},
                                "y": {"type": "number", "description": "Y坐标"},
                                "z": {"type": "number", "description": "Z坐标"}
                            }
                        }
                    },
                    "required": ["source_name"]
                }
            ),
            types.Tool(
                name="删除对象",
                description="删除Blender中的对象",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "object_name": {"type": "string", "description": "对象名称"}
                    },
                    "required": ["object_name"]
                }
            ),
            
            # 3. 材质工具
            types.Tool(
                name="创建材质",
                description="创建新材质",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "材质名称"},
                        "color": {
                            "type": "object",
                            "properties": {
                                "r": {"type": "number", "description": "红色(0-1)"},
                                "g": {"type": "number", "description": "绿色(0-1)"},
                                "b": {"type": "number", "description": "蓝色(0-1)"}
                            }
                        },
                        "metallic": {"type": "number", "description": "金属度(0-1)"},
                        "roughness": {"type": "number", "description": "粗糙度(0-1)"}
                    },
                    "required": ["name"]
                }
            ),
            types.Tool(
                name="应用材质",
                description="将材质应用到对象",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "object_name": {"type": "string", "description": "对象名称"},
                        "material_name": {"type": "string", "description": "材质名称"}
                    },
                    "required": ["object_name", "material_name"]
                }
            ),
            
            # 4. 场景工具
            types.Tool(
                name="新建场景",
                description="创建新场景",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "场景名称"},
                        "clear_all": {"type": "boolean", "description": "是否清除所有对象"}
                    }
                }
            ),
            types.Tool(
                name="切换场景",
                description="切换到指定场景",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "场景名称"}
                    },
                    "required": ["name"]
                }
            ),
            types.Tool(
                name="添加光源",
                description="添加光源到场景",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "description": "光源类型(POINT, SUN, SPOT, AREA)"},
                        "name": {"type": "string", "description": "光源名称"},
                        "location": {
                            "type": "object",
                            "properties": {
                                "x": {"type": "number", "description": "X坐标"},
                                "y": {"type": "number", "description": "Y坐标"},
                                "z": {"type": "number", "description": "Z坐标"}
                            }
                        },
                        "energy": {"type": "number", "description": "光源强度"}
                    },
                    "required": ["type"]
                }
            ),
            types.Tool(
                name="添加相机",
                description="添加相机到场景",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "相机名称"},
                        "location": {
                            "type": "object",
                            "properties": {
                                "x": {"type": "number", "description": "X坐标"},
                                "y": {"type": "number", "description": "Y坐标"},
                                "z": {"type": "number", "description": "Z坐标"}
                            }
                        },
                        "rotation": {
                            "type": "object",
                            "properties": {
                                "x": {"type": "number", "description": "X轴旋转(弧度)"},
                                "y": {"type": "number", "description": "Y轴旋转(弧度)"},
                                "z": {"type": "number", "description": "Z轴旋转(弧度)"}
                            }
                        }
                    }
                }
            ),
            
            # 5. 渲染工具
            types.Tool(
                name="设置渲染参数",
                description="设置渲染引擎和参数",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "engine": {"type": "string", "description": "渲染引擎(CYCLES, EEVEE)"},
                        "resolution_x": {"type": "integer", "description": "分辨率宽度"},
                        "resolution_y": {"type": "integer", "description": "分辨率高度"},
                        "samples": {"type": "integer", "description": "采样数量"}
                    }
                }
            ),
            types.Tool(
                name="渲染图像",
                description="渲染当前场景并保存",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string", "description": "保存路径"},
                        "file_format": {"type": "string", "description": "文件格式(PNG, JPEG, etc)"}
                    }
                }
            ),
            
            # 6. 动画工具
            types.Tool(
                name="设置关键帧",
                description="为对象属性设置关键帧",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "object_name": {"type": "string", "description": "对象名称"},
                        "property": {"type": "string", "description": "属性名称(location, rotation, scale)"},
                        "frame": {"type": "integer", "description": "帧数"}
                    },
                    "required": ["object_name", "property", "frame"]
                }
            ),
            types.Tool(
                name="设置动画范围",
                description="设置动画开始和结束帧",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "start_frame": {"type": "integer", "description": "开始帧"},
                        "end_frame": {"type": "integer", "description": "结束帧"},
                        "fps": {"type": "integer", "description": "每秒帧数"}
                    }
                }
            ),
            
            # 7. 通用工具
            types.Tool(
                name="执行代码",
                description="在Blender中执行Python代码",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "要执行的Python代码"}
                    },
                    "required": ["code"]
                }
            ),
            types.Tool(
                name="列出对象",
                description="列出Blender场景中的所有对象",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "type_filter": {"type": "string", "description": "对象类型过滤器(MESH, LIGHT, CAMERA等)"}
                    }
                }
            ),
            types.Tool(
                name="测试连接",
                description="测试与Blender的连接",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "测试消息"}
                    }
                }
            )
        ]
        
        print(f"MCP服务器：返回 {len(tools)} 个工具")
        return tools
    
    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None = None):
        """处理所有工具调用的统一入口"""
        print(f"===== 调用工具: {name}, 参数: {arguments} =====")
        arguments = arguments or {}
        
        try:
            # 创建立方体
            if name == "创建立方体":
                location = arguments.get("location", {"x": 0, "y": 0, "z": 0})
                size = arguments.get("size", 2.0)
                obj_name = arguments.get("name", "立方体")
                
                # 构建Python代码
                code = f"""
import bpy
bpy.ops.mesh.primitive_cube_add(
    size={size}, 
    location=({location.get('x', 0)}, {location.get('y', 0)}, {location.get('z', 0)})
)
if bpy.context.active_object:
    bpy.context.active_object.name = "{obj_name}"
    result = {{"name": bpy.context.active_object.name, "status": "success"}}
else:
    result = {{"error": "创建对象失败", "status": "error"}}
"""
                # 通过execute_python工具执行
                blender_request = {
                    "action": "call_tool",
                    "tool": "execute_python",
                    "arguments": {"code": code}
                }
                
                result = await ipc_client.send_request(blender_request)
                message = f"已创建立方体 '{obj_name}'，位置: ({location.get('x', 0)}, {location.get('y', 0)}, {location.get('z', 0)}), 大小: {size}"
                return [types.TextContent(type="text", text=message)]
                
            elif name == "创建球体":
                location = arguments.get("location", {"x": 0, "y": 0, "z": 0})
                radius = arguments.get("radius", 1.0)
                obj_name = arguments.get("name", "球体")
                
                code = f"""
import bpy
bpy.ops.mesh.primitive_uv_sphere_add(
    radius={radius}, 
    location=({location.get('x', 0)}, {location.get('y', 0)}, {location.get('z', 0)})
)
if bpy.context.active_object:
    bpy.context.active_object.name = "{obj_name}"
    result = {{"name": bpy.context.active_object.name}}
else:
    result = {{"error": "创建对象失败"}}
result
"""
                result = await ipc_client.execute_in_blender(code)
                message = f"已创建球体 '{obj_name}'，位置: ({location.get('x', 0)}, {location.get('y', 0)}, {location.get('z', 0)}), 半径: {radius}"
                return [types.TextContent(type="text", text=message)]
                
            elif name == "创建圆柱体":
                location = arguments.get("location", {"x": 0, "y": 0, "z": 0})
                radius = arguments.get("radius", 1.0)
                depth = arguments.get("depth", 2.0)
                obj_name = arguments.get("name", "圆柱体")
                
                code = f"""
import bpy
bpy.ops.mesh.primitive_cylinder_add(
    radius={radius},
    depth={depth},
    location=({location.get('x', 0)}, {location.get('y', 0)}, {location.get('z', 0)})
)
if bpy.context.active_object:
    bpy.context.active_object.name = "{obj_name}"
    result = {{"name": bpy.context.active_object.name}}
else:
    result = {{"error": "创建对象失败"}}
result
"""
                result = await ipc_client.execute_in_blender(code)
                message = f"已创建圆柱体 '{obj_name}'，位置: ({location.get('x', 0)}, {location.get('y', 0)}, {location.get('z', 0)}), 半径: {radius}, 高度: {depth}"
                return [types.TextContent(type="text", text=message)]
                
            elif name == "创建平面":
                location = arguments.get("location", {"x": 0, "y": 0, "z": 0})
                size = arguments.get("size", 2.0)
                obj_name = arguments.get("name", "平面")
                
                code = f"""
import bpy
bpy.ops.mesh.primitive_plane_add(
    size={size},
    location=({location.get('x', 0)}, {location.get('y', 0)}, {location.get('z', 0)})
)
if bpy.context.active_object:
    bpy.context.active_object.name = "{obj_name}"
    result = {{"name": bpy.context.active_object.name}}
else:
    result = {{"error": "创建对象失败"}}
result
"""
                result = await ipc_client.execute_in_blender(code)
                message = f"已创建平面 '{obj_name}'，位置: ({location.get('x', 0)}, {location.get('y', 0)}, {location.get('z', 0)}), 大小: {size}"
                return [types.TextContent(type="text", text=message)]
            
            # 2. 对象操作工具
            elif name == "移动对象":
                object_name = arguments.get("object_name", "")
                location = arguments.get("location", {"x": 0, "y": 0, "z": 0})
                
                code = f"""
import bpy
result = {{"status": "error", "message": "对象未找到"}}
if "{object_name}" in bpy.data.objects:
    obj = bpy.data.objects["{object_name}"]
    obj.location = ({location.get('x', 0)}, {location.get('y', 0)}, {location.get('z', 0)})
    result = {{"status": "success", "location": [obj.location.x, obj.location.y, obj.location.z]}}
result
"""
                result = await ipc_client.execute_in_blender(code)
                if isinstance(result, dict) and result.get("status") == "success":
                    message = f"已移动对象 '{object_name}' 到位置: ({location.get('x', 0)}, {location.get('y', 0)}, {location.get('z', 0)})"
                else:
                    message = f"移动对象失败: {result.get('message', '未知错误')}"
                return [types.TextContent(type="text", text=message)]
                
            elif name == "旋转对象":
                object_name = arguments.get("object_name", "")
                rotation = arguments.get("rotation", {"x": 0, "y": 0, "z": 0})
                
                code = f"""
import bpy
result = {{"status": "error", "message": "对象未找到"}}
if "{object_name}" in bpy.data.objects:
    obj = bpy.data.objects["{object_name}"]
    obj.rotation_euler = ({rotation.get('x', 0)}, {rotation.get('y', 0)}, {rotation.get('z', 0)})
    result = {{"status": "success", "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z]}}
result
"""
                result = await ipc_client.execute_in_blender(code)
                if isinstance(result, dict) and result.get("status") == "success":
                    message = f"已旋转对象 '{object_name}', 旋转角度: ({rotation.get('x', 0)}, {rotation.get('y', 0)}, {rotation.get('z', 0)}) 弧度"
                else:
                    message = f"旋转对象失败: {result.get('message', '未知错误')}"
                return [types.TextContent(type="text", text=message)]
                
            elif name == "缩放对象":
                object_name = arguments.get("object_name", "")
                scale = arguments.get("scale", {"x": 1, "y": 1, "z": 1})
                
                code = f"""
import bpy
result = {{"status": "error", "message": "对象未找到"}}
if "{object_name}" in bpy.data.objects:
    obj = bpy.data.objects["{object_name}"]
    obj.scale = ({scale.get('x', 1)}, {scale.get('y', 1)}, {scale.get('z', 1)})
    result = {{"status": "success", "scale": [obj.scale.x, obj.scale.y, obj.scale.z]}}
result
"""
                result = await ipc_client.execute_in_blender(code)
                if isinstance(result, dict) and result.get("status") == "success":
                    message = f"已缩放对象 '{object_name}', 缩放比例: ({scale.get('x', 1)}, {scale.get('y', 1)}, {scale.get('z', 1)})"
                else:
                    message = f"缩放对象失败: {result.get('message', '未知错误')}"
                return [types.TextContent(type="text", text=message)]
                
            elif name == "复制对象":
                source_name = arguments.get("source_name", "")
                new_name = arguments.get("new_name", source_name + ".复制")
                location = arguments.get("location", {"x": 0, "y": 0, "z": 0})
                
                code = f"""
import bpy
result = {{"status": "error", "message": "源对象未找到"}}
if "{source_name}" in bpy.data.objects:
    # 复制对象
    orig_obj = bpy.data.objects["{source_name}"]
    new_obj = orig_obj.copy()
    new_obj.data = orig_obj.data.copy()
    new_obj.name = "{new_name}"
    new_obj.location = ({location.get('x', 0)}, {location.get('y', 0)}, {location.get('z', 0)})
    
    # 添加到场景集合
    bpy.context.collection.objects.link(new_obj)
    
    result = {{"status": "success", "name": new_obj.name, "location": [new_obj.location.x, new_obj.location.y, new_obj.location.z]}}
result
"""
                result = await ipc_client.execute_in_blender(code)
                if isinstance(result, dict) and result.get("status") == "success":
                    message = f"已复制对象 '{source_name}' 到 '{new_name}', 位置: ({location.get('x', 0)}, {location.get('y', 0)}, {location.get('z', 0)})"
                else:
                    message = f"复制对象失败: {result.get('message', '未知错误')}"
                return [types.TextContent(type="text", text=message)]
                
            elif name == "删除对象":
                object_name = arguments.get("object_name", "")
                
                code = f"""
import bpy
result = {{"status": "error", "message": "对象未找到"}}
if "{object_name}" in bpy.data.objects:
    obj = bpy.data.objects["{object_name}"]
    bpy.data.objects.remove(obj)
    result = {{"status": "success", "message": "对象已删除"}}
result
"""
                result = await ipc_client.execute_in_blender(code)
                if isinstance(result, dict) and result.get("status") == "success":
                    message = f"已删除对象 '{object_name}'"
                else:
                    message = f"删除对象失败: {result.get('message', '未知错误')}"
                return [types.TextContent(type="text", text=message)]
            
            # 3. 材质工具
            elif name == "创建材质":
                mat_name = arguments.get("name", "新材质")
                color = arguments.get("color", {"r": 0.8, "g": 0.8, "b": 0.8})
                metallic = arguments.get("metallic", 0.0)
                roughness = arguments.get("roughness", 0.5)
                
                code = f"""
import bpy
# 创建新材质
mat = bpy.data.materials.new(name="{mat_name}")
mat.use_nodes = True
nodes = mat.node_tree.nodes

# 清除默认节点
for node in nodes:
    nodes.remove(node)

# 创建主要着色器节点
output = nodes.new(type='ShaderNodeOutputMaterial')
principled = nodes.new(type='ShaderNodeBsdfPrincipled')

# 设置材质属性
principled.inputs['Base Color'].default_value = ({color.get('r', 0.8)}, {color.get('g', 0.8)}, {color.get('b', 0.8)}, 1.0)
principled.inputs['Metallic'].default_value = {metallic}
principled.inputs['Roughness'].default_value = {roughness}

# 连接节点
mat.node_tree.links.new(principled.outputs[0], output.inputs[0])

result = {{"status": "success", "name": mat.name}}
result
"""
                result = await ipc_client.execute_in_blender(code)
                message = f"已创建材质 '{mat_name}', 颜色: RGB({color.get('r', 0.8)}, {color.get('g', 0.8)}, {color.get('b', 0.8)}), 金属度: {metallic}, 粗糙度: {roughness}"
                return [types.TextContent(type="text", text=message)]
                
            elif name == "应用材质":
                object_name = arguments.get("object_name", "")
                material_name = arguments.get("material_name", "")
                
                code = f"""
import bpy
result = {{"status": "error", "message": "对象或材质未找到"}}

if "{object_name}" in bpy.data.objects and "{material_name}" in bpy.data.materials:
    obj = bpy.data.objects["{object_name}"]
    mat = bpy.data.materials["{material_name}"]
    
    # 清除现有材质
    if obj.data.materials:
        obj.data.materials.clear()
    
    # 应用新材质
    obj.data.materials.append(mat)
    result = {{"status": "success", "message": "材质已应用"}}

result
"""
                result = await ipc_client.execute_in_blender(code)
                if isinstance(result, dict) and result.get("status") == "success":
                    message = f"已将材质 '{material_name}' 应用到对象 '{object_name}'"
                else:
                    message = f"应用材质失败: {result.get('message', '未知错误')}"
                return [types.TextContent(type="text", text=message)]
            
            # 4. 场景工具
            elif name == "新建场景":
                scene_name = arguments.get("name", "新场景")
                clear_all = arguments.get("clear_all", False)
                
                code = f"""
import bpy
# 创建新场景
new_scene = bpy.data.scenes.new(name="{scene_name}")
bpy.context.window.scene = new_scene

# 清除所有对象
if {str(clear_all).lower()}:
    for obj in new_scene.objects:
        bpy.data.objects.remove(obj)

result = {{"status": "success", "name": new_scene.name}}
result
"""
                result = await ipc_client.execute_in_blender(code)
                message = f"已创建新场景 '{scene_name}'" + ("并清除所有对象" if clear_all else "")
                return [types.TextContent(type="text", text=message)]
                
            elif name == "切换场景":
                scene_name = arguments.get("name", "")
                
                code = f"""
import bpy
result = {{"status": "error", "message": "场景未找到"}}

if "{scene_name}" in bpy.data.scenes:
    bpy.context.window.scene = bpy.data.scenes["{scene_name}"]
    result = {{"status": "success", "name": bpy.context.scene.name}}

result
"""
                result = await ipc_client.execute_in_blender(code)
                if isinstance(result, dict) and result.get("status") == "success":
                    message = f"已切换到场景 '{scene_name}'"
                else:
                    message = f"切换场景失败: {result.get('message', '未知错误')}"
                return [types.TextContent(type="text", text=message)]
                
            elif name == "添加光源":
                light_type = arguments.get("type", "POINT")
                light_name = arguments.get("name", f"{light_type}光源")
                location = arguments.get("location", {"x": 0, "y": 0, "z": 5})
                energy = arguments.get("energy", 1000)
                
                code = f"""
import bpy
light_data = bpy.data.lights.new(name="{light_name}", type="{light_type}")
light_data.energy = {energy}

light_obj = bpy.data.objects.new(name="{light_name}", object_data=light_data)
light_obj.location = ({location.get('x', 0)}, {location.get('y', 0)}, {location.get('z', 5)})

bpy.context.collection.objects.link(light_obj)

result = {{"status": "success", "name": light_obj.name}}
result
"""
                result = await ipc_client.execute_in_blender(code)
                message = f"已添加{light_type}光源 '{light_name}', 位置: ({location.get('x', 0)}, {location.get('y', 0)}, {location.get('z', 5)}), 强度: {energy}"
                return [types.TextContent(type="text", text=message)]
                
            elif name == "添加相机":
                camera_name = arguments.get("name", "相机")
                location = arguments.get("location", {"x": 0, "y": -10, "z": 5})
                rotation = arguments.get("rotation", {"x": 1.0, "y": 0, "z": 0})
                
                code = f"""
import bpy
# 创建相机数据
cam_data = bpy.data.cameras.new(name="{camera_name}")
cam_obj = bpy.data.objects.new(name="{camera_name}", object_data=cam_data)

# 设置位置和旋转
cam_obj.location = ({location.get('x', 0)}, {location.get('y', -10)}, {location.get('z', 5)})
cam_obj.rotation_euler = ({rotation.get('x', 1.0)}, {rotation.get('y', 0)}, {rotation.get('z', 0)})

# 添加到场景
bpy.context.collection.objects.link(cam_obj)

# 设置为活动相机
bpy.context.scene.camera = cam_obj

result = {{"status": "success", "name": cam_obj.name}}
result
"""
                result = await ipc_client.execute_in_blender(code)
                message = f"已添加相机 '{camera_name}', 位置: ({location.get('x', 0)}, {location.get('y', -10)}, {location.get('z', 5)})"
                return [types.TextContent(type="text", text=message)]
            
            # 5. 渲染工具
            elif name == "设置渲染参数":
                engine = arguments.get("engine", "CYCLES")
                resolution_x = arguments.get("resolution_x", 1920)
                resolution_y = arguments.get("resolution_y", 1080)
                samples = arguments.get("samples", 128)
                
                code = f"""
import bpy
render = bpy.context.scene.render

# 设置渲染引擎
render.engine = '{engine}'

# 设置分辨率
render.resolution_x = {resolution_x}
render.resolution_y = {resolution_y}

# 设置采样数
if render.engine == 'CYCLES':
    bpy.context.scene.cycles.samples = {samples}
elif render.engine == 'BLENDER_EEVEE':
    bpy.context.scene.eevee.taa_render_samples = {samples}

result = {{
    "status": "success",
    "engine": render.engine,
    "resolution": {{"x": render.resolution_x, "y": render.resolution_y}},
    "samples": {samples}
}}
result
"""
                result = await ipc_client.execute_in_blender(code)
                message = f"已设置渲染参数: 引擎={engine}, 分辨率={resolution_x}x{resolution_y}, 采样数={samples}"
                return [types.TextContent(type="text", text=message)]
                
            elif name == "渲染图像":
                filepath = arguments.get("filepath", "//render.png")
                file_format = arguments.get("file_format", "PNG")
                
                code = f"""
import bpy
render = bpy.context.scene.render

# 设置输出路径和格式
render.filepath = "{filepath}"
render.image_settings.file_format = "{file_format}"

# 执行渲染
bpy.ops.render.render(write_still=True)

result = {{"status": "success", "filepath": render.filepath}}
result
"""
                result = await ipc_client.execute_in_blender(code)
                message = f"已渲染图像并保存到 {filepath}, 格式: {file_format}"
                return [types.TextContent(type="text", text=message)]
            
            # 6. 动画工具
            elif name == "设置关键帧":
                object_name = arguments.get("object_name", "")
                property_name = arguments.get("property", "location")
                frame = arguments.get("frame", 1)
                
                code = f"""
import bpy
result = {{"status": "error", "message": "对象未找到"}}

if "{object_name}" in bpy.data.objects:
    obj = bpy.data.objects["{object_name}"]
    # 设置当前帧
    bpy.context.scene.frame_set({frame})
    
    # 根据属性类型设置关键帧
    if "{property_name}" == "location":
        obj.keyframe_insert(data_path="location")
        result = {{"status": "success", "property": "location", "frame": {frame}}}
    elif "{property_name}" == "rotation":
        obj.keyframe_insert(data_path="rotation_euler")
        result = {{"status": "success", "property": "rotation", "frame": {frame}}}
    elif "{property_name}" == "scale":
        obj.keyframe_insert(data_path="scale")
        result = {{"status": "success", "property": "scale", "frame": {frame}}}
    else:
        result = {{"status": "error", "message": "不支持的属性"}}

result
"""
                result = await ipc_client.execute_in_blender(code)
                if isinstance(result, dict) and result.get("status") == "success":
                    message = f"已为对象 '{object_name}' 的 {property_name} 在帧 {frame} 设置关键帧"
                else:
                    message = f"设置关键帧失败: {result.get('message', '未知错误')}"
                return [types.TextContent(type="text", text=message)]
                
            elif name == "设置动画范围":
                start_frame = arguments.get("start_frame", 1)
                end_frame = arguments.get("end_frame", 250)
                fps = arguments.get("fps", 24)
                
                code = f"""
import bpy
scene = bpy.context.scene

# 设置开始和结束帧
scene.frame_start = {start_frame}
scene.frame_end = {end_frame}

# 设置帧率
scene.render.fps = {fps}

result = {{
    "status": "success", 
    "start": scene.frame_start,
    "end": scene.frame_end,
    "fps": scene.render.fps
}}
result
"""
                result = await ipc_client.execute_in_blender(code)
                message = f"已设置动画范围: 开始帧={start_frame}, 结束帧={end_frame}, 帧率={fps} FPS"
                return [types.TextContent(type="text", text=message)]
            
            # 7. 通用工具
            elif name == "执行代码":
                code = arguments.get("code", "")
                if not code:
                    return [types.TextContent(type="text", text="请提供要执行的Python代码")]
                
                try:
                    result = await ipc_client.execute_in_blender(code)
                    try:
                        if isinstance(result, (dict, list)):
                            result_str = json.dumps(result, indent=2, ensure_ascii=False)
                        else:
                            result_str = str(result)
                    except:
                        result_str = str(result)
                    return [types.TextContent(type="text", text=f"代码执行结果:\n{result_str}")]
                except Exception as e:
                    return [types.TextContent(type="text", text=f"代码执行错误: {str(e)}")]
                
            elif name == "列出对象":
                type_filter = arguments.get("type_filter", "")
                
                code = f"""
import bpy
result = []

for obj in bpy.data.objects:
    if not "{type_filter}" or obj.type == "{type_filter}":
        result.append({{
            "name": obj.name,
            "type": obj.type,
            "visible": obj.visible_get(),
            "location": [round(obj.location.x, 3), round(obj.location.y, 3), round(obj.location.z, 3)],
            "dimensions": [round(obj.dimensions.x, 3), round(obj.dimensions.y, 3), round(obj.dimensions.z, 3)]
        }})

result
"""
                result = await ipc_client.execute_in_blender(code)
                if isinstance(result, list):
                    if result:
                        objects_info = json.dumps(result, indent=2, ensure_ascii=False)
                        type_msg = f"类型为 {type_filter} 的" if type_filter else ""
                        message = f"场景中{type_msg}对象列表 (共 {len(result)} 个):\n{objects_info}"
                    else:
                        type_msg = f"类型为 {type_filter} 的" if type_filter else ""
                        message = f"场景中没有{type_msg}对象"
                else:
                    message = f"获取对象列表失败: {result}"
                return [types.TextContent(type="text", text=message)]
            
            # 8. 测试连接
            elif name == "测试连接":
                message = arguments.get("message", "Hello Blender")
                code = f"""
import bpy
result = {{
    "blender_version": bpy.app.version_string,
    "message_received": "{message}",
    "status": "连接成功"
}}
result
"""
                try:
                    print("发送测试连接代码...")
                    result = await ipc_client.execute_in_blender(code)
                    print(f"测试连接结果: {result}")
                    return [types.TextContent(type="text", text=f"连接测试结果:\n{json.dumps(result, indent=2, ensure_ascii=False)}")]
                except Exception as e:
                    error_msg = f"测试连接失败: {str(e)}"
                    print(error_msg)
                    return [types.TextContent(type="text", text=error_msg)]
            
            # 未知工具
            else:
                return [types.TextContent(type="text", text=f"未知工具: {name}")]
                
        except Exception as e:
            error_message = f"工具执行错误: {str(e)}"
            print(error_message)
            return [types.TextContent(type="text", text=error_message)]

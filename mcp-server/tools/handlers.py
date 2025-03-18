import mcp.types as types
from .schemas import *
import json

def register_tool_handlers(server, ipc_client):
    """注册所有Blender工具处理程序"""
    
    @server.list_tools()
    async def handle_list_tools():
        """列出可用的Blender工具"""

        tool_resources = await ipc_client.send_request({"action": "list_tools"})
        print(f"MCP服务器：获取到的工具列表: {tool_resources}")
        
        print("MCP服务器：处理list_tools请求")
        tools = [
            # 1. 基础对象创建工具
            types.Tool(
                name="create_object",
                description="在Blender中创建一个对象",
                inputSchema={
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
            ),
            
            # 2. 材质工具
            types.Tool(
                name="set_material",
                description="为对象设置材质",
                inputSchema={
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
                        },
                        "specular": {
                            "type": "number",
                            "description": "镜面反射强度(0-1)",
                            "default": 0.5
                        }
                    },
                    "required": ["object_name"]
                }
            ),
            
            # 3. 灯光工具
            types.Tool(
                name="add_light",
                description="添加灯光到场景",
                inputSchema={
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
            ),
            
            # 4. 相机工具
            types.Tool(
                name="set_camera",
                description="设置相机位置和属性",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "相机位置 [x, y, z]"
                        },
                        "rotation": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "相机旋转(弧度) [x, y, z]"
                        },
                        "name": {
                            "type": "string",
                            "description": "相机名称(可选)"
                        },
                        "lens": {
                            "type": "number",
                            "description": "镜头焦距(mm)"
                        }
                    },
                    "required": ["location", "rotation"]
                }
            ),
            
            # 5. 渲染工具
            types.Tool(
                name="render_scene",
                description="渲染场景并返回结果",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "output_path": {
                            "type": "string",
                            "description": "输出文件路径(可选)"
                        },
                        "resolution_x": {
                            "type": "integer",
                            "description": "渲染宽度"
                        },
                        "resolution_y": {
                            "type": "integer",
                            "description": "渲染高度"
                        },
                        "samples": {
                            "type": "integer",
                            "description": "采样数(Cycles渲染)"
                        }
                    }
                }
            ),
            
            # 6. 修改器工具
            types.Tool(
                name="apply_modifier",
                description="向对象应用修改器",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "object_name": {
                            "type": "string",
                            "description": "目标对象名称"
                        },
                        "modifier_type": {
                            "type": "string",
                            "enum": ["SUBSURF", "BEVEL", "SOLIDIFY", "ARRAY", "MIRROR"],
                            "description": "修改器类型"
                        },
                        "parameters": {
                            "type": "object",
                            "description": "修改器特定参数"
                        }
                    },
                    "required": ["object_name", "modifier_type"]
                }
            ),
            
            # 7. 对象变换工具
            types.Tool(
                name="transform_object",
                description="转换对象位置、旋转或缩放",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "object_name": {
                            "type": "string",
                            "description": "目标对象名称"
                        },
                        "location": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "位置 [x, y, z]"
                        },
                        "rotation": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "旋转(弧度) [x, y, z]"
                        },
                        "scale": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "缩放 [x, y, z]"
                        }
                    },
                    "required": ["object_name"]
                }
            ),
            
            # 8. 模型导入工具
            types.Tool(
                name="import_model",
                description="导入3D模型文件",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "文件路径"
                        },
                        "import_type": {
                            "type": "string",
                            "enum": ["OBJ", "FBX", "GLB", "STL"],
                            "description": "导入文件类型"
                        }
                    },
                    "required": ["file_path", "import_type"]
                }
            ),
            
            # 9. Python代码执行工具
            types.Tool(
                name="execute_python",
                description="在Blender中执行Python代码",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "要执行的Python代码"
                        }
                    },
                    "required": ["code"]
                }
            ),
            
            # 10. 挤出面工具
            types.Tool(
                name="extrude_faces",
                description="挤出面",
                inputSchema=EXTRUDE_FACES_SCHEMA
            ),
            
            # 11. 细分网格工具
            types.Tool(
                name="subdivide_mesh",
                description="细分网格",
                inputSchema=SUBDIVIDE_MESH_SCHEMA
            ),
            
            # 12. 环切工具
            types.Tool(
                name="loop_cut",
                description="环切",
                inputSchema=LOOP_CUT_SCHEMA
            ),
            
            # 13. 设置顶点位置工具
            types.Tool(
                name="set_vertex_position",
                description="设置顶点位置",
                inputSchema=SET_VERTEX_POSITION_SCHEMA
            ),
            
            # 14. 创建动画工具
            types.Tool(
                name="create_animation",
                description="创建动画",
                inputSchema=CREATE_ANIMATION_SCHEMA
            ),
            
            # 15. 创建节点材质工具
            types.Tool(
                name="create_node_material",
                description="创建节点材质",
                inputSchema=CREATE_NODE_MATERIAL_SCHEMA
            ),
            
            # 16. 设置UV映射工具
            types.Tool(
                name="set_uv_mapping",
                description="设置UV映射",
                inputSchema=SET_UV_MAPPING_SCHEMA
            ),
            
            # 17. 合并对象工具
            types.Tool(
                name="join_objects",
                description="合并对象",
                inputSchema=JOIN_OBJECTS_SCHEMA
            ),
            
            # 18. 分离网格工具
            types.Tool(
                name="separate_mesh",
                description="分离网格",
                inputSchema=SEPARATE_MESH_SCHEMA
            ),
            
            # 19. 创建文本工具
            types.Tool(
                name="create_text",
                description="创建3D文本",
                inputSchema=CREATE_TEXT_SCHEMA
            ),
            
            # 20. 创建曲线工具
            types.Tool(
                name="create_curve",
                description="创建曲线",
                inputSchema=CREATE_CURVE_SCHEMA
            ),
            
            # 21. 创建粒子系统工具
            types.Tool(
                name="create_particle_system",
                description="创建粒子系统",
                inputSchema=CREATE_PARTICLE_SYSTEM_SCHEMA
            ),
            
            # 22. 高级灯光工具
            types.Tool(
                name="advanced_lighting",
                description="创建高级灯光",
                inputSchema=ADVANCED_LIGHTING_SCHEMA
            )
        ]
        
        print(f"MCP服务器：返回 {len(tools)} 个工具")
        return tools
        
    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None = None):
        """调用Blender工具"""
        print(f"MCP服务器：调用工具 {name}，参数: {arguments}")
        arguments = arguments or {}
        
        try:
            # 使用正确的IPC请求格式
            request = {
                "action": "call_tool",
                "tool": name,
                "arguments": arguments
            }
            
            # 发送请求到Blender
            result = await ipc_client.send_request(request)
            
            # 检查结果
            if "error" in result:
                error_message = f"工具调用错误: {result['error']}"
                print(error_message)
                return [types.TextContent(
                    type="text",
                    text=json.dumps({"error": error_message})
                )]
            
            # 返回工具执行结果
            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
            
        except Exception as e:
            error_message = f"工具调用异常: {str(e)}"
            print(error_message)
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": error_message})
            )]

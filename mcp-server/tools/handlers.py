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
                        "color": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "RGBA颜色值 [r, g, b, a]"
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

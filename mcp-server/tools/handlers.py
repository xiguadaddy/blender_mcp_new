import logging
import json
from typing import List, Dict, Any, Optional, Union
import time
import mcp.types as types
import traceback

# 配置日志
logger = logging.getLogger("BlenderMCP.Server")

# 添加预定义工具列表，在无法从Blender获取工具时使用
PREDEFINED_TOOLS = [
    {
        "name": "create_object",
        "description": "创建3D对象，如立方体、球体、平面等",
        "schema": {
            "type": "object",
            "properties": {
                "object_type": {
                    "type": "string",
                    "title": "对象类型",
                    "description": "要创建的3D对象类型",
                    "enum": ["cube", "sphere", "plane", "cylinder", "cone", "torus"]
                },
                "name": {
                    "type": "string",
                    "title": "名称",
                    "description": "新对象的名称"
                },
                "location": {
                    "type": "array",
                    "title": "位置",
                    "description": "对象的位置坐标 [x, y, z]",
                    "items": {
                        "type": "number"
                    }
                },
                "size": {
                    "type": "number",
                    "title": "尺寸",
                    "description": "对象的整体尺寸"
                }
            },
            "required": ["object_type"]
        }
    },
    {
        "name": "set_material",
        "description": "为对象设置材质属性",
        "schema": {
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
                    "description": "要创建或应用的材质名称"
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
                    "description": "材质的金属度 (0.0 - 1.0)"
                },
                "roughness": {
                    "type": "number",
                    "title": "粗糙度",
                    "description": "材质的粗糙度 (0.0 - 1.0)"
                }
            },
            "required": ["object_name"]
        }
    },
    {
        "name": "add_light",
        "description": "添加光源到场景",
        "schema": {
            "type": "object",
            "properties": {
                "light_type": {
                    "type": "string",
                    "title": "光源类型",
                    "description": "要添加的光源类型",
                    "enum": ["point", "sun", "spot", "area"]
                },
                "name": {
                    "type": "string",
                    "title": "名称",
                    "description": "光源的名称"
                },
                "location": {
                    "type": "array",
                    "title": "位置",
                    "description": "光源的位置坐标 [x, y, z]",
                    "items": {
                        "type": "number"
                    }
                },
                "energy": {
                    "type": "number",
                    "title": "能量/强度",
                    "description": "光源的强度值"
                },
                "color": {
                    "type": "array",
                    "title": "颜色",
                    "description": "RGB颜色值 [r, g, b]",
                    "items": {
                        "type": "number"
                    }
                }
            },
            "required": ["light_type"]
        }
    },
    {
        "name": "set_camera",
        "description": "设置相机参数或创建新相机",
        "schema": {
            "type": "object",
            "properties": {
                "camera_name": {
                    "type": "string",
                    "title": "相机名称",
                    "description": "要设置的相机名称，若不存在则创建新相机"
                },
                "location": {
                    "type": "array",
                    "title": "位置",
                    "description": "相机的位置坐标 [x, y, z]",
                    "items": {
                        "type": "number"
                    }
                },
                "rotation": {
                    "type": "array",
                    "title": "旋转",
                    "description": "相机的旋转欧拉角 [x, y, z]，单位为弧度",
                    "items": {
                        "type": "number"
                    }
                },
                "focal_length": {
                    "type": "number",
                    "title": "焦距",
                    "description": "相机的焦距，单位为毫米"
                }
            },
            "required": ["camera_name"]
        }
    },
    {
        "name": "render_scene",
        "description": "渲染当前场景",
        "schema": {
            "type": "object",
            "properties": {
                "output_path": {
                    "type": "string",
                    "title": "输出路径",
                    "description": "渲染输出的文件路径"
                },
                "resolution_x": {
                    "type": "integer",
                    "title": "分辨率X",
                    "description": "输出图像的宽度（像素）"
                },
                "resolution_y": {
                    "type": "integer",
                    "title": "分辨率Y",
                    "description": "输出图像的高度（像素）"
                },
                "render_engine": {
                    "type": "string",
                    "title": "渲染引擎",
                    "description": "要使用的渲染引擎",
                    "enum": ["CYCLES", "BLENDER_EEVEE", "WORKBENCH"]
                },
                "samples": {
                    "type": "integer",
                    "title": "采样数",
                    "description": "渲染的采样次数"
                }
            }
        }
    }
]

def register_tool_handlers(server, ipc_client):
    """注册所有Blender工具处理器"""
    
    @server.list_tools()
    async def handle_list_tools() -> List[types.Tool]:
        """处理工具列表请求，返回可用工具列表
        
        首先返回预定义工具确保快速响应，同时尝试从Blender获取更多工具
        
        Returns:
            List[types.Tool]: MCP工具对象列表
        """
        logger.info("正在处理list_tools请求，准备获取工具数据...")
        
        try:
            # 初始化预定义工具列表 - 总是可用
            mcp_tools = []
            for tool in PREDEFINED_TOOLS:
                try:
                    mcp_tool = types.Tool(
                        name=tool["name"],
                        description=tool.get("description", None),
                        inputSchema=tool.get("schema", None)
                    )
                    mcp_tools.append(mcp_tool)
                except Exception as tool_err:
                    logger.error(f"创建预定义工具时出错: {str(tool_err)}")
            
            logger.info(f"已准备 {len(mcp_tools)} 个预定义工具")
            
            # 通过IPC获取Blender中的更多工具，使用重试机制
            try:
                logger.info("尝试使用MCP标准格式获取工具...")
                results = await ipc_client.send_request_with_retry({
                        "method": "mcp/listTools",
                        "params": {}
                    })
                
                tools_data = results['result'].get('tools', [])
                
                # 检查返回结果
                if isinstance(tools_data, list) and len(tools_data) > 0:
                    logger.debug(f"从Blender获取到 {len(tools_data)} 个额外工具")
                    
                    # 创建工具名称集合以避免重复
                    existing_tool_names = {tool.name for tool in mcp_tools}
                    
                    # 添加Blender提供的工具
                    for tool_data in tools_data:
                        try:
                            # 检查必要的字段
                            tool_name = str(tool_data.get("name", tool_data.get("id", "")))
                            if not tool_name or tool_name in existing_tool_names:
                                continue
                            
                            # 获取工具描述，确保为字符串类型
                            description = tool_data.get("description", "")
                            if not isinstance(description, str):
                                description = str(description)
                            
                            # 处理输入模式 - 关键是只处理为None的情况
                            input_schema = tool_data.get('input_schema')
                            
                            # 仅当input_schema为None时才设置默认值
                            if input_schema is None:
                                input_schema = {"type": "object", "properties": {}, "required": []}
                            
                            # 创建MCP工具对象
                            mcp_tool = types.Tool(
                                name=tool_name,
                                description=description if description else None,
                                inputSchema=input_schema
                            )
                            
                            mcp_tools.append(mcp_tool)
                            existing_tool_names.add(tool_name)

                        except Exception as tool_err:
                            logger.error(f"处理Blender工具时出错: {str(tool_err)}")
                            continue
                else:
                    logger.warning("从Blender获取工具列表失败或为空，仅使用预定义工具")
            except Exception as e:
                logger.error(f"获取Blender工具列表时出错: {str(e)}")
                logger.warning("仅使用预定义工具列表")
            
            logger.info(f"最终返回 {len(mcp_tools)} 个可用工具")
            return mcp_tools
                
        except Exception as e:
            logger.error(f"列出工具时发生错误: {str(e)}")
            
            # 在出错时确保至少返回预定义工具列表
            try:
                backup_tools = []
                for tool in PREDEFINED_TOOLS:
                    try:
                        backup_tools.append(types.Tool(
                            name=tool["name"],
                            description=tool.get("description", None),
                            inputSchema=tool.get("schema", None)
                        ))
                    except Exception:
                        pass
                
                logger.info(f"返回 {len(backup_tools)} 个预定义工具作为后备方案")
                return backup_tools
            except Exception as final_err:
                logger.error(f"创建后备工具列表也失败: {str(final_err)}")
                return []
    
    @server.call_tool()
    async def handle_call_tool(tool_name: str, tool_args: Dict[str, Any]) -> types.CallToolResult:
        """
        处理工具调用请求
        
        Args:
            tool_name: 工具名称
            tool_args: 工具参数
            
        Returns:
            工具调用结果
        """
        print(f"处理工具调用: {tool_name}, {tool_args}")
        logger.debug(f"调用工具: {tool_name}, 参数: {tool_args}")
        
        try:
            # 调用Blender中的工具
            logger.info(f"发送MCP工具请求到Blender: {tool_name}")
            
            # 构建请求
            blender_request = {
                "jsonrpc": "2.0",
                "id": f"tool_call_{int(time.time() * 1000000)}",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": tool_args or {}
                },
                "arguments": {}  # 兼容旧格式
            }
            
            # 发送请求
            logger.debug(f"发送请求: {blender_request}")
            response = await ipc_client.send_request(blender_request)
            logger.debug(f"原始响应类型: {type(response)}")
            logger.debug(f"原始响应数据: {json.dumps(response, ensure_ascii=False)}")
            
            # 从响应中提取result
            result = response.get("result", {})
            content = result.get("content", [])
            
            # 检查content格式
            logger.debug(f"响应content类型: {type(content)}")
            if content and len(content) > 0:
                logger.debug(f"响应content[0]类型: {type(content[0])}")
                logger.debug(f"响应content[0]数据: {json.dumps(content[0], ensure_ascii=False)}")
            
            # 确保结果是标准格式
            return_obj = {
                "content": content,
                "isError": result.get("isError", False)
            }
            
            logger.debug(f"返回对象类型: {type(return_obj)}")
            logger.debug(f"返回对象是否包含content字段: {return_obj.get('content') is not None}")
            logger.debug(f"返回对象是否包含isError字段: {return_obj.get('isError') is not None}")
            
            # 创建并返回CallToolResult实例
            logger.info(f"工具 {tool_name} 调用成功（MCP格式）")
            return types.CallToolResult(
                content=content,
                isError=result.get("isError", False)
            )
            
        except Exception as e:
            logger.error(f"调用工具 {tool_name} 时出错: {str(e)}")
            logger.error(traceback.format_exc())
            
            # 返回错误结果
            error_content = [{"type": "text", "text": f"调用工具时出错: {str(e)}"}]
            return types.CallToolResult(
                content=error_content,
                isError=True
            )

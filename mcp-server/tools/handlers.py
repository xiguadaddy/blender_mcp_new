import logging
import json
from mcp.server import Server
import mcp.types as types
from .schemas import *

# 配置日志
logger = logging.getLogger("BlenderMCP.Server")

def register_tool_handlers(server, ipc_client):
    """注册所有Blender工具处理器"""
    
    @server.list_tools()
    async def handle_list_tools():
        """处理工具列表请求"""
        logger.debug("处理工具列表请求")
        
        try:
            # 通过IPC获取Blender中的所有工具
            tools_data = ipc_client.send_request({"action": "list_tools"})
            
            # 检查返回结果
            if isinstance(tools_data, dict) and "error" in tools_data:
                logger.error(f"获取工具列表失败: {tools_data['error']}")
                return []
            
            if not isinstance(tools_data, list):
                logger.error(f"工具数据格式错误: {type(tools_data)}")
                return []
            
            logger.debug(f"从Blender获取到 {len(tools_data)} 个工具")
            
            # 转换为MCP工具格式
            mcp_tools = []
            for tool in tools_data:
                tool_schema = {
                    "type": "object",
                    "properties": {}
                }
                
                # 如果工具有输入模式定义，使用它
                if "input_schema" in tool:
                    tool_schema = tool["input_schema"]
                    
                # 构建MCP工具对象
                mcp_tool = types.Tool(
                    name=tool["name"],
                    description=tool["description"],
                    inputSchema=tool_schema
                )
                mcp_tools.append(mcp_tool)
            
            logger.info(f"返回 {len(mcp_tools)} 个可用工具")
            return mcp_tools
        except Exception as e:
            logger.error(f"获取工具列表时出错: {str(e)}")
            return []
    
    @server.call_tool()
    async def handle_call_tool(name, arguments):
        """处理工具调用请求"""
        logger.debug(f"调用工具: {name}, 参数: {arguments}")
        
        try:
            # 通过IPC执行工具
            result = ipc_client.send_request({
                "action": "call_tool",
                "tool": name,
                "arguments": arguments
            })
            
            # 检查是否有错误
            if "error" in result:
                logger.error(f"工具 {name} 执行出错: {result['error']}")
                return types.CallToolResult(
                    isError=True,
                    content=[types.TextContent(
                        type="text",
                        text=f"工具执行出错: {result['error']}"
                    )]
                )
            
            # 将工具结果转换为可读文本
            result_text = json.dumps(result, ensure_ascii=False, indent=2)
            
            logger.debug(f"工具 {name} 执行成功")
            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=result_text
                )]
            )
            
        except Exception as e:
            logger.error(f"调用工具时出错: {str(e)}")
            return types.CallToolResult(
                isError=True,
                content=[types.TextContent(
                    type="text",
                    text=f"调用工具时出错: {str(e)}"
                )]
            )

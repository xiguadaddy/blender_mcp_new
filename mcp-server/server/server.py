from mcp.server import Server, NotificationOptions
import mcp.types as types
from resources.handlers import register_resource_handlers
from tools.handlers import register_tool_handlers
from prompts.handlers import register_prompt_handlers
import asyncio

def create_server(ipc_client):
    """创建并配置MCP服务器"""
    
    # 正确初始化Server
    server = Server("blender-mcp")
    
    # 注册常规处理程序
    print("注册资源处理程序...")
    register_resource_handlers(server, ipc_client)
    print("注册工具处理程序...")
    register_tool_handlers(server, ipc_client)
    print("注册提示处理程序...")
    register_prompt_handlers(server, ipc_client)
    
    # 添加服务器信息调试
    print(f"服务器类型: {type(server)}")
    print(f"服务器可用方法: {[method for method in dir(server) if not method.startswith('_')]}")
    
    # 注册完成后添加调试任务
    async def debug_handlers():
        """调试输出已注册的处理程序"""
        try:
            # 检查服务器对象是否有处理请求的方法
            if hasattr(server, "_request_handlers"):
                print(f"已注册的请求处理程序: {server._request_handlers.keys()}")
            
            if hasattr(server, "handle_message"):
                # 模拟listTools请求
                list_tools_msg = {
                    "jsonrpc": "2.0",
                    "id": "debug-1",
                    "method": "mcp/listTools",
                    "params": {}
                }
                resp = await server.handle_message(list_tools_msg)
                print(f"listTools响应: {resp}")
                
                # 模拟listResources请求
                list_resources_msg = {
                    "jsonrpc": "2.0",
                    "id": "debug-2",
                    "method": "mcp/listResources",
                    "params": {}
                }
                resp = await server.handle_message(list_resources_msg)
                print(f"listResources响应: {resp}")
        except Exception as e:
            print(f"调试处理程序时出错: {e}")
    
    # 创建调试任务
    asyncio.create_task(debug_handlers())
    
    print("所有处理程序注册完成")
    return server


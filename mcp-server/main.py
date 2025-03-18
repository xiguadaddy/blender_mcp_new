#!/usr/bin/env python3

import asyncio
import argparse
from server.server import create_server
from server.ipc_client import IPCClient
import mcp.server.stdio
import sys
from mcp.server import NotificationOptions
import os
import mcp.server.models

print("="*50)
print("MCP服务器启动")
print(f"Python版本: {sys.version}")
print(f"工作目录: {os.getcwd()}")
print("="*50)

async def main():
    parser = argparse.ArgumentParser(description="Blender MCP Server")
    parser.add_argument("--socket-path", default="port:27015" if sys.platform == "win32" else "/tmp/blender-mcp.sock",
                      help="IPC通信路径")
    
    args = parser.parse_args()
    
    # 打印连接信息以便调试
    print(f"尝试连接到Blender IPC服务器，通信路径: {args.socket_path}")
    
    # 初始化IPC客户端
    ipc_client = IPCClient(args.socket_path)
    await ipc_client.connect()
    
    # 创建并启动MCP服务器
    server = create_server(ipc_client)
    
    # 使用标准输入/输出来通信
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        print("MCP服务器: 准备启动服务器")
        server_name = "blender-mcp"
        server_version = "0.2.0"
        
        # 检查NotificationOptions的正确用法
        print("检查NotificationOptions参数...")
        try:
            # 尝试无参数初始化
            notification_options = NotificationOptions()
            print("使用默认NotificationOptions")
        except Exception as e:
            print(f"NotificationOptions初始化错误: {e}")
            # 如果失败，使用空字典
            notification_options = {}
        
        # 获取服务器能力
        capabilities = server.get_capabilities(
            notification_options=notification_options,
            experimental_capabilities={},
        )
        
        print(f"服务器信息: name={server_name}, version={server_version}")
        print(f"服务器能力: {capabilities}")
        print(f"MCP SDK 版本: {mcp.__version__ if hasattr(mcp, '__version__') else '未知'}")
        print("准备处理消息...")

        # 尝试获取Server对象的注册处理程序信息
        if hasattr(server, "_request_handlers"):
            print(f"已注册的请求处理程序: {list(server._request_handlers.keys())}")

        await server.run(
            read_stream,
            write_stream,
            mcp.server.models.InitializationOptions(
                server_name=server_name,
                server_version=server_version,
                capabilities=capabilities,
                protocol_version="0.3.0"
            ),
        )

    # 在服务器启动后添加
    print("添加调试任务...")
    async def debug_handlers():
        """测试资源和工具处理程序"""
        try:
            # 尝试直接调用资源列表处理程序
            print("测试资源列表处理程序...")
            resources = await server.handle_request("mcp/listResources", {})
            print(f"资源列表处理结果: {resources}")
            
            # 尝试获取处理程序信息
            if hasattr(server, "request_handlers"):
                print(f"注册的请求处理程序: {server.request_handlers.keys()}")
        except Exception as e:
            print(f"调试处理程序出错: {e}")

    # 创建任务
    asyncio.create_task(debug_handlers())

if __name__ == "__main__":
    asyncio.run(main())

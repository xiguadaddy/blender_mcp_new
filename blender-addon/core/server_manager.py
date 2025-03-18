import bpy
from ..ipc.server import start_ipc_server, stop_ipc_server
import sys

def start_server(socket_path, debug_mode=False):
    """启动MCP服务器"""
    print(f"[Blender MCP] 正在启动IPC服务器，通信路径: {socket_path}")
    start_ipc_server(socket_path, debug_mode)
    bpy.types._mcp_server_running = True
    # 保存socket_path以便MCP服务器能使用相同的路径连接
    bpy.types._mcp_socket_path = socket_path
    print(f"[Blender MCP] IPC服务器已启动，_mcp_socket_path = {bpy.types._mcp_socket_path}")

def stop_server():
    """停止MCP服务器"""
    stop_ipc_server()
    bpy.types._mcp_server_running = False
    if hasattr(bpy.types, "_mcp_socket_path"):
        delattr(bpy.types, "_mcp_socket_path")
    print("[Blender MCP] IPC服务器已停止")

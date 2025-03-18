import json
import socket
import asyncio
import sys
import os

class IPCClient:
    """负责与Blender插件通信的IPC客户端"""
    
    def __init__(self, socket_path):
        self.socket_path = socket_path
        self.socket = None
        self.is_windows = sys.platform == "win32"
        
        # Windows平台解析地址和端口
        if self.is_windows:
            if socket_path.startswith("port:"):
                self.port = int(socket_path.split(":", 1)[1])
            else:
                self.port = 27015
            self.host = "127.0.0.1"
        
    async def connect(self):
        """连接到Blender插件的IPC服务器"""
        retry_count = 0
        max_retries = 5
        
        while retry_count < max_retries:
            try:
                if self.is_windows:
                    # Windows使用TCP套接字
                    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.socket.connect((self.host, self.port))
                    print(f"已连接到Blender IPC服务器，地址: {self.host}:{self.port}")
                else:
                    # Unix/Linux使用Unix域套接字
                    self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    self.socket.connect(self.socket_path)
                    print(f"已连接到Blender IPC服务器，路径: {self.socket_path}")
                
                return True
            except (FileNotFoundError, ConnectionRefusedError) as e:
                print(f"等待IPC服务器启动 (尝试 {retry_count+1}/{max_retries})... 错误: {str(e)}")
                retry_count += 1
                await asyncio.sleep(2)
        
        raise ConnectionError("无法连接到Blender IPC服务器")
    
    async def send_request(self, data):
        """异步发送请求并获取响应"""
        message = json.dumps(data)
        
        # 创建异步任务来发送数据
        loop = asyncio.get_event_loop()
        await loop.sock_sendall(self.socket, f"{len(message)}:".encode() + message.encode())
        
        # 异步接收响应
        header = b""
        while b":" not in header:
            chunk = await loop.sock_recv(self.socket, 1)
            if not chunk:
                raise ConnectionError("连接已关闭")
            header += chunk
            
        length = int(header.decode().split(":")[0])
        response_data = b""
        while len(response_data) < length:
            chunk = await loop.sock_recv(self.socket, min(4096, length - len(response_data)))
            if not chunk:
                raise ConnectionError("连接已关闭")
            response_data += chunk
            
        return json.loads(response_data.decode())
    
    def close(self):
        """关闭连接"""
        if self.socket:
            self.socket.close()

    async def execute_in_blender(self, code):
        """在Blender中执行Python代码"""
        try:
            print(f"正在发送代码到Blender执行:\n{code}")
            
            # 使用正确的请求格式 - 通过call_tool操作执行Python代码
            request = {
                "action": "call_tool",
                "tool": "execute_python",  # 假设有这个工具
                "arguments": {
                    "code": code
                }
            }
            
            result = await self.send_request(request)
            print(f"Blender执行结果: {result}")
            return result
        except Exception as e:
            print(f"在Blender中执行代码时出错: {e}")
            return {"error": str(e)}

    async def send_command(self, command, data):
        """向Blender发送命令"""
        try:
            # 尝试符合Blender插件预期的格式
            request = {
                "type": command,
                "data": data
            }
            print(f"发送命令结构: {request}")
            response = await self.send_request(request)
            return response
        except Exception as e:
            print(f"发送命令失败: {e}")
            raise

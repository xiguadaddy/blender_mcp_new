import json
import socket
import asyncio
import sys
import os
import traceback

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
        try:
            # 优化特定请求类型
            if data.get("action") == "call_tool" and data.get("tool") == "set_material":
                data = self._optimize_material_request(data)

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
        except Exception as e:
            print(f"发送请求时出错: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def _optimize_material_request(self, request):
        """优化材质相关请求
        
        参数:
            request: 原始请求
            
        返回:
            优化后的请求
        """
        # 复制请求以避免修改原始请求
        optimized = request.copy()
        arguments = optimized.get("arguments", {}).copy()
        
        # 确保颜色格式正确 (支持RGB和RGBA)
        if "color" in arguments:
            color = arguments["color"]
            if color and isinstance(color, list):
                # 如果是RGB格式，添加Alpha通道
                if len(color) == 3:
                    arguments["color"] = color + [1.0]
                    print(f"材质优化: 为颜色添加Alpha通道 {color} -> {arguments['color']}")
                # 确保所有颜色值在0-1范围内
                arguments["color"] = [max(0.0, min(c, 1.0)) for c in arguments["color"]]
        
        # 确保金属度和粗糙度在有效范围内
        for param in ["metallic", "roughness", "specular"]:
            if param in arguments:
                arguments[param] = max(0.0, min(arguments[param], 1.0))
        
        # 更新请求参数
        optimized["arguments"] = arguments
        return optimized
    
    def close(self):
        """关闭连接"""
        if self.socket:
            self.socket.close()

    async def check_object_exists(self, object_name):
        """检查对象是否存在"""
        try:
            request = {
                "action": "check_object_exists",
                "object_name": object_name
            }
            result = await self.send_request(request)
            return result.get("exists", False)
        except Exception as e:
            print(f"检查对象存在性时出错: {e}")
            return False

"""
Socket 传输实现

提供基于 TCP 套接字的传输层实现，用于与 Blender MCP 插件通信。
"""

import socket
import json
import logging
from typing import Dict, Any, Optional, Union

logger = logging.getLogger("BlenderMCPTransport")

class SocketTransport:
    """基于套接字的传输实现"""
    
    def __init__(self, host: str, port: int, timeout: float = 10.0):
        """
        初始化套接字传输
        
        Args:
            host: 服务器主机名或 IP
            port: 服务器端口
            timeout: 连接和操作超时（秒）
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket = None
        self.connected = False
        
    def connect(self) -> bool:
        """
        连接到服务器
        
        Returns:
            连接成功返回 True，否则返回 False
        """
        try:
            if self.connected:
                return True
                
            logger.debug(f"连接到服务器 {self.host}:{self.port}")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            self.connected = True
            logger.debug("已连接到服务器")
            return True
        except Exception as e:
            logger.error(f"连接到服务器时出错: {str(e)}")
            self.connected = False
            return False
            
    def disconnect(self) -> None:
        """断开与服务器的连接"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self.connected = False
        logger.debug("已断开与服务器的连接")
        
    def send(self, data: Union[str, bytes]) -> None:
        """
        发送数据到服务器
        
        Args:
            data: 要发送的数据
            
        Raises:
            Exception: 如果发送失败
        """
        if not self.connected:
            if not self.connect():
                raise Exception("未连接到服务器")
                
        try:
            # 确保数据是字节
            if isinstance(data, str):
                data = data.encode()
                
            # 添加长度前缀
            header = f"{len(data)}:".encode()
            
            # 发送数据
            self.socket.sendall(header + data)
        except Exception as e:
            self.connected = False
            raise Exception(f"发送数据时出错: {str(e)}")
            
    def receive(self) -> Optional[str]:
        """
        从服务器接收数据
        
        Returns:
            接收到的数据
            
        Raises:
            Exception: 如果接收失败
        """
        if not self.connected:
            if not self.connect():
                raise Exception("未连接到服务器")
                
        try:
            # 读取消息头（字节数）
            header = b""
            while b":" not in header:
                chunk = self.socket.recv(1)
                if not chunk:  # 连接关闭
                    self.connected = False
                    raise Exception("连接已关闭")
                header += chunk
            
            # 解析消息长度
            length = int(header.decode().split(":")[0])
            
            # 读取消息内容
            data = b""
            while len(data) < length:
                chunk = self.socket.recv(min(4096, length - len(data)))
                if not chunk:  # 连接关闭
                    self.connected = False
                    raise Exception("读取消息时连接关闭")
                data += chunk
            
            # 返回解码后的数据
            return data.decode()
        except Exception as e:
            self.connected = False
            raise Exception(f"接收数据时出错: {str(e)}")
            
    def send_json(self, obj: Any) -> None:
        """
        发送 JSON 对象到服务器
        
        Args:
            obj: 要发送的对象
            
        Raises:
            Exception: 如果发送失败
        """
        try:
            data = json.dumps(obj)
            self.send(data)
        except json.JSONDecodeError as e:
            raise Exception(f"序列化 JSON 时出错: {str(e)}")
        except Exception as e:
            raise Exception(f"发送 JSON 时出错: {str(e)}")
            
    def receive_json(self) -> Optional[Any]:
        """
        从服务器接收 JSON 对象
        
        Returns:
            接收到的对象
            
        Raises:
            Exception: 如果接收失败
        """
        try:
            data = self.receive()
            if data:
                return json.loads(data)
            return None
        except json.JSONDecodeError as e:
            raise Exception(f"解析 JSON 时出错: {str(e)}")
        except Exception as e:
            raise Exception(f"接收 JSON 时出错: {str(e)}")
            
    def is_connected(self) -> bool:
        """
        检查是否已连接
        
        Returns:
            如果已连接返回 True，否则返回 False
        """
        return self.connected

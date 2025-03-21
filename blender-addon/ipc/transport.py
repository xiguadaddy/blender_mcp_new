"""
MCP传输层抽象

定义传输MCP消息的接口和基础实现。
"""

import json
import sys
import traceback
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, Union

# 消息处理器类型
MessageHandler = Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]

class TransportError(Exception):
    """传输层错误"""
    pass

class Transport(ABC):
    """MCP传输抽象基类"""
    
    @abstractmethod
    def send(self, message: Dict[str, Any]) -> None:
        """
        发送MCP消息
        
        Args:
            message: 要发送的消息
            
        Raises:
            TransportError: 如果发送失败
        """
        pass
        
    @abstractmethod
    def receive(self) -> Optional[Dict[str, Any]]:
        """
        接收MCP消息
        
        Returns:
            接收到的消息，如果没有消息可用则返回None
            
        Raises:
            TransportError: 如果接收失败
        """
        pass
        
    @abstractmethod
    def close(self) -> None:
        """关闭传输连接"""
        pass
        
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """传输是否已连接"""
        pass
        
    def send_json(self, obj: Any) -> None:
        """
        将对象转换为JSON并发送
        
        Args:
            obj: 要发送的对象
            
        Raises:
            TransportError: 如果发送失败
        """
        try:
            message = json.dumps(obj)
            self.send(message)
        except Exception as e:
            raise TransportError(f"JSON发送失败: {str(e)}")
        
    def receive_json(self) -> Optional[Any]:
        """
        接收并解析JSON消息
        
        Returns:
            解析后的JSON对象，如果没有消息可用则返回None
            
        Raises:
            TransportError: 如果接收或解析失败
        """
        message = self.receive()
        if message is None:
            return None
            
        try:
            return json.loads(message)
        except json.JSONDecodeError as e:
            raise TransportError(f"JSON解析失败: {str(e)}")

class MemoryTransport(Transport):
    """内存传输实现，用于测试"""
    
    def __init__(self):
        self._connected = True
        self._queue = []
        
    def send(self, message: Dict[str, Any]) -> None:
        if not self._connected:
            raise TransportError("传输已关闭")
        self._queue.append(message)
        
    def receive(self) -> Optional[Dict[str, Any]]:
        if not self._connected:
            raise TransportError("传输已关闭")
        if not self._queue:
            return None
        return self._queue.pop(0)
        
    def close(self) -> None:
        self._connected = False
        self._queue = []
        
    @property
    def is_connected(self) -> bool:
        return self._connected

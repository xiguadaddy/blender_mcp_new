"""
基于WebSocket的MCP传输实现
"""

import json
import asyncio
import threading
import queue
from typing import Dict, Any, Optional

from .transport import Transport, TransportError

class WebSocketTransport(Transport):
    """WebSocket传输层实现"""
    
    def __init__(self, websocket):
        """
        初始化WebSocket传输
        
        Args:
            websocket: WebSocket连接对象
        """
        self._websocket = websocket
        self._connected = True
        self._recv_queue = queue.Queue()
        self._send_queue = queue.Queue()
        
        # 启动接收和发送线程
        self._recv_thread = threading.Thread(target=self._receive_loop)
        self._recv_thread.daemon = True
        self._recv_thread.start()
        
        self._send_thread = threading.Thread(target=self._send_loop)
        self._send_thread.daemon = True
        self._send_thread.start()
        
    def send(self, message: str) -> None:
        """
        发送消息
        
        Args:
            message: 要发送的消息
            
        Raises:
            TransportError: 如果发送失败
        """
        if not self._connected:
            raise TransportError("WebSocket连接已关闭")
            
        self._send_queue.put(message)
        
    def receive(self) -> Optional[str]:
        """
        接收消息
        
        Returns:
            接收到的消息，如果没有消息可用则返回None
            
        Raises:
            TransportError: 如果接收失败
        """
        if not self._connected:
            raise TransportError("WebSocket连接已关闭")
            
        try:
            return self._recv_queue.get_nowait()
        except queue.Empty:
            return None
        
    def close(self) -> None:
        """关闭连接"""
        self._connected = False
        
        # 在事件循环中关闭WebSocket
        if self._websocket and not self._websocket.closed:
            asyncio.run_coroutine_threadsafe(
                self._websocket.close(),
                asyncio.get_event_loop()
            )
        
    @property
    def is_connected(self) -> bool:
        """连接是否已建立"""
        return self._connected and not (self._websocket and self._websocket.closed)
        
    def _receive_loop(self):
        """接收消息循环"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def receive_task():
            try:
                while self._connected:
                    try:
                        # 非阻塞接收消息
                        message = await asyncio.wait_for(
                            self._websocket.recv(),
                            timeout=0.1
                        )
                        self._recv_queue.put(message)
                    except asyncio.TimeoutError:
                        # 超时，继续循环
                        continue
                    except Exception as e:
                        print(f"WebSocket接收错误: {str(e)}")
                        self._connected = False
                        break
            except Exception as e:
                print(f"WebSocket接收循环错误: {str(e)}")
                self._connected = False
                
        # 运行接收任务
        loop.run_until_complete(receive_task())
        
    def _send_loop(self):
        """发送消息循环"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def send_task():
            try:
                while self._connected:
                    try:
                        # 获取要发送的消息
                        try:
                            message = self._send_queue.get(timeout=0.1)
                        except queue.Empty:
                            # 没有消息，继续循环
                            await asyncio.sleep(0.01)
                            continue
                            
                        # 发送消息
                        await self._websocket.send(message)
                        self._send_queue.task_done()
                    except Exception as e:
                        print(f"WebSocket发送错误: {str(e)}")
                        self._connected = False
                        break
            except Exception as e:
                print(f"WebSocket发送循环错误: {str(e)}")
                self._connected = False
                
        # 运行发送任务
        loop.run_until_complete(send_task())

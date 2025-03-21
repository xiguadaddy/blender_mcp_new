"""
Blender MCP 客户端

提供与运行 Blender MCP 插件的 Blender 实例通信的客户端。
"""

import json
import socket
import threading
import time
import uuid
import logging
from typing import Dict, Any, Optional, Callable, List, Union

# 设置日志
logger = logging.getLogger("BlenderMCPClient")

class BlenderMCPClient:
    """与 Blender MCP 插件通信的客户端"""
    
    def __init__(self, host="127.0.0.1", port=27015, timeout=10.0):
        """
        初始化 Blender MCP 客户端
        
        Args:
            host: Blender MCP 插件服务器主机名或 IP
            port: Blender MCP 插件服务器端口
            timeout: 连接和操作超时（秒）
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket = None
        self.connected = False
        self._lock = threading.Lock()
        self._pending_requests = {}  # id -> callback
        self._response_thread = None
        
    def connect(self) -> bool:
        """
        连接到 Blender MCP 插件服务器
        
        Returns:
            连接成功返回 True，否则返回 False
        """
        try:
            if self.connected:
                return True
                
            logger.info(f"连接到 Blender MCP 服务器 {self.host}:{self.port}")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            self.connected = True
            
            # 启动响应处理线程
            self._response_thread = threading.Thread(target=self._process_responses)
            self._response_thread.daemon = True
            self._response_thread.start()
            
            logger.info("已连接到 Blender MCP 服务器")
            return True
        except Exception as e:
            logger.error(f"连接到 Blender MCP 服务器时出错: {str(e)}")
            self.connected = False
            return False
            
    def disconnect(self) -> None:
        """断开与 Blender MCP 插件服务器的连接"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self.connected = False
        logger.info("已断开与 Blender MCP 服务器的连接")
        
    def send_request(self, method: str, params: Optional[Dict[str, Any]] = None,
                    callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> str:
        """
        发送请求到 Blender MCP 插件服务器
        
        Args:
            method: 请求方法
            params: 请求参数（可选）
            callback: 响应回调函数（可选）
            
        Returns:
            请求 ID
            
        Raises:
            Exception: 如果连接失败
        """
        with self._lock:
            if not self.connected:
                if not self.connect():
                    raise Exception("未连接到 Blender MCP 服务器")
            
            # 创建请求 ID
            request_id = str(uuid.uuid4())
            
            # 构建请求
            request = {
                "jsonrpc": "2.0",
                "method": method,
                "id": request_id
            }
            
            if params:
                request["params"] = params
                
            # 如果提供了回调，注册它
            if callback:
                self._pending_requests[request_id] = callback
                
            # 发送请求
            logger.debug(f"发送请求: {method}")
            self._send_message(request)
            
            return request_id
    
    def send_request_sync(self, method: str, params: Optional[Dict[str, Any]] = None, 
                         timeout: float = 30.0) -> Dict[str, Any]:
        """
        同步发送请求并等待响应
        
        Args:
            method: 请求方法
            params: 请求参数（可选）
            timeout: 等待响应的超时时间（秒）
            
        Returns:
            响应结果
            
        Raises:
            Exception: 如果请求失败或超时
        """
        # 创建事件和结果容器
        event = threading.Event()
        result_container = {}
        
        def callback(response):
            result_container["response"] = response
            event.set()
        
        # 发送请求
        request_id = self.send_request(method, params, callback)
        
        # 等待响应或超时
        if not event.wait(timeout):
            # 移除回调
            with self._lock:
                if request_id in self._pending_requests:
                    del self._pending_requests[request_id]
            raise Exception(f"请求超时: {method}")
        
        # 返回结果
        return result_container.get("response", {})
            
    def _send_message(self, message: Dict[str, Any]) -> None:
        """
        发送消息到服务器
        
        Args:
            message: 要发送的消息
            
        Raises:
            Exception: 如果发送失败
        """
        try:
            # 序列化消息
            message_json = json.dumps(message)
            message_bytes = message_json.encode()
            
            # 添加长度前缀
            header = f"{len(message_bytes)}:".encode()
            
            # 发送消息
            self.socket.sendall(header + message_bytes)
        except Exception as e:
            self.connected = False
            raise Exception(f"发送消息时出错: {str(e)}")
    
    def _process_responses(self):
        """处理来自服务器的响应"""
        while self.connected:
            try:
                # 接收消息
                message = self._receive_message()
                if not message:
                    continue
                
                # 检查是否为响应（有 ID）
                if "id" in message:
                    request_id = message.get("id")
                    # 查找并调用对应的回调
                    with self._lock:
                        callback = self._pending_requests.pop(request_id, None)
                    
                    if callback:
                        # 提取结果或错误
                        if "error" in message:
                            logger.warning(f"收到错误响应: {message['error']}")
                            # 仍然调用回调，让调用者决定如何处理错误
                            callback({"error": message["error"]})
                        elif "result" in message:
                            logger.debug(f"收到成功响应: ID={request_id}")
                            callback(message["result"])
                    else:
                        logger.warning(f"收到未知请求 ID 的响应: {request_id}")
            except Exception as e:
                if self.connected:  # 只在连接仍然活跃时报告错误
                    logger.error(f"处理响应时出错: {str(e)}")
            
            # 短暂休眠，避免 CPU 过载
            time.sleep(0.01)
            
    def _receive_message(self) -> Optional[Dict[str, Any]]:
        """
        从服务器接收消息
        
        Returns:
            接收到的消息，如果出错则返回 None
            
        Raises:
            Exception: 如果接收失败
        """
        try:
            # 设置超时，使循环可以定期检查连接状态
            self.socket.settimeout(0.5)
            
            # 读取消息头（字节数）
            header = b""
            while b":" not in header:
                try:
                    chunk = self.socket.recv(1)
                    if not chunk:  # 连接关闭
                        self.connected = False
                        return None
                    header += chunk
                except socket.timeout:
                    # 超时继续
                    return None
            
            # 解析消息长度
            length = int(header.decode().split(":")[0])
            
            # 读取消息内容
            data = b""
            while len(data) < length:
                try:
                    chunk = self.socket.recv(min(4096, length - len(data)))
                    if not chunk:  # 连接关闭
                        self.connected = False
                        return None
                    data += chunk
                except socket.timeout:
                    # 超时继续
                    continue
            
            # 解析响应
            return json.loads(data.decode())
        except socket.timeout:
            # 超时但不报错
            return None
        except json.JSONDecodeError as e:
            logger.error(f"解析响应时出错: {str(e)}")
            return None
        except Exception as e:
            if self.connected:
                logger.error(f"接收消息时出错: {str(e)}")
            self.connected = False
            return None
            
    # 便捷方法 - 资源相关
    def list_resources(self) -> List[Dict[str, Any]]:
        """
        列出可用资源
        
        Returns:
            资源列表
        """
        try:
            result = self.send_request_sync("resources/list")
            return result.get("resources", [])
        except Exception as e:
            logger.error(f"列出资源时出错: {str(e)}")
            return []
        
    def read_resource(self, uri: str) -> Dict[str, Any]:
        """
        读取资源内容
        
        Args:
            uri: 资源 URI
            
        Returns:
            资源内容
        """
        try:
            return self.send_request_sync("resources/read", {"uri": uri})
        except Exception as e:
            logger.error(f"读取资源时出错: {str(e)}")
            return {"error": str(e)}
        
    # 便捷方法 - 工具相关
    def list_tools(self) -> List[Dict[str, Any]]:
        """
        列出可用工具
        
        Returns:
            工具列表
        """
        try:
            result = self.send_request_sync("tools/list")
            return result.get("tools", [])
        except Exception as e:
            logger.error(f"列出工具时出错: {str(e)}")
            return []
        
    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        调用工具
        
        Args:
            name: 工具名称
            arguments: 工具参数（可选）
            
        Returns:
            工具执行结果
        """
        try:
            params = {"name": name}
            if arguments:
                params["arguments"] = arguments
            return self.send_request_sync("tools/call", params)
        except Exception as e:
            logger.error(f"调用工具时出错: {str(e)}")
            return {"error": str(e)}
        
    # 便捷方法 - 提示相关
    def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        获取提示
        
        Args:
            name: 提示名称
            arguments: 提示参数（可选）
            
        Returns:
            提示内容
        """
        try:
            params = {"name": name}
            if arguments:
                params["arguments"] = arguments
            return self.send_request_sync("prompts/get", params)
        except Exception as e:
            logger.error(f"获取提示时出错: {str(e)}")
            return {"error": str(e)}

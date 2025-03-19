import json
import socket
import asyncio
import sys
import os
import traceback
import logging
import re
import time
from threading import Lock
from typing import Dict, Any, Optional, Union, List

# 配置日志
logger = logging.getLogger("BlenderMCP.IPCClient")

class IPCClient:
    """负责与Blender插件通信的IPC客户端"""
    
    def __init__(self, socket_path, max_retries=3, retry_delay=1.0):
        """初始化IPC客户端
        
        Args:
            socket_path: IPC通信路径，对于Windows是'port:端口号'，对于Unix是套接字文件路径
            max_retries: 连接和请求失败时的最大重试次数
            retry_delay: 重试之间的延迟(秒)
        """
        self.socket_path = socket_path
        self.writer = None
        self.reader = None
        self.is_connected = False
        self.is_windows = sys.platform == "win32"
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # 检查是否使用端口模式（Windows）
        self.port_mode = False
        self.port = None
        
        if socket_path.startswith('port:'):
            self.port_mode = True
            match = re.search(r'port:(\d+)', socket_path)
            if match:
                self.port = int(match.group(1))
                logger.debug(f"使用端口模式，端口号: {self.port}")
            else:
                logger.error(f"端口格式无效: {socket_path}")
                raise ValueError(f"端口格式无效: {socket_path}")
        
        # 从路径中解析IP和端口（如果格式是"port:xxxx"）
        self._host = "127.0.0.1"
        self._port = 27015
        if socket_path.startswith("port:"):
            try:
                self._port = int(socket_path.split(":", 1)[1])
                logger.debug(f"使用端口模式，端口号: {self._port}")
            except Exception as e:
                logger.error(f"解析端口号时出错: {e}，使用默认端口 {self._port}")
        else:
            # Unix socket模式，目前不支持
            logger.warning("检测到Unix socket路径，在Windows上将使用TCP/IP模式")
        
    async def connect(self):
        """连接到Blender IPC服务器
        
        Returns:
            bool: 连接是否成功
        """
        if self.is_connected:
            logger.debug("已连接到Blender IPC服务器")
            return True
            
        logger.info(f"正在连接到Blender IPC服务器: {self.socket_path}")
        
        try:
            if self.port_mode:
                # 尝试连接
                for attempt in range(1, self.max_retries + 1):
                    try:
                        self.reader, self.writer = await asyncio.open_connection(
                            self._host, self._port
                        )
                        self.is_connected = True
                        logger.info(f"成功连接到Blender IPC服务器，端口: {self._port}")
                        return True
                    except ConnectionRefusedError:
                        if attempt < self.max_retries:
                            retry_delay = self.retry_delay * (1 + 0.5 * attempt)
                            logger.warning(f"连接被拒绝，尝试 {attempt}/{self.max_retries}，将在 {retry_delay:.1f} 秒后重试...")
                            await asyncio.sleep(retry_delay)
                        else:
                            logger.error(f"连接到Blender IPC服务器失败: 连接被拒绝")
                            return False
                    except Exception as e:
                        logger.error(f"连接到Blender IPC服务器失败: {str(e)}")
                        logger.debug(traceback.format_exc())
                        return False
            else:
                # Unix域套接字模式
                try:
                    self.reader, self.writer = await asyncio.open_unix_connection(
                        self.socket_path
                    )
                    self.is_connected = True
                    logger.info(f"成功连接到Blender IPC服务器，套接字: {self.socket_path}")
                    return True
                except FileNotFoundError:
                    logger.error(f"连接到Blender IPC服务器失败: 套接字文件不存在 - {self.socket_path}")
                    return False
                except Exception as e:
                    logger.error(f"连接到Blender IPC服务器失败: {str(e)}")
                    logger.debug(traceback.format_exc())
                    return False
        except Exception as e:
            logger.error(f"连接到Blender IPC服务器时发生未知错误: {str(e)}")
            logger.debug(traceback.format_exc())
            return False
        
        return False
    
    async def send_request(self, request_data):
        """发送请求到Blender并获取响应
        
        Args:
            request_data: 请求数据(字典)
            
        Returns:
            dict: 响应数据
        """
        if not self.is_connected:
            logger.warning("尝试在未连接状态下发送请求，尝试重新连接...")
            if not await self.connect():
                logger.error("无法重新连接，放弃发送请求")
                return {"error": "未连接到Blender IPC服务器"}
        
        try:
            # 将请求数据转换为JSON
            request_json = json.dumps(request_data)
            message = f"{len(request_json)}:{request_json}"
            
            # 发送请求
            logger.debug(f"发送请求: {request_data}")
            self.writer.write(message.encode())
            await self.writer.drain()
            
            # 接收响应头部（长度前缀）
            header = b""
            while b":" not in header:
                chunk = await self.reader.read(1)
                if not chunk:  # 连接关闭
                    logger.error("接收响应头部时连接关闭")
                    self.is_connected = False
                    return {"error": "接收响应时连接断开"}
                header += chunk
            
            # 解析长度前缀
            length = int(header.decode().split(":", 1)[0])
            
            # 接收完整响应数据
            response_data = b""
            while len(response_data) < length:
                chunk = await self.reader.read(min(4096, length - len(response_data)))
                if not chunk:  # 连接关闭
                    logger.error("接收响应数据时连接关闭")
                    self.is_connected = False
                    return {"error": "接收响应数据时连接断开"}
                response_data += chunk
            
            # 解析响应
            try:
                response = json.loads(response_data.decode())
                logger.debug(f"收到响应: {response}")
                return response
            except json.JSONDecodeError as e:
                logger.error(f"解析响应JSON时出错: {str(e)}")
                logger.error(f"收到的响应数据: {response_data.decode()}")
                return {"error": f"响应解析失败: {str(e)}"}
                
        except ConnectionResetError:
            logger.error("连接被重置，可能是Blender IPC服务器关闭了连接")
            self.is_connected = False
            return {"error": "连接被重置"}
        except ConnectionAbortedError:
            logger.error("连接被中止，可能是Blender IPC服务器异常关闭")
            self.is_connected = False
            return {"error": "连接被中止"}
        except Exception as e:
            logger.error(f"发送请求时发生错误: {str(e)}")
            logger.debug(traceback.format_exc())
            self.is_connected = False
            return {"error": str(e)}
    
    async def send_request_with_retry(self, request_data):
        """
        发送请求到Blender，支持重试（完全异步版本）
        确保在任何地方使用这个函数都使用await

        Args:
            request_data: 请求数据(字典)
            
        Returns:
            dict: 响应数据
        """
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                # 确保连接
                if not self.is_connected:
                    connected = await self.connect()
                    if not connected:
                        if attempt == self.max_retries:
                            logger.error("达到最大重试次数，无法连接")
                            return {"error": "无法连接到Blender IPC服务器"}
                        retry_delay = self.retry_delay * (1 + 0.5 * attempt)
                        logger.warning(f"连接失败，将在{retry_delay:.1f}秒后重试... ({attempt}/{self.max_retries})")
                        await asyncio.sleep(retry_delay)
                        continue
                
                # 直接异步发送请求（没有任何事件循环操作）
                response = await self.send_request(request_data)
                
                # 检查响应是否有错误
                if isinstance(response, dict) and "error" in response:
                    error_msg = response["error"]
                    if "连接" in error_msg or "断开" in error_msg:
                        # 连接相关错误，尝试重试
                        if attempt < self.max_retries:
                            retry_delay = self.retry_delay * (1 + 0.5 * attempt)
                            logger.warning(f"请求失败: {error_msg}，将在 {retry_delay:.1f} 秒后重试... ({attempt}/{self.max_retries})")
                            self.is_connected = False  # 重置连接状态
                            await asyncio.sleep(retry_delay)
                            continue
                    
                # 其他情况直接返回响应
                return response
                
            except Exception as e:
                last_error = e
                logger.error(f"请求处理过程中发生异常: {str(e)}")
                logger.debug(f"异常详情: {type(e).__name__}，尝试: {attempt}/{self.max_retries}")
                
                if attempt < self.max_retries:
                    retry_delay = self.retry_delay * (1 + 0.5 * attempt)
                    logger.warning(f"请求异常，将在 {retry_delay:.1f} 秒后重试... ({attempt}/{self.max_retries})")
                    await asyncio.sleep(retry_delay)
                else:
                    # 最后一次尝试也失败
                    error_msg = f"请求处理失败: {str(e)}"
                    logger.error(error_msg)
                    return {"error": error_msg}
        
        # 如果所有尝试都失败
        error_msg = f"达到最大重试次数 ({self.max_retries})，请求失败"
        if last_error:
            error_msg += f": {str(last_error)}"
        logger.error(error_msg)
        return {"error": error_msg}
    
    def disconnect(self):
        """断开与Blender IPC服务器的连接"""
        if not self.is_connected:
            return
            
        logger.info("断开连接...")
        
        try:
            if self.writer:
                self.writer.close()
        except Exception as e:
            logger.error(f"关闭连接时出错: {str(e)}")
        
        self.is_connected = False
        self.writer = None
        self.reader = None
    
    async def reconnect(self) -> bool:
        """重新连接到Blender IPC服务器
        
        Returns:
            bool: 重连成功返回True，否则返回False
        """
        logger.info("尝试重新连接到Blender IPC服务器")
        self.disconnect()
        
        for attempt in range(1, self.max_retries + 1):
            logger.info(f"重连尝试 {attempt}/{self.max_retries}")
            if await self.connect():
                return True
            # 使用异步的sleep而不是阻塞的time.sleep
            await asyncio.sleep(self.retry_delay)
        
        logger.error(f"在 {self.max_retries} 次尝试后无法重新连接")
        return False
    
    async def ping(self) -> Dict[str, Any]:
        """检查与Blender的连接状态（异步版本）"""
        if not self.is_connected:
            return {"status": "disconnected", "message": "未连接到Blender IPC服务器"}
        
        try:
            # 使用直接的异步请求，避免事件循环冲突
            response = await self.send_request({"action": "ping"})
            
            if isinstance(response, dict) and "error" in response:
                return {
                    "status": "error", 
                    "message": f"连接存在但出现错误: {response['error']}"
                }
            
            return {"status": "connected", "message": "连接正常"}
        except Exception as e:
            logger.error(f"Ping时出错: {str(e)}")
            return {"status": "error", "message": f"检查连接时出错: {str(e)}"}
    
    async def check_object_exists(self, object_name):
        """检查对象是否存在"""
        if not object_name:
            return False
            
        response = await self.send_request({
            "action": "check_object",
            "name": object_name
        })
        
        if isinstance(response, dict) and "exists" in response:
            return response["exists"]
        return False

    def _optimize_material_request(self, request):
        """优化材质相关请求
        
        Args:
            request: 原始请求
            
        Returns:
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
                    logger.debug(f"材质优化: 为颜色添加Alpha通道 {color} -> {arguments['color']}")
                # 确保所有颜色值在0-1范围内
                arguments["color"] = [max(0.0, min(c, 1.0)) for c in arguments["color"]]
        
        # 确保金属度和粗糙度在有效范围内
        for param in ["metallic", "roughness", "specular"]:
            if param in arguments:
                arguments[param] = max(0.0, min(arguments[param], 1.0))
        
        # 更新请求参数
        optimized["arguments"] = arguments
        return optimized

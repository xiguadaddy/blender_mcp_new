import socket
import threading
import json
import os
import bpy
import logging
import sys
import tempfile
import time
from ..handlers import resource_handlers, tool_handlers

# 设置日志
logger = logging.getLogger("BlenderMCP.IPC")

# 全局IPC服务器实例
_ipc_server = None

class IPCServer(threading.Thread):
    """处理与MCP服务器核心通信的IPC服务器"""
    
    def __init__(self, socket_path, debug_mode=False):
        threading.Thread.__init__(self)
        self.socket_path = socket_path
        self.server_socket = None
        self.running = False
        self.daemon = True
        self.debug_mode = debug_mode
        self.is_windows = sys.platform == "win32"
        
        # 资源订阅和客户端管理
        self.clients = []
        self.subscribed_resources = {}  # 资源URI -> 客户端列表
        self.resource_poll_interval = 1.0  # 每秒检查一次资源变化
        self.last_resource_check = time.time()
        
        # Windows平台使用TCP套接字而不是Unix域套接字
        if self.is_windows:
            # 从socket_path提取端口号，或使用默认值
            # 格式：port:12345 或默认使用27015
            if socket_path.startswith("port:"):
                self.port = int(socket_path.split(":", 1)[1])
            else:
                self.port = 27015
            self.host = "127.0.0.1"  # 本地回环地址
            
        # 配置日志级别
        if debug_mode:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
        
    def run(self):
        """启动服务器并处理连接"""
        if self.is_windows:
            # Windows使用TCP套接字
            self._run_tcp_server()
        else:
            # Unix/Linux使用Unix域套接字
            self._run_unix_socket_server()
            
    def _check_resource_changes(self):
        """检查资源变化并通知订阅者"""
        current_time = time.time()
        
        # 按指定间隔检查资源
        if current_time - self.last_resource_check >= self.resource_poll_interval:
            self.last_resource_check = current_time
            
            # 获取变化的资源
            changed_resources = resource_handlers.update_resource_state()
            
            if changed_resources:
                logger.debug(f"检测到 {len(changed_resources)} 个资源变化")
                
                # 对于每个变化的资源，通知订阅者
                for resource_uri in changed_resources:
                    if resource_uri in self.subscribed_resources:
                        clients = self.subscribed_resources[resource_uri]
                        for client in clients:
                            if client in self.clients:
                                self._send_resource_update(client, resource_uri)
                                
    def _send_resource_update(self, client, resource_uri):
        """发送资源更新通知"""
        try:
            # 构建资源更新通知
            notification = {
                "type": "resource_update",
                "uri": resource_uri,
                "timestamp": time.time()
            }
            
            # 发送通知
            message = json.dumps(notification)
            header = f"{len(message)}:".encode()
            client.sendall(header + message.encode())
            logger.debug(f"已发送资源更新通知: {resource_uri}")
            
        except Exception as e:
            logger.error(f"发送资源更新通知时出错: {str(e)}")
            # 移除失效的客户端
            if client in self.clients:
                self.clients.remove(client)
                # 从所有订阅中移除该客户端
                for uri, clients in self.subscribed_resources.items():
                    if client in clients:
                        clients.remove(client)
                        
    def _run_tcp_server(self):
        """使用TCP套接字启动服务器(Windows)"""
        try:
            # 先检查端口是否已被占用
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                test_socket.bind((self.host, self.port))
                test_socket.close()
            except OSError as e:
                error_msg = f"端口 {self.port} 已被占用，请尝试使用其他端口: {str(e)}"
                print(error_msg)
                logger.error(error_msg)
                # 设置全局标志表明服务器未启动
                bpy.types._mcp_server_running = False
                return

            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 设置选项允许地址重用
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            try:
                self.server_socket.bind((self.host, self.port))
                self.server_socket.listen(1)
                # 确认绑定成功后才设置运行标志
                self.running = True
                # 存储实际端口号到全局变量
                bpy.types._mcp_server_port = self.port
                
                print(f"***** IPC TCP服务器成功绑定并监听：{self.host}:{self.port} *****")
            except Exception as e:
                error_msg = f"绑定端口 {self.port} 失败: {str(e)}"
                print(error_msg)
                logger.error(error_msg)
                # 设置全局标志表明服务器未启动
                bpy.types._mcp_server_running = False
                return
            
            # 设置socket非阻塞模式
            self.server_socket.settimeout(1.0)
            
            # 输出进程ID
            pid = os.getpid()
            print(f"Blender进程ID: {pid}")
            # 将进程ID保存到全局变量
            bpy.types._mcp_server_pid = pid
            
            # 开始接受连接
            while self.running:
                try:
                    # 接受连接
                    client_socket, client_address = self.server_socket.accept()
                    logger.info(f"接受来自 {client_address} 的连接")
                    
                    # 保存客户端引用
                    self.clients.append(client_socket)
                    
                    # 在新线程中处理客户端
                    client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.timeout:
                    # 超时，继续循环并检查资源变化
                    self._check_resource_changes()
                except Exception as e:
                    if self.running:  # 只在服务器仍在运行时记录错误
                        logger.error(f"接受连接时出错: {str(e)}")
        except Exception as e:
            error_msg = f"启动TCP服务器时出错: {str(e)}"
            print(error_msg)
            logger.error(error_msg)
            # 设置全局标志表明服务器未启动
            bpy.types._mcp_server_running = False
            
    def _run_unix_socket_server(self):
        """使用Unix域套接字启动服务器(Unix/Linux/Mac)"""
        try:
            # 检查套接字文件是否已存在，如果存在则移除
            if os.path.exists(self.socket_path):
                try:
                    os.unlink(self.socket_path)
                    logger.debug(f"已移除现有套接字文件: {self.socket_path}")
                except OSError as e:
                    error_msg = f"无法移除现有套接字文件: {str(e)}"
                    print(error_msg)
                    logger.error(error_msg)
                    return
            
            # 创建Unix域套接字
            self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            
            try:
                self.server_socket.bind(self.socket_path)
                self.server_socket.listen(1)
                # 确认绑定成功后才设置运行标志
                self.running = True
                
                print(f"***** IPC Unix套接字服务器成功绑定并监听：{self.socket_path} *****")
            except Exception as e:
                error_msg = f"绑定套接字 {self.socket_path} 失败: {str(e)}"
                print(error_msg)
                logger.error(error_msg)
                # 设置全局标志表明服务器未启动
                bpy.types._mcp_server_running = False
                return
            
            # 设置socket非阻塞
            self.server_socket.settimeout(1.0)
            
            # 输出进程ID
            pid = os.getpid()
            print(f"Blender进程ID: {pid}")
            # 将进程ID保存到全局变量
            bpy.types._mcp_server_pid = pid
            
            # 开始接受连接
            while self.running:
                try:
                    # 接受连接
                    client_socket, _ = self.server_socket.accept()
                    logger.info(f"接受来自Unix套接字的连接")
                    
                    # 保存客户端引用
                    self.clients.append(client_socket)
                    
                    # 在新线程中处理客户端
                    client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.timeout:
                    # 超时，继续循环并检查资源变化
                    self._check_resource_changes()
                except Exception as e:
                    if self.running:  # 只在服务器仍在运行时记录错误
                        logger.error(f"接受Unix套接字连接时出错: {str(e)}")
                        
        except Exception as e:
            error_msg = f"启动Unix套接字服务器时出错: {str(e)}"
            print(error_msg)
            logger.error(error_msg)
            # 设置全局标志表明服务器未启动
            bpy.types._mcp_server_running = False
            
    def handle_client(self, client_socket):
        """处理客户端连接"""
        logger.debug("处理新客户端连接")
        
        try:
            # 设置socket为非阻塞，避免读取阻塞整个服务器
            client_socket.settimeout(0.5)
            
            while self.running:
                try:
                    # 读取消息头（字节数）
                    header = b""
                    while b":" not in header:
                        chunk = client_socket.recv(1)
                        if not chunk:  # 连接关闭
                            raise ConnectionError("连接已关闭")
                        header += chunk
                    
                    # 解析消息长度
                    length = int(header.decode().split(":")[0])
                    
                    # 读取消息内容
                    data = b""
                    while len(data) < length:
                        chunk = client_socket.recv(min(4096, length - len(data)))
                        if not chunk:  # 连接关闭
                            raise ConnectionError("读取消息时连接关闭")
                        data += chunk
                    
                    # 解析请求
                    request = json.loads(data.decode())
                    
                    # 添加客户端引用到请求中，用于资源订阅
                    request["_client"] = client_socket
                    
                    # 处理请求
                    response = self.handle_request(request)
                    
                    # 发送响应
                    response_json = json.dumps(response)
                    client_socket.sendall(f"{len(response_json)}:".encode() + response_json.encode())
                    
                except socket.timeout:
                    # 超时但继续循环
                    continue
                except ConnectionError as e:
                    logger.debug(f"客户端连接关闭: {str(e)}")
                    break
                except Exception as e:
                    logger.error(f"处理客户端消息时出错: {str(e)}")
                    try:
                        # 尝试发送错误响应
                        error_response = json.dumps({"error": str(e)})
                        client_socket.sendall(f"{len(error_response)}:".encode() + error_response.encode())
                    except:
                        # 无法发送错误响应，则关闭连接
                        break
        finally:
            # 客户端断开连接，清理资源
            logger.debug("客户端连接已关闭，清理资源")
            try:
                client_socket.close()
            except:
                pass
                
            # 从客户端列表中移除
            if client_socket in self.clients:
                self.clients.remove(client_socket)
                
            # 从所有订阅中移除
            for uri, clients in self.subscribed_resources.items():
                if client_socket in clients:
                    clients.remove(client_socket)
            
    def handle_request(self, request):
        """处理请求并返回结果"""
        action = request.get("action")
        logger.debug(f"处理动作: {action}")
        
        try:
            # 资源相关操作
            if action == "list_resources":
                return resource_handlers.handle_list_resources()
            elif action == "list_tools":
                # 硬编码工具列表作为临时解决方案
                # 这样无需重新启动Blender即可响应list_tools请求
                return [
                    {
                        "name": "create_object",
                        "description": "在Blender中创建一个对象",
                        "version": "1.0",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "object_type": {
                                    "type": "string", 
                                    "enum": ["cube", "sphere", "cylinder", "plane", "cone", "torus"],
                                    "description": "要创建的对象类型"
                                },
                                "name": {
                                    "type": "string",
                                    "description": "对象名称(可选)"
                                },
                                "location": {
                                    "type": "array",
                                    "items": {"type": "number"},
                                    "description": "对象位置坐标 [x, y, z]"
                                },
                                "size": {
                                    "type": "number",
                                    "description": "对象大小"
                                }
                            },
                            "required": ["object_type"]
                        }
                    },
                    {
                        "name": "set_material",
                        "description": "为对象设置材质",
                        "version": "1.0",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "object_name": {
                                    "type": "string",
                                    "description": "目标对象名称"
                                },
                                "material_name": {
                                    "type": "string",
                                    "description": "材质名称（如果不提供则自动生成）"
                                },
                                "color": {
                                    "type": "array",
                                    "items": {"type": "number"},
                                    "description": "RGBA颜色值 [r, g, b, a]，或RGB颜色值 [r, g, b]"
                                },
                                "metallic": {
                                    "type": "number",
                                    "description": "金属度(0-1)"
                                },
                                "roughness": {
                                    "type": "number",
                                    "description": "粗糙度(0-1)"
                                }
                            },
                            "required": ["object_name"]
                        }
                    },
                    {
                        "name": "add_light",
                        "description": "添加灯光到场景",
                        "version": "1.0",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "light_type": {
                                    "type": "string",
                                    "enum": ["POINT", "SUN", "SPOT", "AREA"],
                                    "description": "灯光类型"
                                },
                                "name": {
                                    "type": "string",
                                    "description": "灯光名称(可选)"
                                },
                                "location": {
                                    "type": "array",
                                    "items": {"type": "number"},
                                    "description": "灯光位置 [x, y, z]"
                                },
                                "color": {
                                    "type": "array",
                                    "items": {"type": "number"},
                                    "description": "RGB颜色值 [r, g, b]"
                                },
                                "energy": {
                                    "type": "number",
                                    "description": "灯光强度"
                                }
                            },
                            "required": ["light_type"]
                        }
                    }
                ]
            elif action == "read_resource":
                return resource_handlers.handle_read_resource(
                    request.get("type"),
                    request.get("id")
                )
            elif action == "check_object_exists":
                return resource_handlers.check_object_exists(
                    request.get("object_name")
                )
            elif action == "subscribe_resource":
                # 处理资源订阅请求
                uri = request.get("uri")
                client = request.get("_client")  # 由handle_client函数添加的客户端引用
                
                if uri and client:
                    if uri not in self.subscribed_resources:
                        self.subscribed_resources[uri] = []
                    if client not in self.subscribed_resources[uri]:
                        self.subscribed_resources[uri].append(client)
                    return {"status": "subscribed", "uri": uri}
                else:
                    return {"error": "无效的订阅请求"}
                
            # 工具相关操作
            elif action == "call_tool":
                return tool_handlers.execute_tool(
                    request.get("tool"),
                    request.get("arguments", {})
                )
                
            # 未知操作
            else:
                error_msg = f"未知操作: {action}"
                logger.error(error_msg)
                return {"error": error_msg}
                
        except Exception as e:
            error_msg = f"处理请求时出错: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
        
    def stop(self):
        """停止服务器"""
        logger.info("正在停止IPC服务器...")
        self.running = False
        
        # 关闭所有客户端连接
        for client in self.clients:
            try:
                client.close()
            except:
                pass
        self.clients = []
        
        # 关闭服务器套接字
        if self.server_socket:
            self.server_socket.close()
            
        # 如果是Unix套接字，删除文件
        if not self.is_windows and os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
            
        logger.info("IPC服务器已停止")

def start_ipc_server(socket_path=None, debug_mode=False):
    """启动IPC服务器"""
    global _ipc_server
    
    # 如果未提供socket_path，则根据平台生成一个默认值
    if socket_path is None:
        if sys.platform == "win32":
            socket_path = "port:27015"  # Windows使用TCP端口
        else:
            socket_path = os.path.join(tempfile.gettempdir(), "blender-mcp.sock")
    
    if _ipc_server is None:
        logger.info(f"启动IPC服务器，通信路径: {socket_path}")
        _ipc_server = IPCServer(socket_path, debug_mode)
        _ipc_server.start()
        
        # 存储socket_path用于客户端连接
        bpy.types._mcp_socket_path = socket_path

def stop_ipc_server():
    """停止IPC服务器"""
    global _ipc_server
    if _ipc_server is not None:
        _ipc_server.stop()
        _ipc_server = None

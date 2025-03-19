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
# 配置日志格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# 添加控制台处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# 添加文件处理器
log_file = os.path.join(tempfile.gettempdir(), "blender_mcp_ipc.log")
file_handler = logging.FileHandler(log_file, mode='a')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

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
        
        logger.info(f"IPC服务器初始化完成，{'使用调试模式' if debug_mode else '使用普通模式'}")
        logger.debug(f"平台: {'Windows' if self.is_windows else 'Unix/Linux/MacOS'}")
        if self.is_windows:
            logger.debug(f"使用TCP套接字: {self.host}:{self.port}")
        else:
            logger.debug(f"使用Unix域套接字: {self.socket_path}")
        
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
                    
                    # 添加更多详细日志
                    logger.debug(f"收到IPC请求: {request}")
                    response = self.handle_request(request)
                    logger.debug(f"发送IPC响应: {response.get('status', 'unknown')} ({len(str(response))} 字节)")
                    
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
        method = request.get("method")
        logger.debug(f"处理请求: action={action}, method={method}")
        
        try:
            # 处理MCP方法请求
            if method == "mcp/listTools":
                logger.info("收到MCP/listTools请求")
                tools = tool_handlers.list_tools()
                logger.debug(f"返回工具列表，共{len(tools)}个工具")
                return {"result": {"tools": tools}}
            elif method == "mcp/listResources":
                logger.info("收到MCP/listResources请求")
                try:
                    # 添加超时保护，最多等待3秒
                    import time
                    import threading
                    
                    result = {"resources": []}
                    completed = threading.Event()
                    
                    def fetch_resources():
                        try:
                            resources = resource_handlers.handle_list_resources()
                            result["resources"] = resources
                            completed.set()
                        except Exception as e:
                            logger.error(f"获取资源列表时出错: {e}")
                            completed.set()
                    
                    # 在后台线程中获取资源
                    thread = threading.Thread(target=fetch_resources)
                    thread.daemon = True
                    thread.start()
                    
                    # 等待结果，最多3秒
                    if completed.wait(3.0):
                        logger.debug(f"返回资源列表，共{len(result['resources'])}个资源")
                    else:
                        logger.warning("获取资源列表超时，返回空列表")
                        
                    return {"result": result}
                except Exception as e:
                    logger.error(f"处理listResources请求时出错: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    return {"result": {"resources": []}}
                
            # 资源相关操作
            if action == "list_resources":
                logger.debug("处理list_resources请求")
                resources = resource_handlers.handle_list_resources()
                logger.debug(f"找到{len(resources)}个资源")
                return resources
            elif action == "list_tools":
                logger.debug("处理list_tools请求")
                tools = tool_handlers.list_tools()
                logger.info(f"返回{len(tools)}个工具")
                return tools
            elif action == "read_resource":
                resource_type = request.get("type")
                resource_id = request.get("id")
                logger.debug(f"处理read_resource请求: type={resource_type}, id={resource_id}")
                return resource_handlers.handle_read_resource(resource_type, resource_id)
                
            # 工具相关操作
            elif action == "call_tool":
                tool_name = request.get("tool")
                arguments = request.get("arguments", {})
                logger.info(f"执行工具: {tool_name}, 参数: {json.dumps(arguments)}")
                
                # 添加超时保护，最多等待10秒
                try:
                    import threading
                    import time
                    
                    tool_result = {"error": "工具执行超时"}
                    execution_complete = threading.Event()
                    
                    def execute_tool_with_timeout():
                        nonlocal tool_result
                        try:
                            result = tool_handlers.execute_tool(tool_name, arguments)
                            tool_result = result
                            execution_complete.set()
                        except Exception as e:
                            logger.error(f"执行工具时出错: {e}")
                            tool_result = {"error": str(e)}
                            execution_complete.set()
                    
                    # 在后台线程中执行工具
                    thread = threading.Thread(target=execute_tool_with_timeout)
                    thread.daemon = True
                    thread.start()
                    
                    # 等待最多10秒
                    if execution_complete.wait(10.0):
                        logger.debug(f"工具执行完成: {json.dumps(tool_result)}")
                    else:
                        logger.warning(f"工具 {tool_name} 执行超时")
                        tool_result = {"error": f"工具 {tool_name} 执行超时 (>10秒)"}
                    
                    return tool_result
                except Exception as e:
                    logger.error(f"添加工具超时保护时出错: {e}")
                    # 如果超时机制本身出错，回退到直接执行
                    result = tool_handlers.execute_tool(tool_name, arguments)
                    logger.debug(f"工具执行结果: {json.dumps(result)}")
                    return result
                
            # 订阅资源变化
            elif action == "subscribe_resource":
                resource_uri = request.get("uri")
                client_socket = request.get("_client_socket")
                
                logger.debug(f"处理资源订阅请求: {resource_uri}")
                
                if not resource_uri or not client_socket:
                    return {"error": "缺少必要参数"}
                    
                if resource_uri not in self.subscribed_resources:
                    self.subscribed_resources[resource_uri] = []
                    
                if client_socket not in self.subscribed_resources[resource_uri]:
                    self.subscribed_resources[resource_uri].append(client_socket)
                    
                logger.debug(f"客户端已订阅资源 {resource_uri}")
                return {"status": "success", "message": f"已订阅资源 {resource_uri}"}
                
            # 取消订阅资源变化
            elif action == "unsubscribe_resource":
                resource_uri = request.get("uri")
                client_socket = request.get("_client_socket")
                
                logger.debug(f"处理资源取消订阅请求: {resource_uri}")
                
                if not resource_uri or not client_socket:
                    return {"error": "缺少必要参数"}
                    
                if resource_uri in self.subscribed_resources and client_socket in self.subscribed_resources[resource_uri]:
                    self.subscribed_resources[resource_uri].remove(client_socket)
                    logger.debug(f"客户端已取消订阅资源 {resource_uri}")
                    
                return {"status": "success", "message": f"已取消订阅资源 {resource_uri}"}
            
            # 测试命令
            elif action == "test":
                logger.debug("处理测试请求")
                return {"status": "success", "server_time": time.time()}
                
            # 停止服务器
            elif action == "stop" or request.get("command") == "stop":
                logger.info("收到停止服务器请求")
                self.running = False
                return {"status": "shutting_down"}
                
            # 获取服务器状态
            elif action == "status":
                logger.debug("处理状态请求")
                return {
                    "status": "running",
                    "uptime": time.time() - self.start_time if hasattr(self, 'start_time') else 0,
                    "clients_count": len(self.clients),
                    "subscriptions_count": sum(len(clients) for clients in self.subscribed_resources.values())
                }
                
            else:
                error_msg = f"未知操作: {action or method}"
                logger.warning(error_msg)
                return {"error": error_msg}
                
        except Exception as e:
            import traceback
            error_msg = f"处理请求时出错: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
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

    def is_running(self):
        """检查服务器是否正在运行"""
        return self.running and self.is_alive()

def start_ipc_server(socket_path=None, debug_mode=False):
    """启动IPC服务器"""
    global _ipc_server
    
    try:
        if _ipc_server is not None:
            logger.warning("IPC服务器已经在运行")
            return True  # 已经运行也视为成功
            
        logger.info("正在启动IPC服务器...")
        
        # 如果没有提供socket_path，则使用默认值
        if socket_path is None:
            if sys.platform == "win32":
                socket_path = "port:27015"
            else:
                socket_path = os.path.join(tempfile.gettempdir(), "blender-mcp.sock")
                
        logger.info(f"使用socket路径: {socket_path}")
        
        # 快速创建和启动服务器，避免复杂的等待逻辑
        _ipc_server = IPCServer(socket_path, debug_mode)
        _ipc_server.start()
        
        # 给服务器一点时间启动，但不等待太久
        time.sleep(0.1)
        
        # 快速检查服务器是否启动
        if not _ipc_server.is_alive():
            logger.error("IPC服务器启动失败")
            _ipc_server = None
            return False
            
        logger.info("IPC服务器已启动")
        
        # 确保主线程处理器已注册
        try:
            from ..utils import thread_utils
            thread_utils.register_main_thread_processor()
        except Exception as e:
            logger.error(f"注册主线程处理器失败: {e}")
            # 但不要因为这个失败就停止服务器
        
        return True
        
    except Exception as e:
        logger.error(f"启动IPC服务器出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # 清理资源
        if _ipc_server is not None:
            try:
                _ipc_server.stop()
            except:
                pass
            _ipc_server = None
            
        return False

def stop_ipc_server():
    """停止IPC服务器"""
    global _ipc_server
    
    if _ipc_server is not None:
        logger.info("正在停止IPC服务器...")
        _ipc_server.stop()
        _ipc_server = None
        logger.info("IPC服务器已停止")
        return True
    else:
        logger.warning("没有正在运行的IPC服务器")
        return False

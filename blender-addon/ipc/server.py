import socket
import threading
import json
import os
import bpy
import sys
import tempfile
import time
from ..handlers import resource_handlers, tool_handlers
from ..mcp_types import (
    RequestId,
    ErrorData,
    create_error_data
)
from ..logger import get_logger

# 设置日志
logger = get_logger("BlenderMCP.IPC")


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
                    
                    # 检查请求类型
                    is_jsonrpc = "jsonrpc" in request and "id" in request
                    has_method = "method" in request
                    has_action = "action" in request
                    
                    # 添加更多详细日志
                    if is_jsonrpc:
                        logger.debug(f"收到JSON-RPC请求: id={request.get('id')}, method={request.get('method')}")
                    elif has_method:
                        logger.debug(f"收到MCP方法请求: {request.get('method')}")
                    elif has_action:
                        logger.debug(f"收到Action请求: {request.get('action')}")
                    else:
                        logger.debug(f"收到未知类型请求: {request}")
                    
                    # 处理请求
                    response = self.handle_request(request)
                    
                    # 记录响应类型
                    if "error" in response:
                        logger.debug(f"发送错误响应: {response.get('error')}")
                    elif "result" in response:
                        logger.debug(f"发送成功响应: 结果类型={type(response.get('result'))}")
                    else:
                        logger.debug(f"发送响应: {response.get('status', 'unknown')} ({len(str(response))} 字节)")
                    
                    # 发送响应
                    response_json = json.dumps(response)
                    client_socket.sendall(f"{len(response_json)}:".encode() + response_json.encode())
                    
                except socket.timeout:
                    # 超时但继续循环
                    continue
                except ConnectionError as e:
                    logger.debug(f"客户端连接关闭: {str(e)}")
                    break
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析错误: {str(e)}")
                    # 尝试发送错误响应
                    error_data = create_error_data(-32700, f"解析错误: {str(e)}").to_dict()
                    error_response = json.dumps({
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": error_data
                    })
                    client_socket.sendall(f"{len(error_response)}:".encode() + error_response.encode())
                except Exception as e:
                    logger.error(f"处理客户端消息时出错: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    try:
                        # 尝试发送错误响应
                        error_data = create_error_data(-32603, f"内部错误: {str(e)}").to_dict()
                        error_response = json.dumps({
                            "jsonrpc": "2.0",
                            "id": None,
                            "error": error_data
                        })
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
        
        # 检查是否为JSON-RPC请求
        jsonrpc = request.get("jsonrpc")
        req_id = request.get("id")
        is_jsonrpc = jsonrpc == "2.0" and req_id is not None
        
        try:
            # 处理MCP方法请求
            if method is not None:
                logger.info(f"收到MCP方法请求: {method}")
                
                # 处理各种MCP方法
                if method == "tools/list":
                    logger.info("处理tools/list方法")
                    
                    # 使用新的工具处理系统获取工具列表
                    try:
                        from ..handlers.tools import list_tools
                        tools_list = list_tools()
                        
                        logger.debug(f"找到 {len(tools_list)} 个工具")
                        
                        # 标准MCP响应格式
                        result = {"tools": tools_list}
                        
                        # 返回结果
                        if is_jsonrpc:
                            return {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "result": result
                            }
                        return {"result": result}
                    except Exception as e:
                        logger.error(f"获取工具列表时出错: {str(e)}")
                        import traceback
                        logger.error(traceback.format_exc())
                        
                        error_data = create_error_data(
                            -32603,
                            f"获取工具列表时出错: {str(e)}"
                        ).to_dict()
                        
                        if is_jsonrpc:
                            return {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": error_data
                            }
                        return {"error": error_data}
                    
                elif method == "tools/call":
                    logger.info("处理tools/call方法")
                    params = request.get("params", {})
                    tool_name = params.get("name")
                    arguments = params.get("arguments", {})
                    
                    if not tool_name:
                        error_data = create_error_data(
                            -32602,
                            "无效的工具参数，缺少tool_name"
                        ).to_dict()
                        
                        if is_jsonrpc:
                            return {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": error_data
                            }
                        return {"error": error_data}
                    
                    # 使用新的工具处理系统执行工具
                    try:
                        logger.info(f"执行工具: {tool_name}, 参数: {arguments}")
                        from ..handlers.tools import execute_tool
                        
                        # 执行工具并获取标准格式的结果
                        result = execute_tool(tool_name, arguments)
                        logger.debug(f"工具执行结果: {result}")
                        
                        # 返回结果
                        if is_jsonrpc:
                            return {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "result": result
                            }
                        return {"result": result}
                    except Exception as e:
                        import traceback
                        logger.error(f"执行工具时出错: {str(e)}")
                        logger.error(traceback.format_exc())
                        
                        # 创建标准格式的错误响应
                        from ..handlers.tools import MCPSerializer
                        error_content = MCPSerializer.create_text_content(f"执行工具时出错: {str(e)}")
                        error_result = MCPSerializer.create_tool_result([error_content], is_error=True)
                        standardized_result = MCPSerializer.standardize_result(error_result)
                        
                        if is_jsonrpc:
                            return {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "result": standardized_result
                            }
                        return {"result": standardized_result}
                    
                elif method == "resources/list":
                    logger.info("处理resources/list方法")
                    try:
                        # 添加超时保护，最多等待3秒
                        import time
                        import threading
                        
                        resources = resource_handlers.handle_list_resources()
                        
                        if is_jsonrpc:
                            return {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "result": resources
                            }
                        return {"result": resources}
                    except Exception as e:
                        logger.error(f"处理resources/list请求时出错: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        
                        error_data = create_error_data(
                            -32603,
                            f"处理resources/list请求时出错: {str(e)}"
                        ).to_dict()
                        
                        if is_jsonrpc:
                            return {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": error_data
                            }
                        return {"error": error_data}
                    
                elif method == "resources/read":
                    logger.info("处理resources/read方法")
                    params = request.get("params", {})
                    uri = params.get("uri")
                    
                    if not uri:
                        error_data = create_error_data(
                            -32602,
                            "无效的资源参数，缺少uri"
                        ).to_dict()
                        
                        if is_jsonrpc:
                            return {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": error_data
                            }
                        return {"error": error_data}
                    
                    try:
                        # 解析URI
                        if uri.startswith("blender://"):
                            # 去除协议部分
                            path = uri[len("blender://"):]
                            # 分割资源类型和ID
                            parts = path.split('/')
                            if len(parts) < 2:
                                raise ValueError(f"无效的Blender资源URI: {uri}")
                                
                            resource_type = parts[0]
                            resource_id = '/'.join(parts[1:])
                            
                            # 读取资源
                            result = resource_handlers.handle_read_resource(resource_type, resource_id)
                            
                            if is_jsonrpc:
                                return {
                                    "jsonrpc": "2.0",
                                    "id": req_id,
                                    "result": result
                                }
                            return {"result": result}
                        else:
                            error_data = create_error_data(
                                -32602,
                                f"不支持的URI协议: {uri}"
                            ).to_dict()
                            
                            if is_jsonrpc:
                                return {
                                    "jsonrpc": "2.0",
                                    "id": req_id,
                                    "error": error_data
                                }
                            return {"error": error_data}
                    except Exception as e:
                        import traceback
                        logger.error(f"处理resources/read请求时出错: {str(e)}")
                        logger.error(traceback.format_exc())
                        
                        error_data = create_error_data(
                            -32603,
                            f"处理resources/read请求时出错: {str(e)}"
                        ).to_dict()
                        
                        if is_jsonrpc:
                            return {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": error_data
                            }
                        return {"error": error_data}
                
                else:
                    # 处理未知MCP方法
                    error_data = create_error_data(
                        -32601,
                        f"未知方法: {method}"
                    ).to_dict()
                    
                    if is_jsonrpc:
                        return {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "error": error_data
                        }
                    return {"error": error_data}
            
            # 处理传统action请求
            elif action is not None:
                # 资源相关操作
                if action == "list_resources":
                    logger.debug("处理list_resources请求")
                    resources = resource_handlers.handle_list_resources()
                    logger.debug(f"找到{len(resources)}个资源")
                    return resources
                elif action == "list_tools":
                    logger.debug("处理list_tools请求")
                    # 使用新的工具处理系统获取工具列表
                    try:
                        from ..handlers.tools import list_tools
                        tools_list = list_tools()
                        logger.info(f"返回{len(tools_list)}个工具")
                        return {"tools": tools_list}
                    except Exception as e:
                        logger.error(f"获取工具列表时出错: {str(e)}")
                        import traceback
                        logger.error(traceback.format_exc())
                        return {"error": f"获取工具列表时出错: {str(e)}"}
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
                                # 使用新的工具处理系统执行工具
                                from ..handlers.tools import execute_tool
                                result = execute_tool(tool_name, arguments)
                                tool_result = result
                                execution_complete.set()
                            except Exception as e:
                                logger.error(f"执行工具时出错: {e}")
                                # 创建标准格式的错误响应
                                from ..handlers.tools import MCPSerializer
                                error_content = MCPSerializer.create_text_content(f"执行工具时出错: {str(e)}")
                                error_result = MCPSerializer.create_tool_result([error_content], is_error=True)
                                tool_result = MCPSerializer.standardize_result(error_result)
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
                            # 创建标准格式的错误响应
                            from ..handlers.tools import MCPSerializer
                            error_content = MCPSerializer.create_text_content(f"工具 {tool_name} 执行超时 (>10秒)")
                            error_result = MCPSerializer.create_tool_result([error_content], is_error=True)
                            tool_result = MCPSerializer.standardize_result(error_result)
                        
                        return tool_result
                    except Exception as e:
                        logger.error(f"添加工具超时保护时出错: {e}")
                        # 如果超时机制本身出错，回退到直接执行
                        try:
                            # 使用新的工具处理系统执行工具
                            from ..handlers.tools import execute_tool
                            result = execute_tool(tool_name, arguments)
                            logger.debug(f"工具执行结果: {json.dumps(result)}")
                            return result
                        except Exception as exec_err:
                            logger.error(f"直接执行工具时出错: {exec_err}")
                            # 创建标准格式的错误响应
                            from ..handlers.tools import MCPSerializer
                            error_content = MCPSerializer.create_text_content(f"执行工具时出错: {str(exec_err)}")
                            error_result = MCPSerializer.create_tool_result([error_content], is_error=True)
                            return MCPSerializer.standardize_result(error_result)
                
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
                    error_msg = f"未知操作: {action}"
                    logger.warning(error_msg)
                    return {"error": error_msg}
                    
            else:
                error_msg = "请求中未指定action或method"
                logger.warning(error_msg)
                
                error_data = create_error_data(
                    -32600,
                    error_msg
                ).to_dict()
                
                if is_jsonrpc:
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": error_data
                    }
                return {"error": error_msg}
                
        except Exception as e:
            import traceback
            error_msg = f"处理请求时出错: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            error_data = create_error_data(
                -32603,
                error_msg
            ).to_dict()
            
            if is_jsonrpc:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": error_data
                }
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

def start_ipc_server(socket_path, debug_mode=False):
    """
    启动IPC服务器
    
    参数:
        socket_path: 服务器套接字路径，Windows上为"port:端口号"，Unix上为套接字文件路径
        debug_mode: 是否启用调试模式
        
    返回:
        bool: 服务器启动是否成功
    """
    global _ipc_server
    
    # 首先重新配置日志级别
    try:
        from ..logger import configure_logging
        import logging
        log_level = logging.DEBUG if debug_mode else logging.INFO
        configure_logging(log_level=log_level)
        logger.info(f"IPC服务器启动，设置日志级别: {'DEBUG' if debug_mode else 'INFO'}")
    except Exception as e:
        print(f"配置日志级别时出错: {str(e)}")
        # 出错时继续启动服务器，但不改变日志级别
    
    logger.info(f"正在启动IPC服务器，通信路径: {socket_path}")
    
    try:
        # 检查服务器是否已经运行
        if _ipc_server is not None and _ipc_server.running:
            logger.warning("IPC服务器已在运行中，无需再次启动")
            return True
        
        # 停止可能已存在的服务器实例
        if _ipc_server is not None:
            logger.info("停止现有IPC服务器实例")
            _ipc_server.stop()
            _ipc_server = None
        
        # 创建新的服务器实例
        _ipc_server = IPCServer(socket_path, debug_mode)
        _ipc_server.start()
        
        # 设置全局标志指示服务器已启动
        bpy.types._mcp_server_running = True
        bpy.types._mcp_server_socket_path = socket_path
        
        logger.info("IPC服务器启动成功")
        return True
    except Exception as e:
        logger.error(f"启动IPC服务器时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # 确保服务器实例被正确清理
        if _ipc_server is not None:
            try:
                _ipc_server.stop()
            except:
                pass
            _ipc_server = None
            
        # 设置全局标志指示服务器未启动
        bpy.types._mcp_server_running = False
        return False

def stop_ipc_server():
    """停止IPC服务器"""
    global _ipc_server
    
    if _ipc_server is not None:
        logger.info("正在停止IPC服务器...")
        try:
            _ipc_server.stop()
            _ipc_server = None
            # 设置全局标志指示服务器已停止
            bpy.types._mcp_server_running = False
            if hasattr(bpy.types, "_mcp_server_socket_path"):
                delattr(bpy.types, "_mcp_server_socket_path")
            logger.info("IPC服务器已停止")
            return True
        except Exception as e:
            logger.error(f"停止IPC服务器时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            _ipc_server = None
            # 设置全局标志指示服务器已停止
            bpy.types._mcp_server_running = False
            if hasattr(bpy.types, "_mcp_server_socket_path"):
                delattr(bpy.types, "_mcp_server_socket_path")
            return False
    else:
        logger.warning("没有正在运行的IPC服务器")
        # 确保全局状态一致
        bpy.types._mcp_server_running = False
        if hasattr(bpy.types, "_mcp_server_socket_path"):
            delattr(bpy.types, "_mcp_server_socket_path")
        return False

def get_server():
    """
    获取全局IPC服务器实例
    
    Returns:
        IPCServer: 全局IPC服务器实例，如果服务器尚未启动，则返回None
    """
    global _ipc_server
    return _ipc_server

import socket
import threading
import json
import os
import bpy
import logging
import sys
import tempfile
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
                    client_socket, addr = self.server_socket.accept()
                    print(f"接受到新的连接：{addr}")
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket,)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                except socket.timeout:
                    # 超时但继续循环
                    continue
                except Exception as e:
                    if self.running:
                        print(f"接受连接时出错: {e}")
                        logger.error(f"接受连接时出错: {e}")
                    break
        except Exception as e:
            error_msg = f"启动TCP服务器时出错: {str(e)}"
            print(error_msg)
            logger.error(error_msg)
            # 设置全局标志表明服务器未启动
            bpy.types._mcp_server_running = False
            
    def _run_unix_socket_server(self):
        """使用Unix域套接字启动服务器(Unix/Linux)"""
        # 如果socket文件已存在，删除它
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
            
        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_socket.bind(self.socket_path)
        self.server_socket.listen(1)
        
        self.running = True
        logger.info(f"IPC Unix套接字服务器已启动，监听：{self.socket_path}")
        
        while self.running:
            try:
                client_socket, _ = self.server_socket.accept()
                logger.debug("接受到新的连接")
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket,)
                )
                client_thread.daemon = True
                client_thread.start()
            except Exception as e:
                if self.running:
                    logger.error(f"接受连接时出错: {e}")
                break
                
    def handle_client(self, client_socket):
        """处理客户端连接"""
        try:
            while self.running:
                # 读取消息长度
                header = b""
                while b":" not in header:
                    chunk = client_socket.recv(1)
                    if not chunk:
                        logger.debug("客户端断开连接")
                        return
                    header += chunk
                    
                length = int(header.decode().split(":")[0])
                logger.debug(f"接收到消息头，消息长度: {length}")
                
                # 读取消息内容
                data = b""
                while len(data) < length:
                    chunk = client_socket.recv(min(4096, length - len(data)))
                    if not chunk:
                        logger.error("接收数据时连接意外关闭")
                        return
                    data += chunk
                    
                # 解析请求
                request = json.loads(data.decode())
                logger.debug(f"收到请求: {request}")
                
                # 处理请求
                response = self.handle_request(request)
                logger.debug(f"发送响应: {response}")
                
                # 发送响应
                response_data = json.dumps(response).encode()
                client_socket.sendall(f"{len(response_data)}:".encode() + response_data)
                
        except Exception as e:
            logger.error(f"处理客户端时出错: {e}")
        finally:
            client_socket.close()
            logger.debug("客户端连接已关闭")
            
    def handle_request(self, request):
        """处理请求并返回结果"""
        action = request.get("action")
        logger.debug(f"处理动作: {action}")
        
        try:
            # 资源相关操作
            if action == "list_resources":
                return resource_handlers.handle_list_resources()
            elif action == "read_resource":
                return resource_handlers.handle_read_resource(
                    request.get("type"),
                    request.get("id")
                )
            elif action == "check_object_exists":
                return resource_handlers.check_object_exists(
                    request.get("object_name")
                )
                
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
        if self.server_socket:
            self.server_socket.close()
        if os.path.exists(self.socket_path):
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

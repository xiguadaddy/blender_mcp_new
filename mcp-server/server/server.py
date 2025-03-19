import asyncio
import logging
import sys
import traceback
import json
import time
from mcp.server import Server, NotificationOptions
from tools.handlers import register_tool_handlers
from resources.handlers import register_resource_handlers
from prompts.handlers import register_prompt_handlers
from typing import Dict, Any, Optional, Tuple, List

# 配置日志
logger = logging.getLogger("BlenderMCP.Server")

class BlenderMCPServer:
    """Blender MCP服务器类，负责初始化和管理MCP服务器实例"""
    
    def __init__(self, ipc_client):
        """初始化服务器
        
        Args:
            ipc_client: IPC客户端实例，用于与Blender通信
        """
        self.ipc_client = ipc_client
        self.server = None
        self.server_name = "blender-mcp"
        self.server_version = "0.2.1"  # 更新版本号
        self.health_check_interval = 30  # 默认健康检查间隔(秒)
        self.last_health_check = None  # 上次健康检查时间
        self.health_status = {
            "blender_connected": False,
            "server_initialized": False,
            "last_error": None,
            "last_check_time": None
        }
        self.capabilities = None  # 缓存的服务器能力
        
    def initialize(self):
        """初始化并配置MCP服务器
        
        Returns:
            Server: 初始化好的MCP服务器实例
        """
        logger.info("初始化Blender MCP服务器...")
        
        # 创建服务器实例
        try:
            self.server = Server(self.server_name)
            logger.debug(f"服务器实例创建成功: {type(self.server).__name__}")
        except Exception as e:
            logger.error(f"创建服务器实例时出错: {str(e)}")
            logger.error(traceback.format_exc())
            raise
        
        # 注册处理程序
        self._register_handlers()
        
        # 检查服务器配置
        self._verify_server()
        
        # 更新健康状态
        self.health_status["server_initialized"] = True
        
        logger.info("服务器初始化完成")
        return self.server
    
    def _register_handlers(self):
        """注册所有必要的处理程序"""
        handlers_registered = {
            "resource": False,
            "tool": False,
            "prompt": False
        }
        
        try:
            logger.info("注册资源处理程序...")
            register_resource_handlers(self.server, self.ipc_client)
            handlers_registered["resource"] = True
            
            logger.info("注册工具处理程序...")
            register_tool_handlers(self.server, self.ipc_client)
            handlers_registered["tool"] = True
            
            logger.info("注册提示处理程序...")
            register_prompt_handlers(self.server, self.ipc_client)
            handlers_registered["prompt"] = True
        except Exception as e:
            logger.error(f"注册处理程序时出错: {str(e)}")
            logger.error(f"处理程序注册状态: {handlers_registered}")
            logger.error(traceback.format_exc())
            raise
    
    def _verify_server(self):
        """验证服务器配置和必要方法"""
        # 安全地检查服务器类型和方法
        logger.info(f"服务器类型: {type(self.server).__name__}")
        
        # 检查可用方法
        safe_methods = []
        unsafe_attrs = ["request_context", "session", "handle_request"]
        
        for m in dir(self.server):
            if m.startswith('_') or m in unsafe_attrs:
                continue
            try:
                attr = getattr(self.server, m)
                if callable(attr):
                    safe_methods.append(m)
            except Exception:
                # 忽略访问属性时的任何错误
                pass
        
        logger.info(f"可用方法: {safe_methods}")
        
        # 检查装饰器方法
        logger.info("检查装饰器方法...")
        decorator_methods = [
            "list_tools", "call_tool", "list_resources", "read_resource", 
            "list_prompts", "get_prompt"
        ]
        
        for method in decorator_methods:
            if hasattr(self.server, method):
                logger.info(f"服务器具有{method}装饰器方法")
            else:
                logger.warning(f"服务器缺少{method}装饰器方法")
        
        # 确保 run 方法存在
        if hasattr(self.server, "run") and callable(getattr(self.server, "run")):
            logger.info("服务器具有run方法")
        else:
            logger.error("服务器缺少run方法，这是必需的！")
            raise RuntimeError("服务器缺少run方法")
        
        # 尝试安全地获取处理程序信息
        if hasattr(self.server, "_request_handlers") and isinstance(self.server._request_handlers, dict):
            logger.info(f"处理程序: {list(self.server._request_handlers.keys())}")
        else:
            logger.warning("无法访问处理程序列表，跳过验证")
    
    def get_capabilities(self) -> Dict[str, Any]:
        """获取服务器能力
        
        Returns:
            dict: 服务器能力字典
        """
        try:
            # 创建完整的通知选项
            notification_options = NotificationOptions(
                prompts_changed=True,
                resources_changed=True,  # 启用资源更新通知
                tools_changed=True    # 启用方法结果通知
            )
            
            # 设置MCP功能支持
            experimental_capabilities = {
                "blender": {
                    "can_render": True,
                    "supports_3d": True,
                    "supports_materials": True,
                    "supports_animation": True
                }
            }
            
            # 获取完整的服务器能力
            capabilities = self.server.get_capabilities(
                notification_options=notification_options,
                experimental_capabilities=experimental_capabilities,
            )
            
            # 缓存能力信息
            self.capabilities = capabilities
            logger.debug(f"成功获取服务器能力: {capabilities}")
            return capabilities
        except Exception as e:
            logger.error(f"获取服务器能力时出错: {e}")
            logger.error(traceback.format_exc())
            return {}
    
    async def health_check(self) -> Tuple[bool, str]:
        """检查服务器和Blender连接的健康状态
        
        Returns:
            tuple: (状态布尔值, 状态描述)
        """
        try:
            current_time = time.time()
            self.health_status["last_check_time"] = current_time
            
            # 检查Blender连接
            ping_status = self.ipc_client.ping()
            self.health_status["blender_connected"] = (
                ping_status.get("status") == "connected"
            )
            
            if not self.health_status["blender_connected"]:
                error_msg = f"Blender连接问题: {ping_status.get('message', '未知错误')}"
                self.health_status["last_error"] = error_msg
                return False, error_msg
                
            # 检查服务器状态
            if not self.server:
                error_msg = "服务器未初始化"
                self.health_status["last_error"] = error_msg
                return False, error_msg
            
            # 更新上次健康检查时间
            self.last_health_check = current_time
                
            return True, "服务器运行正常"
        except Exception as e:
            error_msg = f"服务器健康检查失败: {str(e)}"
            self.health_status["last_error"] = error_msg
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return False, error_msg
    
    def get_health_status(self) -> Dict[str, Any]:
        """获取完整的健康状态信息
        
        Returns:
            Dict[str, Any]: 健康状态信息
        """
        # 如果上次检查时间超过间隔，执行同步健康检查
        if (
            self.last_health_check is None or 
            time.time() - self.last_health_check > self.health_check_interval
        ):
            logger.debug("健康状态过期，执行同步检查")
            try:
                # 直接检查Blender连接
                ping_status = self.ipc_client.ping()
                self.health_status["blender_connected"] = (
                    ping_status.get("status") == "connected"
                )
                self.health_status["last_check_time"] = time.time()
            except Exception as e:
                logger.error(f"同步健康检查出错: {e}")
                self.health_status["last_error"] = str(e)
                
        return {
            **self.health_status,
            "server_version": self.server_version,
            "capabilities": self.capabilities
        }
    
    async def recover(self) -> bool:
        """尝试恢复服务器和Blender连接
        
        Returns:
            bool: 恢复成功返回True，否则返回False
        """
        logger.info("尝试恢复服务器和Blender连接")
        
        try:
            # 1. 尝试重新连接Blender
            if not self.health_status["blender_connected"]:
                logger.info("尝试重新连接Blender")
                reconnect_result = await self.ipc_client.reconnect()
                if not reconnect_result:
                    logger.error("重新连接Blender失败")
                    return False
                logger.info("重新连接Blender成功")
            
            # 2. 检查服务器初始化
            if not self.health_status["server_initialized"]:
                logger.info("重新初始化服务器")
                self.initialize()
            
            # 3. 进行健康检查
            status, message = await self.health_check()
            if not status:
                logger.error(f"恢复后健康检查仍然失败: {message}")
                return False
            
            logger.info("服务器和Blender连接已恢复")
            return True
        except Exception as e:
            logger.error(f"恢复服务器和Blender连接时出错: {e}")
            logger.error(traceback.format_exc())
            return False


def create_server(ipc_client):
    """创建并配置MCP服务器（兼容旧版API）
    
    Args:
        ipc_client: IPC客户端实例
        
    Returns:
        Server: 配置好的MCP服务器实例
    """
    server_manager = BlenderMCPServer(ipc_client)
    return server_manager.initialize()


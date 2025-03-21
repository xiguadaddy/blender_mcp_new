"""
MCP处理程序基类

定义处理MCP请求和通知的基本接口。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import sys
import traceback

# 导入MCP类型

from ..mcp_types import Request, Result, Notification, ErrorData, create_error_data

class Handler(ABC):
    """所有MCP处理程序的基类"""
    
    @property
    @abstractmethod
    def method(self) -> str:
        """处理程序处理的方法名称"""
        pass
        
    def validate(self, params: Dict[str, Any]) -> Optional[ErrorData]:
        """
        验证请求或通知参数
        
        Args:
            params: 请求或通知参数
            
        Returns:
            如果验证失败，返回ErrorData；否则返回None
        """
        return None

class RequestHandler(Handler):
    """处理MCP请求的基类"""
    
    @abstractmethod
    def handle(self, request: Request) -> Result:
        """
        处理MCP请求
        
        Args:
            request: MCP请求对象
            
        Returns:
            处理结果
        """
        pass
        
    def safe_handle(self, request: Request) -> Dict[str, Any]:
        """
        安全处理MCP请求，捕获异常
        
        Args:
            request: MCP请求对象
            
        Returns:
            JSON-RPC响应字典
        """
        try:
            # 验证参数
            error = self.validate(request.params.to_dict() if request.params else {})
            if error:
                return {
                    "jsonrpc": "2.0",
                    "id": request.id,
                    "error": error.to_dict()
                }
                
            # 处理请求
            result = self.handle(request)
            
            # 构建成功响应
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "result": result.to_dict()
            }
        except Exception as e:
            # 捕获异常并返回错误响应
            exc_type, exc_value, exc_traceback = sys.exc_info()
            trace = traceback.format_exception(exc_type, exc_value, exc_traceback)
            
            error = create_error_data(
                code=-32000,
                message=str(e),
                data={"traceback": "".join(trace)}
            )
            
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "error": error.to_dict()
            }

class NotificationHandler(Handler):
    """处理MCP通知的基类"""
    
    @abstractmethod
    def handle(self, notification: Notification) -> None:
        """
        处理MCP通知
        
        Args:
            notification: MCP通知对象
        """
        pass
        
    def safe_handle(self, notification: Notification) -> None:
        """
        安全处理MCP通知，捕获异常
        
        Args:
            notification: MCP通知对象
        """
        try:
            # 验证参数
            error = self.validate(notification.params.to_dict() if notification.params else {})
            if error:
                print(f"通知验证失败: {error.message}")
                return
                
            # 处理通知
            self.handle(notification)
        except Exception as e:
            # 捕获异常并记录
            print(f"处理通知时出错: {str(e)}")
            traceback.print_exc()

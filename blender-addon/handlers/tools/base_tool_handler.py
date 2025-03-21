import logging
import json
import traceback
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from ..handler_base import RequestHandler
from .serializer import MCPSerializer
from ...mcp_types import Request, Result, CallToolResult

# 获取日志器
logger = logging.getLogger("BlenderMCP.ToolHandler")

class BaseToolHandler(ABC):
    """
    工具处理器基类
    所有工具处理器都应该继承此类
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass
        
    @property
    def description(self) -> Optional[str]:
        """工具描述"""
        return None
        
    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """工具输入模式"""
        pass
        
    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """
        验证工具参数
        
        Args:
            arguments: 工具参数
            
        Returns:
            如果验证失败，返回错误消息；否则返回None
        """
        # 默认实现不进行验证
        return None
        
    @abstractmethod
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """
        执行工具
        
        Args:
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        pass
        
    def create_text_content(self, text: str) -> Any:
        """创建文本内容对象"""
        return MCPSerializer.create_text_content(text)
        
    def create_image_content(self, data: str, mime_type: str) -> Any:
        """创建图像内容对象"""
        return MCPSerializer.create_image_content(data, mime_type)
        
    def create_result(self, content: List[Any], is_error: bool = False) -> CallToolResult:
        """创建工具调用结果对象"""
        return MCPSerializer.create_tool_result(content, is_error)
        
    def handle(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理工具调用
        
        Args:
            arguments: 工具参数
            
        Returns:
            标准化的工具调用结果
        """
        try:
            # 参数验证
            error = self.validate_arguments(arguments)
            if error:
                logger.error(f"工具 {self.name} 参数验证失败: {error}")
                error_content = self.create_text_content(f"参数验证失败: {error}")
                result = self.create_result([error_content], is_error=True)
                return MCPSerializer.standardize_result(result)
                
            # 执行工具
            logger.info(f"执行工具 {self.name} 参数: {json.dumps(arguments, ensure_ascii=False)}")
            result = self.execute(arguments)
            
            # 处理执行结果
            standardized_result = MCPSerializer.standardize_result(result)
            
            # 添加调试信息
            logger.debug(f"工具 {self.name} 执行结果: {json.dumps(standardized_result, ensure_ascii=False)[:200]}...")
            
            return standardized_result
            
        except Exception as e:
            logger.error(f"工具 {self.name} 执行错误: {str(e)}")
            logger.error(traceback.format_exc())
            
            # 创建错误结果
            error_content = self.create_text_content(f"工具执行错误: {str(e)}")
            result = self.create_result([error_content], is_error=True)
            
            return MCPSerializer.standardize_result(result)

class ToolsRegistryMixin:
    """工具注册管理混入类"""
    
    def __init__(self):
        self._tools = {}
        
    def register_tool(self, tool_handler: BaseToolHandler) -> None:
        """
        注册工具处理器
        
        Args:
            tool_handler: 工具处理器实例
        """
        try:
            tool_name = tool_handler.name
            logger.info(f"开始注册工具: {tool_name}")
            
            if tool_name in self._tools:
                logger.warning(f"工具 {tool_name} 已存在，将被覆盖")
                
            self._tools[tool_name] = tool_handler
            logger.info(f"成功注册工具: {tool_name}, 当前工具总数: {len(self._tools)}")
            
            # 输出已注册工具列表，用于调试
            tool_names = list(self._tools.keys())
            logger.debug(f"当前已注册工具列表: {tool_names}")
        except Exception as e:
            logger.error(f"注册工具失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        
    def get_tool(self, name: str) -> Optional[BaseToolHandler]:
        """
        获取工具处理器
        
        Args:
            name: 工具名称
            
        Returns:
            工具处理器实例，如果不存在则返回None
        """
        return self._tools.get(name)
        
    def list_tools(self) -> List[Dict[str, Any]]:
        """
        列出所有已注册工具
        
        Returns:
            工具定义列表
        """
        tools = []
        for name, handler in self._tools.items():
            tools.append({
                "name": name,
                "description": handler.description,
                "inputSchema": handler.input_schema
            })
        return tools
        
    def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行工具
        
        Args:
            name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        handler = self.get_tool(name)
        if not handler:
            logger.error(f"未找到工具: {name}")
            error_content = MCPSerializer.create_text_content(f"未找到工具: {name}")
            result = MCPSerializer.create_tool_result([error_content], is_error=True)
            return MCPSerializer.standardize_result(result)
            
        return handler.handle(arguments)

class ToolsRequestHandler(RequestHandler, ToolsRegistryMixin):
    """工具请求处理器"""
    
    def __init__(self):
        ToolsRegistryMixin.__init__(self)
        
    @property
    def method(self) -> str:
        return "tools/call"
        
    def handle(self, request: Request) -> Dict[str, Any]:
        """处理工具调用请求"""
        tool_name = request.params.get("name")
        arguments = request.params.get("arguments", {})
        
        # 执行工具并获取标准化的结果
        result = self.execute_tool(tool_name, arguments)
        
        # 直接返回字典形式的结果
        logger.debug(f"返回工具执行结果: {result}")
        return result 
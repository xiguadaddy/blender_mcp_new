import logging
from typing import Dict, Any, List, Optional
import os
import importlib

from .base_tool_handler import BaseToolHandler, ToolsRegistryMixin


# 获取日志器
logger = logging.getLogger("BlenderMCP.ToolRegistry")

class ToolRegistry(ToolsRegistryMixin):
    """工具注册表，管理所有工具处理器"""
    
    def __init__(self):
        """初始化工具注册表"""
        super().__init__()
        self._register_default_tools()
        
    def _register_default_tools(self):
        """注册默认工具"""
        # 导入工具模块（工具将在导入时自动注册）
        try:
            # 导入工具模块 - 工具会在模块初始化时自动注册
            # 仅导入子目录，不直接注册工具
            # 改为让子目录中的工具自己注册
            # 注意：这里不执行实际的导入，因为会在__init__.py中执行
            logger.info(f"工具注册表初始化完成，等待工具注册")
        except Exception as e:
            logger.error(f"注册默认工具时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
    def _import_tools_from_module(self, module):
        """从模块导入工具
        
        Args:
            module: 工具模块
        """
        try:
            if hasattr(module, 'tool_map'):
                tool_map = module.tool_map
                # 检查tool_map是否为空
                if not tool_map:
                    logger.debug(f"模块 {module.__name__} 的工具映射为空")
                    return
                    
                for name, tool_func in tool_map.items():
                    if not name.startswith('mcp_blender_'):
                        name = f"mcp_blender_{name}"
                    
                    # 使用传统工具适配器包装工具函数
                    from .legacy_adapter import LegacyToolAdapter
                    handler = LegacyToolAdapter(name, tool_func)
                    self.register_tool(handler)
                    logger.debug(f"已从模块 {module.__name__} 导入工具: {name}")
        except Exception as e:
            logger.error(f"从模块 {module.__name__} 导入工具时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
    def register_custom_tool(self, handler: BaseToolHandler) -> None:
        """
        注册自定义工具处理器
        
        Args:
            handler: 工具处理器实例
        """
        self.register_tool(handler)
        
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        获取所有工具的模式定义
        
        Returns:
            工具模式定义列表
        """
        schemas = []
        for name, handler in self._tools.items():
            schemas.append({
                "name": name,
                "description": handler.description or "",
                "inputSchema": handler.input_schema
            })
        return schemas

# 全局工具注册表实例
_tool_registry = None
_initialized = False

def get_tool_registry() -> ToolRegistry:
    """
    获取全局工具注册表实例
    
    Returns:
        工具注册表实例
    """
    global _tool_registry, _initialized
    
    # 延迟初始化
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
        _initialized = True
    
    return _tool_registry

def ensure_initialized() -> None:
    """
    确保工具注册表已初始化
    """
    global _initialized
    if not _initialized:
        get_tool_registry()

def register_tool(handler: BaseToolHandler) -> None:
    """
    注册工具处理器到全局注册表
    
    Args:
        handler: 工具处理器实例
    """
    registry = get_tool_registry()
    registry.register_tool(handler)
    
def execute_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行工具
    
    Args:
        name: 工具名称
        arguments: 工具参数
        
    Returns:
        工具执行结果
    """
    registry = get_tool_registry()
    result = registry.execute_tool(name, arguments)
    
    # 使用序列化工具将结果标准化
    from .serializer import MCPSerializer
    return MCPSerializer.fix_tuple_format(result)
    
def list_tools() -> List[Dict[str, Any]]:
    """
    列出所有已注册工具
    
    Returns:
        工具定义列表
    """
    registry = get_tool_registry()
    return registry.list_tools() 
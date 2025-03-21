"""
传统工具适配器

为老式函数式工具提供兼容层，使其能够集成到新的基于类的工具架构中。
"""

import logging
from .registry import register_tool
import inspect
from typing import Any, Dict, Callable, Optional, List, Tuple

from .base_tool_handler import BaseToolHandler
from . import registry

# 获取日志器
logger = logging.getLogger("BlenderMCP.LegacyAdapter")

class LegacyToolAdapter(BaseToolHandler):
    """
    传统工具适配器类
    
    将老式函数式工具包装为新的工具处理器类
    """
    
    def __init__(self, name: str, func: Callable, description: Optional[str] = None, input_schema: Optional[Dict[str, Any]] = None):
        """
        初始化传统工具适配器
        
        Args:
            name: 工具名称
            func: 工具函数
            description: 工具描述
            input_schema: 输入模式
        """
        self._name = name
        self._func = func
        self._description = description
        self._input_schema = input_schema or self._generate_input_schema()
        
        # 从函数文档中提取描述（如果没有提供）
        if not self._description and self._func.__doc__:
            self._description = self._func.__doc__.strip().split('\n')[0]
        
    @property
    def name(self) -> str:
        """工具名称"""
        # 确保工具名称有统一前缀
        if not self._name.startswith("mcp_blender_"):
            return f"mcp_blender_{self._name}"
        return self._name
        
    @property
    def description(self) -> Optional[str]:
        """工具描述"""
        return self._description
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        """工具输入模式"""
        return self._input_schema
        
    def execute(self, arguments: Dict[str, Any]) -> Any:
        """
        执行工具
        
        Args:
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        logger.debug(f"通过适配器执行传统工具: {self.name}")
        
        try:
            # 调用原始函数
            result = self._func(**arguments)
            return result
        except Exception as e:
            logger.error(f"执行传统工具 {self.name} 时出错: {str(e)}")
            raise
            
    def _generate_input_schema(self) -> Dict[str, Any]:
        """
        从函数签名生成输入模式
        
        Returns:
            生成的输入模式
        """
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        # 获取函数参数
        sig = inspect.signature(self._func)
        for param_name, param in sig.parameters.items():
            # 跳过self参数
            if param_name == "self":
                continue
                
            # 获取参数类型
            param_type = "string"  # 默认类型
            if param.annotation != inspect.Parameter.empty:
                type_name = param.annotation.__name__
                if type_name in ["int", "float", "bool"]:
                    param_type = type_name
                elif type_name == "list" or type_name == "List":
                    param_type = "array"
                elif type_name == "dict" or type_name == "Dict":
                    param_type = "object"
            
            # 创建属性定义
            property_def = {
                "type": param_type,
                "title": param_name.replace("_", " ").title(),
                "description": f"{param_name} 参数"
            }
            
            # 添加属性定义
            schema["properties"][param_name] = property_def
            
            # 如果参数没有默认值，则为必填项
            if param.default == inspect.Parameter.empty:
                schema["required"].append(param_name)
                
        return schema

def adapt_legacy_tools(tools_dict: Dict[str, Callable]) -> List[BaseToolHandler]:
    """
    将传统工具字典适配为工具处理器列表
    
    Args:
        tools_dict: 传统工具字典，键为工具名称，值为工具函数
        
    Returns:
        适配后的工具处理器列表
    """
    handlers = []
    
    for name, func in tools_dict.items():
        try:
            # 创建适配器
            handler = LegacyToolAdapter(name, func)
            handlers.append(handler)
            logger.debug(f"已适配传统工具: {name}")
        except Exception as e:
            logger.error(f"适配传统工具 {name} 时出错: {str(e)}")
            
    return handlers

def register_legacy_tools(tools_dict: Dict[str, Callable]) -> None:
    """
    注册传统工具到全局工具注册表
    
    Args:
        tools_dict: 传统工具字典，键为工具名称，值为工具函数
    """
    handlers = adapt_legacy_tools(tools_dict)
    
    # 获取工具注册表
    tool_registry = registry.get_tool_registry()
    
    # 注册工具处理器
    for handler in handlers:
        tool_registry.register_tool(handler)
        
    logger.info(f"已注册 {len(handlers)} 个传统工具")

def register_legacy_modules() -> None:
    """
    注册传统工具模块中的工具
    
    自动发现和导入当前目录下所有工具子模块，并注册其中的工具
    """
    import os
    import importlib
    import sys
    
    logger.info("开始自动发现并注册传统工具模块...")
    
    # 获取当前目录路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 获取所有子目录（可能的工具模块）
    tool_module_dirs = []
    for item in os.listdir(current_dir):
        item_path = os.path.join(current_dir, item)
        # 检查是否为目录，且包含__init__.py文件（即Python包）
        if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "__init__.py")):
            # 不包括以下划线开头的目录
            if not item.startswith("_"):
                tool_module_dirs.append(item)
    
    logger.debug(f"发现可能的工具模块目录: {tool_module_dirs}")
    
    # 导入各模块并注册工具
    registered_modules = 0
    for module_name in tool_module_dirs:
        try:
            # 构建完整模块路径
            full_module_path = f".{module_name}"
            # 导入模块
            module = importlib.import_module(full_module_path, package=__package__)
            
            # 检查模块是否有register_tools函数或tool_map属性
            if hasattr(module, 'tool_map'):
                # 注册模块中的工具
                tools_count = len(module.tool_map)
                if tools_count > 0:
                    register_legacy_tools(module.tool_map)
                    registered_modules += 1
                    logger.info(f"已注册 {module_name} 模块中的 {tools_count} 个工具")
            else:
                logger.warning(f"模块 {module_name} 没有工具映射 (tool_map)")
                
        except Exception as e:
            logger.error(f"注册 {module_name} 模块工具时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    logger.info(f"自动注册完成，共注册了 {registered_modules} 个工具模块")

# 初始化时自动注册传统工具
try:
    register_legacy_modules()
except Exception as e:
    logger.error(f"注册传统工具模块时出错: {e}") 

# 在导入时自动注册工具实例
register_tool(LegacyToolAdapter())
"""
MCP工具处理器包

包含处理Blender工具调用的各种处理器。
此模块使用基于类的架构处理工具调用，提供更好的可扩展性和错误处理。
"""

import logging
import os
import importlib
import inspect
import sys
import traceback
from pathlib import Path

from ...logger import get_logger

logger = get_logger("BlenderMCP.Tools")

# 记录模块加载
logger.info("正在初始化tools包...")

# 导出核心类和函数
try:
    from .registry import get_tool_registry, register_tool, execute_tool, list_tools, ToolRegistry, ensure_initialized
    from .base_tool_handler import BaseToolHandler
    from .serializer import MCPSerializer
    
    logger.info("基础类和函数导入成功")
except Exception as e:
    logger.error(f"导入基础类和函数失败: {str(e)}")
    logger.error(traceback.format_exc())

# 确保工具注册表已初始化
try:
    ensure_initialized()
    registry = get_tool_registry()
    logger.info("工具注册表初始化成功")
except Exception as e:
    logger.error(f"初始化工具注册表失败: {str(e)}")
    logger.error(traceback.format_exc())

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 在这里导入各个工具包，这样它们会在导入时自动注册其中的工具
try:
    logger.info("开始导入工具包...")
    
    # 扫描工具目录，查找所有工具包
    tool_packages = []
    for item in os.listdir(current_dir):
        item_path = os.path.join(current_dir, item)
        init_file = os.path.join(item_path, "__init__.py")
        
        if os.path.isdir(item_path) and item.endswith("_tools") and os.path.exists(init_file):
            tool_packages.append(item)
    
    logger.info(f"找到 {len(tool_packages)} 个工具包: {tool_packages}")
    
    # 动态导入所有工具包
    for package_name in tool_packages:
        try:
            # 动态导入
            module = importlib.import_module(f".{package_name}", package=__package__)
            globals()[package_name] = module
            logger.info(f"{package_name}导入成功")
            
            # 尝试重新加载模块以确保最新代码
            importlib.reload(module)
        except Exception as e:
            logger.error(f"导入 {package_name} 失败: {str(e)}")
            logger.error(traceback.format_exc())
    
    # 查看已注册的工具数量
    tool_count = len(registry._tools) if hasattr(registry, '_tools') else 0
    logger.info(f"已加载 {tool_count} 个工具")
    
    # 如果没有找到工具，尝试强制导入所有工具模块
    if tool_count == 0:
        logger.warning("未找到任何工具，尝试强制导入所有工具模块...")
        
        # 遍历所有工具目录并导入其中的Python文件
        for package_name in tool_packages:
            package_dir = os.path.join(current_dir, package_name)
            logger.info(f"扫描工具目录: {package_dir}")
            
            for file_path in Path(package_dir).glob("*.py"):
                filename = file_path.name
                if filename != "__init__.py" and filename.endswith(".py"):
                    module_name = filename[:-3]  # 去掉.py后缀
                    full_module_name = f".{package_name}.{module_name}"
                    
                    try:
                        # 动态导入模块
                        module = importlib.import_module(full_module_name, package=__package__)
                        logger.info(f"已导入工具模块: {full_module_name}")
                    except Exception as e:
                        logger.error(f"导入工具模块 {full_module_name} 时出错: {e}")
                        logger.error(traceback.format_exc())
        
        # 再次检查工具注册情况
        tool_count = len(registry._tools) if hasattr(registry, '_tools') else 0
        logger.info(f"强制导入后，已加载 {tool_count} 个工具")
    
    # 输出已注册的工具名称列表
    if hasattr(registry, '_tools') and registry._tools:
        tool_names = list(registry._tools.keys())
        logger.debug(f"已注册工具列表: {tool_names}")
    
except Exception as e:
    logger.error(f"导入工具包时出错: {e}")
    logger.error(traceback.format_exc())

logger.info("tools包初始化完成")

# 导出所有公共符号
__all__ = [
    'get_tool_registry',
    'register_tool',
    'execute_tool',
    'list_tools',
    'BaseToolHandler',
    'MCPSerializer',
    'ToolRegistry',
    'ensure_initialized',
]

# 将找到的所有工具包添加到__all__中
for package_name in [p for p in globals() if p.endswith('_tools')]:
    __all__.append(package_name)

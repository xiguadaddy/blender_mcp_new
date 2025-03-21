"""
统一日志系统

为整个Blender插件提供统一的日志配置和获取方法。
"""

import logging
import os
import tempfile
import sys
import bpy
# 配置日志级别映射，允许从字符串转换到日志级别
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

# 默认日志级别
# 根据context.preferences.addons[addon_id].preferences.debug_mode 是否为True，决定日志级别
def get_default_log_level(context):
    try:
        addon_id = __package__.split('.')[0]  # 提取插件的主包名
        if context and hasattr(context, 'preferences') and hasattr(context.preferences, 'addons'):
            if addon_id in context.preferences.addons:
                preferences = context.preferences.addons[addon_id].preferences
                if hasattr(preferences, 'debug_mode'):
                    return logging.DEBUG if preferences.debug_mode else logging.INFO
    except (AttributeError, TypeError, Exception) as e:
        print(f"获取日志级别时出错: {str(e)}，使用默认DEBUG级别")
    # 如果出现任何错误或无法找到首选项，默认使用DEBUG级别
    return logging.DEBUG

# 安全地获取默认日志级别
try:
    DEFAULT_LOG_LEVEL = get_default_log_level(bpy.context)
except Exception as e:
    print(f"设置默认日志级别时出错: {str(e)}，使用默认DEBUG级别")
    DEFAULT_LOG_LEVEL = logging.DEBUG

# 全局日志配置标志
_logger_configured = False

# 日志文件路径
LOG_FILE = os.path.join(tempfile.gettempdir(), "blender_mcp.log")

# 日志格式
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

def configure_logging(log_level=None, log_file=None):
    """
    配置全局日志系统
    
    参数:
        log_level: 日志级别，可以是字符串或者日志常量
        log_file: 日志文件路径，如果不提供则使用默认路径
    """
    global _logger_configured
    
    if _logger_configured:
        return
    
    # 确定日志级别
    if log_level is None:
        level = DEFAULT_LOG_LEVEL
    elif isinstance(log_level, str) and log_level.upper() in LOG_LEVELS:
        level = LOG_LEVELS[log_level.upper()]
    elif isinstance(log_level, int):
        level = log_level
    else:
        level = DEFAULT_LOG_LEVEL
        
    # 获取根日志器
    root_logger = logging.getLogger("BlenderMCP")
    root_logger.setLevel(level)
    
    # 创建并配置控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(LOG_FORMAT)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # 创建并配置文件处理器
    file_path = log_file or LOG_FILE
    try:
        file_handler = logging.FileHandler(file_path, mode='a', encoding='utf-8')
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(LOG_FORMAT)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    except (IOError, PermissionError) as e:
        console_handler.setLevel(logging.WARNING)
        root_logger.warning(f"无法创建日志文件: {e}")
    
    # 标记日志系统已配置
    _logger_configured = True
    
    return root_logger

def get_logger(name):
    """
    获取指定名称的日志器
    
    参数:
        name: 日志器名称
        
    返回:
        Logger对象
    """
    # 确保全局日志已配置
    if not _logger_configured:
        configure_logging()
        
    # 返回指定名称的日志器
    return logging.getLogger(name)

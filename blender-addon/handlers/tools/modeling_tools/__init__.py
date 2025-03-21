"""
modeling工具模块
"""


import os
import importlib
import inspect
from pathlib import Path

from ....logger import get_logger

logger = get_logger("BlenderMCP.ModelingTools")

# 记录加载日志
logger.info("正在加载modeling_tools包")

# 当前目录路径
current_dir = os.path.dirname(os.path.abspath(__file__))

# 自动导入当前目录中的所有.py文件（除了__init__.py）
for file_path in Path(current_dir).glob("*.py"):
    filename = file_path.name
    if filename != "__init__.py" and filename.endswith(".py"):
        module_name = filename[:-3]  # 去掉.py后缀
        try:
            # 动态导入模块
            module = importlib.import_module(f"..modeling_tools.{module_name}", __package__)
            logger.info(f"已导入工具模块: {module_name}")
        except Exception as e:
            logger.error(f"导入工具模块 {module_name} 时出错: {e}")
            import traceback
            logger.error(traceback.format_exc())

# 导出工具映射，保持这个变量供其他模块导入
# 但工具现在直接通过各个工具类中的注册代码注册到注册表
tool_map = {}

logger.info("modeling_tools包加载完成")


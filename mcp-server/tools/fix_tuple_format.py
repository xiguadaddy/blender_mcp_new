#!/usr/bin/env python3
"""
MCP对象序列化修复工具

这个模块包含用于处理MCP对象序列化的函数，特别是解决CallToolResult对象
被错误序列化为元组格式的问题。

通过猴子补丁方法修改MCP库内部的序列化行为。
"""

import logging
import inspect
from typing import Any, Dict, List, Optional, Tuple, Union
import json

# 配置日志记录器
logger = logging.getLogger("BlenderMCP.FixTupleFormat")

# 尝试导入MCP类型
try:
    import mcp.types as mcp_types
    from mcp.types import CallToolResult, TextContent
    HAS_MCP = True
except ImportError:
    logger.warning("无法导入MCP类型，修复将不会生效")
    HAS_MCP = False

def install_patches():
    """
    安装所有必要的猴子补丁
    """
    if not HAS_MCP:
        return False
    
    logger.info("安装MCP对象序列化修复补丁...")
    
    # 备份原始方法
    original_model_dump = getattr(mcp_types.CallToolResult, "model_dump", None)
    
    if original_model_dump:
        logger.debug(f"找到原始model_dump方法: {original_model_dump}")
        
        # 定义替代方法
        def patched_model_dump(self, **kwargs):
            """
            修补的model_dump方法，确保返回字典而不是元组列表
            """
            # 调用原始方法
            result = original_model_dump(self, **kwargs)
            
            # 检查是否为元组列表格式
            if isinstance(result, list) and len(result) > 0 and isinstance(result[0], tuple):
                logger.debug("检测到元组列表格式，转换为字典")
                
                # 将元组列表转换为字典
                result_dict = {}
                for key, value in result:
                    result_dict[key] = value
                
                return result_dict
            
            return result
        
        # 应用补丁
        setattr(mcp_types.CallToolResult, "model_dump", patched_model_dump)
        logger.info("成功修补CallToolResult.model_dump方法")
    else:
        logger.warning("未找到CallToolResult.model_dump方法，无法应用补丁")
    
    # 修补__getstate__方法（如果存在）
    if hasattr(mcp_types.CallToolResult, "__getstate__"):
        original_getstate = mcp_types.CallToolResult.__getstate__
        
        def patched_getstate(self):
            """
            修补的__getstate__方法，确保返回字典而不是元组
            """
            state = original_getstate(self)
            
            # 检查是否为元组列表
            if isinstance(state, list) and len(state) > 0 and isinstance(state[0], tuple):
                logger.debug("在__getstate__中检测到元组列表，转换为字典")
                
                # 转换为字典
                state_dict = {}
                for key, value in state:
                    state_dict[key] = value
                
                return state_dict
            
            return state
        
        mcp_types.CallToolResult.__getstate__ = patched_getstate
        logger.info("成功修补CallToolResult.__getstate__方法")
    
    # 其他可能需要修补的方法...
    
    logger.info("所有补丁安装完成")
    return True

def create_standard_result(content_text: str, is_error: bool = False) -> Dict[str, Any]:
    """
    创建标准格式的结果对象
    
    Args:
        content_text: 要包含的文本内容
        is_error: 是否为错误结果
        
    Returns:
        Dict: 标准格式的结果字典
    """
    return {
        "content": [
            {
                "type": "text",
                "text": content_text
            }
        ],
        "isError": is_error
    }

def convert_to_standard_format(result: Any) -> Dict[str, Any]:
    """
    将各种格式的结果转换为标准格式
    
    Args:
        result: 任何格式的结果对象
        
    Returns:
        Dict: 标准格式的结果字典
    """
    # 如果已经是字典形式
    if isinstance(result, dict):
        if "content" in result:
            # 确保content是列表
            if not isinstance(result["content"], list):
                result["content"] = [result["content"]]
            
            # 确保每个内容项都有type和text
            for i, item in enumerate(result["content"]):
                if isinstance(item, str):
                    result["content"][i] = {"type": "text", "text": item}
                elif isinstance(item, dict) and "text" in item and "type" not in item:
                    item["type"] = "text"
            
            # 确保有isError字段
            if "isError" not in result:
                result["isError"] = False
            
            return result
        else:
            # 结果没有content字段，创建一个标准格式
            return create_standard_result(json.dumps(result, ensure_ascii=False))
    
    # 如果是元组列表格式
    elif isinstance(result, list) and len(result) > 0 and isinstance(result[0], tuple):
        # 将元组列表转换为字典
        result_dict = {}
        for key, value in result:
            result_dict[key] = value
        
        # 递归处理转换后的字典
        return convert_to_standard_format(result_dict)
    
    # 如果是CallToolResult对象
    elif HAS_MCP and isinstance(result, mcp_types.CallToolResult):
        # 尝试使用model_dump方法
        try:
            result_dict = result.model_dump()
            return convert_to_standard_format(result_dict)
        except Exception as e:
            logger.error(f"无法转换CallToolResult对象: {e}")
            # 从对象属性创建字典
            content_list = []
            for item in result.content:
                if hasattr(item, "text"):
                    content_list.append({
                        "type": getattr(item, "type", "text"),
                        "text": item.text
                    })
            
            return {
                "content": content_list,
                "isError": result.isError
            }
    
    # 其他情况，转为字符串
    return create_standard_result(str(result))

# 自动安装补丁
if HAS_MCP:
    install_patches() 
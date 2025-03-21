import json
import logging
from typing import Any, Dict, List, Optional, Union

# 尝试导入MCP类型
try:
    from mcp.types import (
        CallToolResult,
        TextContent,
        ImageContent,
        EmbeddedResource,
        ErrorData
    )
    # 标记已导入MCP原生类型
    HAS_MCP_TYPES = True
except ImportError:
    # 如果没有MCP库，使用本地类型定义
    from ...mcp_types import (
        CallToolResult,
        TextContent,
        ImageContent,
        ErrorData,
        create_text_content,
        create_image_content,
        create_error_data
    )
    HAS_MCP_TYPES = False

# 获取日志器
logger = logging.getLogger("BlenderMCP.Serializer")

class MCPSerializer:
    """
    MCP序列化工具类，用于处理MCP对象和Blender通信格式之间的转换
    """
    
    @staticmethod
    def create_text_content(text: str) -> Dict[str, Any]:
        """
        创建文本内容对象
        
        Args:
            text: 文本内容
            
        Returns:
            标准化的文本内容对象
        """
        return {
            "type": "text",
            "text": text
        }
            
    @staticmethod
    def create_image_content(data: str, mime_type: str) -> Dict[str, Any]:
        """
        创建图像内容对象
        
        Args:
            data: Base64编码的图像数据
            mime_type: 图像MIME类型
            
        Returns:
            标准化的图像内容对象
        """
        return {
            "type": "image",
            "image_data": data,
            "mime_type": mime_type
        }
            
    @staticmethod
    def create_error_data(code: int, message: str, data: Any = None) -> ErrorData:
        """
        创建错误数据对象
        
        Args:
            code: 错误代码
            message: 错误消息
            data: 额外错误数据
            
        Returns:
            错误数据对象
        """
        if HAS_MCP_TYPES:
            return ErrorData(code=code, message=message, data=data)
        else:
            return create_error_data(code, message, data)
            
    @staticmethod
    def create_tool_result(content: List[Dict[str, Any]], is_error: bool = False) -> Dict[str, Any]:
        """
        创建工具调用结果对象
        
        Args:
            content: 内容列表
            is_error: 是否为错误结果
            
        Returns:
            标准化的工具调用结果对象
        """
        return {
            "content": content,
            "isError": is_error
        }
            
    @staticmethod
    def standardize_result(result: Any) -> Dict[str, Any]:
        """
        将工具调用结果标准化为MCP格式
        
        Args:
            result: 工具调用结果，可以是任意类型
            
        Returns:
            标准化的工具调用结果
        """
        # 如果结果已经是标准格式，直接返回
        if isinstance(result, dict) and "content" in result and "isError" in result:
            return result
            
        # 创建空结果
        standardized_result = {
            "content": [],
            "isError": False
        }
        
        try:
            # 处理None结果
            if result is None:
                standardized_result["content"].append(
                    MCPSerializer.create_text_content("操作成功完成，但没有返回结果")
                )
                return standardized_result
                
            # 处理已经是字典的结果
            if isinstance(result, dict):
                # 检查是否为错误结果
                if "error" in result:
                    standardized_result["isError"] = True
                    standardized_result["content"].append(
                        MCPSerializer.create_text_content(str(result["error"]))
                    )
                    return standardized_result
                    
                # 检查是否已经是内容对象
                if "type" in result and result["type"] in ["text", "image"]:
                    standardized_result["content"].append(result)
                    return standardized_result
                    
                # 检查是否是正常的数据字典
                # 如果包含图像数据和MIME类型
                if "image_data" in result and "mime_type" in result:
                    standardized_result["content"].append(
                        MCPSerializer.create_image_content(
                            result["image_data"],
                            result["mime_type"]
                        )
                    )
                    return standardized_result
                    
                # 如果包含文本数据
                if "text" in result:
                    standardized_result["content"].append(
                        MCPSerializer.create_text_content(result["text"])
                    )
                    return standardized_result
                    
                # 一般字典，转为JSON文本
                standardized_result["content"].append(
                    MCPSerializer.create_text_content(json.dumps(result, ensure_ascii=False))
                )
                return standardized_result
                
            # 处理列表结果
            if isinstance(result, list):
                # 如果结果是内容对象列表
                if all(isinstance(item, dict) and "type" in item for item in result):
                    standardized_result["content"] = result
                    return standardized_result
                    
                # 处理一般列表，将每个项目转为字符串
                content_items = []
                for item in result:
                    if isinstance(item, dict):
                        # 字典项转为JSON
                        content_items.append(
                            MCPSerializer.create_text_content(json.dumps(item, ensure_ascii=False))
                        )
                    else:
                        # 其他项转为字符串
                        content_items.append(
                            MCPSerializer.create_text_content(str(item))
                        )
                
                # 如果只有一个项目，直接返回
                if len(content_items) == 1:
                    standardized_result["content"] = content_items
                    return standardized_result
                    
                # 如果有多个项目，合并为一个文本内容
                combined_text = "\n".join([
                    item["text"] for item in content_items
                    if isinstance(item, dict) and "text" in item
                ])
                standardized_result["content"].append(
                    MCPSerializer.create_text_content(combined_text)
                )
                return standardized_result
                
            # 处理字符串结果
            if isinstance(result, str):
                standardized_result["content"].append(
                    MCPSerializer.create_text_content(result)
                )
                return standardized_result
                
            # 处理其他类型结果
            standardized_result["content"].append(
                MCPSerializer.create_text_content(str(result))
            )
            return standardized_result
            
        except Exception as e:
            logger.error(f"标准化结果时出错: {str(e)}")
            # 返回错误结果
            return {
                "content": [
                    MCPSerializer.create_text_content(f"标准化结果时出错: {str(e)}")
                ],
                "isError": True
            }
            
    @staticmethod
    def fix_tuple_format(result: Any) -> Dict[str, Any]:
        """修复元组格式的结果，将其转换为标准字典
        
        Args:
            result: 可能是元组格式的结果
            
        Returns:
            标准化的工具调用结果
        """
        try:
            # 如果是元组格式
            if isinstance(result, list) and all(isinstance(item, tuple) for item in result):
                # 转换为字典
                result_dict = {}
                for key, value in result:
                    result_dict[key] = value
                
                # 标准化字典
                return MCPSerializer.standardize_result(result_dict)
            
            # 否则使用常规标准化处理
            return MCPSerializer.standardize_result(result)
        except Exception as e:
            logger.error(f"修复元组格式时出错: {str(e)}")
            # 返回错误结果
            return {
                "content": [
                    MCPSerializer.create_text_content(f"修复元组格式时出错: {str(e)}")
                ],
                "isError": True
            } 
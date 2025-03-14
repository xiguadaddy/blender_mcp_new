"""
响应工具模块 - 提供标准化的JSON-RPC 2.0响应格式和错误代码

这个模块实现了符合JSON-RPC 2.0规范的响应生成和错误处理功能，
确保所有API响应格式一致，便于客户端处理。
"""

import logging
logger = logging.getLogger("BlenderMCPServer")

# JSON-RPC 2.0标准错误代码
ERROR_CODES = {
    # 协议标准错误（-32768 到 -32000 是保留的）
    "PARSE_ERROR": -32700,          # 无效的JSON
    "INVALID_REQUEST": -32600,      # 请求对象无效
    "METHOD_NOT_FOUND": -32601,     # 方法不存在或不可用
    "INVALID_PARAMS": -32602,       # 无效的方法参数
    "INTERNAL_ERROR": -32603,       # 内部JSON-RPC错误
    
    # Blender MCP自定义错误代码（-32000 到 -32099）
    "OBJECT_NOT_FOUND": -32000,     # 找不到请求的对象
    "OPERATION_FAILED": -32001,     # 操作执行失败
    "INVALID_OBJECT_TYPE": -32002,  # 对象类型无效或不兼容
    "RENDER_ERROR": -32003,         # 渲染操作失败
    "TIMEOUT_ERROR": -32004,        # 操作超时
    "MATERIAL_ERROR": -32005,       # 材质操作失败
    "SCENE_ERROR": -32006,          # 场景操作失败
    "AUTHENTICATION_ERROR": -32007, # 身份验证失败
    "PERMISSION_ERROR": -32008,     # 权限不足
    "RESOURCE_LIMIT": -32009,       # 资源限制（内存、CPU等）
}

# 错误消息模板
ERROR_MESSAGES = {
    "PARSE_ERROR": "无效的JSON：无法解析请求",
    "INVALID_REQUEST": "无效的请求对象",
    "METHOD_NOT_FOUND": "找不到请求的方法",
    "INVALID_PARAMS": "无效的方法参数",
    "INTERNAL_ERROR": "内部服务器错误",
    "OBJECT_NOT_FOUND": "找不到指定的对象",
    "OPERATION_FAILED": "操作执行失败",
    "INVALID_OBJECT_TYPE": "对象类型无效或不兼容",
    "RENDER_ERROR": "渲染操作失败",
    "TIMEOUT_ERROR": "操作超时",
    "MATERIAL_ERROR": "材质操作失败",
    "SCENE_ERROR": "场景操作失败",
    "AUTHENTICATION_ERROR": "身份验证失败",
    "PERMISSION_ERROR": "权限不足",
    "RESOURCE_LIMIT": "达到资源限制",
}

def create_success_response(result, request_id=None):
    """
    创建成功响应
    
    参数:
        result: 操作结果数据
        request_id: 请求ID，用于匹配请求和响应
        
    返回:
        符合JSON-RPC 2.0规范的成功响应字典
    """
    response = {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result
    }
    return response

def create_error_response(error_type, message=None, data=None, request_id=None):
    """
    创建错误响应
    
    参数:
        error_type: 错误类型，从ERROR_CODES中选择
        message: 自定义错误消息，如不提供则使用默认消息
        data: 附加错误数据（可选）
        request_id: 请求ID，用于匹配请求和响应
        
    返回:
        符合JSON-RPC 2.0规范的错误响应字典
    """
    if error_type not in ERROR_CODES:
        logger.warning(f"未定义的错误类型: {error_type}，使用INTERNAL_ERROR代替")
        error_type = "INTERNAL_ERROR"
        
    error_code = ERROR_CODES[error_type]
    error_message = message if message else ERROR_MESSAGES.get(error_type, "未知错误")
    
    response = {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": error_code,
            "message": error_message
        }
    }
    
    # 如果提供了附加数据，则添加到错误对象中
    if data:
        response["error"]["data"] = data
        
    return response

def convert_legacy_response(legacy_response, request_id=None):
    """
    将旧格式响应转换为JSON-RPC 2.0格式
    
    参数:
        legacy_response: 旧格式响应（通常包含status字段）
        request_id: 请求ID
        
    返回:
        符合JSON-RPC 2.0规范的响应字典
    """
    # 检查是否是旧格式的错误响应
    if legacy_response.get("status") == "error":
        return create_error_response(
            "OPERATION_FAILED", 
            message=legacy_response.get("message", "操作失败"),
            data=legacy_response.get("data"),
            request_id=request_id
        )
    
    # 处理旧格式的成功响应
    result = legacy_response.get("result", {})
    
    # 如果没有result字段但有其他数据，则将整个响应作为结果
    if "result" not in legacy_response and "status" in legacy_response:
        # 移除status字段，只保留实际数据
        legacy_copy = legacy_response.copy()
        if "status" in legacy_copy:
            del legacy_copy["status"]
        if "message" in legacy_copy and not legacy_copy:  # 如果只剩message字段
            result = {"message": legacy_copy.get("message")}
        else:
            result = legacy_copy
            
    return create_success_response(result, request_id) 
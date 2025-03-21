"""
Model Context Protocol (MCP) 类型定义

这个模块提供了MCP核心类型的Python实现，不依赖外部库（如Pydantic）。
这些类型与MCP规范兼容，但被简化以适用于Blender插件环境。
"""

from typing import List, Dict, Any, Optional, Union, Literal
import json
import base64
import uuid

# MCP协议版本
LATEST_PROTOCOL_VERSION = "2025-03-21"

# 基本类型
Role = Literal["user", "assistant"]
RequestId = Union[str, int]

# ===============================
# 基础类
# ===============================

class BaseModel:
    """所有MCP类型的基类"""
    
    def to_dict(self) -> Dict[str, Any]:
        """将对象转换为字典"""
        result = {}
        for key, value in self.__dict__.items():
            # 跳过私有属性和None值
            if key.startswith('_') or value is None:
                continue
                
            # 递归处理嵌套对象
            if isinstance(value, BaseModel):
                result[key] = value.to_dict()
            elif isinstance(value, list):
                result[key] = [item.to_dict() if isinstance(item, BaseModel) else item for item in value]
            else:
                result[key] = value
                
        return result
        
    def to_json(self) -> str:
        """将对象转换为JSON字符串"""
        return json.dumps(self.to_dict())
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """从字典创建对象"""
        instance = cls()
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        return instance

class RequestParams(BaseModel):
    """请求参数基类"""
    
    def __init__(self):
        self.meta = None  # 元数据，可选
    
class NotificationParams(BaseModel):
    """通知参数基类"""
    
    def __init__(self):
        self.meta = None  # 元数据，可选

class Request(BaseModel):
    """请求基类"""
    
    def __init__(self):
        self.method = ""  # 请求方法
        self.params = None  # 请求参数
        self.jsonrpc = "2.0"  # JSON-RPC版本
        self.id = str(uuid.uuid4())  # 请求ID

class PaginatedRequest(Request):
    """分页请求基类"""
    
    def __init__(self):
        super().__init__()
        self.cursor = None  # 分页游标

class Notification(BaseModel):
    """通知基类"""
    
    def __init__(self):
        self.method = ""  # 通知方法
        self.params = None  # 通知参数
        self.jsonrpc = "2.0"  # JSON-RPC版本

class Result(BaseModel):
    """结果基类"""
    
    def __init__(self):
        self.meta = None  # 元数据，可选

class PaginatedResult(Result):
    """分页结果基类"""
    
    def __init__(self):
        super().__init__()
        self.nextCursor = None  # 下一页游标

class ErrorData(BaseModel):
    """错误数据"""
    
    def __init__(self):
        self.code = 0  # 错误代码
        self.message = ""  # 错误消息
        self.data = None  # 附加错误数据，可选

# ===============================
# 资源相关类型
# ===============================

class ResourceContents(BaseModel):
    """资源内容基类"""
    
    def __init__(self):
        self.uri = ""  # 资源URI
        self.mimeType = None  # MIME类型，可选

class TextResourceContents(ResourceContents):
    """文本资源内容"""
    
    def __init__(self):
        super().__init__()
        self.text = ""  # 文本内容

class BlobResourceContents(ResourceContents):
    """二进制资源内容"""
    
    def __init__(self):
        super().__init__()
        self.blob = ""  # Base64编码的二进制数据

class ReadResourceRequestParams(RequestParams):
    """读取资源请求参数"""
    
    def __init__(self):
        super().__init__()
        self.uri = ""  # 资源URI

class ReadResourceRequest(Request):
    """读取资源请求"""
    
    def __init__(self):
        super().__init__()
        self.method = "resources/read"
        self.params = ReadResourceRequestParams()

class ReadResourceResult(Result):
    """读取资源结果"""
    
    def __init__(self):
        super().__init__()
        self.contents = []  # 资源内容列表

class Resource(BaseModel):
    """资源定义"""
    
    def __init__(self):
        self.uri = ""  # 资源URI
        self.name = ""  # 资源名称
        self.description = None  # 资源描述，可选
        self.mimeType = None  # MIME类型，可选
        self.size = None  # 资源大小，可选
        self.annotations = None  # 资源注释，可选

class ListResourcesResult(PaginatedResult):
    """列出资源结果"""
    
    def __init__(self):
        super().__init__()
        self.resources = []  # 资源列表

# ===============================
# 工具相关类型
# ===============================

class TextContent(BaseModel):
    """文本内容"""
    
    def __init__(self):
        self.type = "text"  # 内容类型
        self.text = ""  # 文本内容
        self.annotations = None  # 注释，可选

class ImageContent(BaseModel):
    """图像内容"""
    
    def __init__(self):
        self.type = "image"  # 内容类型
        self.data = ""  # Base64编码的图像数据
        self.mimeType = ""  # MIME类型
        self.annotations = None  # 注释，可选

class EmbeddedResource(BaseModel):
    """嵌入式资源"""
    
    def __init__(self):
        self.type = "resource"  # 内容类型
        self.resource = None  # 资源内容
        self.annotations = None  # 注释，可选

class Tool(BaseModel):
    """工具定义"""
    
    def __init__(self):
        self.name = ""  # 工具名称
        self.description = None  # 工具描述，可选
        self.inputSchema = {}  # 输入参数结构

class ListToolsResult(PaginatedResult):
    """列出工具结果"""
    
    def __init__(self):
        super().__init__()
        self.tools = []  # 工具列表

class CallToolRequestParams(RequestParams):
    """调用工具请求参数"""
    
    def __init__(self):
        super().__init__()
        self.name = ""  # 工具名称
        self.arguments = None  # 工具参数，可选

class CallToolRequest(Request):
    """调用工具请求"""
    
    def __init__(self):
        super().__init__()
        self.method = "tools/call"
        self.params = CallToolRequestParams()

class CallToolResult(Result):
    """调用工具结果"""
    
    def __init__(self):
        super().__init__()
        self.content = []  # 内容列表
        self.isError = False  # 是否为错误

# ===============================
# 提示相关类型
# ===============================

class PromptMessage(BaseModel):
    """提示消息"""
    
    def __init__(self):
        self.role = ""  # 角色
        self.content = None  # 内容

class GetPromptRequestParams(RequestParams):
    """获取提示请求参数"""
    
    def __init__(self):
        super().__init__()
        self.name = ""  # 提示名称
        self.arguments = None  # 模板参数，可选

class GetPromptRequest(Request):
    """获取提示请求"""
    
    def __init__(self):
        super().__init__()
        self.method = "prompts/get"
        self.params = GetPromptRequestParams()

class GetPromptResult(Result):
    """获取提示结果"""
    
    def __init__(self):
        super().__init__()
        self.description = None  # 提示描述，可选
        self.messages = []  # 提示消息列表

# ===============================
# 辅助函数
# ===============================

def create_text_content(text: str) -> TextContent:
    """创建文本内容对象"""
    content = TextContent()
    content.text = text
    return content

def create_image_content(image_data: bytes, mime_type: str) -> ImageContent:
    """创建图像内容对象"""
    content = ImageContent()
    content.data = base64.b64encode(image_data).decode('utf-8')
    content.mimeType = mime_type
    return content

def create_text_resource_contents(uri: str, text: str, mime_type: Optional[str] = None) -> TextResourceContents:
    """创建文本资源内容对象"""
    contents = TextResourceContents()
    contents.uri = uri
    contents.text = text
    contents.mimeType = mime_type
    return contents

def create_blob_resource_contents(uri: str, blob_data: bytes, mime_type: Optional[str] = None) -> BlobResourceContents:
    """创建二进制资源内容对象"""
    contents = BlobResourceContents()
    contents.uri = uri
    contents.blob = base64.b64encode(blob_data).decode('utf-8')
    contents.mimeType = mime_type
    return contents

def create_error_data(code: int, message: str, data: Any = None) -> ErrorData:
    """创建错误数据对象"""
    error = ErrorData()
    error.code = code
    error.message = message
    error.data = data
    return error 
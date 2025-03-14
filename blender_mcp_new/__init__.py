"""
BlenderMCP - 通过网络API控制Blender的工具包

包含两个主要模块:
- client: 不依赖bpy的客户端模块，可在任何Python环境中运行
- server: 依赖bpy的服务器模块，必须在Blender内部运行

版本: 0.2.0
"""

__version__ = "0.2.0"

# 默认导入客户端，因为它可以在任何环境中使用
from .client import BlenderMCPClient

__all__ = ['BlenderMCPClient']

# 服务器模块必须显式导入，只能在Blender环境中使用 
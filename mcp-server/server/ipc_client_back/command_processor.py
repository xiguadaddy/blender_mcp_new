"""
MCP 命令处理器

提供处理 MCP 协议命令的高级接口。
"""

import logging
import json
import base64
from typing import Dict, Any, List, Optional, Callable

from .client import BlenderMCPClient

logger = logging.getLogger("BlenderMCPCommands")

class MCPCommandProcessor:
    """MCP 协议命令处理器"""
    
    def __init__(self, client: BlenderMCPClient):
        """
        初始化命令处理器
        
        Args:
            client: Blender MCP 客户端实例
        """
        self.client = client
        
    def create_object(self, object_type: str, location: Optional[List[float]] = None, 
                     name: Optional[str] = None, size: Optional[float] = None) -> Dict[str, Any]:
        """
        创建 3D 对象
        
        Args:
            object_type: 对象类型 (cube, sphere, plane 等)
            location: 对象位置坐标 [x, y, z]
            name: 对象名称
            size: 对象大小
            
        Returns:
            创建结果
        """
        arguments = {"object_type": object_type}
        
        if location:
            arguments["location"] = location
        if name:
            arguments["name"] = name
        if size is not None:
            arguments["size"] = size
            
        return self.client.call_tool("create_object", arguments)
        
    def set_material(self, object_name: str, color: Optional[List[float]] = None,
                    metallic: Optional[float] = None, roughness: Optional[float] = None) -> Dict[str, Any]:
        """
        设置对象材质
        
        Args:
            object_name: 目标对象名称
            color: RGBA 颜色值 [r, g, b, a]
            metallic: 金属度 (0-1)
            roughness: 粗糙度 (0-1)
            
        Returns:
            操作结果
        """
        arguments = {"object_name": object_name}
        
        if color:
            arguments["color"] = color
        if metallic is not None:
            arguments["metallic"] = metallic
        if roughness is not None:
            arguments["roughness"] = roughness
            
        return self.client.call_tool("set_material", arguments)
        
    def add_light(self, light_type: str, location: Optional[List[float]] = None,
                 color: Optional[List[float]] = None, energy: Optional[float] = None) -> Dict[str, Any]:
        """
        添加灯光
        
        Args:
            light_type: 灯光类型 (POINT, SUN, SPOT, AREA)
            location: 灯光位置 [x, y, z]
            color: RGB 颜色值 [r, g, b]
            energy: 灯光强度
            
        Returns:
            操作结果
        """
        arguments = {"light_type": light_type}
        
        if location:
            arguments["location"] = location
        if color:
            arguments["color"] = color
        if energy is not None:
            arguments["energy"] = energy
            
        return self.client.call_tool("add_light", arguments)
        
    def execute_python(self, code: str) -> Dict[str, Any]:
        """
        执行 Python 代码
        
        Args:
            code: 要执行的 Python 代码
            
        Returns:
            执行结果
        """
        return self.client.call_tool("execute_python", {"code": code})
        
    def get_scene_data(self) -> Dict[str, Any]:
        """
        获取当前场景数据
        
        Returns:
            场景数据
        """
        # 读取场景资源
        return self.client.read_resource("blender://scene/current")
        
    def get_object_data(self, object_name: str) -> Dict[str, Any]:
        """
        获取对象数据
        
        Args:
            object_name: 对象名称
            
        Returns:
            对象数据
        """
        # 首先确定对象类型
        scene_data = self.get_scene_data()
        if "error" in scene_data:
            return scene_data
            
        # 在场景对象中查找
        objects = scene_data.get("contents", [{}])[0].get("text", "{}")
        objects_data = json.loads(objects)
        
        # 根据对象名称查找对象类型
        object_type = None
        for obj_type in ["mesh", "light", "camera"]:
            if object_name in objects_data.get(f"{obj_type}s", []):
                object_type = obj_type
                break
                
        if not object_type:
            return {"error": f"找不到对象: {object_name}"}
            
        # 读取对象资源
        return self.client.read_resource(f"blender://{object_type}/{object_name}")
        
    def render_scene(self, resolution: Optional[List[int]] = None, 
                    samples: Optional[int] = None) -> Dict[str, Any]:
        """
        渲染当前场景
        
        Args:
            resolution: 分辨率 [宽, 高]
            samples: 采样数量
            
        Returns:
            渲染结果
        """
        arguments = {}
        
        if resolution:
            arguments["resolution"] = resolution
        if samples is not None:
            arguments["samples"] = samples
            
        return self.client.call_tool("render_scene", arguments)

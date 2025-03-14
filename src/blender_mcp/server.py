# blender_mcp_server.py
from mcp.server.fastmcp import FastMCP, Context, Image
import socket
import json
import asyncio
import logging
from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, List
import bpy
import threading
import time
import traceback
import math
import random

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BlenderMCPServer")

@dataclass
class BlenderConnection:
    host: str
    port: int
    sock: socket.socket = None  # Changed from 'socket' to 'sock' to avoid naming conflict
    
    def connect(self) -> bool:
        """Connect to the Blender addon socket server"""
        if self.sock:
            return True
            
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            logger.info(f"Connected to Blender at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Blender: {str(e)}")
            self.sock = None
            return False
    
    def disconnect(self):
        """Disconnect from the Blender addon"""
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                logger.error(f"Error disconnecting from Blender: {str(e)}")
            finally:
                self.sock = None

    def receive_full_response(self, sock, buffer_size=8192):
        """Receive the complete response, potentially in multiple chunks"""
        chunks = []
        # Use a consistent timeout value that matches the addon's timeout
        sock.settimeout(15.0)  # Match the addon's timeout
        
        try:
            while True:
                try:
                    chunk = sock.recv(buffer_size)
                    if not chunk:
                        # If we get an empty chunk, the connection might be closed
                        if not chunks:  # If we haven't received anything yet, this is an error
                            raise Exception("Connection closed before receiving any data")
                        break
                    
                    chunks.append(chunk)
                    
                    # Check if we've received a complete JSON object
                    try:
                        data = b''.join(chunks)
                        json.loads(data.decode('utf-8'))
                        # If we get here, it parsed successfully
                        logger.info(f"Received complete response ({len(data)} bytes)")
                        return data
                    except json.JSONDecodeError:
                        # Incomplete JSON, continue receiving
                        continue
                except socket.timeout:
                    # If we hit a timeout during receiving, break the loop and try to use what we have
                    logger.warning("Socket timeout during chunked receive")
                    break
                except (ConnectionError, BrokenPipeError, ConnectionResetError) as e:
                    logger.error(f"Socket connection error during receive: {str(e)}")
                    raise  # Re-raise to be handled by the caller
        except socket.timeout:
            logger.warning("Socket timeout during chunked receive")
        except Exception as e:
            logger.error(f"Error during receive: {str(e)}")
            raise
            
        # If we get here, we either timed out or broke out of the loop
        # Try to use what we have
        if chunks:
            data = b''.join(chunks)
            logger.info(f"Returning data after receive completion ({len(data)} bytes)")
            try:
                # Try to parse what we have
                json.loads(data.decode('utf-8'))
                return data
            except json.JSONDecodeError:
                # If we can't parse it, it's incomplete
                raise Exception("Incomplete JSON response received")
        else:
            raise Exception("No data received")

    def send_command(self, command_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a command to Blender and return the response"""
        if not self.sock and not self.connect():
            raise ConnectionError("Not connected to Blender")
        
        command = {
            "type": command_type,
            "params": params or {}
        }
        
        try:
            # Log the command being sent
            logger.info(f"Sending command: {command_type} with params: {params}")
            
            # Send the command
            self.sock.sendall(json.dumps(command).encode('utf-8'))
            logger.info(f"Command sent, waiting for response...")
            
            # Set a timeout for receiving - use the same timeout as in receive_full_response
            self.sock.settimeout(15.0)  # Match the addon's timeout
            
            # Receive the response using the improved receive_full_response method
            response_data = self.receive_full_response(self.sock)
            logger.info(f"Received {len(response_data)} bytes of data")
            
            response = json.loads(response_data.decode('utf-8'))
            logger.info(f"Response parsed, status: {response.get('status', 'unknown')}")
            
            if response.get("status") == "error":
                logger.error(f"Blender error: {response.get('message')}")
                raise Exception(response.get("message", "Unknown error from Blender"))
            
            return response.get("result", {})
        except socket.timeout:
            logger.error("Socket timeout while waiting for response from Blender")
            # Don't try to reconnect here - let the get_blender_connection handle reconnection
            # Just invalidate the current socket so it will be recreated next time
            self.sock = None
            raise Exception("Timeout waiting for Blender response - try simplifying your request")
        except (ConnectionError, BrokenPipeError, ConnectionResetError) as e:
            logger.error(f"Socket connection error: {str(e)}")
            self.sock = None
            raise Exception(f"Connection to Blender lost: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Blender: {str(e)}")
            # Try to log what was received
            if 'response_data' in locals() and response_data:
                logger.error(f"Raw response (first 200 bytes): {response_data[:200]}")
            raise Exception(f"Invalid response from Blender: {str(e)}")
        except Exception as e:
            logger.error(f"Error communicating with Blender: {str(e)}")
            # Don't try to reconnect here - let the get_blender_connection handle reconnection
            self.sock = None
            raise Exception(f"Communication error with Blender: {str(e)}")

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle"""
    # We don't need to create a connection here since we're using the global connection
    # for resources and tools
    
    try:
        # Just log that we're starting up
        logger.info("BlenderMCP server starting up")
        
        # Try to connect to Blender on startup to verify it's available
        try:
            # This will initialize the global connection if needed
            blender = get_blender_connection()
            logger.info("Successfully connected to Blender on startup")
        except Exception as e:
            logger.warning(f"Could not connect to Blender on startup: {str(e)}")
            logger.warning("Make sure the Blender addon is running before using Blender resources or tools")
        
        # Return an empty context - we're using the global connection
        yield {}
    finally:
        # Clean up the global connection on shutdown
        global _blender_connection
        if _blender_connection:
            logger.info("Disconnecting from Blender on shutdown")
            _blender_connection.disconnect()
            _blender_connection = None
        logger.info("BlenderMCP server shut down")

# Create the MCP server with lifespan support
mcp = FastMCP(
    "BlenderMCP",
    description="Blender integration through the Model Context Protocol",
    lifespan=server_lifespan
)

# Resource endpoints

# Global connection for resources (since resources can't access context)
_blender_connection = None

def get_blender_connection():
    """Get or create a persistent Blender connection"""
    global _blender_connection
    
    # If we have an existing connection, check if it's still valid
    if _blender_connection is not None:
        # Test if the connection is still alive with a simple ping
        try:
            # Just try to send a small message to check if the socket is still connected
            _blender_connection.sock.sendall(b'')
            return _blender_connection
        except Exception as e:
            # Connection is dead, close it and create a new one
            logger.warning(f"Existing connection is no longer valid: {str(e)}")
            try:
                _blender_connection.disconnect()
            except:
                pass
            _blender_connection = None
    
    # Create a new connection if needed
    if _blender_connection is None:
        _blender_connection = BlenderConnection(host="localhost", port=9876)
        if not _blender_connection.connect():
            logger.error("Failed to connect to Blender")
            _blender_connection = None
            raise Exception("Could not connect to Blender. Make sure the Blender addon is running.")
        logger.info("Created new persistent connection to Blender")
    
    return _blender_connection


@mcp.tool()
def get_scene_info(ctx: Context) -> str:
    """Get detailed information about the current Blender scene"""
    try:
        blender = get_blender_connection()
        result = blender.send_command("get_scene_info")
        
        # Just return the JSON representation of what Blender sent us
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting scene info from Blender: {str(e)}")
        return f"Error getting scene info: {str(e)}"

@mcp.tool()
def get_object_info(ctx: Context, object_name: str) -> str:
    """
    Get detailed information about a specific object in the Blender scene.
    
    Parameters:
    - object_name: The name of the object to get information about
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("get_object_info", {"name": object_name})
        
        # Just return the JSON representation of what Blender sent us
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting object info from Blender: {str(e)}")
        return f"Error getting object info: {str(e)}"

# Tool endpoints

@mcp.tool()
def create_primitive(
    ctx: Context,
    type: str = "CUBE",
    location: List[float] = None,
    color: List[float] = None
) -> str:
    """
    Create a basic primitive object in Blender.
    
    Parameters:
    - type: Object type (CUBE, SPHERE, CYLINDER, PLANE)
    - location: Optional [x, y, z] location coordinates
    - color: Optional [R, G, B] color values (0.0-1.0)
    """
    try:
        blender = get_blender_connection()
        loc = location or [0, 0, 0]
        
        # First create the object
        params = {
            "type": type,
            "location": loc
        }
        result = blender.send_command("create_object", params)
        
        # If color specified, set the material
        if color:
            blender.send_command("set_material", {
                "object_name": result["name"],
                "color": color
            })
            
        return f"Created {type} at location {loc}"
    except Exception as e:
        return f"Error creating primitive: {str(e)}"

@mcp.tool()
def set_object_property(
    ctx: Context,
    name: str,
    property: str,
    value: Any
) -> str:
    """
    Set a single property of an object.
    
    Parameters:
    - name: Name of the object
    - property: Property to set (location, rotation, scale, color, visible)
    - value: New value for the property
    """
    try:
        blender = get_blender_connection()
        params = {"name": name, property: value}
        result = blender.send_command("modify_object", params)
        return f"Set {property} of {name} to {value}"
    except Exception as e:
        return f"Error setting property: {str(e)}"

@mcp.tool()
def create_object(
    ctx: Context,
    type: str = "CUBE",
    name: str = None,
    location: List[float] = None,
    rotation: List[float] = None,
    scale: List[float] = None
) -> str:
    """
    Create a new object in the Blender scene.
    
    Parameters:
    - type: Object type (CUBE, SPHERE, CYLINDER, PLANE, CONE, TORUS, EMPTY, CAMERA, LIGHT)
    - name: Optional name for the object
    - location: Optional [x, y, z] location coordinates
    - rotation: Optional [x, y, z] rotation in radians
    - scale: Optional [x, y, z] scale factors
    """
    try:
        # Get the global connection
        blender = get_blender_connection()
        
        # Set default values for missing parameters
        loc = location or [0, 0, 0]
        rot = rotation or [0, 0, 0]
        sc = scale or [1, 1, 1]
        
        params = {
            "type": type,
            "location": loc,
            "rotation": rot,
            "scale": sc
        }
        
        if name:
            params["name"] = name
            
        result = blender.send_command("create_object", params)
        return f"Created {type} object: {result['name']}"
    except Exception as e:
        logger.error(f"Error creating object: {str(e)}")
        return f"Error creating object: {str(e)}"

@mcp.tool()
def modify_object(
    ctx: Context,
    name: str,
    location: List[float] = None,
    rotation: List[float] = None,
    scale: List[float] = None,
    visible: bool = None
) -> str:
    """
    Modify an existing object in the Blender scene.
    
    Parameters:
    - name: Name of the object to modify
    - location: Optional [x, y, z] location coordinates
    - rotation: Optional [x, y, z] rotation in radians
    - scale: Optional [x, y, z] scale factors
    - visible: Optional boolean to set visibility
    """
    try:
        # Get the global connection
        blender = get_blender_connection()
        
        params = {"name": name}
        
        if location is not None:
            params["location"] = location
        if rotation is not None:
            params["rotation"] = rotation
        if scale is not None:
            params["scale"] = scale
        if visible is not None:
            params["visible"] = visible
            
        result = blender.send_command("modify_object", params)
        return f"Modified object: {result['name']}"
    except Exception as e:
        logger.error(f"Error modifying object: {str(e)}")
        return f"Error modifying object: {str(e)}"

@mcp.tool()
def delete_object(ctx: Context, name: str) -> str:
    """
    Delete an object from the Blender scene.
    
    Parameters:
    - name: Name of the object to delete
    """
    try:
        # Get the global connection
        blender = get_blender_connection()
        
        result = blender.send_command("delete_object", {"name": name})
        return f"Deleted object: {name}"
    except Exception as e:
        logger.error(f"Error deleting object: {str(e)}")
        return f"Error deleting object: {str(e)}"

@mcp.tool()
def set_material(
    ctx: Context,
    object_name: str,
    material_name: str = None,
    color: List[float] = None
) -> str:
    """
    Set or create a material for an object.
    
    Parameters:
    - object_name: Name of the object to apply the material to
    - material_name: Optional name of the material to use or create
    - color: Optional [R, G, B] color values (0.0-1.0)
    """
    try:
        # Get the global connection
        blender = get_blender_connection()
        
        params = {"object_name": object_name}
        
        if material_name:
            params["material_name"] = material_name
        if color:
            params["color"] = color
            
        result = blender.send_command("set_material", params)
        return f"Applied material to {object_name}: {result.get('material_name', 'unknown')}"
    except Exception as e:
        logger.error(f"Error setting material: {str(e)}")
        return f"Error setting material: {str(e)}"

@mcp.tool()
def execute_blender_code(ctx: Context, code: str) -> str:
    """
    Execute arbitrary Python code in Blender.
    
    Parameters:
    - code: The Python code to execute
    """
    try:
        # Get the global connection
        blender = get_blender_connection()
        
        result = blender.send_command("execute_code", {"code": code})
        return f"Code executed successfully: {result.get('result', '')}"
    except Exception as e:
        logger.error(f"Error executing code: {str(e)}")
        return f"Error executing code: {str(e)}"

@mcp.prompt()
def create_basic_object() -> str:
    """Create a single object with basic properties"""
    return """Create a blue cube at position [0, 1, 0]"""

@mcp.prompt()
def modify_basic_object() -> str:
    """Modify a single property of an object"""
    return """Make the cube red"""

# Main execution

def main():
    """Run the MCP server"""
    mcp.run()

class BlenderMCPServer:
    """
    Blender MCP服务器
    提供TCP接口让外部应用程序控制Blender
    """
    
    def __init__(self, host='localhost', port=9876, buffer_size=40960):
        """初始化服务器"""
        self.host = host
        self.port = port
        self.buffer_size = buffer_size
        self.server_socket = None
        self.running = False
        self.thread = None
        self.clients = []
        self.command_handlers = self._register_command_handlers()
        self.last_error = None
        # 防止重复创建标识
        self.last_created_objects = {}
        # 每10秒自动清理一次
        self.last_cleanup_time = time.time()
        
    def _register_command_handlers(self):
        """注册所有可用的命令处理器"""
        return {
            "ping": self._handle_ping,
            "get_scene_info": self._handle_get_scene_info,
            "get_object_info": self._handle_get_object_info,
            "create_object": self._handle_create_object,
            "modify_object": self._handle_modify_object,
            "delete_object": self._handle_delete_object,
            "join_objects": self._handle_join_objects,
            "set_material": self._handle_set_material,
            "set_light_type": self._handle_set_light_type,
            "set_light_energy": self._handle_set_light_energy,
            "set_active_camera": self._handle_set_active_camera,
            "render_scene": self._handle_render_scene,
            "advanced_lighting": self._handle_advanced_lighting,
            "execute_code": self._handle_execute_code,
            "verify_object_exists": self._handle_verify_object_exists,
            "safe_join_objects": self._handle_safe_join_objects,
        }
    
    def start(self):
        """启动服务器"""
        if self.running:
            return {"status": "error", "message": "服务器已经在运行"}
        
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            self.thread = threading.Thread(target=self._accept_connections)
            self.thread.daemon = True
            self.thread.start()
            return {"status": "success", "message": f"服务器运行在 {self.host}:{self.port}"}
        except Exception as e:
            self.last_error = str(e)
            return {"status": "error", "message": f"启动服务器失败: {str(e)}"}
    
    def stop(self):
        """停止服务器"""
        if not self.running:
            return {"status": "error", "message": "服务器未运行"}
        
        try:
            self.running = False
            if self.server_socket:
                self.server_socket.close()
            
            for client in self.clients:
                try:
                    client.close()
                except:
                    pass
            
            self.clients = []
            return {"status": "success", "message": "服务器已停止"}
        except Exception as e:
            self.last_error = str(e)
            return {"status": "error", "message": f"停止服务器失败: {str(e)}"}
    
    def _accept_connections(self):
        """接受新连接的线程函数"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                self.clients.append(client_socket)
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()
            except Exception as e:
                if self.running:  # 只有在服务器应该运行时才报错
                    self.last_error = str(e)
                    print(f"接受连接时出错: {str(e)}")
                time.sleep(0.1)  # 避免CPU占用过高
    
    def _handle_client(self, client_socket, address):
        """处理单个客户端连接"""
        print(f"新客户端连接: {address}")
        while self.running:
            try:
                data = client_socket.recv(self.buffer_size)
                if not data:
                    break
                
                try:
                    message = json.loads(data.decode('utf-8'))
                    response = self._process_command(message)
                except json.JSONDecodeError:
                    response = {"status": "error", "message": "无效的JSON格式"}
                except Exception as e:
                    response = {"status": "error", "message": f"处理命令时出错: {str(e)}"}
                    traceback.print_exc()
                
                client_socket.sendall(json.dumps(response).encode('utf-8'))
                
                # 自动清理过期的对象引用
                current_time = time.time()
                if current_time - self.last_cleanup_time > 10:
                    self._cleanup_stale_objects()
                    self.last_cleanup_time = current_time
                
            except ConnectionError:
                break
            except Exception as e:
                self.last_error = str(e)
                print(f"处理客户端时出错: {str(e)}")
                traceback.print_exc()
                break
        
        try:
            client_socket.close()
        except:
            pass
        
        if client_socket in self.clients:
            self.clients.remove(client_socket)
        print(f"客户端断开连接: {address}")
    
    def _cleanup_stale_objects(self):
        """清理不再存在的对象引用"""
        to_remove = []
        for obj_id, obj_name in self.last_created_objects.items():
            if obj_name not in bpy.data.objects:
                to_remove.append(obj_id)
        
        for obj_id in to_remove:
            del self.last_created_objects[obj_id]
        
    def _process_command(self, message):
        """处理从客户端接收的命令"""
        if not isinstance(message, dict):
            return {"status": "error", "message": "命令必须是一个字典"}
        
        command = message.get("command")
        params = message.get("params", {})
        
        if not command:
            return {"status": "error", "message": "缺少命令名称"}
        
        handler = self.command_handlers.get(command)
        if not handler:
            return {"status": "error", "message": f"未知命令: {command}"}
        
        try:
            return handler(params)
        except Exception as e:
            self.last_error = str(e)
            traceback.print_exc()
            return {"status": "error", "message": f"执行命令 '{command}' 失败: {str(e)}"}
    
    def _handle_ping(self, params):
        """处理ping命令，用于检查服务器是否在线"""
        return {"status": "success", "result": "pong"}
    
    def _handle_get_scene_info(self, params):
        """返回当前场景的信息"""
        try:
            objects = []
            for obj in bpy.data.objects:
                obj_info = {
                    "name": obj.name,
                    "type": obj.type,
                    "location": [obj.location.x, obj.location.y, obj.location.z]
                }
                objects.append(obj_info)
            
            scene_info = {
                "name": bpy.context.scene.name,
                "objects": objects
            }
            return {"status": "success", "result": scene_info}
        except Exception as e:
            return {"status": "error", "message": f"获取场景信息失败: {str(e)}"}
    
    def _handle_get_object_info(self, params):
        """返回特定对象的信息"""
        object_name = params.get("object_name") or params.get("name")
        if not object_name:
            return {"status": "error", "message": "缺少对象名称参数"}
        
        try:
            if object_name not in bpy.data.objects:
                return {"status": "error", "message": f"对象 '{object_name}' 不存在"}
            
            obj = bpy.data.objects[object_name]
            obj_info = {
                "name": obj.name,
                "type": obj.type,
                "location": [obj.location.x, obj.location.y, obj.location.z]
            }
            
            if obj.type == 'MESH':
                obj_info["vertices"] = len(obj.data.vertices)
                obj_info["polygons"] = len(obj.data.polygons)
            elif obj.type == 'LIGHT':
                obj_info["light_type"] = obj.data.type
                obj_info["energy"] = obj.data.energy
                obj_info["color"] = [obj.data.color[0], obj.data.color[1], obj.data.color[2]]
            
            return {"status": "success", "result": obj_info}
        except Exception as e:
            return {"status": "error", "message": f"获取对象信息失败: {str(e)}"}
    
    def _handle_create_object(self, params):
        """创建一个新对象"""
        obj_type = params.get("type")
        name = params.get("name")
        location = params.get("location", [0, 0, 0])
        rotation = params.get("rotation", [0, 0, 0])
        scale = params.get("scale", [1, 1, 1])
        
        if not obj_type:
            return {"status": "error", "message": "缺少对象类型参数"}
        
        # 确保在主线程中执行Blender操作
        def create_object_in_blender():
            try:
                # 生成唯一名称如果未提供
                if not name:
                    base_name = obj_type.capitalize()
                    count = 1
                    while f"{base_name}{count}" in bpy.data.objects:
                        count += 1
                    object_name = f"{base_name}{count}"
                else:
                    # 如果名称已存在，附加数字
                    if name in bpy.data.objects:
                        base_name = name
                        count = 1
                        while f"{base_name}.{count:03d}" in bpy.data.objects:
                            count += 1
                        object_name = f"{base_name}.{count:03d}"
                    else:
                        object_name = name
                
                # 根据类型创建对象
                if obj_type == "CUBE":
                    bpy.ops.mesh.primitive_cube_add(location=location)
                elif obj_type == "SPHERE":
                    bpy.ops.mesh.primitive_uv_sphere_add(location=location)
                elif obj_type == "CYLINDER":
                    bpy.ops.mesh.primitive_cylinder_add(location=location)
                elif obj_type == "PLANE":
                    bpy.ops.mesh.primitive_plane_add(location=location)
                elif obj_type == "CONE":
                    bpy.ops.mesh.primitive_cone_add(location=location)
                elif obj_type == "TORUS":
                    bpy.ops.mesh.primitive_torus_add(location=location)
                elif obj_type == "EMPTY":
                    bpy.ops.object.empty_add(location=location)
                elif obj_type == "CAMERA":
                    bpy.ops.object.camera_add(location=location)
                elif obj_type == "LIGHT":
                    bpy.ops.object.light_add(type='POINT', location=location)
                else:
                    return {"status": "error", "message": f"不支持的对象类型: {obj_type}"}
                
                # 获取新创建的对象
                obj = bpy.context.active_object
                obj.name = object_name
                
                # 设置旋转和缩放
                obj.rotation_euler = [
                    rotation[0], rotation[1], rotation[2]
                ]
                obj.scale = [
                    scale[0], scale[1], scale[2]
                ]
                
                # 存储最后创建的对象引用
                obj_id = f"{obj_type}_{int(time.time()*1000)}"
                self.last_created_objects[obj_id] = object_name
                
                # 确保Blender更新场景
                bpy.context.view_layer.update()
                
                return {"status": "success", "result": {"name": object_name, "id": obj_id}}
            except Exception as e:
                traceback.print_exc()
                return {"status": "error", "message": f"创建对象失败: {str(e)}"}
        
        # 调用Blender API
        return self._run_in_main_thread(create_object_in_blender)
    
    def _handle_modify_object(self, params):
        """修改现有对象的属性"""
        name = params.get("name")
        location = params.get("location")
        rotation = params.get("rotation")
        scale = params.get("scale")
        
        if not name:
            return {"status": "error", "message": "缺少对象名称参数"}
        
        def modify_object_in_blender():
            try:
                if name not in bpy.data.objects:
                    return {"status": "error", "message": f"对象 '{name}' 不存在"}
                
                obj = bpy.data.objects[name]
                
                if location:
                    obj.location = (location[0], location[1], location[2])
                
                if rotation:
                    obj.rotation_euler = (rotation[0], rotation[1], rotation[2])
                
                if scale:
                    obj.scale = (scale[0], scale[1], scale[2])
                
                # 确保Blender更新场景
                bpy.context.view_layer.update()
                
                return {"status": "success", "result": {"name": name}}
            except Exception as e:
                return {"status": "error", "message": f"修改对象失败: {str(e)}"}
        
        return self._run_in_main_thread(modify_object_in_blender)
    
    def _handle_delete_object(self, params):
        """删除指定的对象"""
        name = params.get("name")
        
        if not name:
            return {"status": "error", "message": "缺少对象名称参数"}
        
        def delete_object_in_blender():
            try:
                if name not in bpy.data.objects:
                    return {"status": "error", "message": f"对象 '{name}' 不存在"}
                
                obj = bpy.data.objects[name]
                bpy.data.objects.remove(obj)
                
                # 确保Blender更新场景
                bpy.context.view_layer.update()
                
                return {"status": "success", "result": {"name": name}}
            except Exception as e:
                return {"status": "error", "message": f"删除对象失败: {str(e)}"}
        
        return self._run_in_main_thread(delete_object_in_blender)
    
    def _handle_join_objects(self, params):
        """将多个对象合并为一个"""
        objects = params.get("objects", [])
        target_object = params.get("target_object")
        
        if not objects or len(objects) < 2:
            return {"status": "error", "message": "至少需要两个对象才能合并"}
        
        if not target_object:
            target_object = objects[0]
        
        def join_objects_in_blender():
            try:
                # 验证所有对象是否存在
                missing_objects = [name for name in objects if name not in bpy.data.objects]
                if missing_objects:
                    return {
                        "status": "error",
                        "message": f"以下对象不存在: {', '.join(missing_objects)}"
                    }
                
                if target_object not in bpy.data.objects:
                    return {"status": "error", "message": f"目标对象 '{target_object}' 不存在"}
                
                # 确保所有对象都是网格
                non_mesh_objects = [
                    name for name in objects
                    if bpy.data.objects[name].type != 'MESH'
                ]
                if non_mesh_objects:
                    return {
                        "status": "error",
                        "message": f"以下对象不是网格，无法合并: {', '.join(non_mesh_objects)}"
                    }
                
                # 选择所有对象
                bpy.ops.object.select_all(action='DESELECT')
                
                # 首先选择目标对象并使其活动
                target = bpy.data.objects[target_object]
                target.select_set(True)
                bpy.context.view_layer.objects.active = target
                
                # 然后选择其他对象
                for name in objects:
                    if name != target_object:
                        obj = bpy.data.objects[name]
                        obj.select_set(True)
                
                # 合并对象
                bpy.ops.object.join()
                
                # 确保Blender更新场景
                bpy.context.view_layer.update()
                
                return {"status": "success", "result": {"name": target_object}}
            except Exception as e:
                traceback.print_exc()
                return {"status": "error", "message": f"合并对象失败: {str(e)}"}
        
        return self._run_in_main_thread(join_objects_in_blender)
    
    def _handle_safe_join_objects(self, params):
        """安全地合并多个对象，包括存在性验证和错误恢复"""
        objects = params.get("objects", [])
        target_object = params.get("target_object")
        
        if not objects or len(objects) < 2:
            return {"status": "error", "message": "至少需要两个对象才能合并"}
        
        if not target_object:
            target_object = objects[0]
        
        def safe_join_objects_in_blender():
            try:
                # 验证所有对象是否存在
                existing_objects = []
                for name in objects:
                    if name in bpy.data.objects:
                        existing_objects.append(name)
                    else:
                        print(f"警告: 对象 '{name}' 不存在，将从合并列表中排除")
                
                if len(existing_objects) < 2:
                    return {
                        "status": "error",
                        "message": f"没有足够的有效对象来执行合并操作，找到 {len(existing_objects)} 个，需要至少2个"
                    }
                
                # 确保目标对象存在
                if target_object not in bpy.data.objects:
                    # 如果指定的目标不存在，使用第一个有效对象
                    if existing_objects:
                        target_object = existing_objects[0]
                        print(f"注意: 原目标对象不存在，将使用 '{target_object}' 作为目标")
                    else:
                        return {"status": "error", "message": "没有有效的目标对象可用"}
                else:
                    # 确保目标对象在合并列表中
                    if target_object not in existing_objects:
                        existing_objects.append(target_object)
                
                # 过滤出可以合并的网格对象
                mesh_objects = []
                for name in existing_objects:
                    obj = bpy.data.objects[name]
                    if obj.type == 'MESH':
                        mesh_objects.append(name)
                    else:
                        print(f"注意: 对象 '{name}' 不是网格，将从合并列表中排除")
                
                if len(mesh_objects) < 2:
                    return {
                        "status": "error", 
                        "message": f"没有足够的网格对象来执行合并操作，找到 {len(mesh_objects)} 个网格，需要至少2个"
                    }
                
                # 确保目标是网格对象
                if target_object not in mesh_objects and mesh_objects:
                    target_object = mesh_objects[0]
                    print(f"注意: 原目标不是网格对象，将使用 '{target_object}' 作为目标")
                
                # 备份对象以便出错时恢复
                backup_data = {}
                for name in mesh_objects:
                    obj = bpy.data.objects[name]
                    backup_data[name] = {
                        "location": obj.location.copy(),
                        "rotation": obj.rotation_euler.copy(),
                        "scale": obj.scale.copy()
                    }
                
                # 准备合并
                bpy.ops.object.select_all(action='DESELECT')
                
                target = bpy.data.objects[target_object]
                target.select_set(True)
                bpy.context.view_layer.objects.active = target
                
                # 选择其他要合并的对象
                for name in mesh_objects:
                    if name != target_object:
                        obj = bpy.data.objects[name]
                        obj.select_set(True)
                
                # 执行合并操作
                try:
                    bpy.ops.object.join()
                    
                    # 确保Blender更新场景
                    bpy.context.view_layer.update()
                    
                    # 验证目标对象仍然存在
                    if target_object not in bpy.data.objects:
                        raise Exception(f"合并后目标对象 '{target_object}' 不存在")
                    
                    return {"status": "success", "result": {"name": target_object}}
                    
                except Exception as e:
                    # 合并失败，尝试恢复对象
                    print(f"合并失败: {str(e)}，尝试恢复对象状态")
                    
                    # 恢复可能被修改的对象
                    for name, data in backup_data.items():
                        if name in bpy.data.objects:
                            obj = bpy.data.objects[name]
                            obj.location = data["location"]
                            obj.rotation_euler = data["rotation"]
                            obj.scale = data["scale"]
                    
                    raise Exception(f"安全合并失败: {str(e)}")
                
            except Exception as e:
                traceback.print_exc()
                return {"status": "error", "message": f"安全合并对象失败: {str(e)}"}
        
        return self._run_in_main_thread(safe_join_objects_in_blender)
    
    def _handle_verify_object_exists(self, params):
        """验证对象是否存在于场景中"""
        name = params.get("name")
        
        if not name:
            return {"status": "error", "message": "缺少对象名称参数"}
        
        def verify_object_in_blender():
            try:
                exists = name in bpy.data.objects
                return {
                    "status": "success", 
                    "result": {
                        "exists": exists,
                        "name": name
                    }
                }
            except Exception as e:
                return {"status": "error", "message": f"验证对象存在性失败: {str(e)}"}
        
        return self._run_in_main_thread(verify_object_in_blender)
    
    def _handle_set_material(self, params):
        """为对象设置材质"""
        name = params.get("name") or params.get("object")
        color = params.get("color", [0.8, 0.8, 0.8])
        roughness = params.get("roughness", 0.5)
        metallic = params.get("metallic", 0.0)
        
        if not name:
            return {"status": "error", "message": "缺少对象名称参数"}
        
        def set_material_in_blender():
            try:
                if name not in bpy.data.objects:
                    return {"status": "error", "message": f"对象 '{name}' 不存在"}
                
                obj = bpy.data.objects[name]
                
                # 创建新材质
                mat_name = f"Material_{name}"
                if mat_name in bpy.data.materials:
                    mat = bpy.data.materials[mat_name]
                else:
                    mat = bpy.data.materials.new(name=mat_name)
                
                # 设置材质属性
                mat.use_nodes = True
                nodes = mat.node_tree.nodes
                
                # 清除现有节点
                for node in nodes:
                    nodes.remove(node)
                
                # 创建主着色器节点
                principled_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
                principled_bsdf.inputs['Base Color'].default_value = [
                    color[0], color[1], color[2], 1.0
                ]
                principled_bsdf.inputs['Roughness'].default_value = roughness
                principled_bsdf.inputs['Metallic'].default_value = metallic
                
                # 创建输出节点
                material_output = nodes.new(type='ShaderNodeOutputMaterial')
                
                # 连接节点
                links = mat.node_tree.links
                links.new(
                    principled_bsdf.outputs['BSDF'],
                    material_output.inputs['Surface']
                )
                
                # 分配材质给对象
                if obj.data.materials:
                    obj.data.materials[0] = mat
                else:
                    obj.data.materials.append(mat)
                
                return {"status": "success", "result": {"name": name, "material": mat_name}}
            except Exception as e:
                return {"status": "error", "message": f"设置材质失败: {str(e)}"}
        
        return self._run_in_main_thread(set_material_in_blender)
    
    def _handle_set_light_type(self, params):
        """设置灯光类型"""
        name = params.get("name")
        light_type = params.get("light_type")
        
        if not name:
            return {"status": "error", "message": "缺少灯光名称参数"}
        
        if not light_type:
            return {"status": "error", "message": "缺少灯光类型参数"}
        
        valid_types = ['POINT', 'SUN', 'SPOT', 'AREA']
        if light_type not in valid_types:
            return {"status": "error", "message": f"无效的灯光类型: {light_type}. 有效类型: {', '.join(valid_types)}"}
        
        def set_light_type_in_blender():
            try:
                if name not in bpy.data.objects:
                    return {"status": "error", "message": f"对象 '{name}' 不存在"}
                
                obj = bpy.data.objects[name]
                if obj.type != 'LIGHT':
                    return {"status": "error", "message": f"对象 '{name}' 不是灯光"}
                
                obj.data.type = light_type
                
                return {"status": "success", "result": {"name": name, "light_type": light_type}}
            except Exception as e:
                return {"status": "error", "message": f"设置灯光类型失败: {str(e)}"}
        
        return self._run_in_main_thread(set_light_type_in_blender)
    
    def _handle_set_light_energy(self, params):
        """设置灯光能量/强度"""
        name = params.get("name")
        energy = params.get("energy")
        
        if not name:
            return {"status": "error", "message": "缺少灯光名称参数"}
        
        if energy is None:
            return {"status": "error", "message": "缺少灯光能量参数"}
        
        def set_light_energy_in_blender():
            try:
                if name not in bpy.data.objects:
                    return {"status": "error", "message": f"对象 '{name}' 不存在"}
                
                obj = bpy.data.objects[name]
                if obj.type != 'LIGHT':
                    return {"status": "error", "message": f"对象 '{name}' 不是灯光"}
                
                obj.data.energy = float(energy)
                
                return {"status": "success", "result": {"name": name, "energy": float(energy)}}
            except Exception as e:
                return {"status": "error", "message": f"设置灯光能量失败: {str(e)}"}
        
        return self._run_in_main_thread(set_light_energy_in_blender)
    
    def _handle_set_active_camera(self, params):
        """设置活动相机"""
        name = params.get("name")
        
        if not name:
            return {"status": "error", "message": "缺少相机名称参数"}
        
        def set_active_camera_in_blender():
            try:
                if name not in bpy.data.objects:
                    return {"status": "error", "message": f"对象 '{name}' 不存在"}
                
                obj = bpy.data.objects[name]
                if obj.type != 'CAMERA':
                    return {"status": "error", "message": f"对象 '{name}' 不是相机"}
                
                bpy.context.scene.camera = obj
                
                return {"status": "success", "result": {"name": name}}
            except Exception as e:
                return {"status": "error", "message": f"设置活动相机失败: {str(e)}"}
        
        return self._run_in_main_thread(set_active_camera_in_blender)
    
    def _handle_render_scene(self, params):
        """渲染当前场景并保存图像"""
        resolution_x = params.get("resolution_x", 1920)
        resolution_y = params.get("resolution_y", 1080)
        output_path = params.get("output_path", "//render.png")
        
        def render_scene_in_blender():
            try:
                # 设置渲染属性
                bpy.context.scene.render.resolution_x = resolution_x
                bpy.context.scene.render.resolution_y = resolution_y
                bpy.context.scene.render.filepath = output_path
                
                # 渲染场景
                bpy.ops.render.render(write_still=True)
                
                return {
                    "status": "success", 
                    "result": {
                        "resolution": [resolution_x, resolution_y],
                        "path": output_path
                    }
                }
            except Exception as e:
                return {"status": "error", "message": f"渲染场景失败: {str(e)}"}
        
        return self._run_in_main_thread(render_scene_in_blender)
    
    def _handle_advanced_lighting(self, params):
        """创建高级照明设置"""
        name = params.get("name", "AdvancedLight")
        light_type = params.get("light_type", "AREA")
        location = params.get("location", [0, 0, 5])
        rotation = params.get("rotation", [0, 0, 0])
        energy = params.get("energy", 100)
        color = params.get("color", [1.0, 1.0, 1.0])
        size = params.get("size", 5.0)
        
        def create_advanced_lighting_in_blender():
            try:
                # 创建新灯光
                bpy.ops.object.light_add(type=light_type, location=location, rotation=rotation)
                light = bpy.context.active_object
                light.name = name
                
                # 设置灯光属性
                light.data.energy = energy
                light.data.color = color
                
                # 对于区域灯，设置大小
                if light_type == 'AREA':
                    light.data.size = size
                
                return {
                    "status": "success", 
                    "result": {
                        "name": name,
                        "type": light_type,
                        "location": location,
                        "energy": energy
                    }
                }
            except Exception as e:
                return {"status": "error", "message": f"创建高级照明失败: {str(e)}"}
        
        return self._run_in_main_thread(create_advanced_lighting_in_blender)
    
    def _handle_execute_code(self, params):
        """执行任意Python代码，高级功能，谨慎使用"""
        code = params.get("code")
        
        if not code:
            return {"status": "error", "message": "缺少代码参数"}
        
        def execute_code_in_blender():
            try:
                # 创建局部和全局变量字典
                locals_dict = {}
                globals_dict = {"bpy": bpy}
                
                # 执行代码
                exec(code, globals_dict, locals_dict)
                
                # 提取可能的返回值
                result = locals_dict.get("result", "代码执行成功，无返回值")
                
                return {"status": "success", "result": result}
            except Exception as e:
                traceback.print_exc()
                return {"status": "error", "message": f"执行代码失败: {str(e)}"}
        
        return self._run_in_main_thread(execute_code_in_blender)
    
    def _run_in_main_thread(self, func):
        """在Blender主线程中运行函数"""
        if threading.current_thread() is threading.main_thread():
            # 如果当前已在主线程，直接执行
            return func()
        else:
            # 否则，将操作排队到主线程
            return bpy.app.timers.register(func, first_interval=0.0)

if __name__ == "__main__":
    main()
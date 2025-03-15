#!/usr/bin/env python3
"""
BlenderMCP 客户端 - 提供与Blender MCP服务器通信的接口
不依赖于Blender的bpy模块，可以在任何Python环境中运行
"""

import socket
import json
import time
import traceback
import sys
import os


class BlenderMCPClient:
    """BlenderMCP客户端类，用于与Blender MCP服务器通信"""
    
    def __init__(self, host="localhost", port=9876, socket_timeout=5.0, debug=False):
        """初始化客户端
        
        参数:
            host (str): 服务器主机名
            port (int): 服务器端口
            socket_timeout (float): 套接字操作超时时间（秒）
            debug (bool): 是否启用调试模式
        """
        self.host = host
        self.port = port
        self.socket = None
        self.socket_timeout = socket_timeout
        self.debug = debug
        self.connected = False
        self.last_response = None
        self.retry_count = 3  # 默认重试次数
        self.retry_delay = 0.5  # 默认重试延迟（秒）
    
    def connect(self):
        """连接到Blender MCP服务器
        
        返回:
            bool: 连接是否成功
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.socket_timeout)
            self.socket.connect((self.host, self.port))
            self.connected = True
            
            if self.debug:
                print(f"已连接到 {self.host}:{self.port}")
            
            return True
        except Exception as e:
            if self.debug:
                print(f"连接失败: {str(e)}")
                traceback.print_exc()
            
            self.connected = False
            return False
    
    def disconnect(self):
        """断开与服务器的连接"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            finally:
                self.socket = None
                self.connected = False
                
        if self.debug:
            print("已断开连接")
    
    def _handle_response(self, response, operation_name="操作"):
        """处理服务器响应，确保格式一致
        
        参数:
            response (dict/str): 服务器响应
            operation_name (str): 操作名称，用于日志记录
            
        返回:
            dict: 处理后的响应
        """
        self.last_response = response
        
        if not response:
            if self.debug:
                print(f"警告: {operation_name} - 响应为空")
            return {"status": "error", "message": "空响应"}
            
        if isinstance(response, str):
            try:
                response = json.loads(response)
            except:
                if self.debug:
                    print(f"警告: {operation_name} - 无法解析JSON响应: {response}")
                return {"status": "error", "message": f"无法解析响应: {response}"}
        
        # 确保响应有状态字段
        if not isinstance(response, dict):
            return {"status": "error", "message": f"响应不是字典: {response}"}
            
        if "status" not in response:
            # 尝试推断状态
            if "error" in response:
                response["status"] = "error"
                response["message"] = response.pop("error")
            else:
                response["status"] = "success"
        
        return response
    
    def send_command(self, command, params=None, retries=None):
        """向服务器发送命令
        
        参数:
            command (str): 命令名称
            params (dict): 命令参数
            retries (int): 重试次数，如果为None则使用默认值
            
        返回:
            dict: 服务器响应
        """
        if not self.connected:
            if self.debug:
                print("错误: 未连接到服务器")
            return {"status": "error", "message": "未连接到服务器"}
        
        if retries is None:
            retries = self.retry_count
            
        # 构建命令数据
        cmd_data = {"command": command}
        if params:
            cmd_data["params"] = params
            
        # 将命令转换为JSON
        try:
            cmd_json = json.dumps(cmd_data)
        except Exception as e:
            if self.debug:
                print(f"错误: 无法序列化命令: {str(e)}")
            return {"status": "error", "message": f"命令序列化失败: {str(e)}"}
        
        # 发送命令并接收响应
        for attempt in range(retries + 1):
            try:
                if self.debug and attempt > 0:
                    print(f"重试 ({attempt}/{retries})...")
                
                # 发送命令
                self.socket.sendall(cmd_json.encode())
                
                # 接收响应
                response_data = self.socket.recv(65536).decode()
                
                try:
                    # 尝试解析响应
                    response = json.loads(response_data)
                    return self._handle_response(response, command)
                except json.JSONDecodeError:
                    if self.debug:
                        print(f"警告: 无法解析响应: {response_data}")
                    
                    if attempt < retries:
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        return {"status": "error", "message": f"无法解析响应: {response_data}"}
                        
            except socket.timeout:
                if self.debug:
                    print(f"警告: 命令超时: {command}")
                
                if attempt < retries:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    return {"status": "error", "message": "命令超时"}
                    
            except Exception as e:
                if self.debug:
                    print(f"错误: 发送命令时出错: {str(e)}")
                    traceback.print_exc()
                
                if attempt < retries:
                    # 尝试重新连接
                    self.disconnect()
                    if not self.connect():
                        return {"status": "error", "message": "重新连接服务器失败"}
                    time.sleep(self.retry_delay)
                    continue
                else:
                    return {"status": "error", "message": f"发送命令失败: {str(e)}"}
        
        # 如果所有重试都失败
        return {"status": "error", "message": "所有重试都失败"}
    
    def safe_join_objects(self, object_names, target_object=None):
        """安全地合并对象，包括验证步骤
        
        参数:
            object_names (list): 要合并的对象名称列表
            target_object (str): 目标对象名称，如果为None则使用第一个对象
            
        返回:
            dict: 服务器响应
        """
        if not object_names:
            return {"status": "error", "message": "未提供对象名称"}
            
        # 验证所有对象是否存在
        missing_objects = []
        for obj_name in object_names:
            resp = self.verify_object_exists(obj_name)
            if not resp.get("status") == "success" or not resp.get("result", {}).get("exists", False):
                missing_objects.append(obj_name)
        
        if missing_objects:
            return {
                "status": "error", 
                "message": f"以下对象不存在: {', '.join(missing_objects)}"
            }
        
        # 如果未指定目标对象，使用第一个对象
        if not target_object:
            target_object = object_names[0]
            
        # 执行合并操作
        return self.send_command("join_objects", {
            "objects": object_names,
            "target_object": target_object
        })
    
    # 基本命令
    def ping(self):
        """测试服务器连接
        
        返回:
            dict: 服务器响应
        """
        return self.send_command("ping")
    
    def verify_object_exists(self, object_name):
        """验证对象是否存在
        
        参数:
            object_name (str): 要验证的对象名称
            
        返回:
            dict: 包含验证结果的响应
        """
        return self.send_command("verify_object_exists", {"object_name": object_name})
    
    def clear_scene(self):
        """清除当前场景中的所有对象
        
        返回:
            dict: 服务器响应
        """
        return self.send_command("clear_scene")
    
    # 对象操作
    def get_scene_info(self):
        """获取当前场景信息
        
        返回:
            dict: 包含场景信息的响应
        """
        return self.send_command("get_scene_info")
    
    def create_object(self, obj_type, name=None, location=None, rotation=None, scale=None):
        """创建新对象
        
        参数:
            obj_type (str): 对象类型 (CUBE, SPHERE, CYLINDER, PLANE, CONE, TORUS, EMPTY, CAMERA, LIGHT)
            name (str): 对象名称
            location (list): 位置坐标 [x, y, z]
            rotation (list): 旋转角度 [x, y, z]（弧度）
            scale (list): 缩放比例 [x, y, z]
            
        返回:
            dict: 包含创建的对象信息的响应
        """
        params = {"type": obj_type}
        
        if name:
            params["name"] = name
        if location:
            params["location"] = location
        if rotation:
            params["rotation"] = rotation
        if scale:
            params["scale"] = scale
            
        response = self.send_command("create_object", params)
        return response
    
    def modify_object(self, object_name, location=None, rotation=None, scale=None):
        """修改对象属性
        
        参数:
            object_name (str): 对象名称
            location (list): 新的位置坐标 [x, y, z]
            rotation (list): 新的旋转角度 [x, y, z]（弧度）
            scale (list): 新的缩放比例 [x, y, z]
            
        返回:
            dict: 服务器响应
        """
        params = {"object_name": object_name}
        
        if location:
            params["location"] = location
        if rotation:
            params["rotation"] = rotation
        if scale:
            params["scale"] = scale
            
        return self.send_command("modify_object", params)
    
    def delete_object(self, object_name):
        """删除对象
        
        参数:
            object_name (str): 对象名称
            
        返回:
            dict: 服务器响应
        """
        return self.send_command("delete_object", {"object_name": object_name})
    
    # 材质操作
    def set_material(self, object_name, color=None, metallic=None, roughness=None, emission=None):
        """设置对象材质
        
        参数:
            object_name (str): 对象名称
            color (list): RGB颜色值 [r, g, b]
            metallic (float): 金属度 (0.0-1.0)
            roughness (float): 粗糙度 (0.0-1.0)
            emission (list): 发光颜色 [r, g, b, 强度]
            
        返回:
            dict: 服务器响应
        """
        params = {"name": object_name, "object_name": object_name}  # 同时使用两个参数名，确保兼容性
        
        if color:
            params["color"] = color
        if metallic is not None:
            params["metallic"] = metallic
        if roughness is not None:
            params["roughness"] = roughness
        if emission:
            params["emission"] = emission
            
        return self.send_command("set_material", params)
    
    # 灯光操作
    def set_light_type(self, object_name, light_type):
        """设置灯光类型
        
        参数:
            object_name (str): 灯光对象名称
            light_type (str): 灯光类型 (POINT, SUN, SPOT, AREA)
            
        返回:
            dict: 服务器响应
        """
        return self.send_command("set_light_type", {
            "object_name": object_name,
            "light_type": light_type
        })
    
    def set_light_energy(self, object_name, energy):
        """设置灯光能量
        
        参数:
            object_name (str): 灯光对象名称
            energy (float): 灯光能量
            
        返回:
            dict: 服务器响应
        """
        return self.send_command("set_light_energy", {
            "object_name": object_name,
            "energy": energy
        })
    
    def create_advanced_lighting(self, name, light_type, location, energy=1.0, color=None, size=None):
        """创建高级灯光
        
        参数:
            name (str): 灯光名称
            light_type (str): 灯光类型 (POINT, SUN, SPOT, AREA)
            location (list): 位置坐标 [x, y, z]
            energy (float): 灯光能量
            color (list): RGB颜色值 [r, g, b]
            size (float): 灯光尺寸 (仅对AREA类型有效)
            
        返回:
            dict: 服务器响应
        """
        params = {
            "name": name,
            "light_type": light_type,
            "location": location,
            "energy": energy
        }
        
        if color:
            params["color"] = color
        if size is not None:
            params["size"] = size
            
        return self.send_command("create_advanced_lighting", params)
    
    # 相机操作
    def set_active_camera(self, camera_name):
        """设置活动相机
        
        参数:
            camera_name (str): 相机对象名称
            
        返回:
            dict: 服务器响应
        """
        return self.send_command("set_active_camera", {"object_name": camera_name})
    
    # 渲染操作
    def render_scene(self, resolution_x=None, resolution_y=None, output_path=None):
        """渲染当前场景
        
        参数:
            resolution_x (int): 渲染宽度
            resolution_y (int): 渲染高度
            output_path (str): 输出文件路径
            
        返回:
            dict: 服务器响应
        """
        params = {}
        
        if resolution_x:
            params["resolution_x"] = resolution_x
        if resolution_y:
            params["resolution_y"] = resolution_y
        if output_path:
            params["output_path"] = output_path
            
        return self.send_command("render_scene", params)
    
    def render_scene_async(self, resolution_x=None, resolution_y=None, output_path=None):
        """异步渲染当前场景
        
        参数:
            resolution_x (int): 渲染分辨率宽度
            resolution_y (int): 渲染分辨率高度
            output_path (str): 输出文件路径
            
        返回:
            dict: 包含任务ID的响应
        """
        params = {}
        
        if resolution_x:
            params["resolution_x"] = resolution_x
        if resolution_y:
            params["resolution_y"] = resolution_y
        if output_path:
            params["output_path"] = output_path
            
        return self.send_command("render_scene_async", params)
    
    def get_task(self, task_id):
        """获取任务状态
        
        参数:
            task_id (str): 任务ID
            
        返回:
            dict: 包含任务状态的响应
        """
        params = {"task_id": task_id}
        return self.send_command("get_task", params)
    
    def get_task_detailed(self, task_id):
        """获取详细的任务信息
        
        参数:
            task_id (str): 任务ID
            
        返回:
            dict: 包含详细任务信息的响应
        """
        params = {"task_id": task_id}
        return self.send_command("get_task_detailed", params)
    
    def list_tasks(self):
        """获取所有任务列表
        
        返回:
            dict: 包含任务列表的响应
        """
        return self.send_command("list_tasks")
    
    def cancel_task(self, task_id):
        """取消任务
        
        参数:
            task_id (str): 任务ID
            
        返回:
            dict: 操作结果响应
        """
        params = {"task_id": task_id}
        return self.send_command("cancel_task", params)


# 示例用法
if __name__ == "__main__":
    # 创建客户端
    client = BlenderMCPClient(debug=True)
    
    # 连接到服务器
    if not client.connect():
        print("无法连接到服务器")
        sys.exit(1)
    
    try:
        # 测试连接
        response = client.ping()
        print(f"Ping响应: {json.dumps(response, indent=2, ensure_ascii=False)}")
        
        # 获取场景信息
        scene_info = client.get_scene_info()
        print(f"场景信息: {json.dumps(scene_info, indent=2, ensure_ascii=False)}")
        
        # 创建一个立方体
        cube_response = client.create_object("CUBE", name="测试立方体", location=[0, 0, 0], scale=[2, 2, 2])
        print(f"创建立方体响应: {json.dumps(cube_response, indent=2, ensure_ascii=False)}")
        
        # 设置材质
        material_response = client.set_material("测试立方体", color=[1, 0, 0])
        print(f"设置材质响应: {json.dumps(material_response, indent=2, ensure_ascii=False)}")
        
    finally:
        # 断开连接
        client.disconnect() 
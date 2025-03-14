import socket
import json
import time
import traceback

class BlenderMCPClient:
    """BlenderMCP客户端，用于与Blender通信"""
    
    def __init__(self, host='localhost', port=9876, socket_timeout=10.0, debug=False):
        self.host = host
        self.port = port
        self.socket = None
        self.socket_timeout = socket_timeout
        self.debug = debug
    
    def connect(self):
        """连接到BlenderMCP服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.socket_timeout)  # 设置超时
            self.socket.connect((self.host, self.port))
            print(f"已连接到BlenderMCP服务器 {self.host}:{self.port}")
            
            # 测试连接
            ping_result = self.ping()
            if not ping_result or ping_result.get("status") != "success":
                print("警告: 服务器未响应Ping请求")
                return False
                
            return True
        except Exception as e:
            print(f"连接失败: {str(e)}")
            self.socket = None
            return False
    
    def disconnect(self):
        """断开与服务器的连接"""
        if self.socket:
            self.socket.close()
            self.socket = None
            print("已断开与BlenderMCP服务器的连接")
    
    def _handle_response(self, response):
        """统一处理服务器响应"""
        if not response:
            return {"status": "error", "message": "空响应"}
            
        # 确保响应有一致的格式
        if isinstance(response, dict):
            if "status" not in response:
                if "error" in response:
                    return {"status": "error", "message": response["error"]}
                return {"status": "success", "result": response}
        
        return response
    
    def send_command(self, command_type, params=None, retry_count=1):
        """发送命令到Blender服务器，支持重试机制"""
        if not self.socket:
            error_response = {"status": "error", "message": "未连接到服务器"}
            if self.debug:
                print(f"错误: {error_response['message']}")
            return error_response
        
        # 构建命令
        command = {
            "type": command_type,
            "params": params or {}
        }
        
        for attempt in range(retry_count + 1):
            try:
                # 发送JSON格式的命令
                json_command = json.dumps(command)
                if self.debug:
                    print(f"发送命令: {json_command[:200]}{'...' if len(json_command) > 200 else ''}")
                
                self.socket.sendall(json_command.encode('utf-8'))
                
                # 接收响应
                buffer_size = 262144  # 增大到256KB以处理大型响应
                response_data = self.socket.recv(buffer_size)
                
                # 检查是否需要多次接收以获取完整响应
                total_data = []
                total_data.append(response_data)
                
                if len(response_data) == buffer_size:
                    # 可能有更多数据
                    while True:
                        try:
                            self.socket.settimeout(0.5)  # 短暂超时等待更多数据
                            more_data = self.socket.recv(buffer_size)
                            if not more_data:
                                break
                            total_data.append(more_data)
                            if len(more_data) < buffer_size:
                                break
                        except socket.timeout:
                            break
                    
                    # 恢复原始超时
                    self.socket.settimeout(self.socket_timeout)
                
                # 合并所有收到的数据
                response_data = b''.join(total_data)
                
                # 解析JSON响应
                try:
                    response_json = response_data.decode('utf-8')
                    response = json.loads(response_json)
                    if self.debug:
                        print(f"收到响应: {response_json[:200]}{'...' if len(response_json) > 200 else ''}")
                except json.JSONDecodeError as je:
                    print(f"JSON解析错误: {str(je)}")
                    print(f"收到的数据: {response_data[:200]}...")
                    return {"status": "error", "message": f"无法解析服务器响应: {str(je)}"}
                
                # 统一处理响应
                return self._handle_response(response)
                
            except socket.timeout:
                if attempt < retry_count:
                    print(f"命令超时，尝试重试 ({attempt+1}/{retry_count})")
                    time.sleep(0.5)  # 重试前短暂等待
                    continue
                else:
                    return {"status": "error", "message": "命令执行超时"}
                
            except Exception as e:
                if self.debug:
                    traceback.print_exc()
                print(f"通信错误: {str(e)}")
                
                # 尝试重新连接一次
                if attempt < retry_count:
                    print(f"尝试重新连接并重试命令 ({attempt+1}/{retry_count})")
                    self.disconnect()
                    if self.connect():
                        time.sleep(0.5)  # 连接后短暂等待
                        continue
                        
                return {"status": "error", "message": str(e)}
    
    def ping(self):
        """测试服务器连接"""
        return self.send_command("ping")
    
    def get_scene_info(self):
        """获取场景信息"""
        return self.send_command("get_scene_info")
    
    def get_object_info(self, name):
        """获取特定对象的信息"""
        return self.send_command("get_object_info", {"object_name": name})
    
    def get_object_name(self, response):
        """从响应中获取对象名称，处理不同的响应格式"""
        if not response:
            if self.debug:
                print("警告: 尝试从空响应中获取对象名称")
            return None
            
        if self.debug:
            print(f"解析响应以获取对象名称: {json.dumps(response, ensure_ascii=False)[:100]}...")
            
        if isinstance(response, dict):
            # 检查常见响应格式
            if "status" in response and response["status"] == "error":
                if self.debug:
                    print(f"错误响应: {response.get('message', '未知错误')}")
                return None
                
            if "result" in response and isinstance(response["result"], dict):
                if "name" in response["result"]:
                    return response["result"]["name"]
                if "object_name" in response["result"]:
                    return response["result"]["object_name"]
                if "object" in response["result"]:
                    return response["result"]["object"]
                    
            if "name" in response:
                return response["name"]
                
        if self.debug:
            print(f"无法从响应中提取对象名称: {json.dumps(response, ensure_ascii=False)[:100]}...")
        return None
    
    def verify_object_exists(self, name):
        """验证对象是否存在"""
        if not name:
            return False
            
        response = self.get_object_info(name)
        return response.get("status") == "success"
    
    def create_object(self, object_type, name=None, location=None, rotation=None, scale=None):
        """创建一个新对象"""
        params = {"type": object_type}
        if name:
            params["name"] = name
        if location:
            params["location"] = location
        if rotation:
            params["rotation"] = rotation
        if scale:
            params["scale"] = scale
        
        response = self.send_command("create_object", params)
        
        # 检查响应并尝试提取更完整信息
        if response.get("status") == "success" and "result" not in response:
            # 如果成功但没有result字段，尝试使用name参数获取对象信息
            object_name = self.get_object_name(response) or name
            
            if object_name:
                # 尝试获取刚创建的对象信息
                time.sleep(0.1)  # 短暂等待以确保对象创建完成
                obj_info = self.get_object_info(object_name)
                if obj_info.get("status") == "success":
                    response["result"] = obj_info.get("result", {})
                else:
                    # 如果无法获取详细信息，至少提供名称
                    response["result"] = {"name": object_name}
        
        return response
    
    def modify_object(self, name, location=None, rotation=None, scale=None, visible=None):
        """修改对象属性"""
        params = {"name": name}
        if location is not None:
            params["location"] = location
        if rotation is not None:
            params["rotation"] = rotation
        if scale is not None:
            params["scale"] = scale
        if visible is not None:
            params["visible"] = visible
        
        return self.send_command("modify_object", params)
    
    def delete_object(self, name):
        """删除对象"""
        return self.send_command("delete_object", {"name": name})
    
    def safe_join_objects(self, objects, target_object):
        """安全地合并对象，包括验证和错误处理"""
        if not objects or len(objects) < 2:
            return {"status": "error", "message": "至少需要两个对象才能合并"}
            
        if not target_object:
            return {"status": "error", "message": "必须指定目标对象"}
        
        # 验证所有对象是否存在    
        valid_objects = []
        for obj in objects:
            if self.verify_object_exists(obj):
                valid_objects.append(obj)
            else:
                print(f"警告: 对象 '{obj}' 不存在，将从合并列表中移除")
        
        # 检查我们是否有足够的有效对象
        if len(valid_objects) < 2:
            return {"status": "error", "message": "没有足够的有效对象用于合并"}
            
        # 验证目标对象
        if target_object not in valid_objects:
            if len(valid_objects) > 0:
                target_object = valid_objects[0]
                print(f"警告: 目标对象 '{target_object}' 不存在，使用 '{valid_objects[0]}' 作为替代")
            else:
                return {"status": "error", "message": "目标对象无效且没有可用的替代对象"}
                
        # 执行合并
        return self.send_command("join_objects", {
            "objects": valid_objects,
            "target_object": target_object
        })
    
    def join_objects(self, objects, target_object):
        """合并多个对象 - 保留旧方法名以兼容现有代码，但使用新的安全实现"""
        return self.safe_join_objects(objects, target_object)
    
    def extrude_faces(self, object_name, face_indices, direction=None, distance=1.0):
        """挤出指定面"""
        # 首先验证对象是否存在
        if not self.verify_object_exists(object_name):
            return {"status": "error", "message": f"对象 '{object_name}' 不存在"}
            
        params = {
            "object_name": object_name,
            "face_indices": face_indices,
            "distance": distance
        }
        if direction:
            params["direction"] = direction
        
        return self.send_command("extrude_faces", params)
    
    def subdivide_mesh(self, object_name, cuts=1, smooth=0):
        """细分网格"""
        # 首先验证对象是否存在
        if not self.verify_object_exists(object_name):
            return {"status": "error", "message": f"对象 '{object_name}' 不存在"}
            
        return self.send_command("subdivide_mesh", {
            "object_name": object_name,
            "cuts": cuts,
            "smooth": smooth
        })
    
    def create_text(self, text, location=(0,0,0), size=1.0, name=None):
        """创建3D文本"""
        params = {
            "text": text,
            "location": location,
            "size": size
        }
        if name:
            params["name"] = name
            
        return self.send_command("create_text", params)
    
    def set_material(self, object_name, color=None, material_name=None):
        """设置对象材质"""
        # 首先验证对象是否存在
        if not self.verify_object_exists(object_name):
            return {"status": "error", "message": f"对象 '{object_name}' 不存在"}
            
        params = {"object_name": object_name}
        if color:
            params["color"] = color
        if material_name:
            params["material_name"] = material_name
            
        return self.send_command("set_material", params)
    
    def execute_with_retry(self, command, params, max_retries=3, delay=0.1):
        """带重试的命令执行，适用于可能需要多次尝试的操作"""
        for attempt in range(max_retries):
            try:
                response = self.send_command(command, params)
                if response.get("status") != "error":
                    time.sleep(delay)  # 小延迟，让Blender处理完成
                    return response
            except Exception as e:
                print(f"尝试 {attempt+1}/{max_retries} 失败: {str(e)}")
            
            # 失败后等待时间递增
            time.sleep(delay * (attempt + 1))
        
        return {"status": "error", "message": f"执行 {command} 失败，已重试 {max_retries} 次"}
    
    def render_scene(self, output_path=None, resolution_x=None, resolution_y=None):
        """渲染场景"""
        params = {}
        if output_path:
            params["output_path"] = output_path
        if resolution_x:
            params["resolution_x"] = resolution_x
        if resolution_y:
            params["resolution_y"] = resolution_y
            
        return self.send_command("render_scene", params)

# 使用示例
if __name__ == "__main__":
    client = BlenderMCPClient(debug=True)
    
    if client.connect():
        try:
            # 测试连接
            response = client.ping()
            print("Ping结果:", response)
            
            # 获取场景信息
            scene_info = client.get_scene_info()
            print("场景信息:", json.dumps(scene_info, indent=2, ensure_ascii=False))
            
            # 创建一个立方体
            cube = client.create_object("CUBE", name="测试立方体", location=[0, 0, 0])
            print("创建立方体:", cube)
            
            # 获取对象名称
            cube_name = client.get_object_name(cube) or "测试立方体"
            
            # 创建一个球体并设置材质
            sphere = client.create_object("SPHERE", name="测试球体", location=[3, 0, 0])
            sphere_name = client.get_object_name(sphere) or "测试球体"
            client.set_material(sphere_name, color=[1.0, 0.0, 0.0])
            print("创建球体:", sphere)
            
            # 移动立方体
            client.modify_object(cube_name, location=[0, 0, 2])
            print("移动立方体")
            
            # 挤出立方体的顶面
            client.extrude_faces(cube_name, [5], direction=[0, 0, 1], distance=1.5)
            print("挤出立方体顶面")
            
            # 添加文本
            text = client.create_text("BlenderMCP测试", location=[0, -3, 0], size=0.5)
            print("添加文本:", text)
            
            # 渲染场景
            render = client.render_scene(resolution_x=800, resolution_y=600)
            print("渲染结果:", render)
            
        finally:
            client.disconnect()

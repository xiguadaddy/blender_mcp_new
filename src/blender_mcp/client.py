import socket
import json
import time

class BlenderMCPClient:
    """BlenderMCP客户端，用于与Blender通信"""
    
    def __init__(self, host='localhost', port=9876):
        self.host = host
        self.port = port
        self.socket = None
    
    def connect(self):
        """连接到BlenderMCP服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print(f"已连接到BlenderMCP服务器 {self.host}:{self.port}")
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
    
    def send_command(self, command_type, params=None):
        """发送命令到Blender服务器"""
        if not self.socket:
            print("未连接到服务器")
            return {"status": "error", "message": "未连接到服务器"}
        
        # 构建命令
        command = {
            "type": command_type,
            "params": params or {}
        }
        
        try:
            # 发送JSON格式的命令
            json_command = json.dumps(command)
            self.socket.sendall(json_command.encode('utf-8'))
            
            # 接收响应
            response_data = self.socket.recv(65536)  # 增大接收缓冲区以处理大型响应
            
            # 解析JSON响应
            response = json.loads(response_data.decode('utf-8'))
            return response
        except Exception as e:
            print(f"通信错误: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def ping(self):
        """测试服务器连接"""
        return self.send_command("ping")
    
    def get_scene_info(self):
        """获取场景信息"""
        return self.send_command("get_scene_info")
    
    def get_object_name(self, response):
        """从响应中获取对象名称，处理不同的响应格式"""
        if response and "result" in response and isinstance(response["result"], dict) and "name" in response["result"]:
            return response["result"]["name"]
        elif response and "name" in response:
            return response["name"]
        elif response and isinstance(response, dict) and "status" == "success" and "result" in response and "name" in response["result"]:
            return response["result"]["name"]
        else:
            # 对于没有name的情况，尝试从其他字段获取
            if response and "result" in response and isinstance(response["result"], dict) and "object" in response["result"]:
                return response["result"]["object"]
            else:
                return None
    
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
        
        # 需要特殊处理，因为服务器端API需要以type作为参数名而不是在params中
        response = self.send_command("create_object", params)
        
        # 检查响应并尝试提取更完整信息
        if "status" in response and response["status"] == "success" and "result" not in response:
            # 如果成功但没有result字段，尝试使用name参数
            if name:
                # 尝试获取刚创建的对象信息
                time.sleep(0.1)  # 短暂等待以确保对象创建完成
                obj_info = self.send_command("get_object_info", {"name": name})
                if "status" in obj_info and obj_info["status"] == "success":
                    response["result"] = obj_info["result"]
                else:
                    # 如果无法获取详细信息，至少提供名称
                    response["result"] = {"name": name}
        
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
    
    def join_objects(self, objects, target_object):
        """合并多个对象"""
        if not objects or len(objects) < 2:
            return {"status": "error", "message": "至少需要两个对象才能合并"}
            
        if not target_object:
            return {"status": "error", "message": "必须指定目标对象"}
            
        return self.send_command("join_objects", {
            "objects": objects,
            "target_object": target_object
        })
    
    def extrude_faces(self, object_name, face_indices, direction=None, distance=1.0):
        """挤出指定面"""
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
        params = {"object_name": object_name}
        if color:
            params["color"] = color
        if material_name:
            params["material_name"] = material_name
            
        return self.send_command("set_material", params)
    
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
    client = BlenderMCPClient()
    
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

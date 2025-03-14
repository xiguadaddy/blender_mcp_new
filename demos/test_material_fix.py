#!/usr/bin/env python3
"""
测试脚本 - 验证材质应用和对象合并
此脚本测试材质应用和对象合并后材质保留的问题
"""

import sys
import os
import json
import time
import traceback
import socket

# 添加BlenderMCP客户端库到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from src.blender_mcp.client import BlenderMCPClient
except ImportError:
    # 尝试直接导入
    try:
        from blender_mcp.client import BlenderMCPClient
    except ImportError:
        print("无法导入BlenderMCPClient，请确保路径正确")
        sys.exit(1)

# 设置调试级别
DEBUG = True

def debug_print(message):
    """调试信息输出函数"""
    if DEBUG:
        print(f"[调试] {message}")

def check_response(response, operation_name):
    """检查响应状态，如有错误则打印"""
    if not response:
        print(f"警告: {operation_name} - 响应为空")
        return False
    
    if isinstance(response, dict):
        if "error" in response:
            print(f"错误: {operation_name} - {response['error']}")
            return False
        
        if "status" in response and response["status"] == "error":
            print(f"错误: {operation_name} - {response.get('message', '未知错误')}")
            return False
    
    debug_print(f"{operation_name} - 成功")
    return True

def get_object_name(response):
    """从创建对象的响应中提取对象名称"""
    debug_print(f"尝试获取对象名称，响应: {response}")
    
    # 如果响应是字符串，尝试解析为JSON
    if isinstance(response, str):
        try:
            response = json.loads(response)
            debug_print(f"将字符串响应解析为JSON: {response}")
        except:
            debug_print(f"无法解析字符串响应为JSON: {response}")
            return None
    
    # 检查常见的响应格式
    if isinstance(response, dict):
        # 检查标准成功响应格式
        if "status" in response and response["status"] == "success" and "result" in response:
            result = response["result"]
            if isinstance(result, dict) and "name" in result:
                debug_print(f"从标准响应格式中提取名称: {result['name']}")
                return result["name"]
        
        # 检查直接格式
        if "name" in response:
            debug_print(f"从响应中直接获取名称: {response['name']}")
            return response["name"]
        
        # 检查其他可能的字段
        for field in ["object_name", "objName", "objectName"]:
            if field in response:
                debug_print(f"从字段 {field} 中获取名称: {response[field]}")
                return response[field]
        
        # 输出响应的所有键，用于调试
        debug_print(f"响应中的所有键: {list(response.keys())}")
        
        # 检查是否有错误
        if "error" in response:
            print(f"响应包含错误: {response['error']}")
        elif "status" in response and response["status"] == "error":
            print(f"响应状态为错误: {response.get('message', 'No error message')}")
    
    print(f"无法从响应中提取对象名称: {response}")
    return None

class SimpleBlenderClient:
    """简单的Blender客户端，直接使用socket通信"""
    def __init__(self, host='localhost', port=9876):
        self.host = host
        self.port = port
        self.socket = None
        self.connect()
    
    def connect(self):
        """连接到Blender服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print(f"已连接到BlenderMCP服务器 {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"连接到服务器失败: {str(e)}")
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
            if not self.connect():
                return {"status": "error", "message": "未连接到服务器"}
        
        cmd = {
            "type": command_type,
            "params": params or {}
        }
        
        try:
            # 发送命令
            cmd_json = json.dumps(cmd)
            self.socket.sendall(cmd_json.encode('utf-8'))
            
            # 接收响应
            data = self.socket.recv(65536)  # 增大缓冲区大小
            response = json.loads(data.decode('utf-8'))
            return response
        except Exception as e:
            print(f"发送命令错误: {str(e)}")
            # 尝试重新连接
            self.disconnect()
            if self.connect():
                return self.send_command(command_type, params)
            return {"status": "error", "message": str(e)}

def test_material_application(client):
    """测试材质应用并验证合并后的保留"""
    try:
        # 检查连接状态
        print("\n=== 检查服务器连接 ===")
        ping_response = client.send_command("ping")
        debug_print(f"Ping响应: {ping_response}")
        if not check_response(ping_response, "服务器连接检查"):
            print("服务器未连接，请确保Blender中的MCP服务器已启动")
            return False
        
        # 尝试清空场景，如果此命令不可用则忽略
        print("\n=== 尝试清空场景 ===")
        try:
            result = client.send_command("clear_scene")
            print(f"清空场景结果: {result}")
        except Exception as e:
            print(f"清空场景失败(忽略此错误): {str(e)}")
            # 尝试使用execute_code删除所有对象
            delete_code = "for obj in bpy.data.objects: bpy.data.objects.remove(obj)"
            client.send_command("execute_code", {"code": delete_code})
            print("已尝试使用execute_code清空场景")
        
        # 创建白色立方体
        print("\n=== 创建白色立方体 ===")
        white_cube_response = client.send_command("create_object", {
            "type": "CUBE", 
            "name": "white_cube", 
            "location": [1, 0, 0]
        })
        debug_print(f"白色立方体响应: {white_cube_response}")
        white_cube = get_object_name(white_cube_response)
        print(f"白色立方体名称: {white_cube}")
        if not white_cube:
            print("警告: 无法获取白色立方体的名称，使用默认值")
            white_cube = "white_cube"
        
        # 创建黑色立方体
        print("\n=== 创建黑色立方体 ===")
        black_cube_response = client.send_command("create_object", {
            "type": "CUBE", 
            "name": "black_cube", 
            "location": [-1, 0, 0]
        })
        debug_print(f"黑色立方体响应: {black_cube_response}")
        black_cube = get_object_name(black_cube_response)
        print(f"黑色立方体名称: {black_cube}")
        if not black_cube:
            print("警告: 无法获取黑色立方体的名称，使用默认值")
            black_cube = "black_cube"
        
        # 创建白色材质
        print("\n=== 应用白色材质 ===")
        white_material_response = client.send_command("set_material", {
            "object_name": white_cube,
            "material_name": "white_material",
            "color": [0.95, 0.95, 0.95]
        })
        print(f"白色材质应用结果: {white_material_response}")
        
        # 创建黑色材质
        print("\n=== 应用黑色材质 ===")
        black_material_response = client.send_command("set_material", {
            "object_name": black_cube,
            "material_name": "black_material",
            "color": [0.02, 0.02, 0.02]
        })
        print(f"黑色材质应用结果: {black_material_response}")
        
        # 添加第三个对象用于测试
        print("\n=== 创建测试立方体 ===")
        test_cube_response = client.send_command("create_object", {
            "type": "CUBE", 
            "name": "test_cube", 
            "location": [0, 1, 0]
        })
        debug_print(f"测试立方体响应: {test_cube_response}")
        test_cube = get_object_name(test_cube_response)
        print(f"测试立方体名称: {test_cube}")
        if not test_cube:
            print("警告: 无法获取测试立方体的名称，使用默认值")
            test_cube = "test_cube"
        
        # 给测试立方体应用红色材质
        print("\n=== 应用红色材质 ===")
        red_material_response = client.send_command("set_material", {
            "object_name": test_cube,
            "material_name": "red_material",
            "color": [0.8, 0.1, 0.1]
        })
        print(f"红色材质应用结果: {red_material_response}")
        
        # 合并操作前检查所有对象的材质
        print("\n=== 合并前验证材质 ===")
        objects_to_check = [white_cube, black_cube, test_cube]
        
        for obj_name in objects_to_check:
            print(f"获取对象信息: {obj_name}")
            try:
                # 使用send_command获取对象信息
                debug_print(f"使用send_command获取对象信息: {obj_name}")
                obj_info = client.send_command("get_object_info", {"object_name": obj_name})
                print(f"对象 {obj_name} 信息: {obj_info}")
            except Exception as e:
                print(f"获取对象 {obj_name} 信息时出错: {str(e)}")
                traceback.print_exc()
        
        # 测试合并操作：黑色立方体作为目标（保留黑色材质）
        print("\n=== 测试合并 - 保留黑色材质 ===")
        merge_result_black = client.send_command("join_objects", {
            "objects": [black_cube, white_cube],
            "target_object": black_cube
        })
        print(f"合并到黑色对象结果: {merge_result_black}")
        
        # 获取合并后的黑色对象信息
        print("\n=== 验证黑色合并结果 ===")
        try:
            merged_black_info = client.send_command("get_object_info", {"object_name": black_cube})
            print(f"合并后的黑色对象信息: {merged_black_info}")
        except Exception as e:
            print(f"获取合并对象信息时出错: {str(e)}")
            traceback.print_exc()
        
        # 测试另一组合并：白色作为目标
        print("\n=== 创建新对象用于第二次测试 ===")
        white_cube2_response = client.send_command("create_object", {
            "type": "CUBE", 
            "name": "white_cube2", 
            "location": [3, 0, 0]
        })
        white_cube2 = get_object_name(white_cube2_response)
        print(f"第二个白色立方体名称: {white_cube2}")
        if not white_cube2:
            print("警告: 无法获取第二个白色立方体的名称，使用默认值")
            white_cube2 = "white_cube2"
        
        black_cube2_response = client.send_command("create_object", {
            "type": "CUBE", 
            "name": "black_cube2", 
            "location": [5, 0, 0]
        })
        black_cube2 = get_object_name(black_cube2_response)
        print(f"第二个黑色立方体名称: {black_cube2}")
        if not black_cube2:
            print("警告: 无法获取第二个黑色立方体的名称，使用默认值")
            black_cube2 = "black_cube2"
        
        # 应用材质到新对象
        print("\n=== 应用材质到第二组对象 ===")
        client.send_command("set_material", {
            "object_name": white_cube2,
            "material_name": "white_material2",
            "color": [0.95, 0.95, 0.95]
        })
        
        client.send_command("set_material", {
            "object_name": black_cube2,
            "material_name": "black_material2",
            "color": [0.02, 0.02, 0.02]
        })
        
        # 合并操作：白色立方体作为目标（保留白色材质）
        print("\n=== 测试合并 - 保留白色材质 ===")
        merge_result_white = client.send_command("join_objects", {
            "objects": [white_cube2, black_cube2],
            "target_object": white_cube2
        })
        print(f"合并到白色对象结果: {merge_result_white}")
        
        # 获取合并后的白色对象信息
        print("\n=== 验证白色合并结果 ===")
        try:
            merged_white_info = client.send_command("get_object_info", {"object_name": white_cube2})
            print(f"合并后的白色对象信息: {merged_white_info}")
        except Exception as e:
            print(f"获取合并对象信息时出错: {str(e)}")
            traceback.print_exc()
        
        # 最后测试与红色对象的合并
        print("\n=== 测试与红色对象合并 ===")
        merge_result_red = client.send_command("join_objects", {
            "objects": [test_cube, black_cube],
            "target_object": test_cube
        })
        print(f"合并到红色对象结果: {merge_result_red}")
        
        # 获取合并后的红色对象信息
        print("\n=== 验证红色合并结果 ===")
        try:
            merged_red_info = client.send_command("get_object_info", {"object_name": test_cube})
            print(f"合并后的红色对象信息: {merged_red_info}")
        except Exception as e:
            print(f"获取合并对象信息时出错: {str(e)}")
            traceback.print_exc()
        
        print("\n=== 材质测试完成 ===")
        return True
        
    except Exception as e:
        print(f"测试过程中出错: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """主函数：运行测试"""
    # 创建自定义的简单客户端而不是使用BlenderMCPClient
    client = SimpleBlenderClient(host="localhost", port=9876)
    print(f"连接到BlenderMCP服务器: localhost:9876")
    
    try:
        # 运行材质测试
        success = test_material_application(client)
        
        # 输出结果
        if success:
            print("\n✅ 材质测试完成，请检查Blender视图以验证材质是否正确保留")
        else:
            print("\n❌ 材质测试失败，请检查错误信息")
        
    except Exception as e:
        print(f"运行测试时出错: {str(e)}")
        traceback.print_exc()
    finally:
        # 关闭客户端连接
        client.disconnect()
        print("已关闭客户端连接")

if __name__ == "__main__":
    main() 
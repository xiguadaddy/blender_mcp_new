#!/usr/bin/env python3
"""
BlenderMCP 测试脚本 - 测试join_objects功能
"""

import sys
import os
import json
import traceback

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.blender_mcp.client import BlenderMCPClient

# 启用调试模式
DEBUG = True

def debug_print(message):
    """打印调试信息"""
    if DEBUG:
        print(f"[调试] {message}")

def check_response(response, operation_name):
    """检查响应状态，如有错误则打印"""
    if not response:
        print(f"警告: {operation_name} - 响应为空")
        return False
    
    if "error" in response:
        print(f"错误: {operation_name} - {response['error']}")
        return False
    
    if "status" in response and response["status"] == "error":
        print(f"错误: {operation_name} - {response.get('message', '未知错误')}")
        return False
    
    debug_print(f"{operation_name} - 成功")
    return True

def get_object_name(response):
    """从响应中获取对象名称，处理不同的响应格式"""
    if response and "result" in response and isinstance(response["result"], dict) and "name" in response["result"]:
        return response["result"]["name"]
    elif response and "name" in response:
        return response["name"]
    elif response and "status" == "success" and "result" in response and "name" in response["result"]:
        return response["result"]["name"]
    else:
        print(f"警告: 无法从响应中获取对象名称: {json.dumps(response, ensure_ascii=False)[:100]}")
        return None

def main():
    client = BlenderMCPClient()
    
    try:
        # 连接到服务器
        if not client.connect():
            print("无法连接到BlenderMCP服务器。请确保Blender已启动并激活了BlenderMCP插件。")
            return
        
        # 测试服务器连接
        ping_response = client.ping()
        debug_print(f"服务器ping响应: {json.dumps(ping_response, ensure_ascii=False)}")
        
        # 创建第一个立方体
        debug_print("创建第一个立方体...")
        cube1_response = client.create_object("CUBE", name="Cube1", location=[0, 0, 0])
        debug_print(f"Cube1响应: {json.dumps(cube1_response, ensure_ascii=False)}")
        
        # 使用辅助方法获取名称
        cube1_name = client.get_object_name(cube1_response)
        if not cube1_name:
            print("错误：无法获取Cube1名称。服务器响应:", json.dumps(cube1_response, ensure_ascii=False))
            return
        
        debug_print(f"Cube1名称: {cube1_name}")
        
        # 为立方体设置红色材质
        debug_print(f"为{cube1_name}设置红色材质...")
        material_response = client.set_material(cube1_name, color=[1.0, 0.0, 0.0])
        debug_print(f"设置材质响应: {json.dumps(material_response, ensure_ascii=False)}")
        
        # 创建第二个立方体
        debug_print("创建第二个立方体...")
        cube2_response = client.create_object("CUBE", name="Cube2", location=[2, 0, 0])
        debug_print(f"Cube2响应: {json.dumps(cube2_response, ensure_ascii=False)}")
        cube2_name = client.get_object_name(cube2_response)
        if not cube2_name:
            print("错误：无法获取Cube2名称。服务器响应:", json.dumps(cube2_response, ensure_ascii=False))
            return
        
        debug_print(f"Cube2名称: {cube2_name}")
        
        # 为第二个立方体设置绿色材质
        debug_print(f"为{cube2_name}设置绿色材质...")
        client.set_material(cube2_name, color=[0.0, 1.0, 0.0])
        
        # 创建一个球体
        debug_print("创建球体...")
        sphere_response = client.create_object("SPHERE", name="Sphere", location=[1, 1, 0])
        debug_print(f"球体响应: {json.dumps(sphere_response, ensure_ascii=False)}")
        sphere_name = client.get_object_name(sphere_response)
        if not sphere_name:
            print("错误：无法获取Sphere名称。服务器响应:", json.dumps(sphere_response, ensure_ascii=False))
            return
        
        debug_print(f"Sphere名称: {sphere_name}")
        
        # 为球体设置蓝色材质
        debug_print(f"为{sphere_name}设置蓝色材质...")
        client.set_material(sphere_name, color=[0.0, 0.0, 1.0])
        
        # 合并对象
        debug_print(f"合并对象 {cube1_name}, {cube2_name}, {sphere_name}...")
        join_response = client.join_objects(
            objects=[cube1_name, cube2_name, sphere_name],
            target_object=cube1_name
        )
        
        debug_print(f"合并响应: {json.dumps(join_response, ensure_ascii=False)}")
        
        if "status" in join_response and join_response["status"] == "success":
            print("成功合并对象！")
            
            # 检查目标对象是否存在
            check_response = client.send_command("get_object_info", {"name": cube1_name})
            if "status" in check_response and check_response["status"] == "success":
                print(f"合并后的对象信息: {json.dumps(check_response['result'], ensure_ascii=False)}")
            else:
                print(f"警告：无法获取合并后的对象信息。响应: {json.dumps(check_response, ensure_ascii=False)}")
        else:
            print(f"合并对象失败! 错误: {join_response.get('message', '未知错误')}")
            
            # 检查对象是否仍然存在
            print("\n检查各个对象是否仍然存在:")
            for name in [cube1_name, cube2_name, sphere_name]:
                obj_info = client.send_command("get_object_info", {"name": name})
                if isinstance(obj_info, dict) and obj_info.get("status") == "success":
                    print(f"  - {name}: 存在")
                else:
                    print(f"  - {name}: 不存在")
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
        traceback.print_exc()
    finally:
        # 断开连接
        client.disconnect()

if __name__ == "__main__":
    main() 
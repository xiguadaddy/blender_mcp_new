#!/usr/bin/env python3
"""
BlenderMCP 测试脚本 - 测试advanced_lighting功能
"""

import sys
import os
import json
import traceback

# 确保可以导入客户端类
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.blender_mcp.client import BlenderMCPClient

# 设置调试级别
DEBUG = True

def debug_print(message):
    """调试信息输出函数"""
    if DEBUG:
        print(f"[DEBUG] {message}")

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

# 创建客户端
client = BlenderMCPClient()
if not client.connect():
    print("无法连接到BlenderMCP服务器")
    sys.exit(1)

try:
    print("开始测试advanced_lighting功能...")
    
    # 测试服务器连接
    ping_response = client.ping()
    if not check_response(ping_response, "测试服务器连接"):
        raise Exception("服务器ping测试失败，请检查连接")
    else:
        print("服务器连接正常，继续执行...")
    
    # 清除现有场景
    scene_info = client.get_scene_info()
    if "result" in scene_info and "objects" in scene_info["result"]:
        for obj in scene_info["result"]["objects"]:
            if "Light" in obj["name"]:  # 只删除灯光对象
                client.delete_object(obj["name"])
                debug_print(f"删除灯光对象: {obj['name']}")
    
    # 创建一个简单场景
    print("\n1. 创建测试场景...")
    cube = client.create_object("CUBE", name="TestCube", location=[0, 0, 0])
    if not check_response(cube, "创建测试立方体"):
        raise Exception("无法创建测试场景")
    
    plane = client.create_object("PLANE", name="TestPlane", location=[0, 0, -1], scale=[5, 5, 1])
    if not check_response(plane, "创建测试平面"):
        print("警告：无法创建测试平面，但将继续测试")
    
    # 设置材质
    client.set_material(cube["result"]["name"], color=[0.8, 0.8, 0.8])
    client.set_material(plane["result"]["name"], color=[0.5, 0.5, 0.5])
    
    # 测试各种灯光类型
    print("\n2. 测试各种灯光类型...")
    
    # 测试点光源
    print("\n测试点光源...")
    point_light = client.send_command("advanced_lighting", {
        "light_type": "POINT",
        "name": "TestPointLight",
        "location": [3, 0, 3],
        "energy": 1000,
        "color": [1, 1, 1]
    })
    
    if check_response(point_light, "创建点光源"):
        print(f"点光源创建成功: {json.dumps(point_light, ensure_ascii=False)}")
    else:
        print("点光源创建失败，但将继续测试")
    
    # 测试太阳光
    print("\n测试太阳光...")
    sun_light = client.send_command("advanced_lighting", {
        "light_type": "SUN",
        "name": "TestSunLight",
        "location": [5, 5, 10],
        "energy": 1.0,
        "color": [1, 0.9, 0.8]
    })
    
    if check_response(sun_light, "创建太阳光"):
        print(f"太阳光创建成功: {json.dumps(sun_light, ensure_ascii=False)}")
    else:
        error_msg = sun_light.get("error", "未知错误")
        print(f"太阳光创建失败: {error_msg}")
        
        # 检查是否缺少radians函数
        if "radians" in error_msg:
            print("可能是由于缺少radians函数，请检查addon.py是否正确导入math.radians")
    
    # 测试区域光
    print("\n测试区域光...")
    area_light = client.send_command("advanced_lighting", {
        "light_type": "AREA",
        "name": "TestAreaLight",
        "location": [-5, -5, 5],
        "energy": 100,
        "color": [0.8, 0.9, 1.0]
    })
    
    if check_response(area_light, "创建区域光"):
        print(f"区域光创建成功: {json.dumps(area_light, ensure_ascii=False)}")
    else:
        error_msg = area_light.get("error", "未知错误")
        print(f"区域光创建失败: {error_msg}")
    
    # 测试聚光灯
    print("\n测试聚光灯...")
    spot_light = client.send_command("advanced_lighting", {
        "light_type": "SPOT",
        "name": "TestSpotLight",
        "location": [0, -5, 5],
        "energy": 500,
        "color": [1.0, 0.8, 0.8]
    })
    
    if check_response(spot_light, "创建聚光灯"):
        print(f"聚光灯创建成功: {json.dumps(spot_light, ensure_ascii=False)}")
    else:
        error_msg = spot_light.get("error", "未知错误")
        print(f"聚光灯创建失败: {error_msg}")
    
    # 获取场景信息，验证灯光是否创建成功
    print("\n3. 验证灯光创建结果...")
    scene_info_after = client.get_scene_info()
    if "result" in scene_info_after and "objects" in scene_info_after["result"]:
        light_objects = [obj for obj in scene_info_after["result"]["objects"] if "Light" in obj["name"]]
        print(f"场景中有 {len(light_objects)} 个灯光对象:")
        for light in light_objects:
            print(f"  - {light['name']} (类型: {light.get('type', '未知')})")
    
    # 渲染测试
    print("\n4. 渲染测试场景...")
    render_response = client.send_command("render_scene", {
        "resolution_x": 800,
        "resolution_y": 600
    })
    
    if check_response(render_response, "渲染场景"):
        print("渲染成功，请检查Blender中的结果")
    else:
        print("渲染失败")
    
    print("\n测试完成！")

except Exception as e:
    print(f"测试过程中发生错误: {str(e)}")
    traceback.print_exc()
finally:
    print("断开与服务器的连接...")
    client.disconnect() 
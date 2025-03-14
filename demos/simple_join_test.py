import sys
import os
import traceback
import time
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.blender_mcp.client import BlenderMCPClient

# 启用调试模式
DEBUG = True

def debug_print(message):
    """打印调试信息"""
    if DEBUG:
        print(f"[调试] {message}")

def get_object_name(response):
    """从响应中获取对象名称，处理不同的响应格式"""
    if response is None:
        debug_print("警告: 响应为None")
        return None
        
    debug_print(f"响应类型: {type(response)}, 内容: {json.dumps(response, ensure_ascii=False)[:100]}")
    
    if isinstance(response, dict):
        if "status" in response and response["status"] == "error":
            debug_print(f"错误响应: {response.get('message', '未知错误')}")
            return None
            
        if "result" in response and isinstance(response["result"], dict):
            if "name" in response["result"]:
                return response["result"]["name"]
            if "object" in response["result"]:
                return response["result"]["object"]
                
        if "name" in response:
            return response["name"]
    
    debug_print(f"无法从响应中提取对象名称: {json.dumps(response, ensure_ascii=False)[:100]}")
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
        debug_print(f"服务器Ping响应: {ping_response}")
        
        # 清除现有场景
        debug_print("清除现有场景...")
        scene_info = client.get_scene_info()
        if "result" in scene_info and "objects" in scene_info["result"]:
            for obj in scene_info["result"]["objects"]:
                if obj.get("name") != "Camera":  # 保留相机
                    client.delete_object(obj["name"])
        
        # 基本步骤
        # 1. 创建简单对象
        print("\n第1步: 创建简单对象")
        
        # 创建立方体
        cube_response = client.create_object("CUBE", name="SimpleCube", location=[0, 0, 0])
        debug_print(f"立方体响应: {json.dumps(cube_response, ensure_ascii=False)}")
        
        # 获取立方体名称
        cube_name = get_object_name(cube_response)
        if not cube_name:
            # 创建失败，重试一次
            print("注意: 立方体创建失败，尝试重新创建...")
            time.sleep(0.5)  # 等待一段时间
            cube_response = client.create_object("CUBE", name="SimpleCube", location=[0, 0, 0])
            debug_print(f"重试立方体响应: {json.dumps(cube_response, ensure_ascii=False)}")
            cube_name = get_object_name(cube_response)
            
            if not cube_name:
                print("错误: 立方体创建失败，无法继续测试")
                return
        
        # 验证对象是否真的存在
        verify_response = client.send_command("get_object_info", {"name": cube_name})
        if "status" not in verify_response or verify_response["status"] != "success":
            print(f"错误: 立方体 {cube_name} 不存在于场景中，无法继续测试")
            return
            
        print(f"成功创建立方体: {cube_name}")
        
        # 创建球体 (添加验证)
        sphere_response = client.create_object("SPHERE", name="SimpleSphere", location=[2, 0, 0])
        debug_print(f"球体响应: {json.dumps(sphere_response, ensure_ascii=False)}")
        sphere_name = get_object_name(sphere_response)
        if not sphere_name:
            print("错误: 球体创建失败，无法继续测试")
            return
            
        # 验证球体存在
        verify_response = client.send_command("get_object_info", {"name": sphere_name})
        if "status" not in verify_response or verify_response["status"] != "success":
            print(f"错误: 球体 {sphere_name} 不存在于场景中，无法继续测试")
            return
            
        print(f"成功创建球体: {sphere_name}")
        
        # 创建圆柱体 (添加验证)
        cylinder_response = client.create_object("CYLINDER", name="SimpleCylinder", location=[0, 2, 0])
        debug_print(f"圆柱体响应: {json.dumps(cylinder_response, ensure_ascii=False)}")
        cylinder_name = get_object_name(cylinder_response)
        if not cylinder_name:
            print("错误: 圆柱体创建失败，无法继续测试")
            return
            
        # 验证圆柱体存在
        verify_response = client.send_command("get_object_info", {"name": cylinder_name})
        if "status" not in verify_response or verify_response["status"] != "success":
            print(f"错误: 圆柱体 {cylinder_name} 不存在于场景中，无法继续测试")
            return
            
        print(f"成功创建圆柱体: {cylinder_name}")
        
        # 2. 设置材质
        print("\n第2步: 设置材质")
        client.set_material(cube_name, color=[1, 0, 0])
        client.set_material(sphere_name, color=[0, 1, 0])
        client.set_material(cylinder_name, color=[0, 0, 1])
        print("已应用材质")
        
        # 3. 合并对象
        print("\n第3步: 合并对象")
        print(f"尝试合并: {cube_name}, {sphere_name}, {cylinder_name}")
        join_response = client.join_objects(
            objects=[cube_name, sphere_name, cylinder_name],
            target_object=cube_name
        )
        
        debug_print(f"合并响应: {json.dumps(join_response, ensure_ascii=False)}")
        
        if isinstance(join_response, dict) and join_response.get("status") == "success":
            print("合并对象成功!")
            
            # 验证场景中的对象
            scene_after = client.get_scene_info()
            if "result" in scene_after and "objects" in scene_after["result"]:
                objects = scene_after["result"]["objects"]
                print(f"合并后场景中有 {len(objects)} 个对象")
                
                for obj in objects:
                    if obj.get("name") != "Camera":
                        print(f"  - {obj.get('name')}")
        else:
            print(f"合并对象失败! 错误: {join_response.get('message', '未知错误')}")
            
            # 检查对象是否仍然存在
            print("\n检查各个对象是否仍然存在:")
            for name in [cube_name, sphere_name, cylinder_name]:
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
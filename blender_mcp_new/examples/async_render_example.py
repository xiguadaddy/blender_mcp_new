#!/usr/bin/env python3
"""
BlenderMCP 异步渲染示例脚本
演示如何使用BlenderMCP API的异步渲染功能
"""

import sys
import os
import json
import time
import traceback

# 导入客户端模块，以支持在任何环境下运行
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from blender_mcp_new import BlenderMCPClient

# 设置调试级别
DEBUG = True  # 可以控制是否输出详细日志

def debug_print(message):
    """调试信息输出函数"""
    if DEBUG:
        print(f"[DEBUG] {message}")

def check_response(response, operation_name):
    """检查响应状态，如有错误则打印"""
    if not response:
        print(f"警告: {operation_name} - 响应为空")
        return False
    
    if "status" in response and response["status"] == "error":
        print(f"错误: {operation_name} - {response.get('message', '未知错误')}")
        return False
    
    debug_print(f"{operation_name} - 成功")
    return True

def safe_operation(client, func, *args, operation_name="操作", **kwargs):
    """安全执行操作，包括延迟和错误处理"""
    try:
        debug_print(f"执行 {operation_name}...")
        
        # 在操作前短暂延迟，让Blender有时间处理前一个操作
        time.sleep(0.05)
        
        # 执行操作
        result = func(*args, **kwargs)
        
        # 检查结果并打印信息
        if check_response(result, operation_name):
            time.sleep(0.05)  # 操作成功后再短暂延迟
            return result
        else:
            # 如果操作失败，暂停更长时间
            time.sleep(0.1)
            return None
    except Exception as e:
        print(f"执行 {operation_name} 时出错: {str(e)}")
        traceback.print_exc()
        time.sleep(0.2)  # 出错后暂停更长时间
        return None

def create_simple_scene(client):
    """创建一个简单的场景用于渲染测试"""
    try:
        # 清除现有场景
        debug_print("清除现有场景...")
        clear_response = safe_operation(client, client.clear_scene, operation_name="清空场景")
        if not check_response(clear_response, "清空场景"):
            print("注意: 清空场景可能失败，尝试继续...")
            time.sleep(0.5)
        
        # 创建一个平面作为地面
        debug_print("创建地面...")
        ground_response = safe_operation(client, client.create_object, "PLANE", name="地面", 
                                        location=[0, 0, 0], scale=[5, 5, 1],
                                        operation_name="创建地面")
        
        # 设置地面材质
        ground_name = ground_response.get("result", {}).get("name", "地面")
        safe_operation(client, client.set_material, ground_name, color=[0.8, 0.8, 0.8],
                      operation_name="设置地面材质")
        
        # 创建一个立方体
        debug_print("创建立方体...")
        cube_response = safe_operation(client, client.create_object, "CUBE", name="立方体", 
                                      location=[0, 0, 1], scale=[1, 1, 1],
                                      operation_name="创建立方体")
        
        # 设置立方体材质
        cube_name = cube_response.get("result", {}).get("name", "立方体")
        safe_operation(client, client.set_material, cube_name, color=[0.8, 0.2, 0.2],
                      operation_name="设置立方体材质")
        
        # 创建一个球体
        debug_print("创建球体...")
        sphere_response = safe_operation(client, client.create_object, "SPHERE", name="球体", 
                                        location=[2, 2, 1], scale=[1, 1, 1],
                                        operation_name="创建球体")
        
        # 设置球体材质
        sphere_name = sphere_response.get("result", {}).get("name", "球体")
        safe_operation(client, client.set_material, sphere_name, color=[0.2, 0.2, 0.8],
                      operation_name="设置球体材质")
        
        # 添加灯光
        debug_print("添加灯光...")
        light_response = safe_operation(client, client.create_object, "LIGHT", name="灯光", 
                                       location=[4, 1, 5],
                                       operation_name="创建灯光")
        
        light_name = light_response.get("result", {}).get("name", "灯光")
        safe_operation(client, client.set_light_type, light_name, "SUN",
                      operation_name="设置灯光类型")
        safe_operation(client, client.set_light_energy, light_name, 2.0,
                      operation_name="设置灯光强度")
        
        # 设置相机
        debug_print("设置相机...")
        camera_response = safe_operation(client, client.create_object, "CAMERA", name="相机", 
                                        location=[5, -5, 3],
                                        operation_name="创建相机")
        
        camera_name = camera_response.get("result", {}).get("name", "相机")
        safe_operation(client, client.modify_object, camera_name, 
                      rotation=[0.6, 0, 0.8],
                      operation_name="调整相机角度")
        
        safe_operation(client, client.set_active_camera, camera_name,
                      operation_name="设置活动相机")
        
        print("简单场景创建完成！")
        return True
        
    except Exception as e:
        print(f"创建场景时发生错误: {str(e)}")
        traceback.print_exc()
        return False

def test_async_render():
    """测试异步渲染功能"""
    # 创建客户端
    client = BlenderMCPClient(debug=DEBUG)
    if not client.connect():
        print("无法连接到BlenderMCP服务器")
        sys.exit(1)
        
    try:
        # 测试服务器连接
        ping_response = client.ping()
        debug_print(f"服务器Ping响应: {json.dumps(ping_response, ensure_ascii=False) if isinstance(ping_response, dict) else ping_response}")
        
        # 创建一个简单场景
        if not create_simple_scene(client):
            print("创建场景失败，无法继续测试")
            return
        
        # 开始异步渲染
        debug_print("开始异步渲染...")
        render_response = safe_operation(client, client.render_scene_async, 
                                        resolution_x=1920, 
                                        resolution_y=1080, 
                                        output_path="//async_render.png",
                                        operation_name="异步渲染场景")
        
        if not check_response(render_response, "异步渲染"):
            print("启动异步渲染失败")
            return
        
        # 获取任务ID
        task_id = render_response.get("result", {}).get("task_id")
        if not task_id:
            print("无法获取渲染任务ID")
            return
        
        print(f"渲染任务已启动，任务ID: {task_id}")
        
        # 轮询任务状态
        completed = False
        while not completed:
            # 获取任务状态
            task_response = safe_operation(client, client.get_task, task_id,
                                         operation_name="获取任务状态")
            
            if not check_response(task_response, "获取任务状态"):
                print("获取任务状态失败")
                break
            
            # 解析任务状态
            task_status = task_response.get("result", {}).get("status")
            task_progress = task_response.get("result", {}).get("progress", 0)
            
            print(f"任务状态: {task_status}, 进度: {task_progress:.1f}%")
            
            # 检查任务是否完成
            if task_status == "completed":
                completed = True
                print("渲染任务已完成！")
                
                # 获取详细任务信息
                detail_response = safe_operation(client, client.get_task_detailed, task_id,
                                              operation_name="获取详细任务信息")
                
                if check_response(detail_response, "获取详细任务信息"):
                    result = detail_response.get("result", {}).get("result", {})
                    print(f"渲染结果: {result}")
                
            elif task_status == "failed":
                print("渲染任务失败！")
                
                # 获取详细任务信息以查看错误
                detail_response = safe_operation(client, client.get_task_detailed, task_id,
                                              operation_name="获取详细任务信息")
                
                if check_response(detail_response, "获取详细任务信息"):
                    error = detail_response.get("result", {}).get("error", "未知错误")
                    print(f"错误信息: {error}")
                
                break
            
            # 等待一段时间再检查
            time.sleep(1)
        
        # 列出所有任务
        debug_print("列出所有任务...")
        tasks_response = safe_operation(client, client.list_tasks,
                                      operation_name="列出所有任务")
        
        if check_response(tasks_response, "列出所有任务"):
            tasks = tasks_response.get("result", {}).get("tasks", [])
            print(f"当前任务列表 ({len(tasks)} 个任务):")
            for task in tasks:
                print(f"  - 任务ID: {task.get('task_id')}, 状态: {task.get('status')}, 进度: {task.get('progress')}%")
        
        print("异步渲染测试完成！")
        
    except Exception as e:
        print(f"测试异步渲染时发生错误: {str(e)}")
        traceback.print_exc()
    finally:
        # 确保断开连接
        client.disconnect()

if __name__ == "__main__":
    test_async_render() 
#!/usr/bin/env python3
"""
测试MCP-Blender通信
该脚本测试与Blender MCP服务器的通信，检查是否能获取工具列表和资源列表
"""

import socket
import json
import sys
import os
import time

SOCKET_PATH = "/tmp/blender-mcp.sock"

def send_request(action, **params):
    """发送请求到MCP服务器"""
    print(f"\n===== 发送 {action} 请求 =====")
    
    # 检查套接字文件是否存在
    if not os.path.exists(SOCKET_PATH):
        print(f"错误: 套接字文件不存在: {SOCKET_PATH}")
        return None
        
    try:
        # 创建套接字连接
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.connect(SOCKET_PATH)
        print(f"已连接到MCP服务器: {SOCKET_PATH}")
        
        # 构建请求数据
        request = {"action": action, **params}
        request_data = json.dumps(request)
        
        # 添加长度前缀并发送
        message = f"{len(request_data)}:{request_data}".encode()
        client.sendall(message)
        print(f"已发送请求: {action}")
        
        # 读取响应头
        header = b""
        while b":" not in header:
            chunk = client.recv(1)
            if not chunk:
                print("错误: 连接关闭，无法读取响应头")
                return None
            header += chunk
            
        # 解析响应长度
        length = int(header.decode().split(":")[0])
        
        # 读取响应内容
        data = b""
        while len(data) < length:
            chunk = client.recv(min(4096, length - len(data)))
            if not chunk:
                print("错误: 连接关闭，无法读取完整响应")
                return None
            data += chunk
            
        # 解析响应
        response = json.loads(data.decode())
        print(f"收到响应 ({len(data)} 字节)")
        
        return response
        
    except Exception as e:
        print(f"发送请求时出错: {str(e)}")
        return None
        
    finally:
        try:
            client.close()
        except:
            pass

def test_list_tools():
    """测试获取工具列表"""
    print("\n----- 测试获取工具列表 -----")
    
    response = send_request("list_tools")
    
    if response is None:
        print("无法获取工具列表")
        return
        
    if "error" in response:
        print(f"获取工具列表出错: {response['error']}")
        return
        
    tools_count = len(response)
    print(f"获取到 {tools_count} 个工具:")
    
    for i, tool in enumerate(response, 1):
        print(f"{i}. {tool['name']} - {tool.get('description', '无描述')}")
        
    return response

def test_list_resources():
    """测试获取资源列表"""
    print("\n----- 测试获取资源列表 -----")
    
    response = send_request("list_resources")
    
    if response is None:
        print("无法获取资源列表")
        return
        
    if "error" in response:
        print(f"获取资源列表出错: {response['error']}")
        return
        
    resources_count = len(response)
    print(f"获取到 {resources_count} 个资源:")
    
    for i, resource in enumerate(response, 1):
        print(f"{i}. [{resource['type']}] {resource.get('name', '无名称')} (ID: {resource.get('id', '无ID')})")
        
    return response

def test_create_cube():
    """测试创建立方体"""
    print("\n----- 测试创建立方体 -----")
    
    response = send_request(
        "call_tool",
        tool="create_object",
        arguments={
            "object_type": "cube",
            "location": [0, 0, 0],
            "size": 2.0,
            "name": "MCP_Test_Cube"
        }
    )
    
    if response is None:
        print("无法创建立方体")
        return
        
    if "error" in response:
        print(f"创建立方体出错: {response['error']}")
        return
        
    print(f"创建立方体成功: {json.dumps(response, indent=2)}")
    return response

def main():
    """主函数"""
    print("=== MCP-Blender通信测试 ===")
    
    # 尝试获取工具列表
    tools = test_list_tools()
    
    # 尝试获取资源列表
    resources = test_list_resources()
    
    # 如果工具可用，尝试创建立方体
    if tools is not None and any(t["name"] == "create_object" for t in tools):
        cube = test_create_cube()
        
        # 再次获取资源，查看是否包含新创建的立方体
        if cube and "status" in cube and cube["status"] == "success":
            print("\n----- 再次测试获取资源列表 -----")
            time.sleep(1)  # 稍等片刻，确保资源已更新
            test_list_resources()
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
import json
import socket
import sys
import os
import select
import time

def send_request(socket_path="/tmp/blender-mcp.sock", request=None):
    """向MCP服务器发送请求并获取响应"""
    if request is None:
        request = {}
    
    print(f"检查套接字文件: {socket_path}")
    if not os.path.exists(socket_path):
        raise FileNotFoundError(f"套接字文件不存在: {socket_path}")
    print(f"套接字文件存在")
    
    client_socket = None
    try:
        # 创建Unix域套接字连接
        print("创建套接字...")
        client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client_socket.settimeout(10)  # 设置10秒超时
        print(f"连接到套接字: {socket_path}")
        client_socket.connect(socket_path)
        print("连接成功")
        
        # 将请求转换为JSON并编码
        request_data = json.dumps(request).encode()
        print(f"请求数据: {request_data}")
        
        # 发送请求（添加长度前缀）
        prefix = f"{len(request_data)}:".encode()
        print(f"发送前缀: {prefix}")
        client_socket.sendall(prefix)
        print("前缀发送完成")
        time.sleep(0.1)  # 稍微等待，确保前缀被正确处理
        
        print(f"发送数据...")
        client_socket.sendall(request_data)
        print("数据发送完成")
        
        # 接收响应
        print("等待响应...")
        
        # 检查是否有数据可读
        ready = select.select([client_socket], [], [], 15)  # 15秒超时
        if not ready[0]:
            print("等待服务器响应超时")
            return {"error": "服务器响应超时"}
            
        # 读取前缀
        header = b""
        print("开始读取响应前缀...")
        while b":" not in header:
            ready = select.select([client_socket], [], [], 5)  # 5秒超时
            if not ready[0]:
                print("读取前缀超时")
                return {"error": "读取前缀超时"}
                
            chunk = client_socket.recv(1)
            if not chunk:
                raise ConnectionError("连接已关闭，无法接收前缀")
            header += chunk
            print(f"当前读取前缀: {header}")
            
        length = int(header.decode().split(":")[0])
        print(f"获取到响应长度: {length}")
        
        # 读取响应数据
        response_data = b""
        while len(response_data) < length:
            bytes_to_read = min(4096, length - len(response_data))
            ready = select.select([client_socket], [], [], 10)  # 10秒超时
            if not ready[0]:
                print(f"读取响应数据超时 ({len(response_data)}/{length})")
                return {"error": f"读取响应数据超时 ({len(response_data)}/{length})"}
                
            chunk = client_socket.recv(bytes_to_read)
            if not chunk:
                raise ConnectionError("连接已关闭，无法接收数据")
            response_data += chunk
            print(f"已接收 {len(response_data)}/{length} 字节")
            
        # 解析并返回响应
        print(f"原始响应: {response_data}")
        response = json.loads(response_data.decode())
        return response
    
    except socket.timeout:
        print("套接字操作超时")
        return {"error": "套接字操作超时"}
    except Exception as e:
        print(f"发送请求时出错: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
    
    finally:
        if client_socket:
            print("关闭客户端套接字")
            client_socket.close()

def list_resources():
    """获取可用资源列表"""
    print("\n===== 获取资源列表 =====")
    
    request = {
        "action": "list_resources"
    }
    
    response = send_request(request=request)
    print(f"服务器响应: {json.dumps(response, ensure_ascii=False, indent=2)}")
    if isinstance(response, list):
        print(f"发现 {len(response)} 个资源")
        for i, resource in enumerate(response):
            print(f"资源 {i+1}: 类型={resource.get('type', '未知')}, ID={resource.get('id', '未知')}")
    return response

def check_server():
    """检查服务器状态"""
    print("\n===== 检查服务器状态 =====")
    
    request = {
        "action": "ping"
    }
    
    response = send_request(request=request)
    print(f"服务器响应: {json.dumps(response, ensure_ascii=False, indent=2)}")
    return response

if __name__ == "__main__":
    try:
        # 检查服务器状态
        check_server()
        
        # 获取资源列表
        list_resources()
            
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 
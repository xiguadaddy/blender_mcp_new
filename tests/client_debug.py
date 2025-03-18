#!/usr/bin/env python3
"""
Blender IPC调试客户端
该脚本直接连接到Blender IPC服务器，用于诊断连接问题
"""

import socket
import json
import sys
import os
import time

SOCKET_PATH = "/tmp/blender-mcp.sock"

def send_raw_request(request):
    """发送原始请求到Blender IPC服务器"""
    print(f"\n===== 发送原始请求 =====")
    print(f"请求内容: {json.dumps(request, indent=2)}")
    
    # 检查套接字文件是否存在
    if not os.path.exists(SOCKET_PATH):
        print(f"错误: 套接字文件不存在: {SOCKET_PATH}")
        return None
        
    try:
        # 创建套接字连接
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.connect(SOCKET_PATH)
        print(f"已连接到Blender IPC服务器: {SOCKET_PATH}")
        
        # 序列化请求数据
        request_data = json.dumps(request)
        
        # 添加长度前缀并发送
        message = f"{len(request_data)}:{request_data}".encode()
        client.sendall(message)
        print(f"已发送数据: {len(request_data)} 字节")
        
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
        print(f"响应长度: {length} 字节")
        
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
        print(f"收到响应: {json.dumps(response, indent=2)}")
        
        return response
        
    except Exception as e:
        print(f"发送请求时出错: {str(e)}")
        return None
        
    finally:
        try:
            client.close()
        except:
            pass

def main():
    """主函数"""
    print("=== Blender IPC调试客户端 ===")
    
    try:
        # 测试操作命令和参数
        while True:
            print("\n可用操作:")
            print("1. list_resources - 获取资源列表")
            print("2. list_tools - 获取工具列表")
            print("3. call_tool - 调用工具")
            print("4. check_object_exists - 检查对象是否存在")
            print("5. read_resource - 读取资源")
            print("6. 自定义请求")
            print("0. 退出")
            
            choice = input("\n选择操作 (0-6): ").strip()
            
            if choice == "0":
                break
                
            elif choice == "1":
                # 列出资源
                send_raw_request({"action": "list_resources"})
                
            elif choice == "2":
                # 列出工具
                send_raw_request({"action": "list_tools"})
                
            elif choice == "3":
                # 调用工具
                tool_name = input("输入工具名称: ").strip()
                print("输入JSON格式的参数(例如: {\"object_type\": \"cube\"})")
                args_str = input("参数: ").strip()
                try:
                    if args_str:
                        arguments = json.loads(args_str)
                    else:
                        arguments = {}
                    send_raw_request({
                        "action": "call_tool",
                        "tool": tool_name,
                        "arguments": arguments
                    })
                except json.JSONDecodeError:
                    print("错误: 无效的JSON参数")
                    
            elif choice == "4":
                # 检查对象是否存在
                obj_name = input("输入对象名称: ").strip()
                send_raw_request({
                    "action": "check_object_exists",
                    "object_name": obj_name
                })
                
            elif choice == "5":
                # 读取资源
                res_type = input("输入资源类型: ").strip()
                res_id = input("输入资源ID: ").strip()
                send_raw_request({
                    "action": "read_resource",
                    "type": res_type,
                    "id": res_id
                })
                
            elif choice == "6":
                # 自定义请求
                print("输入JSON格式的请求(例如: {\"action\": \"custom_action\"})")
                req_str = input("请求: ").strip()
                try:
                    request = json.loads(req_str)
                    send_raw_request(request)
                except json.JSONDecodeError:
                    print("错误: 无效的JSON请求")
                    
            else:
                print("无效的选择")
                
    except KeyboardInterrupt:
        print("\n操作已取消")
    
    print("\n=== 调试结束 ===")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
BlenderMCP端口检查工具
用于检测某个端口是否被占用
"""

import socket
import sys

def check_port(host='localhost', port=9876):
    """检查端口是否可用"""
    print(f"检查端口: {host}:{port}")
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.bind((host, port))
            print(f"✅ 端口 {host}:{port} 可用")
            return True
    except socket.error as e:
        print(f"❌ 端口 {host}:{port} 不可用: {e}")
        return False

def check_multiple_configs():
    """检查多种常见配置"""
    configs = [
        ('localhost', 9876),
        ('127.0.0.1', 9876),
        ('0.0.0.0', 9876),
        ('localhost', 9877),
        ('127.0.0.1', 9877),
        ('0.0.0.0', 9877),
    ]
    
    print("开始端口检查...")
    print("="*50)
    
    available_configs = []
    for host, port in configs:
        if check_port(host, port):
            available_configs.append((host, port))
        print("-"*50)
    
    print("="*50)
    print("检查结果摘要:")
    
    if available_configs:
        print("可用配置:")
        for host, port in available_configs:
            print(f"  - {host}:{port}")
    else:
        print("❌ 没有找到可用的配置")
        print("请尝试释放端口或使用其他端口")
    
    return available_configs

if __name__ == "__main__":
    # 如果提供了命令行参数，使用它们
    if len(sys.argv) >= 3:
        host = sys.argv[1]
        port = int(sys.argv[2])
        check_port(host, port)
    else:
        # 否则检查多种配置
        check_multiple_configs() 
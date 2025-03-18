#!/usr/bin/env python3
import json
import socket
import sys
import os
import select
import time
import logging

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('blender-mcp-client')

def send_request(socket_path="/tmp/blender-mcp.sock", request=None):
    """向MCP服务器发送请求并获取响应"""
    if request is None:
        request = {}
    
    logger.info(f"检查套接字文件: {socket_path}")
    if not os.path.exists(socket_path):
        logger.error(f"套接字文件不存在: {socket_path}")
        raise FileNotFoundError(f"套接字文件不存在: {socket_path}")
    logger.info(f"套接字文件存在")
    
    client_socket = None
    try:
        # 创建Unix域套接字连接
        logger.info("创建套接字...")
        client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client_socket.settimeout(10)  # 设置10秒超时
        logger.info(f"连接到套接字: {socket_path}")
        client_socket.connect(socket_path)
        logger.info("连接成功")
        
        # 将请求转换为JSON并编码
        request_data = json.dumps(request).encode()
        logger.debug(f"请求数据: {request_data}")
        
        # 发送请求（添加长度前缀）
        prefix = f"{len(request_data)}:".encode()
        logger.debug(f"发送前缀: {prefix}")
        client_socket.sendall(prefix)
        logger.debug("前缀发送完成")
        time.sleep(0.1)  # 稍微等待，确保前缀被正确处理
        
        logger.info(f"发送数据...")
        client_socket.sendall(request_data)
        logger.info("数据发送完成")
        
        # 接收响应
        logger.info("等待响应...")
        
        # 检查是否有数据可读
        ready = select.select([client_socket], [], [], 15)  # 15秒超时
        if not ready[0]:
            logger.error("等待服务器响应超时")
            return {"error": "服务器响应超时"}
            
        # 读取前缀
        header = b""
        logger.debug("开始读取响应前缀...")
        while b":" not in header:
            ready = select.select([client_socket], [], [], 5)  # 5秒超时
            if not ready[0]:
                logger.error("读取前缀超时")
                return {"error": "读取前缀超时"}
                
            chunk = client_socket.recv(1)
            if not chunk:
                logger.error("连接已关闭，无法接收前缀")
                raise ConnectionError("连接已关闭，无法接收前缀")
            header += chunk
            logger.debug(f"当前读取前缀: {header}")
            
        length = int(header.decode().split(":")[0])
        logger.info(f"获取到响应长度: {length}")
        
        # 读取响应数据
        response_data = b""
        while len(response_data) < length:
            bytes_to_read = min(4096, length - len(response_data))
            ready = select.select([client_socket], [], [], 10)  # 10秒超时
            if not ready[0]:
                logger.error(f"读取响应数据超时 ({len(response_data)}/{length})")
                return {"error": f"读取响应数据超时 ({len(response_data)}/{length})"}
                
            chunk = client_socket.recv(bytes_to_read)
            if not chunk:
                logger.error("连接已关闭，无法接收数据")
                raise ConnectionError("连接已关闭，无法接收数据")
            response_data += chunk
            logger.debug(f"已接收 {len(response_data)}/{length} 字节")
            
        # 解析并返回响应
        logger.debug(f"原始响应: {response_data}")
        response = json.loads(response_data.decode())
        return response
    
    except socket.timeout:
        logger.error("套接字操作超时")
        return {"error": "套接字操作超时"}
    except Exception as e:
        logger.exception(f"发送请求时出错: {e}")
        return {"error": str(e)}
    
    finally:
        if client_socket:
            logger.info("关闭客户端套接字")
            client_socket.close()

def create_cube():
    """发送创建立方体的请求"""
    logger.info("\n===== 发送创建立方体请求 =====")
    
    # 使用IPC服务器支持的call_tool操作
    request = {
        "action": "call_tool",
        "tool": "create_object",
        "arguments": {
            "object_type": "cube",
            "size": 2.0,
            "name": "Test_Cube",
            "location": [0, 0, 0]
        }
    }
    
    response = send_request(request=request)
    logger.info(f"服务器响应: {json.dumps(response, ensure_ascii=False, indent=2)}")
    return response

def direct_execute_tool():
    """直接使用Blender插件的execute_tool方法"""
    logger.info("\n===== 直接执行工具 =====")
    
    # 使用直接的execute_tool操作
    request = {
        "action": "execute_tool",
        "tool_name": "create_object",
        "arguments": {
            "object_type": "cube",
            "size": 2.0,
            "name": "Direct_Test_Cube",
            "location": [0, 0, 0]
        }
    }
    
    response = send_request(request=request)
    logger.info(f"服务器响应: {json.dumps(response, ensure_ascii=False, indent=2)}")
    return response

if __name__ == "__main__":
    try:
        # 先尝试标准方法
        logger.info("尝试使用call_tool方法创建立方体")
        result = create_cube()
        
        # 如果失败，尝试直接方法
        if "error" in result:
            logger.info("call_tool方法失败，尝试直接方法")
            result = direct_execute_tool()
        
        if "error" in result:
            logger.error(f"所有方法都失败了: {result.get('error')}")
        else:
            logger.info(f"立方体创建成功，结果: {result}")
            
    except Exception as e:
        logger.exception(f"严重错误: {e}")
        sys.exit(1) 
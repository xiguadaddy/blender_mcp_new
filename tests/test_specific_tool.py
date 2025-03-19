#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Blender MCP工具测试脚本
专门测试create_object和set_material工具的功能
"""

import asyncio
import json
import logging
import socket
import sys
from typing import Dict, Any, Optional, Union

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("tool_test.log")
    ]
)

logger = logging.getLogger("BlenderMCPToolTest")

# 服务器连接配置
MCP_SERVER_HOST = "localhost"
MCP_SERVER_PORT = 8237  # 默认端口，可能需要根据实际配置调整

async def send_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    向MCP服务器发送请求并接收响应
    
    Args:
        request: 请求数据字典
    
    Returns:
        Dict[str, Any]: 服务器响应的JSON数据
    """
    # 创建新套接字连接
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        # 连接服务器
        client_socket.connect((MCP_SERVER_HOST, MCP_SERVER_PORT))
        
        # 将请求转换为JSON字符串并添加长度前缀
        request_json = json.dumps(request)
        message = f"{len(request_json)}:{request_json}"
        
        logger.info(f"发送请求: {request}")
        client_socket.sendall(message.encode('utf-8'))
        
        # 读取响应长度
        data = b''
        while b':' not in data:
            chunk = client_socket.recv(1)
            if not chunk:
                raise ConnectionError("连接断开")
            data += chunk
        
        length_str, remaining = data.split(b':', 1)
        content_length = int(length_str)
        
        # 读取完整的响应内容
        content = remaining
        while len(content) < content_length:
            chunk = client_socket.recv(min(4096, content_length - len(content)))
            if not chunk:
                raise ConnectionError("连接断开")
            content += chunk
        
        # 解析JSON响应
        response_json = json.loads(content)
        logger.info(f"收到响应: {response_json}")
        
        return response_json
    
    except Exception as e:
        logger.error(f"请求过程中出错: {str(e)}")
        raise
    
    finally:
        client_socket.close()

async def test_create_cube() -> Union[str, None]:
    """
    测试创建立方体
    
    Returns:
        Union[str, None]: 成功时返回创建的对象名称，失败时返回None
    """
    logger.info("===== 测试：创建立方体 =====")
    
    # 使用action格式的请求创建立方体
    request = {
        "action": "call_tool",
        "tool": "create_object",
        "arguments": {
            "object_type": "cube",
            "name": "TestCube",
            "location": [0, 0, 0],
            "size": 2.0
        }
    }
    
    try:
        response = await send_request(request)
        
        # 打印完整响应以便调试
        logger.info(f"完整响应: {json.dumps(response, indent=2)}")
        
        # 检查响应是否成功
        if "error" not in response:
            logger.info("✓ 成功创建立方体")
            
            # 尝试从响应中获取对象名称
            object_name = "TestCube"  # 默认名称
            
            # 检查不同可能的响应格式
            if "object_name" in response:
                object_name = response["object_name"]
            elif "result" in response and isinstance(response["result"], dict) and "object_name" in response["result"]:
                object_name = response["result"]["object_name"]
            elif "content" in response and isinstance(response["content"], list) and len(response["content"]) > 0:
                content_text = response["content"][0].get("text", "")
                if "创建了对象" in content_text:
                    logger.info(f"从内容文本中检测到对象创建: {content_text}")
            
            logger.info(f"将使用对象名称: {object_name}")
            return object_name
        else:
            error = response.get("error", "未知错误")
            logger.error(f"创建立方体失败: {error}")
            return None
    
    except Exception as e:
        logger.error(f"测试创建立方体时出错: {str(e)}")
        return None

async def test_set_material(object_name: str) -> bool:
    """
    测试设置材质
    
    Args:
        object_name: 要设置材质的对象名称
    
    Returns:
        bool: 操作是否成功
    """
    logger.info(f"===== 测试：为对象 '{object_name}' 设置材质 =====")
    
    # 使用action格式的请求设置材质
    request = {
        "action": "call_tool",
        "tool": "set_material",
        "arguments": {
            "object_name": object_name,
            "material_name": "TestMaterial",
            "color": [1.0, 0.0, 0.0, 1.0],  # 红色
            "metallic": 0.1,
            "roughness": 0.5
        }
    }
    
    try:
        response = await send_request(request)
        
        # 打印完整响应以便调试
        logger.info(f"完整响应: {json.dumps(response, indent=2)}")
        
        # 检查响应是否成功
        if "error" not in response:
            logger.info(f"✓ 成功为对象 '{object_name}' 设置材质")
            return True
        else:
            error = response.get("error", "未知错误")
            logger.error(f"设置材质失败: {error}")
            return False
    
    except Exception as e:
        logger.error(f"测试设置材质时出错: {str(e)}")
        return False

async def run_tests():
    """运行测试"""
    try:
        logger.info("======= 开始Blender MCP工具测试 =======")
        
        # 测试创建立方体
        cube_name = await test_create_cube()
        
        # 如果创建立方体成功，测试设置材质
        if cube_name:
            await test_set_material(cube_name)
        
        logger.info("======= 测试完成 =======")
    
    except Exception as e:
        logger.error(f"测试过程中出错: {str(e)}")

if __name__ == "__main__":
    asyncio.run(run_tests()) 
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Blender MCP服务器功能测试脚本
测试MCP服务器的基本功能，包括：
1. 连接服务器
2. 获取工具列表
3. 获取资源列表
4. 创建3D对象
5. 设置材质属性
"""

import asyncio
import json
import logging
import socket
import sys
import time
from typing import Dict, Any, Optional, List, Union

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("mcp_test.log")
    ]
)

logger = logging.getLogger("BlenderMCPTest")

# 服务器连接配置
MCP_SERVER_HOST = "localhost"
MCP_SERVER_PORT = 8237  # 默认端口，可能需要根据实际配置调整

# 控制是否打印详细结果
VERBOSE = True

async def send_request(client_socket: Optional[socket.socket], request: Dict[str, Any]) -> Dict[str, Any]:
    """
    向MCP服务器发送请求并接收响应
    
    Args:
        client_socket: 客户端套接字，如果为None则创建新连接
        request: 请求数据字典
    
    Returns:
        Dict[str, Any]: 服务器响应的JSON数据
    """
    close_after = False
    if client_socket is None:
        # 创建新套接字连接
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((MCP_SERVER_HOST, MCP_SERVER_PORT))
        close_after = True
    
    try:
        # 将请求转换为JSON字符串并添加长度前缀
        request_json = json.dumps(request)
        message = f"{len(request_json)}:{request_json}"
        
        # 发送请求
        client_socket.sendall(message.encode('utf-8'))
        logger.debug(f"已发送请求: {message}")
        
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
        logger.debug(f"收到响应: {response_json}")
        
        return response_json
    
    finally:
        if close_after:
            client_socket.close()

async def test_get_tools() -> List[Dict[str, Any]]:
    """
    测试获取工具列表
    
    Returns:
        List[Dict[str, Any]]: 工具列表
    """
    logger.info("测试: 获取工具列表")
    
    request = {
        "method": "mcp/listTools",
        "params": {}
    }
    
    try:
        response = await send_request(None, request)
        
        if "result" in response and "tools" in response["result"]:
            tools = response["result"]["tools"]
            logger.info(f"成功获取 {len(tools)} 个工具")
            
            if VERBOSE:
                for i, tool in enumerate(tools[:5], 1):  # 只显示前5个工具
                    logger.info(f"工具 {i}: {tool['name']} - {tool.get('description', '无描述')}")
                
                if len(tools) > 5:
                    logger.info(f"... 以及其他 {len(tools)-5} 个工具")
            
            return tools
        else:
            logger.error(f"获取工具列表失败: {response}")
            return []
    
    except Exception as e:
        logger.error(f"获取工具列表时出错: {str(e)}")
        return []

async def test_get_resources() -> List[Dict[str, Any]]:
    """
    测试获取资源列表
    
    Returns:
        List[Dict[str, Any]]: 资源列表
    """
    logger.info("测试: 获取资源列表")
    
    request = {
        "method": "mcp/listResources",
        "params": {}
    }
    
    try:
        response = await send_request(None, request)
        
        if "result" in response and "resources" in response["result"]:
            resources = response["result"]["resources"]
            logger.info(f"成功获取 {len(resources)} 个资源")
            
            if VERBOSE:
                for i, resource in enumerate(resources[:5], 1):  # 只显示前5个资源
                    logger.info(f"资源 {i}: {resource['name']} - 类型: {resource.get('type', '未知')}")
                
                if len(resources) > 5:
                    logger.info(f"... 以及其他 {len(resources)-5} 个资源")
            
            return resources
        else:
            logger.error(f"获取资源列表失败: {response}")
            return []
    
    except Exception as e:
        logger.error(f"获取资源列表时出错: {str(e)}")
        return []

async def test_create_cube() -> Union[str, None]:
    """
    测试创建立方体
    
    Returns:
        Union[str, None]: 成功时返回创建的对象名称，失败时返回None
    """
    logger.info("测试: 创建立方体")
    
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
        response = await send_request(None, request)
        
        # 检查响应是否成功
        if response and not response.get("error"):
            logger.info("成功创建立方体")
            
            # 尝试从响应中获取对象名称
            object_name = None
            if "object_name" in response:
                object_name = response["object_name"]
            elif "result" in response and isinstance(response["result"], dict) and "object_name" in response["result"]:
                object_name = response["result"]["object_name"]
            
            if object_name:
                logger.info(f"创建的对象名称: {object_name}")
            else:
                logger.info("创建了对象，但没有返回对象名称")
                object_name = "TestCube"  # 使用默认名称
            
            return object_name
        else:
            error = response.get("error", "未知错误")
            logger.error(f"创建立方体失败: {error}")
            return None
    
    except Exception as e:
        logger.error(f"创建立方体时出错: {str(e)}")
        return None

async def test_set_material(object_name: str) -> bool:
    """
    测试设置材质
    
    Args:
        object_name: 要设置材质的对象名称
    
    Returns:
        bool: 操作是否成功
    """
    logger.info(f"测试: 为对象 '{object_name}' 设置材质")
    
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
        response = await send_request(None, request)
        
        # 检查响应是否成功
        if response and not response.get("error"):
            logger.info(f"成功为对象 '{object_name}' 设置材质")
            return True
        else:
            error = response.get("error", "未知错误")
            logger.error(f"设置材质失败: {error}")
            return False
    
    except Exception as e:
        logger.error(f"设置材质时出错: {str(e)}")
        return False

async def test_add_light() -> Union[str, None]:
    """
    测试添加光源
    
    Returns:
        Union[str, None]: 成功时返回创建的光源名称，失败时返回None
    """
    logger.info("测试: 添加点光源")
    
    # 使用action格式的请求添加光源
    request = {
        "action": "call_tool",
        "tool": "add_light",
        "arguments": {
            "light_type": "point",
            "name": "TestLight",
            "location": [2, 2, 3],
            "energy": 1000,
            "color": [1.0, 1.0, 1.0]  # 白色
        }
    }
    
    try:
        response = await send_request(None, request)
        
        # 检查响应是否成功
        if response and not response.get("error"):
            logger.info("成功添加点光源")
            return "TestLight"
        else:
            error = response.get("error", "未知错误")
            logger.error(f"添加光源失败: {error}")
            return None
    
    except Exception as e:
        logger.error(f"添加光源时出错: {str(e)}")
        return None

async def test_execute_python() -> bool:
    """
    测试执行Python代码
    
    Returns:
        bool: 操作是否成功
    """
    logger.info("测试: 执行Python代码")
    
    # 简单的Python代码，创建一个简单的场景
    python_code = """
import bpy

# 打印Blender版本信息
print(f"Blender版本: {bpy.app.version_string}")

# 获取当前场景中的对象数量
object_count = len(bpy.context.scene.objects)
print(f"当前场景中有 {object_count} 个对象")

# 返回一个成功消息
"执行Python代码成功"
"""
    
    # 使用action格式的请求执行Python代码
    request = {
        "action": "call_tool",
        "tool": "execute_python",
        "arguments": {
            "code": python_code
        }
    }
    
    try:
        response = await send_request(None, request)
        
        # 检查响应是否成功
        if response and not response.get("error"):
            logger.info("成功执行Python代码")
            return True
        else:
            error = response.get("error", "未知错误")
            logger.error(f"执行Python代码失败: {error}")
            return False
    
    except Exception as e:
        logger.error(f"执行Python代码时出错: {str(e)}")
        return False

async def test_server_health() -> bool:
    """
    测试服务器健康状况，确保服务器正在运行并响应请求
    
    Returns:
        bool: 服务器是否健康
    """
    logger.info("测试: 服务器健康检查")
    
    try:
        # 创建套接字连接
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(3)  # 设置3秒超时
        
        # 尝试连接服务器
        client_socket.connect((MCP_SERVER_HOST, MCP_SERVER_PORT))
        logger.info(f"成功连接到服务器 {MCP_SERVER_HOST}:{MCP_SERVER_PORT}")
        
        # 发送简单的请求以验证通信
        request = {
            "method": "mcp/listTools",
            "params": {}
        }
        
        response = await send_request(client_socket, request)
        
        if response and "result" in response:
            logger.info("服务器响应正常，健康检查通过")
            client_socket.close()
            return True
        else:
            logger.error(f"服务器响应异常: {response}")
            client_socket.close()
            return False
    
    except Exception as e:
        logger.error(f"服务器健康检查失败: {str(e)}")
        return False

async def run_all_tests():
    """
    运行所有测试
    """
    logger.info("====== 开始Blender MCP服务器测试 ======")
    
    # 测试记录
    test_results = {}
    
    # 1. 健康检查
    test_results["健康检查"] = await test_server_health()
    if not test_results["健康检查"]:
        logger.error("服务器不可用，停止测试")
        return test_results
    
    # 2. 获取工具列表
    tools = await test_get_tools()
    test_results["获取工具列表"] = len(tools) > 0
    
    # 3. 获取资源列表
    resources = await test_get_resources()
    test_results["获取资源列表"] = len(resources) > 0
    
    # 4. 创建立方体
    cube_name = await test_create_cube()
    test_results["创建立方体"] = cube_name is not None
    
    # 5. 如果立方体创建成功，测试设置材质
    if cube_name:
        material_result = await test_set_material(cube_name)
        test_results["设置材质"] = material_result
    else:
        test_results["设置材质"] = False
    
    # 6. 添加光源
    light_name = await test_add_light()
    test_results["添加光源"] = light_name is not None
    
    # 7. 执行Python代码
    python_result = await test_execute_python()
    test_results["执行Python代码"] = python_result
    
    # 显示测试结果摘要
    logger.info("\n====== 测试结果摘要 ======")
    all_passed = True
    for test_name, result in test_results.items():
        status = "通过" if result else "失败"
        logger.info(f"{test_name}: {status}")
        all_passed = all_passed and result
    
    if all_passed:
        logger.info("✓ 所有测试通过!")
    else:
        logger.error("✗ 部分测试失败，请检查日志")
    
    logger.info("====== 测试完成 ======")
    
    return test_results

if __name__ == "__main__":
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
    except Exception as e:
        logger.error(f"测试过程中出错: {str(e)}") 
import asyncio
import json
import logging
import os
import tempfile
import sys

# 设置日志
logger = logging.getLogger("BlenderMCP.Test")
# 配置日志格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# 添加控制台处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# 添加文件处理器
log_file = os.path.join(tempfile.gettempdir(), "blender_mcp_test_cube.log")
file_handler = logging.FileHandler(log_file, mode='a')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

logger.setLevel(logging.DEBUG)

async def send_request(method=None, params=None):
    """发送请求到MCP服务器并获取响应"""
    server_host = "localhost"
    server_port = 27015
    
    if params is None:
        params = {}
    
    if method:
        logger.info(f"向服务器发送请求: {method}")
    else:
        action = params.get("action", "未知操作")
        logger.info(f"向服务器发送操作: {action}")
    
    try:
        reader, writer = await asyncio.open_connection(server_host, server_port)

        # 构造请求消息
        request = {}
        if method:
            request["method"] = method
            request["params"] = params
        else:
            # 直接发送params作为请求
            request = params
        
        # 发送请求
        message = json.dumps(request)
        logger.debug(f"发送消息: {message}")
        
        # 添加长度前缀
        writer.write(f"{len(message)}:".encode() + message.encode())
        await writer.drain()
        
        # 接收响应
        header = b""
        while b":" not in header:
            chunk = await reader.read(1)
            if not chunk:
                logger.error("接收响应时连接断开")
                return None
            header += chunk
        
        length = int(header.decode().split(":")[0])
        response_data = b""
        while len(response_data) < length:
            chunk = await reader.read(min(4096, length - len(response_data)))
            if not chunk:
                logger.error("接收响应数据时连接断开")
                return None
            response_data += chunk
        
        response = json.loads(response_data.decode())
        if method:
            logger.info(f"接收到响应: {method} 成功")
        else:
            logger.info(f"接收到响应成功")
        logger.debug(f"响应内容: {json.dumps(response, indent=4, ensure_ascii=False)}")
        
        writer.close()
        await writer.wait_closed()
        
        return response
    except FileNotFoundError:
        logger.error(f"错误: 在 {server_host}:{server_port} 未找到服务器。请确保MCP服务器正在运行。")
    except ConnectionRefusedError:
        logger.error(f"错误: 在 {server_host}:{server_port} 连接被拒绝。请确保MCP服务器正在运行并监听。")
    except Exception as e:
        logger.error(f"发生错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    return None

async def test_create_cube():
    """测试创建立方体"""
    logger.info("测试创建立方体")
    
    # 创建立方体的参数
    params = {
        "action": "call_tool",
        "tool": "create_object",
        "arguments": {
            "object_type": "cube",
            "name": "TestCube",
            "location": [0, 0, 0],
            "size": 2.0
        }
    }
    
    # 调用工具
    response = await send_request(None, params)
    
    if response and not response.get("error"):
        logger.info(f"创建立方体成功")
        return "TestCube"  # 返回指定的对象名称
    else:
        error = response.get("error", "未知错误")
        logger.error(f"创建立方体失败: {error}")
        return None

async def test_set_material(object_name):
    """测试设置红色材质"""
    logger.info(f"测试为对象 {object_name} 设置红色材质")
    
    # 设置红色材质的参数
    params = {
        "action": "call_tool",
        "tool": "set_material",
        "arguments": {
            "object_name": object_name,
            "material_name": "RedMaterial",
            "color": [1.0, 0.0, 0.0, 1.0],  # 红色 RGBA
            "metallic": 0.0,
            "roughness": 0.5
        }
    }
    
    # 调用工具
    response = await send_request(None, params)
    
    if response and not response.get("error"):
        logger.info(f"设置材质成功")
        return True
    else:
        error = response.get("error", "未知错误")
        logger.error(f"设置材质失败: {error}")
        return False

async def main():
    """运行所有测试"""
    logger.info("开始测试创建红色立方体")
    
    # 测试创建立方体
    object_name = await test_create_cube()
    if not object_name:
        logger.error("测试失败：无法创建立方体")
        return
    
    # 测试设置材质
    success = await test_set_material(object_name)
    if not success:
        logger.error("测试失败：无法设置材质")
        return
    
    logger.info("测试成功完成：已创建红色立方体")

if __name__ == "__main__":
    asyncio.run(main()) 
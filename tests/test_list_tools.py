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
log_file = os.path.join(tempfile.gettempdir(), "blender_mcp_test.log")
file_handler = logging.FileHandler(log_file, mode='a')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

logger.setLevel(logging.DEBUG)

async def send_request(method="mcp/listTools", params=None):
    """发送请求到MCP服务器并获取响应"""
    server_host = "localhost"
    server_port = 27015
    
    logger.info(f"向服务器发送请求: {method}")
    
    try:
        reader, writer = await asyncio.open_connection(server_host, server_port)

        # 构造请求
        request = {
            "method": method,
            "params": params or {}
        }
        message = json.dumps(request)
        logger.debug(f"发送消息: {message}")
        
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
        logger.info(f"接收到响应: {method} 成功")
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

async def test_list_tools():
    """测试获取工具列表"""
    logger.info("测试获取工具列表")
    response = await send_request("mcp/listTools")
    if response and "result" in response and "tools" in response["result"]:
        tools = response["result"]["tools"]
        logger.info(f"成功获取 {len(tools)} 个工具")
        return tools
    else:
        logger.error("获取工具列表失败")
        return None

async def test_list_resources():
    """测试获取资源列表"""
    logger.info("测试获取资源列表")
    response = await send_request("mcp/listResources")
    if response:
        resources = response.get("result", {}).get("resources", [])
        logger.info(f"成功获取 {len(resources)} 个资源")
        return resources
    else:
        logger.error("获取资源列表失败")
        return None
        
async def main():
    """运行所有测试"""
    logger.info("开始MCP通信测试")
    
    # 命令行参数解析
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "tools":
            await test_list_tools()
        elif command == "resources":
            await test_list_resources()
        else:
            logger.info(f"未知命令: {command}，执行所有测试")
            await test_list_tools()
            await test_list_resources()
    else:
        # 默认执行所有测试
        await test_list_tools()
        await test_list_resources()
    
    logger.info("测试完成")

if __name__ == "__main__":
    asyncio.run(main())

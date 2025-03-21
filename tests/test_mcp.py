import socket
import json
import time
import sys
import os

# 设置日志
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MCP-Test")

def send_request(socket_path, request):
    """发送请求到IPC服务器并获取响应"""
    logger.info(f"发送请求: {request}")
    
    try:
        # 确定是TCP还是Unix套接字
        is_tcp = sys.platform == "win32" or socket_path.startswith("port:")
        
        # 创建套接字
        if is_tcp:
            if socket_path.startswith("port:"):
                port = int(socket_path.split(":", 1)[1])
            else:
                port = 27015
            
            # 创建TCP套接字
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect(("127.0.0.1", port))
            logger.debug(f"已连接到TCP套接字: 127.0.0.1:{port}")
        else:
            # 创建Unix套接字
            client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client_socket.connect(socket_path)
            logger.debug(f"已连接到Unix套接字: {socket_path}")
        
        # 发送请求
        request_json = json.dumps(request)
        header = f"{len(request_json)}:".encode()
        client_socket.sendall(header + request_json.encode())
        
        # 接收响应
        header = b""
        while b":" not in header:
            chunk = client_socket.recv(1)
            if not chunk:
                raise ConnectionError("连接关闭")
            header += chunk
        
        # 解析响应长度
        length = int(header.decode().split(":")[0])
        
        # 读取响应内容
        data = b""
        while len(data) < length:
            chunk = client_socket.recv(min(4096, length - len(data)))
            if not chunk:
                raise ConnectionError("读取响应时连接关闭")
            data += chunk
        
        # 解析响应
        response = json.loads(data.decode())
        logger.info(f"收到响应: {response}")
        
        # 关闭套接字
        client_socket.close()
        
        return response
    except Exception as e:
        logger.error(f"发送请求出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"error": str(e)}

def test_mcp_tools_list(socket_path):
    """测试获取工具列表"""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list"
    }
    
    return send_request(socket_path, request)

def test_mcp_tools_call(socket_path, tool_name, arguments=None):
    """测试调用工具"""
    if arguments is None:
        arguments = {}
        
    request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    return send_request(socket_path, request)

def test_mcp_resources_list(socket_path):
    """测试获取资源列表"""
    request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "resources/list"
    }
    
    return send_request(socket_path, request)

def test_mcp_resources_read(socket_path, uri):
    """测试读取资源"""
    request = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "resources/read",
        "params": {
            "uri": uri
        }
    }
    
    return send_request(socket_path, request)

def test_legacy_tools_list(socket_path):
    """测试传统方式获取工具列表"""
    request = {
        "action": "list_tools"
    }
    
    return send_request(socket_path, request)

def test_legacy_tools_call(socket_path, tool_name, arguments=None):
    """测试传统方式调用工具"""
    if arguments is None:
        arguments = {}
        
    request = {
        "action": "call_tool",
        "tool": tool_name,
        "arguments": arguments
    }
    
    return send_request(socket_path, request)

def run_tests(socket_path):
    """运行所有测试"""
    tests = [
        # MCP方式测试
        ("MCP获取工具列表", lambda: test_mcp_tools_list(socket_path)),
        ("MCP调用Python工具", lambda: test_mcp_tools_call(socket_path, "execute_python", {"code": "result = {'status': 'success', 'message': 'Hello from MCP Python!'}"})),
        ("MCP获取资源列表", lambda: test_mcp_resources_list(socket_path)),
        ("MCP读取场景资源", lambda: test_mcp_resources_read(socket_path, "blender://scene/current")),
        
        # 传统方式测试
        ("传统获取工具列表", lambda: test_legacy_tools_list(socket_path)),
        ("传统调用Python工具", lambda: test_legacy_tools_call(socket_path, "execute_python", {"code": "result = {'status': 'success', 'message': 'Hello from Legacy Python!'}"}))
    ]
    
    results = {}
    for name, test_func in tests:
        logger.info(f"=== 运行测试: {name} ===")
        try:
            result = test_func()
            success = "error" not in result
            results[name] = {"success": success, "result": result}
            logger.info(f"测试结果: {'成功' if success else '失败'}")
        except Exception as e:
            logger.error(f"测试出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            results[name] = {"success": False, "error": str(e)}
    
    # 打印测试结果摘要
    logger.info("\n=== 测试结果摘要 ===")
    for name, result in results.items():
        logger.info(f"{name}: {'成功' if result['success'] else '失败'}")
    
    success_count = sum(1 for result in results.values() if result["success"])
    total_count = len(results)
    logger.info(f"总计: {success_count}/{total_count} 测试成功")

if __name__ == "__main__":
    # 获取套接字路径
    if len(sys.argv) > 1:
        socket_path = sys.argv[1]
    else:
        if sys.platform == "win32":
            socket_path = "port:27015"
        else:
            socket_path = os.path.join("/tmp", "blender-mcp.sock")
    
    logger.info(f"使用套接字路径: {socket_path}")
    
    # 运行测试
    run_tests(socket_path) 
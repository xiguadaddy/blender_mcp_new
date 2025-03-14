#!/usr/bin/env python3
"""
BlenderMCP服务器调试脚本
用于测试服务器在各种配置下的启动情况，并输出详细错误信息
"""

import os
import sys
import socket
import time
import traceback
import logging
import importlib.util

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('blender_mcp_debug.log')
    ]
)
logger = logging.getLogger("BlenderMCPDebug")

def test_port(host, port):
    """测试端口是否可用"""
    logger.info(f"测试端口可用性: {host}:{port}")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.bind((host, port))
            logger.info(f"端口 {host}:{port} 可用")
            return True
    except Exception as e:
        logger.error(f"端口 {host}:{port} 不可用: {e}")
        return False

def import_server_module():
    """尝试导入服务器模块，记录详细信息"""
    logger.info("尝试导入服务器模块")
    
    # 获取当前脚本的目录，假设server.py在同一目录或子目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    server_py_path = os.path.join(current_dir, "server", "server.py")
    
    if not os.path.exists(server_py_path):
        logger.error(f"服务器文件不存在: {server_py_path}")
        server_py_path = os.path.join(current_dir, "server.py")
        if not os.path.exists(server_py_path):
            logger.error(f"也找不到备选服务器文件: {server_py_path}")
            sys.exit(1)
    
    logger.info(f"找到服务器文件: {server_py_path}")
    
    # 检查相关依赖文件
    response_utils_path = os.path.join(os.path.dirname(server_py_path), "response_utils.py")
    task_manager_path = os.path.join(os.path.dirname(server_py_path), "task_manager.py")
    
    logger.info(f"response_utils.py 存在: {os.path.exists(response_utils_path)}")
    logger.info(f"task_manager.py 存在: {os.path.exists(task_manager_path)}")
    
    # 导入服务器模块
    try:
        # 首先导入辅助模块，避免循环导入问题
        logger.debug("尝试导入response_utils模块")
        spec = importlib.util.spec_from_file_location("response_utils", response_utils_path)
        response_utils = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(response_utils)
        sys.modules["response_utils"] = response_utils
        
        logger.debug("尝试导入task_manager模块")
        spec = importlib.util.spec_from_file_location("task_manager", task_manager_path)
        task_manager = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(task_manager)
        sys.modules["task_manager"] = task_manager
        
        # 然后导入服务器模块
        logger.debug("尝试导入server模块")
        spec = importlib.util.spec_from_file_location("server", server_py_path)
        server = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(server)
        sys.modules["server"] = server
        
        logger.info("所有模块导入成功")
        return server
    except Exception as e:
        logger.error(f"导入模块时出错: {e}")
        logger.error(traceback.format_exc())
        return None

def start_server(server_module, host="localhost", port=9876, debug=True):
    """尝试启动服务器"""
    logger.info(f"尝试启动服务器: {host}:{port}")
    
    try:
        # 创建服务器
        server_instance = server_module.BlenderMCPServer(host=host, port=port, debug=debug)
        logger.info("服务器实例创建成功")
        
        # 启动服务器
        start_result = server_instance.start()
        if start_result.get("status", "") == "success":
            logger.info(f"服务器启动成功: {start_result}")
            return server_instance
        else:
            logger.error(f"服务器启动失败: {start_result}")
            return None
    except Exception as e:
        logger.error(f"启动服务器过程中发生错误: {e}")
        logger.error(traceback.format_exc())
        return None

def inspect_blender_mcp_class(server_module):
    """检查BlenderMCPServer类的方法和属性"""
    logger.info("检查BlenderMCPServer类")
    
    try:
        # 检查类是否存在
        if not hasattr(server_module, "BlenderMCPServer"):
            logger.error("服务器模块中没有BlenderMCPServer类")
            return
        
        # 获取类对象
        server_class = server_module.BlenderMCPServer
        
        # 检查主要方法
        methods = ["__init__", "start", "stop", "is_running", "handle_command"]
        for method_name in methods:
            if hasattr(server_class, method_name):
                logger.info(f"类方法存在: {method_name}")
            else:
                logger.error(f"缺少必要的类方法: {method_name}")
        
        # 尝试创建一个实例并检查属性
        try:
            instance = server_class(host="localhost", port=9876, debug=True)
            logger.info("成功创建实例")
            
            # 检查主要属性
            properties = ["host", "port", "debug", "server", "thread"]
            for prop_name in properties:
                if hasattr(instance, prop_name):
                    prop_value = getattr(instance, prop_name)
                    logger.info(f"实例属性存在: {prop_name} = {prop_value}")
                else:
                    logger.warning(f"缺少预期的实例属性: {prop_name}")
                    
        except Exception as e:
            logger.error(f"创建实例时出错: {e}")
            logger.error(traceback.format_exc())
            
    except Exception as e:
        logger.error(f"检查BlenderMCPServer类时出错: {e}")
        logger.error(traceback.format_exc())

def main():
    """主函数，执行服务器测试"""
    logger.info("===== 开始BlenderMCP服务器调试 =====")
    
    # 1. 显示系统信息
    logger.info(f"操作系统: {sys.platform}")
    logger.info(f"Python版本: {sys.version}")
    logger.info(f"当前目录: {os.getcwd()}")
    
    # 2. 导入服务器模块
    server_module = import_server_module()
    if not server_module:
        logger.error("导入服务器模块失败，无法继续测试")
        return
    
    # 3. 检查BlenderMCPServer类
    inspect_blender_mcp_class(server_module)
    
    # 4. 测试启动服务器 - 不同的配置
    # 首先默认配置
    logger.info("===== 测试默认配置 =====")
    if test_port("localhost", 9876):
        server = start_server(server_module, "localhost", 9876)
        if server:
            logger.info("服务器成功启动在默认配置下")
            time.sleep(2)  # 让服务器运行一会儿
            server.stop()
            logger.info("服务器已停止")
        else:
            logger.error("服务器启动失败（默认配置）")
    else:
        logger.warning("端口9876在localhost上不可用，跳过默认配置测试")
    
    # 测试不同的主机配置
    logger.info("===== 测试127.0.0.1 =====")
    if test_port("127.0.0.1", 9876):
        server = start_server(server_module, "127.0.0.1", 9876)
        if server:
            logger.info("服务器成功启动在127.0.0.1:9876")
            time.sleep(2)
            server.stop()
            logger.info("服务器已停止")
        else:
            logger.error("服务器启动失败 (127.0.0.1:9876)")
    else:
        logger.warning("端口9876在127.0.0.1上不可用")
    
    # 测试不同的端口
    logger.info("===== 测试不同端口 =====")
    alt_port = 9877
    if test_port("0.0.0.0", alt_port):
        server = start_server(server_module, "0.0.0.0", alt_port)
        if server:
            logger.info(f"服务器成功启动在0.0.0.0:{alt_port}")
            time.sleep(2)
            server.stop()
            logger.info("服务器已停止")
        else:
            logger.error(f"服务器启动失败 (0.0.0.0:{alt_port})")
    else:
        logger.warning(f"端口{alt_port}在0.0.0.0上不可用")
    
    logger.info("===== BlenderMCP服务器调试完成 =====")
    logger.info("详细日志已保存到blender_mcp_debug.log")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3

import asyncio
import argparse
from server.server import BlenderMCPServer
from server.ipc_client import IPCClient
import mcp.server.stdio
import sys
from mcp.server import NotificationOptions
import os
import mcp.server.models
import logging
import traceback
import json
from threading import Thread
import time
import socket

# 在main.py顶部添加，解决Windows平台的编码问题
if sys.platform == "win32" and os.environ.get('PYTHONIOENCODING') is None:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# 尝试导入MCP版本信息
try:
    from mcp import __version__ as mcp_version
    mcp_info = f"v{mcp_version}"
except ImportError:
    try:
        import mcp
        mcp_info = getattr(mcp, "VERSION", "未知")
    except ImportError:
        print("无法导入MCP SDK，请确保已安装")
        mcp_info = "未知"
        mcp = None

# 处理Windows编码问题的StreamHandler
class EncodingSafeStreamHandler(logging.StreamHandler):
    def __init__(self, stream=None):
        super().__init__(stream)
        self.stream_errors = "backslashreplace"
        
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            # 使用替换未知字符的方式写入
            stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

# 检查Blender IPC服务器是否运行
def check_blender_ipc_server(socket_path):
    """检查Blender IPC服务器是否正在运行
    
    Args:
        socket_path: IPC通信路径 (Unix套接字或'port:端口号')
        
    Returns:
        bool: 服务器是否正在运行
    """
    logger = logging.getLogger("BlenderMCP.ServerCheck")
    
    # 检查是否是端口模式
    if socket_path.startswith("port:"):
        try:
            port = int(socket_path.split(":", 1)[1])
            host = "localhost"
            
            logger.info(f"尝试连接Blender IPC服务器 {host}:{port}...")
            
            # 创建TCP套接字并尝试连接
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(2.0)  # 设置超时以避免阻塞
                result = sock.connect_ex((host, port))
                
                if result == 0:
                    logger.info(f"Blender IPC服务器在 {host}:{port} 已运行")
                    return True
                else:
                    logger.warning(f"无法连接到 {host}:{port}，错误代码: {result}")
                    return False
                
        except Exception as e:
            logger.error(f"检查Blender IPC服务器时出错: {str(e)}")
            return False
    else:
        # Unix套接字模式
        try:
            if os.path.exists(socket_path):
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                    sock.settimeout(2.0)
                    result = sock.connect_ex(socket_path)
                    
                    if result == 0:
                        logger.info(f"Blender IPC服务器在 {socket_path} 已运行")
                        return True
                    else:
                        logger.warning(f"Unix套接字存在但无法连接，错误代码: {result}")
                        return False
            else:
                logger.warning(f"Unix套接字路径不存在: {socket_path}")
                return False
        except Exception as e:
            logger.error(f"检查Unix套接字服务器时出错: {str(e)}")
            return False

# 创建异步健康检查函数
async def run_health_check(server_manager, interval=30):
    """定期运行健康检查
    
    Args:
        server_manager: BlenderMCPServer实例
        interval: 检查间隔(秒)
    """
    logger = logging.getLogger("BlenderMCP.HealthCheck")
    logger.info(f"启动健康检查，间隔: {interval}秒")
    
    while True:
        try:
            status, message = await server_manager.health_check()
            if status:
                logger.debug(f"健康检查通过: {message}")
            else:
                logger.warning(f"健康检查失败: {message}")
                # 尝试恢复服务器
                recovery_result = await server_manager.recover()
                if recovery_result:
                    logger.info("服务器已恢复")
                else:
                    logger.error("服务器恢复失败")
        except Exception as e:
            logger.error(f"健康检查过程中出错: {str(e)}")
            logger.error(traceback.format_exc())
        
        await asyncio.sleep(interval)

# 主程序入口
async def main():
    parser = argparse.ArgumentParser(description="Blender MCP Server")
    parser.add_argument("--socket-path", required=True, help="IPC通信路径 (Unix套接字或'port:端口号')")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    parser.add_argument("--protocol-version", default="0.3.0", help="MCP协议版本")
    parser.add_argument("--health-check", action="store_true", help="启用定期健康检查")
    parser.add_argument("--health-interval", type=int, default=30, help="健康检查间隔(秒)")
    parser.add_argument("--retry-count", type=int, default=3, help="连接重试次数")
    parser.add_argument("--retry-delay", type=float, default=1.0, help="重试延迟(秒)")
    
    args = parser.parse_args()
    
    # 创建日志处理器
    console_handler = EncodingSafeStreamHandler()
    file_handler = logging.FileHandler(
        os.path.join(os.path.dirname(__file__), "mcp_server.log"), 
        mode='w',
        encoding='utf-8'  # 明确指定UTF-8编码
    )

    # 根据命令行参数设置日志级别
    log_level = logging.DEBUG if args.debug else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[console_handler, file_handler]
    )
    logger = logging.getLogger("BlenderMCP")

    # 显示启动信息
    logger.info("="*50)
    logger.info("MCP服务器启动")
    logger.info(f"Python版本: {sys.version}")
    logger.info(f"Python路径: {sys.executable}")
    logger.info(f"工作目录: {os.getcwd()}")
    logger.info(f"MCP SDK版本信息: {mcp_info}")
    logger.info(f"MCP SDK路径: {getattr(mcp, '__file__', '未知')}")
    
    # 在调试模式下显示MCP包属性
    if args.debug:
        logger.debug("MCP包属性:")
        for attr in dir(mcp):
            if not attr.startswith("__"):
                try:
                    value = getattr(mcp, attr)
                    logger.debug(f"  - {attr}: {type(value)}")
                except Exception as e:
                    logger.debug(f"  - {attr}: 无法访问 ({str(e)})")
    
    logger.info("="*50)

    # 显示连接信息
    logger.info(f"尝试连接到Blender IPC服务器，通信路径: {args.socket_path}")
    
    # 首先检查Blender IPC服务器是否运行
    is_server_running = check_blender_ipc_server(args.socket_path)
    if not is_server_running:
        logger.error("Blender IPC服务器未运行或无法访问")
        logger.error("请确保在Blender中启动了MCP插件，并按以下步骤操作:")
        logger.error("1. 打开Blender")
        logger.error("2. 确保已安装并激活Blender MCP插件")
        logger.error("3. 在3D视图侧边栏找到'MCP'标签")
        logger.error("4. 点击'启动服务器'按钮")
        logger.error("5. 重新运行此脚本")
        return
    
    # 初始化IPC客户端，设置重试参数
    ipc_client = IPCClient(args.socket_path, max_retries=args.retry_count, retry_delay=args.retry_delay)
    
    # 连接到Blender，使用增强的重试机制
    max_connection_attempts = args.retry_count * 2
    for attempt in range(1, max_connection_attempts + 1):
        logger.info(f"连接尝试 {attempt}/{max_connection_attempts}...")
        if await ipc_client.connect():
            logger.info("成功连接到Blender IPC服务器")
            break
        else:
            if attempt < max_connection_attempts:
                retry_delay = args.retry_delay * (1 + attempt * 0.5)  # 逐渐增加延迟
                logger.warning(f"连接失败，将在 {retry_delay:.1f} 秒后重试...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error("达到最大连接尝试次数，放弃连接")
                logger.error("无法连接到Blender IPC服务器，请检查以下事项:")
                logger.error("1. Blender是否正在运行")
                logger.error("2. MCP插件是否已在Blender中激活")
                logger.error("3. Blender MCP插件中的服务器是否已启动")
                logger.error(f"4. 服务器是否正在监听正确的端口: {args.socket_path}")
                logger.error("5. 是否有防火墙或安全软件阻止连接")
                return
    
    try:
        # 创建服务器管理器
        logger.info("正在创建MCP服务器...")
        server_manager = BlenderMCPServer(ipc_client)
        
        # 设置健康检查间隔
        server_manager.health_check_interval = args.health_interval
        
        # 初始化服务器
        server = server_manager.initialize()
        
        # 如果启用了健康检查，启动健康检查任务
        if args.health_check:
            logger.info(f"启用定期健康检查，间隔: {args.health_interval}秒")
            health_check_task = asyncio.create_task(
                run_health_check(server_manager, args.health_interval)
            )
        
        # 使用标准输入/输出来通信
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            logger.info("MCP服务器: 准备启动服务器")
            
            # 创建初始化选项
            logger.info("初始化NotificationOptions...")
            try:
                # 明确设置所有通知选项
                notification_options = mcp.server.NotificationOptions(
                    resources_changed=True,  # 启用资源更新通知
                    tools_changed=True,    # 启用方法结果通知
                    prompts_changed=True
                )
                logger.debug(f"创建了具有完整功能的NotificationOptions: {notification_options}")
            except Exception as e:
                logger.error(f"创建NotificationOptions时出错: {str(e)}")
                notification_options = None
            
            # 获取服务器能力
            logger.info("获取服务器能力...")
            try:
                capabilities = server_manager.get_capabilities()
                logger.debug(f"服务器能力: {capabilities}")
            except Exception as e:
                logger.error(f"获取服务器能力时出错: {str(e)}")
                logger.error(traceback.format_exc())
                capabilities = {}
            
            # 服务器信息
            logger.info(f"服务器信息: name={server_manager.server_name}, version={server_manager.server_version}")
            
            # 创建初始化选项
            logger.info("创建初始化选项...")
            try:
                # 设置实验性能力，包含服务器和协议版本信息
                experimental_capabilities = {
                    "blender": {
                        "server_version": server_manager.server_version,
                        "protocol_version": args.protocol_version,
                        "supports_resources": True,
                        "supports_tools": True,
                        "supports_prompts": True
                    }
                }
                
                initialization_options = server.create_initialization_options(
                    notification_options=notification_options,
                    experimental_capabilities=experimental_capabilities
                )
                logger.debug(f"初始化选项: {initialization_options}")
            except Exception as e:
                logger.error(f"创建初始化选项时出错: {str(e)}")
                logger.error(traceback.format_exc())
                return
            
            # 显示协议版本
            logger.info(f"使用协议版本: {args.protocol_version}")
            
            # 启动服务器
            logger.info("开始运行服务器...")
            try:
                # 检查run方法签名
                import inspect
                run_sig = inspect.signature(server.run)
                logger.info(f"server.run方法签名: {run_sig}")
                
                # 运行服务器
                await server.run(
                    read_stream=read_stream,
                    write_stream=write_stream,
                    initialization_options=initialization_options
                )
            except TypeError as te:
                # 处理参数不匹配的情况
                logger.error(f"服务器启动参数错误: {str(te)}")
                logger.warning("尝试使用替代方法启动服务器...")
                
                try:
                    # 尝试使用不同的参数形式启动
                    await server.run(
                        read_stream,
                        write_stream,
                        server_manager.server_name,
                        server_manager.server_version,
                        notification_options=notification_options,
                        experimental_capabilities=experimental_capabilities,
                    )
                except Exception as alt_e:
                    logger.error(f"替代启动方法也失败: {str(alt_e)}")
                    logger.error(traceback.format_exc())
            except Exception as e:
                logger.error(f"运行服务器时出错: {str(e)}")
                logger.error(traceback.format_exc())
    except Exception as e:
        logger.error(f"MCP服务器启动过程中出错: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        # 断开IPC连接
        ipc_client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n用户中断，服务器已停止")
    except Exception as e:
        print(f"服务器启动时出错: {e}")
        traceback.print_exc()

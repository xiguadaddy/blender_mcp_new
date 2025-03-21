import bpy
from ..ipc.server import start_ipc_server, stop_ipc_server
import sys
import os
from ..logger import get_logger

# 设置日志
logger = get_logger("BlenderMCP.ServerManager")

def start_server(socket_path, debug_mode=False):
    """启动MCP服务器
    
    参数:
        socket_path (str): IPC通信路径，Windows上是"port:端口号"，Unix/Linux上是套接字文件路径
        debug_mode (bool): 是否启用调试模式
        
    返回:
        bool: 启动成功返回True，否则返回False
    """
    try:
        # 确保socket_path参数有效
        if socket_path is None or not isinstance(socket_path, str) or not socket_path.strip():
            logger.error("无效的socket_path参数")
            if sys.platform == "win32":
                socket_path = "port:27015"
            else:
                import tempfile
                socket_path = os.path.join(tempfile.gettempdir(), "blender-mcp.sock")
            logger.info(f"使用默认socket路径: {socket_path}")
            
        logger.info(f"正在启动IPC服务器，通信路径: {socket_path}")
        
        # 如果服务器已经在运行，先停止它
        if hasattr(bpy.types, "_mcp_server_running") and bpy.types._mcp_server_running:
            logger.warning("检测到IPC服务器已经在运行，先停止它")
            stop_server()
        
        # 启动IPC服务器，使用简化的启动过程
        success = start_ipc_server(socket_path, debug_mode)
        if not success:
            logger.error("IPC服务器启动失败")
            return False
            
        # 设置全局状态
        bpy.types._mcp_server_running = True
        
        # 保存socket_path以便MCP服务器能使用相同的路径连接
        bpy.types._mcp_socket_path = socket_path
        logger.info(f"IPC服务器已启动，_mcp_socket_path = {bpy.types._mcp_socket_path}")
        
        # 使用超时保护来注册工具处理器
        import threading
        import time
        
        registration_success = [False]
        registration_complete = threading.Event()
        
        def register_tools_handler_with_timeout():
            try:
                # 首先尝试加载和初始化工具模块
                import importlib
                logger.info("开始初始化和加载工具模块...")
                
                # 导入工具系统
                from ..handlers import tools
                importlib.reload(tools)
                
                # 手动导入所有工具包以确保它们被加载
                from ..handlers.tools import object_tools, material_tools, lighting_tools
                from ..handlers.tools import camera_tools, scene_tools, mesh_tools
                from ..handlers.tools import effect_tools, animation_tools, modeling_tools
                
                # 使用工具注册表
                from ..handlers.tools.registry import get_tool_registry
                registry = get_tool_registry()
                
                # 检查工具注册状态
                tool_count = len(registry._tools) if hasattr(registry, '_tools') else 0
                logger.info(f"工具注册表初始化完成，已注册 {tool_count} 个工具")
                
                # 现在注册工具处理器
                from ..handlers.tool_handlers import register_tools_handler
                result = register_tools_handler()
                registration_success[0] = result
                
                logger.info(f"工具处理器注册{'成功' if result else '失败'}")
                
                # 再次检查工具注册状态
                tool_count = len(registry._tools) if hasattr(registry, '_tools') else 0
                logger.info(f"处理器注册后，已有 {tool_count} 个已注册工具")
                
                if tool_count > 0:
                    # 输出已注册工具列表
                    tool_names = list(registry._tools.keys())
                    logger.info(f"已注册工具示例: {tool_names[:5]}...")
                
                registration_complete.set()
            except Exception as e:
                logger.error(f"在线程中注册工具处理器时出错: {e}")
                import traceback
                logger.error(traceback.format_exc())
                registration_complete.set()
        
        # 在后台线程中执行注册
        thread = threading.Thread(target=register_tools_handler_with_timeout)
        thread.daemon = True
        thread.start()
        
        # 等待最多2秒钟
        if not registration_complete.wait(2.0):
            logger.warning("注册工具处理器超时，将在用户操作时重试")
        elif registration_success[0]:
            logger.info("已成功注册工具处理器")
        else:
            logger.warning("工具处理器注册失败，将在用户操作时重试")
        
        # 导入operators模块并同步状态
        try:
            from ..addon.operators import set_server_running_status
            set_server_running_status(True)
        except Exception as e:
            logger.warning(f"无法同步操作符状态: {e}，但服务器已启动")
            
        # 强制更新UI
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
        
        return True
    except Exception as e:
        logger.error(f"启动服务器时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def stop_server():
    """停止MCP服务器
    
    返回:
        bool: 停止成功返回True，否则返回False
    """
    try:
        success = stop_ipc_server()
        bpy.types._mcp_server_running = False
        
        if hasattr(bpy.types, "_mcp_socket_path"):
            delattr(bpy.types, "_mcp_socket_path")
        
        # 注销工具处理器
        try:
            from ..handlers.tool_handlers import unregister_tools_handler
            unregister_tools_handler()
            logger.info("已注销工具处理器")
        except Exception as e:
            logger.error(f"注销工具处理器时出错: {e}")
            # 继续执行，因为这不是致命错误
        
        # 导入operators模块并同步状态
        try:
            from ..addon.operators import set_server_running_status
            set_server_running_status(False)
        except Exception as e:
            logger.warning(f"无法同步操作符状态: {e}，但服务器已停止")
            
        # 强制更新UI
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
            
        logger.info("IPC服务器已停止")
        return success
    except Exception as e:
        logger.error(f"停止服务器时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

import bpy
import threading
import time
import queue

from ..logger import get_logger

# 设置日志
logger = get_logger("BlenderMCP.ThreadUtils")

# 用于主线程执行的命令队列
command_queue = queue.Queue()
result_queue = queue.Queue()

def run_in_main_thread(func, *args, **kwargs):
    """将函数放入队列，等待在主线程中执行"""
    # 创建唯一ID
    command_id = str(time.time())
    event = threading.Event()
    
    # 放入命令队列
    command_queue.put({
        "id": command_id,
        "function": func,
        "args": args,
        "kwargs": kwargs,
        "event": event
    })
    
    # 等待执行完成
    event.wait()
    
    # 获取结果
    while not result_queue.empty():
        result = result_queue.get()
        if result["id"] == command_id:
            return result["result"]
    
    return None

def process_command_queue():
    """处理命令队列，在主线程计时器中调用"""
    if command_queue.empty():
        return 1.0  # 如果队列为空，1秒后再次检查
    
    try:
        # 获取命令
        command = command_queue.get(block=False)
        
        # 执行函数
        func = command["function"]
        args = command["args"]
        kwargs = command["kwargs"]
        
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            logger.error(f"在主线程执行函数时出错: {str(e)}")
            result = {"error": str(e)}
        
        # 返回结果
        result_queue.put({
            "id": command["id"],
            "result": result
        })
        
        # 设置事件，通知等待线程
        command["event"].set()
        
    except queue.Empty:
        pass
    
    return 0.1  # 0.1秒后再次检查队列

# 注册主线程处理器
def register_main_thread_processor():
    """注册主线程命令处理器"""
    if not hasattr(register_main_thread_processor, "registered"):
        bpy.app.timers.register(process_command_queue)
        register_main_thread_processor.registered = True
        logger.debug("主线程处理器已注册")

# 取消注册主线程处理器
def unregister_main_thread_processor():
    """取消注册主线程命令处理器"""
    if hasattr(register_main_thread_processor, "registered"):
        if bpy.app.timers.is_registered(process_command_queue):
            bpy.app.timers.unregister(process_command_queue)
        register_main_thread_processor.registered = False
        logger.debug("主线程处理器已取消注册")

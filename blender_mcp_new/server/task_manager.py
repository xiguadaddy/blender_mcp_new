"""
任务管理器模块 - 提供异步任务处理和进度跟踪功能

这个模块实现了一个任务队列系统，用于管理长时间运行的Blender操作，
如渲染和大型场景处理等，同时提供任务进度和状态的查询功能。
"""

import threading
import queue
import time
import uuid
import logging
import traceback
from typing import Dict, Any, Callable, Optional, List, Tuple

logger = logging.getLogger("BlenderMCPServer")

class Task:
    """代表一个异步执行的任务"""
    
    def __init__(self, task_id: str, func: Callable, params: Dict[str, Any]):
        """
        初始化任务
        
        参数:
            task_id: 任务的唯一ID
            func: 要执行的函数
            params: 传递给函数的参数
        """
        self.id = task_id
        self.func = func
        self.params = params
        self.status = "pending"  # pending, running, completed, failed, cancelled
        self.progress = 0.0      # 0.0 到 1.0 的进度
        self.result = None       # 任务结果
        self.error = None        # 错误信息
        self.created_at = time.time()
        self.started_at = None
        self.completed_at = None
        self.progress_updates = []  # 进度更新历史
        self.metadata = {}        # 附加元数据
        
    def update_progress(self, progress: float, message: Optional[str] = None):
        """
        更新任务进度
        
        参数:
            progress: 0.0到1.0之间的进度值
            message: 可选的进度消息
        """
        self.progress = max(0.0, min(1.0, progress))  # 确保在0-1范围内
        update = {
            "time": time.time(),
            "progress": self.progress
        }
        if message:
            update["message"] = message
            
        self.progress_updates.append(update)
        logger.debug(f"任务 {self.id} 进度更新: {self.progress:.1%} {message or ''}")
        
    def to_dict(self, include_history: bool = False) -> Dict[str, Any]:
        """
        将任务转换为字典表示
        
        参数:
            include_history: 是否包含完整的进度历史
        
        返回:
            任务的字典表示
        """
        task_dict = {
            "id": self.id,
            "status": self.status,
            "progress": self.progress,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata
        }
        
        # 只在完成或失败状态才包含结果和错误
        if self.status == "completed":
            task_dict["result"] = self.result
        elif self.status == "failed":
            task_dict["error"] = self.error
            
        # 可选包含完整进度历史
        if include_history and self.progress_updates:
            task_dict["progress_history"] = self.progress_updates
        
        return task_dict


class TaskManager:
    """异步任务管理器"""
    
    def __init__(self, max_workers: int = 3, task_timeout: int = 3600):
        """
        初始化任务管理器
        
        参数:
            max_workers: 最大工作线程数
            task_timeout: 任务超时时间（秒）
        """
        self.tasks: Dict[str, Task] = {}  # 任务ID到任务对象的映射
        self.task_queue = queue.Queue()   # 待处理任务队列
        self.max_workers = max_workers    # 最大工作线程数
        self.task_timeout = task_timeout  # 任务超时时间（秒）
        self.workers: List[threading.Thread] = []  # 工作线程列表
        self.running = False              # 管理器运行状态
        self.lock = threading.Lock()      # 用于同步访问任务字典
        
    def start(self):
        """启动任务管理器"""
        with self.lock:
            if self.running:
                return
            
            self.running = True
            
            # 创建工作线程
            for i in range(self.max_workers):
                worker = threading.Thread(
                    target=self._worker_loop,
                    name=f"TaskWorker-{i}",
                    daemon=True
                )
                worker.start()
                self.workers.append(worker)
                
            # 创建监控线程（检查任务超时）
            monitor = threading.Thread(
                target=self._monitor_loop,
                name="TaskMonitor",
                daemon=True
            )
            monitor.start()
            self.workers.append(monitor)
            
            logger.info(f"任务管理器已启动，工作线程数: {self.max_workers}")
        
    def stop(self):
        """停止任务管理器"""
        with self.lock:
            if not self.running:
                return
                
            self.running = False
            
            # 清空任务队列
            while not self.task_queue.empty():
                try:
                    self.task_queue.get_nowait()
                    self.task_queue.task_done()
                except queue.Empty:
                    break
                    
            # 取消所有正在运行的任务
            for task_id, task in self.tasks.items():
                if task.status == "running" or task.status == "pending":
                    task.status = "cancelled"
                    
            logger.info("任务管理器已停止")
    
    def create_task(self, func: Callable, params: Dict[str, Any], 
                   task_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        创建并排队一个新任务
        
        参数:
            func: 要执行的函数
            params: 传递给函数的参数
            task_id: 可选的任务ID，如果不提供则自动生成
            metadata: 可选的任务元数据
            
        返回:
            任务ID
        """
        # 确保任务管理器在运行
        if not self.running:
            self.start()
            
        # 生成任务ID（如果未提供）
        if not task_id:
            task_id = str(uuid.uuid4())
            
        # 创建任务对象
        task = Task(task_id, func, params)
        
        # 添加元数据（如果提供）
        if metadata:
            task.metadata = metadata
            
        # 存储任务并加入队列
        with self.lock:
            self.tasks[task_id] = task
            self.task_queue.put(task_id)
            
        logger.info(f"已创建任务: {task_id}")
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务信息
        
        参数:
            task_id: 任务ID
            
        返回:
            任务信息字典，如果任务不存在则返回None
        """
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return None
            return task.to_dict()
    
    def get_task_detailed(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取详细的任务信息（包括进度历史）
        
        参数:
            task_id: 任务ID
            
        返回:
            详细的任务信息字典，如果任务不存在则返回None
        """
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return None
            return task.to_dict(include_history=True)
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """
        获取所有任务的信息
        
        返回:
            所有任务的信息列表
        """
        with self.lock:
            return [task.to_dict() for task in self.tasks.values()]
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消一个任务
        
        参数:
            task_id: 任务ID
            
        返回:
            如果成功取消则返回True，否则返回False
        """
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
                
            # 只能取消等待中的任务
            if task.status == "pending":
                task.status = "cancelled"
                logger.info(f"已取消任务: {task_id}")
                return True
                
            return False
    
    def update_task_progress(self, task_id: str, progress: float, message: Optional[str] = None) -> bool:
        """
        更新任务进度
        
        参数:
            task_id: 任务ID
            progress: 0.0到1.0之间的进度值
            message: 可选的进度消息
            
        返回:
            如果成功更新则返回True，否则返回False
        """
        with self.lock:
            task = self.tasks.get(task_id)
            if not task or task.status != "running":
                return False
                
            task.update_progress(progress, message)
            return True
    
    def clean_completed_tasks(self, max_age: int = 3600) -> int:
        """
        清理已完成的老任务
        
        参数:
            max_age: 最大保留时间（秒）
            
        返回:
            清理的任务数量
        """
        current_time = time.time()
        cleaned_count = 0
        
        with self.lock:
            task_ids = list(self.tasks.keys())
            for task_id in task_ids:
                task = self.tasks[task_id]
                
                # 只清理已完成、失败或取消的任务
                if task.status in ["completed", "failed", "cancelled"]:
                    # 检查任务是否足够老
                    completed_time = task.completed_at or task.created_at
                    if current_time - completed_time > max_age:
                        del self.tasks[task_id]
                        cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"已清理 {cleaned_count} 个旧任务")
            
        return cleaned_count
    
    def _worker_loop(self):
        """工作线程的主循环"""
        while self.running:
            try:
                # 从队列获取任务ID
                try:
                    task_id = self.task_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # 获取任务对象
                with self.lock:
                    task = self.tasks.get(task_id)
                    
                if not task or task.status == "cancelled":
                    self.task_queue.task_done()
                    continue
                
                # 标记任务为运行中
                with self.lock:
                    task.status = "running"
                    task.started_at = time.time()
                
                # 执行任务
                try:
                    # 将任务对象传入函数，以便更新进度
                    result = task.func(task, **task.params)
                    
                    # 更新任务状态
                    with self.lock:
                        task.status = "completed"
                        task.completed_at = time.time()
                        task.result = result
                        task.progress = 1.0
                        
                    logger.info(f"任务 {task_id} 完成")
                        
                except Exception as e:
                    # 任务执行失败
                    error_msg = str(e)
                    error_traceback = traceback.format_exc()
                    
                    with self.lock:
                        task.status = "failed"
                        task.completed_at = time.time()
                        task.error = {
                            "message": error_msg,
                            "traceback": error_traceback
                        }
                    
                    logger.error(f"任务 {task_id} 执行失败: {error_msg}")
                    logger.debug(error_traceback)
                
                # 标记队列任务完成
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"工作线程发生意外错误: {str(e)}")
                traceback.print_exc()
    
    def _monitor_loop(self):
        """监控线程，用于检查任务超时和清理旧任务"""
        while self.running:
            try:
                # 等待一段时间
                time.sleep(10.0)
                
                current_time = time.time()
                
                # 检查运行中的任务是否超时
                with self.lock:
                    for task_id, task in self.tasks.items():
                        if task.status == "running" and task.started_at:
                            elapsed = current_time - task.started_at
                            if elapsed > self.task_timeout:
                                # 任务超时
                                task.status = "failed"
                                task.completed_at = current_time
                                task.error = {
                                    "message": f"任务超时，执行时间超过 {self.task_timeout} 秒",
                                    "traceback": None
                                }
                                logger.warning(f"任务 {task_id} 超时")
                
                # 清理旧任务
                self.clean_completed_tasks()
                
            except Exception as e:
                logger.error(f"监控线程发生意外错误: {str(e)}")
                traceback.print_exc()


# 全局任务管理器实例
task_manager = TaskManager()

# 确保任务管理器在导入时启动
task_manager.start() 
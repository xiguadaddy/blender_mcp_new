import socket
import json
import threading
import time
import traceback
import bpy
import math
import random
import os

# 配置日志
import logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BlenderMCPServer")

# 导入响应工具模块
from . import response_utils
from . import task_manager

class BlenderMCPServer:
    """
    Blender MCP服务器
    提供TCP接口让外部应用程序控制Blender
    """
    
    def __init__(self, host='localhost', port=9876, buffer_size=40960, debug=False):
        """初始化服务器"""
        self.host = host
        self.port = port
        self.buffer_size = buffer_size
        self.server_socket = None
        self.running = False
        self.thread = None
        self.clients = []
        self.command_handlers = self._register_command_handlers()
        self.last_error = None
        self.debug = debug
        # 防止重复创建标识
        self.last_created_objects = {}
        # 每10秒自动清理一次
        self.last_cleanup_time = time.time()
        
        # 设置日志级别
        if self.debug:
            logger.setLevel(logging.DEBUG)
            print(f"BlenderMCP服务器调试模式已启用")
        else:
            logger.setLevel(logging.INFO)
            
    def is_running(self):
        """返回服务器是否正在运行"""
        return self.running
    
    def _register_command_handlers(self):
        """注册所有可用的命令处理器"""
        return {
            "ping": self._handle_ping,
            "get_scene_info": self._handle_get_scene_info,
            "get_object_info": self._handle_get_object_info,
            "create_object": self._handle_create_object,
            "modify_object": self._handle_modify_object,
            "delete_object": self._handle_delete_object,
            "join_objects": self._handle_join_objects,
            "set_material": self._handle_set_material,
            "set_light_type": self._handle_set_light_type,
            "set_light_energy": self._handle_set_light_energy,
            "set_active_camera": self._handle_set_active_camera,
            "render_scene": self._handle_render_scene,
            "advanced_lighting": self._handle_advanced_lighting,
            "create_advanced_lighting": self._handle_advanced_lighting,  # 添加别名以保持兼容性
            "execute_code": self._handle_execute_code,
            "verify_object_exists": self._handle_verify_object_exists,
            "safe_join_objects": self._handle_safe_join_objects,
            "clear_scene": self._handle_clear_scene,
            
            # 新增的异步任务相关命令
            "render_scene_async": self._handle_render_scene_async,
            "get_task": self._handle_get_task,
            "get_task_detailed": self._handle_get_task_detailed,
            "list_tasks": self._handle_list_tasks,
            "cancel_task": self._handle_cancel_task,
        }
    
    def start(self):
        """启动服务器"""
        if self.running:
            return response_utils.create_error_response("OPERATION_FAILED", "服务器已经在运行")
        
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            self.thread = threading.Thread(target=self._accept_connections)
            self.thread.daemon = True
            self.thread.start()
            return response_utils.create_success_response({"message": f"服务器运行在 {self.host}:{self.port}"})
        except Exception as e:
            self.last_error = str(e)
            return response_utils.create_error_response("OPERATION_FAILED", f"启动服务器失败: {str(e)}")
    
    def stop(self):
        """停止服务器"""
        if not self.running:
            return response_utils.create_error_response("OPERATION_FAILED", "服务器未运行")
        
        try:
            self.running = False
            if self.server_socket:
                self.server_socket.close()
            
            for client in self.clients:
                try:
                    client.close()
                except:
                    pass
            
            self.clients = []
            return response_utils.create_success_response({"message": "服务器已停止"})
        except Exception as e:
            self.last_error = str(e)
            return response_utils.create_error_response("OPERATION_FAILED", f"停止服务器失败: {str(e)}")
    
    def _accept_connections(self):
        """接受新连接的线程函数"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                self.clients.append(client_socket)
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()
            except Exception as e:
                if self.running:  # 只有在服务器应该运行时才报错
                    self.last_error = str(e)
                    print(f"接受连接时出错: {str(e)}")
                time.sleep(0.1)  # 避免CPU占用过高
    
    def _handle_client(self, client_socket, address):
        """处理单个客户端连接"""
        print(f"新客户端连接: {address}")
        while self.running:
            try:
                data = client_socket.recv(self.buffer_size)
                if not data:
                    break
                
                try:
                    # 解析接收到的JSON数据
                    message = json.loads(data.decode('utf-8'))
                    request_id = message.get("id")
                    
                    # 检查是否是JSON-RPC 2.0格式请求
                    is_jsonrpc = message.get("jsonrpc") == "2.0"
                    
                    # 获取命令/方法名和参数
                    if is_jsonrpc:
                        # JSON-RPC 2.0格式
                        method = message.get("method")
                        params = message.get("params", {})
                    else:
                        # 兼容旧格式 - 支持两种命令格式
                        if "command" in message:
                            method = message["command"]
                            params = message.get("params", {})
                        else:
                            method = message.get("type")
                            params = message.get("params", {})
                    
                    if not method:
                        # 无效请求 - 缺少方法/命令
                        if is_jsonrpc:
                            response = response_utils.create_error_response(
                                "INVALID_REQUEST", 
                                "缺少方法名", 
                                request_id=request_id
                            )
                        else:
                            response = {"status": "error", "message": "缺少命令类型"}
                    else:
                        # 获取处理器并执行命令
                        handler = self.command_handlers.get(method)
                        if handler:
                            try:
                                # 执行命令处理器
                                legacy_response = handler(params)
                                
                                # 根据请求格式返回相应格式的响应
                                if is_jsonrpc:
                                    # 转换为JSON-RPC 2.0格式响应
                                    response = response_utils.convert_legacy_response(
                                        legacy_response, 
                                        request_id=request_id
                                    )
                                else:
                                    # 保持原有格式
                                    response = legacy_response
                            except Exception as cmd_error:
                                # 命令执行出错
                                if is_jsonrpc:
                                    response = response_utils.create_error_response(
                                        "INTERNAL_ERROR", 
                                        f"处理命令时出错: {str(cmd_error)}", 
                                        request_id=request_id
                                    )
                                else:
                                    response = {
                                        "status": "error", 
                                        "message": f"处理命令时出错: {str(cmd_error)}"
                                    }
                        else:
                            # 未知命令/方法
                            if is_jsonrpc:
                                response = response_utils.create_error_response(
                                    "METHOD_NOT_FOUND", 
                                    f"未知方法: {method}", 
                                    request_id=request_id
                                )
                            else:
                                response = {
                                    "status": "error", 
                                    "message": f"未知命令: {method}"
                                }
                except json.JSONDecodeError:
                    # JSON解析错误
                    response = response_utils.create_error_response(
                        "PARSE_ERROR", 
                        "无效的JSON格式", 
                        request_id=None
                    )
                except Exception as e:
                    # 其他处理错误
                    response = response_utils.create_error_response(
                        "INTERNAL_ERROR", 
                        f"处理请求时出错: {str(e)}", 
                        request_id=None
                    )
                    traceback.print_exc()
                
                # 发送响应
                client_socket.sendall(json.dumps(response).encode('utf-8'))
                
                # 自动清理过期的对象引用
                current_time = time.time()
                if current_time - self.last_cleanup_time > 10:
                    self._cleanup_stale_objects()
                    self.last_cleanup_time = current_time
                
            except ConnectionError:
                break
            except Exception as e:
                self.last_error = str(e)
                print(f"处理客户端时出错: {str(e)}")
                traceback.print_exc()
                break
        
        try:
            client_socket.close()
        except:
            pass
        
        if client_socket in self.clients:
            self.clients.remove(client_socket)
        print(f"客户端断开连接: {address}")
    
    def _cleanup_stale_objects(self):
        """清理不再存在的对象引用"""
        to_remove = []
        for obj_id, obj_name in self.last_created_objects.items():
            if obj_name not in bpy.data.objects:
                to_remove.append(obj_id)
        
        for obj_id in to_remove:
            del self.last_created_objects[obj_id]
    
    def _handle_ping(self, params):
        """处理ping命令，用于检查服务器是否在线"""
        return {"status": "success", "result": "pong"}
    
    def _handle_get_scene_info(self, params):
        """返回当前场景的信息"""
        try:
            objects = []
            for obj in bpy.data.objects:
                obj_info = {
                    "name": obj.name,
                    "type": obj.type,
                    "location": [obj.location.x, obj.location.y, obj.location.z]
                }
                objects.append(obj_info)
            
            scene_info = {
                "name": bpy.context.scene.name,
                "objects": objects
            }
            return {"status": "success", "result": scene_info}
        except Exception as e:
            return {"status": "error", "message": f"获取场景信息失败: {str(e)}"}
    
    def _handle_get_object_info(self, params):
        """返回特定对象的信息"""
        object_name = params.get("object_name") or params.get("name")
        if not object_name:
            return {"status": "error", "message": "缺少对象名称参数"}
        
        try:
            if object_name not in bpy.data.objects:
                return {"status": "error", "message": f"对象 '{object_name}' 不存在"}
            
            obj = bpy.data.objects[object_name]
            obj_info = {
                "name": obj.name,
                "type": obj.type,
                "location": [obj.location.x, obj.location.y, obj.location.z]
            }
            
            if obj.type == 'MESH':
                obj_info["vertices"] = len(obj.data.vertices)
                obj_info["polygons"] = len(obj.data.polygons)
            elif obj.type == 'LIGHT':
                obj_info["light_type"] = obj.data.type
                obj_info["energy"] = obj.data.energy
                obj_info["color"] = [obj.data.color[0], obj.data.color[1], obj.data.color[2]]
            
            return {"status": "success", "result": obj_info}
        except Exception as e:
            return {"status": "error", "message": f"获取对象信息失败: {str(e)}"}
    
    def _handle_create_object(self, params):
        """创建一个新对象"""
        obj_type = params.get("type")
        name = params.get("name")
        location = params.get("location", [0, 0, 0])
        rotation = params.get("rotation", [0, 0, 0])
        scale = params.get("scale", [1, 1, 1])
        
        if not obj_type:
            return {"status": "error", "message": "缺少对象类型参数"}
        
        # 确保在主线程中执行Blender操作
        def create_object_in_blender():
            try:
                # 生成唯一名称如果未提供
                if not name:
                    base_name = obj_type.capitalize()
                    count = 1
                    while f"{base_name}{count}" in bpy.data.objects:
                        count += 1
                    object_name = f"{base_name}{count}"
                else:
                    # 如果名称已存在，附加数字
                    if name in bpy.data.objects:
                        base_name = name
                        count = 1
                        while f"{base_name}.{count:03d}" in bpy.data.objects:
                            count += 1
                        object_name = f"{base_name}.{count:03d}"
                    else:
                        object_name = name
                
                # 根据类型创建对象
                if obj_type == "CUBE":
                    bpy.ops.mesh.primitive_cube_add(location=location)
                elif obj_type == "SPHERE":
                    bpy.ops.mesh.primitive_uv_sphere_add(location=location)
                elif obj_type == "CYLINDER":
                    bpy.ops.mesh.primitive_cylinder_add(location=location)
                elif obj_type == "PLANE":
                    bpy.ops.mesh.primitive_plane_add(location=location)
                elif obj_type == "CONE":
                    bpy.ops.mesh.primitive_cone_add(location=location)
                elif obj_type == "TORUS":
                    bpy.ops.mesh.primitive_torus_add(location=location)
                elif obj_type == "EMPTY":
                    bpy.ops.object.empty_add(location=location)
                elif obj_type == "CAMERA":
                    bpy.ops.object.camera_add(location=location)
                elif obj_type == "LIGHT":
                    bpy.ops.object.light_add(type='POINT', location=location)
                else:
                    return {"status": "error", "message": f"不支持的对象类型: {obj_type}"}
                
                # 获取新创建的对象
                obj = bpy.context.active_object
                obj.name = object_name
                
                # 设置旋转和缩放
                obj.rotation_euler = [
                    rotation[0], rotation[1], rotation[2]
                ]
                obj.scale = [
                    scale[0], scale[1], scale[2]
                ]
                
                # 存储最后创建的对象引用
                obj_id = f"{obj_type}_{int(time.time()*1000)}"
                self.last_created_objects[obj_id] = object_name
                
                # 确保Blender更新场景
                bpy.context.view_layer.update()
                
                return {"status": "success", "result": {"name": object_name, "id": obj_id}}
            except Exception as e:
                traceback.print_exc()
                return {"status": "error", "message": f"创建对象失败: {str(e)}"}
        
        # 调用Blender API
        return self._run_in_main_thread(create_object_in_blender)
    
    def _handle_modify_object(self, params):
        """修改现有对象的属性"""
        name = params.get("name")
        location = params.get("location")
        rotation = params.get("rotation")
        scale = params.get("scale")
        
        if not name:
            return {"status": "error", "message": "缺少对象名称参数"}
        
        def modify_object_in_blender():
            try:
                if name not in bpy.data.objects:
                    return {"status": "error", "message": f"对象 '{name}' 不存在"}
                
                obj = bpy.data.objects[name]
                
                if location:
                    obj.location = (location[0], location[1], location[2])
                
                if rotation:
                    obj.rotation_euler = (rotation[0], rotation[1], rotation[2])
                
                if scale:
                    obj.scale = (scale[0], scale[1], scale[2])
                
                # 确保Blender更新场景
                bpy.context.view_layer.update()
                
                return {"status": "success", "result": {"name": name}}
            except Exception as e:
                return {"status": "error", "message": f"修改对象失败: {str(e)}"}
        
        return self._run_in_main_thread(modify_object_in_blender)
    
    def _handle_delete_object(self, params):
        """删除指定的对象"""
        name = params.get("name")
        
        if not name:
            return {"status": "error", "message": "缺少对象名称参数"}
        
        def delete_object_in_blender():
            try:
                if name not in bpy.data.objects:
                    return {"status": "error", "message": f"对象 '{name}' 不存在"}
                
                obj = bpy.data.objects[name]
                bpy.data.objects.remove(obj)
                
                # 确保Blender更新场景
                bpy.context.view_layer.update()
                
                return {"status": "success", "result": {"name": name}}
            except Exception as e:
                return {"status": "error", "message": f"删除对象失败: {str(e)}"}
        
        return self._run_in_main_thread(delete_object_in_blender)
    
    def _handle_join_objects(self, params):
        """将多个对象合并为一个"""
        objects = params.get("objects", [])
        target_object = params.get("target_object")
        
        if not objects or len(objects) < 2:
            return {"status": "error", "message": "至少需要两个对象才能合并"}
        
        if not target_object:
            target_object = objects[0]
        
        def join_objects_in_blender():
            try:
                # 验证所有对象是否存在
                missing_objects = [name for name in objects if name not in bpy.data.objects]
                if missing_objects:
                    return {
                        "status": "error",
                        "message": f"以下对象不存在: {', '.join(missing_objects)}"
                    }
                
                if target_object not in bpy.data.objects:
                    return {"status": "error", "message": f"目标对象 '{target_object}' 不存在"}
                
                # 确保所有对象都是网格
                non_mesh_objects = [
                    name for name in objects
                    if bpy.data.objects[name].type != 'MESH'
                ]
                if non_mesh_objects:
                    return {
                        "status": "error",
                        "message": f"以下对象不是网格，无法合并: {', '.join(non_mesh_objects)}"
                    }
                
                # 选择所有对象
                bpy.ops.object.select_all(action='DESELECT')
                
                # 首先选择目标对象并使其活动
                target = bpy.data.objects[target_object]
                
                # 记录目标对象的材质
                original_materials = []
                if hasattr(target.data, 'materials') and len(target.data.materials) > 0:
                    for mat_slot in target.material_slots:
                        if mat_slot.material:
                            original_materials.append(mat_slot.material)
                    logger.info(f"记录目标对象 {target_object} 的 {len(original_materials)} 个材质")
                
                # 记录材质的引用计数
                material_users = {}
                for mat in original_materials:
                    material_users[mat.name] = mat.users
                    logger.info(f"材质 {mat.name} 的初始引用计数: {mat.users}")
                
                target.select_set(True)
                bpy.context.view_layer.objects.active = target
                
                # 然后选择其他对象
                for name in objects:
                    if name != target_object:
                        obj = bpy.data.objects[name]
                        obj.select_set(True)
                
                # 合并对象
                bpy.ops.object.join()
                
                # 确保Blender更新场景
                bpy.context.view_layer.update()
                
                # 确保合并后重新应用原始材质
                if original_materials:
                    logger.info(f"重新应用原始材质到合并后的对象: {target.name}")
                    
                    # 保存当前材质作为备份
                    current_materials = []
                    for i, mat_slot in enumerate(target.material_slots):
                        if mat_slot.material:
                            current_materials.append(mat_slot.material)
                    
                    # 检查合并后的材质是否与原始材质相同
                    materials_changed = False
                    if len(current_materials) != len(original_materials):
                        materials_changed = True
                        logger.info(f"材质数量改变: {len(current_materials)} vs 原始 {len(original_materials)}")
                    else:
                        for i, mat in enumerate(original_materials):
                            if current_materials[i] != mat:
                                materials_changed = True
                                logger.info(f"材质 #{i} 已改变: {current_materials[i].name} vs 原始 {mat.name}")
                    
                    # 如果材质发生变化，重新应用原始材质
                    if materials_changed:
                        logger.info("材质已改变，重新应用原始材质")
                        
                        # 清除所有现有材质
                        while len(target.data.materials) > 0:
                            target.data.materials.pop(index=0)
                        
                        # 重新应用原始材质
                        for mat in original_materials:
                            target.data.materials.append(mat)
                        
                        # 检查材质的引用计数
                        for mat in original_materials:
                            new_users = mat.users
                            old_users = material_users.get(mat.name, 0)
                            logger.info(f"材质 {mat.name} 的引用计数: {new_users} (之前: {old_users})")
                    else:
                        logger.info("材质保持不变，无需重新应用")
                
                return {"status": "success", "result": {"name": target_object}}
            except Exception as e:
                traceback.print_exc()
                return {"status": "error", "message": f"合并对象失败: {str(e)}"}
        
        return self._run_in_main_thread(join_objects_in_blender)
    
    def _handle_safe_join_objects(self, params):
        """安全地合并多个对象，包括存在性验证和错误恢复"""
        objects = params.get("objects", [])
        target_object = params.get("target_object")
        
        if not objects or len(objects) < 2:
            return {"status": "error", "message": "至少需要两个对象才能合并"}
        
        if not target_object:
            target_object = objects[0]
        
        def safe_join_objects_in_blender():
            try:
                # 验证所有对象是否存在
                existing_objects = []
                for name in objects:
                    if name in bpy.data.objects:
                        existing_objects.append(name)
                    else:
                        print(f"警告: 对象 '{name}' 不存在，将从合并列表中排除")
                
                if len(existing_objects) < 2:
                    return {
                        "status": "error",
                        "message": f"没有足够的有效对象来执行合并操作，找到 {len(existing_objects)} 个，需要至少2个"
                    }
                
                # 确保目标对象存在
                if target_object not in bpy.data.objects:
                    # 如果指定的目标不存在，使用第一个有效对象
                    if existing_objects:
                        target_object = existing_objects[0]
                        print(f"注意: 原目标对象不存在，将使用 '{target_object}' 作为目标")
                    else:
                        return {"status": "error", "message": "没有有效的目标对象可用"}
                else:
                    # 确保目标对象在合并列表中
                    if target_object not in existing_objects:
                        existing_objects.append(target_object)
                
                # 过滤出可以合并的网格对象
                mesh_objects = []
                for name in existing_objects:
                    obj = bpy.data.objects[name]
                    if obj.type == 'MESH':
                        mesh_objects.append(name)
                    else:
                        print(f"注意: 对象 '{name}' 不是网格，将从合并列表中排除")
                
                if len(mesh_objects) < 2:
                    return {
                        "status": "error", 
                        "message": f"没有足够的网格对象来执行合并操作，找到 {len(mesh_objects)} 个网格，需要至少2个"
                    }
                
                # 确保目标是网格对象
                if target_object not in mesh_objects and mesh_objects:
                    target_object = mesh_objects[0]
                    print(f"注意: 原目标不是网格对象，将使用 '{target_object}' 作为目标")
                
                # 备份对象以便出错时恢复
                backup_data = {}
                for name in mesh_objects:
                    obj = bpy.data.objects[name]
                    backup_data[name] = {
                        "location": obj.location.copy(),
                        "rotation": obj.rotation_euler.copy(),
                        "scale": obj.scale.copy()
                    }
                
                # 准备合并
                bpy.ops.object.select_all(action='DESELECT')
                
                target = bpy.data.objects[target_object]
                
                # 记录目标对象的材质
                original_materials = []
                if hasattr(target.data, 'materials') and len(target.data.materials) > 0:
                    for mat_slot in target.material_slots:
                        if mat_slot.material:
                            original_materials.append(mat_slot.material)
                    logger.info(f"记录目标对象 {target_object} 的 {len(original_materials)} 个材质")
                
                # 记录材质的引用计数
                material_users = {}
                for mat in original_materials:
                    material_users[mat.name] = mat.users
                    logger.info(f"材质 {mat.name} 的初始引用计数: {mat.users}")
                
                target.select_set(True)
                bpy.context.view_layer.objects.active = target
                
                # 选择其他要合并的对象
                for name in mesh_objects:
                    if name != target_object:
                        obj = bpy.data.objects[name]
                        obj.select_set(True)
                
                # 执行合并操作
                try:
                    bpy.ops.object.join()
                    
                    # 确保Blender更新场景
                    bpy.context.view_layer.update()
                    
                    # 验证目标对象仍然存在
                    if target_object not in bpy.data.objects:
                        raise Exception(f"合并后目标对象 '{target_object}' 不存在")
                    
                    # 确保合并后重新应用原始材质
                    if original_materials:
                        logger.info(f"重新应用原始材质到合并后的对象: {target.name}")
                        
                        # 保存当前材质作为备份
                        current_materials = []
                        for i, mat_slot in enumerate(target.material_slots):
                            if mat_slot.material:
                                current_materials.append(mat_slot.material)
                        
                        # 检查合并后的材质是否与原始材质相同
                        materials_changed = False
                        if len(current_materials) != len(original_materials):
                            materials_changed = True
                            logger.info(f"材质数量改变: {len(current_materials)} vs 原始 {len(original_materials)}")
                        else:
                            for i, mat in enumerate(original_materials):
                                if current_materials[i] != mat:
                                    materials_changed = True
                                    logger.info(f"材质 #{i} 已改变: {current_materials[i].name} vs 原始 {mat.name}")
                        
                        # 如果材质发生变化，重新应用原始材质
                        if materials_changed:
                            logger.info("材质已改变，重新应用原始材质")
                            
                            # 清除所有现有材质
                            while len(target.data.materials) > 0:
                                target.data.materials.pop(index=0)
                            
                            # 重新应用原始材质
                            for mat in original_materials:
                                target.data.materials.append(mat)
                            
                            # 检查材质的引用计数
                            for mat in original_materials:
                                new_users = mat.users
                                old_users = material_users.get(mat.name, 0)
                                logger.info(f"材质 {mat.name} 的引用计数: {new_users} (之前: {old_users})")
                        else:
                            logger.info("材质保持不变，无需重新应用")
                    
                    return {"status": "success", "result": {"name": target_object}}
                except Exception as e:
                    # 合并失败，尝试恢复对象
                    print(f"合并失败: {str(e)}，尝试恢复对象状态")
                    
                    # 恢复可能被修改的对象
                    for name, data in backup_data.items():
                        if name in bpy.data.objects:
                            obj = bpy.data.objects[name]
                            obj.location = data["location"]
                            obj.rotation_euler = data["rotation"]
                            obj.scale = data["scale"]
                    
                    raise Exception(f"安全合并失败: {str(e)}")
                
            except Exception as e:
                traceback.print_exc()
                return {"status": "error", "message": f"安全合并对象失败: {str(e)}"}
        
        return self._run_in_main_thread(safe_join_objects_in_blender)
    
    def _handle_verify_object_exists(self, params):
        """验证对象是否存在于场景中"""
        name = params.get("object_name") or params.get("name")
        
        if not name:
            return {"status": "error", "message": "缺少对象名称参数"}
        
        def verify_object_in_blender():
            try:
                exists = name in bpy.data.objects
                return {
                    "status": "success", 
                    "result": {
                        "exists": exists,
                        "name": name
                    }
                }
            except Exception as e:
                return {"status": "error", "message": f"验证对象存在性失败: {str(e)}"}
        
        return self._run_in_main_thread(verify_object_in_blender)
    
    def _handle_set_material(self, params):
        """为对象设置材质"""
        name = params.get("name") or params.get("object") or params.get("object_name")
        color = params.get("color", [0.8, 0.8, 0.8, 1.0])
        roughness = params.get("roughness", 0.5)
        metallic = params.get("metallic", 0.0)
        material_name = params.get("material_name")
        
        if not name:
            return {"status": "error", "message": "缺少对象名称参数"}
        
        def set_material_in_blender():
            # 确保material_name在函数开始时就存在，防止引用错误
            nonlocal material_name
            temp_material_name = material_name  # 保存外部传入的值
            
            try:
                # 获取对象
                obj = bpy.data.objects.get(name)
                if not obj:
                    return {"status": "error", "message": f"对象 '{name}' 不存在"}
                
                # 确保对象可以接受材质
                if not hasattr(obj, 'data') or not hasattr(obj.data, 'materials'):
                    return {"status": "error", "message": f"对象 {name} 不能接受材质"}
                
                # 创建或获取材质
                if temp_material_name:
                    mat = bpy.data.materials.get(temp_material_name)
                    if not mat:
                        mat = bpy.data.materials.new(name=temp_material_name)
                        logger.info(f"创建新材质: {temp_material_name}")
                else:
                    # 如果未提供材质名称，则生成唯一名称
                    mat_name = f"{name}_material"
                    mat = bpy.data.materials.get(mat_name)
                    if not mat:
                        mat = bpy.data.materials.new(name=mat_name)
                    temp_material_name = mat_name
                    logger.info(f"使用材质: {mat_name}")
                
                # 设置材质节点
                if mat:
                    if not mat.use_nodes:
                        mat.use_nodes = True
                    
                    # 获取或创建Principled BSDF节点
                    principled = None
                    for node in mat.node_tree.nodes:
                        if node.type == 'BSDF_PRINCIPLED':
                            principled = node
                            break
                    
                    if not principled:
                        # 清理现有节点以避免冲突
                        mat.node_tree.nodes.clear()
                        
                        # 创建新的Principled BSDF节点
                        principled = mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
                        principled.location = (0, 0)
                        
                        # 创建新的输出节点
                        output = mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
                        output.location = (300, 0)
                        
                        # 连接节点
                        mat.node_tree.links.new(principled.outputs[0], output.inputs[0])
                    
                    # 设置颜色
                    if color and len(color) >= 3:
                        # 确保有Alpha通道
                        alpha = 1.0 if len(color) < 4 else color[3]
                        color_rgba = (color[0], color[1], color[2], alpha)
                        
                        # 同时设置diffuse_color和node的Base Color
                        if hasattr(mat, "diffuse_color"):
                            mat.diffuse_color = color_rgba
                            logger.info(f"设置diffuse_color: {color_rgba}")
                        
                        principled.inputs['Base Color'].default_value = color_rgba
                        logger.info(f"设置Base Color: {color_rgba}")
                        
                        # 根据颜色调整材质其他属性
                        if color[0] > 0.8 and color[1] > 0.8 and color[2] > 0.8:
                            # 白色物体调整
                            principled.inputs['Metallic'].default_value = 0.1
                            principled.inputs['Roughness'].default_value = 0.2
                            if 'Specular' in principled.inputs:
                                principled.inputs['Specular'].default_value = 0.8
                        elif color[0] < 0.2 and color[1] < 0.2 and color[2] < 0.2:
                            # 黑色物体调整
                            principled.inputs['Metallic'].default_value = 0.7
                            principled.inputs['Roughness'].default_value = 0.4
                            if 'Specular' in principled.inputs:
                                principled.inputs['Specular'].default_value = 0.5
                        else:
                            # 其他颜色调整
                            principled.inputs['Metallic'].default_value = metallic
                            principled.inputs['Roughness'].default_value = roughness
                            if 'Specular' in principled.inputs:
                                principled.inputs['Specular'].default_value = 0.6
                    
                    # 将材质分配给对象 - 使用与原版相同的逻辑
                    if len(obj.material_slots) == 0:
                        # 如果没有材质槽，添加新材质
                        obj.data.materials.append(mat)
                        logger.info(f"添加材质到对象 {name}: {mat.name}")
                    else:
                        # 更新现有材质槽
                        obj.material_slots[0].material = mat
                        logger.info(f"更新对象 {name} 的材质: {mat.name}")
                    
                    # 确保所有材质槽都有材质
                    for slot in obj.material_slots:
                        if slot.material is None:
                            slot.material = mat
                    
                    # 确保材质更新正确显示
                    bpy.context.view_layer.update()
                    
                    # 确保对象是活动对象并被选中，这有助于材质更新
                    bpy.context.view_layer.objects.active = obj
                    obj.select_set(True)
                    
                    # 设置渲染引擎 - 检测并使用可用的引擎
                    available_engines = []
                    for engine in ['CYCLES', 'BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'BLENDER_WORKBENCH']:
                        try:
                            bpy.context.scene.render.engine = engine
                            available_engines.append(engine)
                            logger.info(f"可用渲染引擎: {engine}")
                            # 如果成功设置了一个引擎，就跳出循环
                            break
                        except:
                            pass
                    
                    if not available_engines:
                        logger.warning("无法设置任何渲染引擎")
                    
                    return {
                        "status": "success", 
                        "object": name,
                        "material": mat.name,
                        "color": color if color else None
                    }
                else:
                    return {"status": "error", "message": f"无法创建或找到材质"}
                
            except Exception as e:
                logger.error(f"设置材质失败: {str(e)}")
                traceback.print_exc()
                return {"status": "error", "message": f"设置材质失败: {str(e)}"}
        
        return self._run_in_main_thread(set_material_in_blender)
    
    def _handle_set_light_type(self, params):
        """设置灯光类型"""
        name = params.get("object_name", params.get("name"))
        light_type = params.get("light_type")
        
        if not name:
            return {"status": "error", "message": "缺少灯光名称参数"}
        
        if not light_type:
            return {"status": "error", "message": "缺少灯光类型参数"}
        
        valid_types = ['POINT', 'SUN', 'SPOT', 'AREA']
        if light_type not in valid_types:
            return {"status": "error", "message": f"无效的灯光类型: {light_type}. 有效类型: {', '.join(valid_types)}"}
        
        def set_light_type_in_blender():
            try:
                if name not in bpy.data.objects:
                    return {"status": "error", "message": f"对象 '{name}' 不存在"}
                
                obj = bpy.data.objects[name]
                if obj.type != 'LIGHT':
                    return {"status": "error", "message": f"对象 '{name}' 不是灯光"}
                
                obj.data.type = light_type
                
                return {"status": "success", "result": {"name": name, "light_type": light_type}}
            except Exception as e:
                return {"status": "error", "message": f"设置灯光类型失败: {str(e)}"}
        
        return self._run_in_main_thread(set_light_type_in_blender)
    
    def _handle_set_light_energy(self, params):
        """设置灯光能量/强度"""
        name = params.get("object_name", params.get("name"))
        energy = params.get("energy")
        
        if not name:
            return {"status": "error", "message": "缺少灯光名称参数"}
        
        if energy is None:
            return {"status": "error", "message": "缺少灯光能量参数"}
        
        def set_light_energy_in_blender():
            try:
                if name not in bpy.data.objects:
                    return {"status": "error", "message": f"对象 '{name}' 不存在"}
                
                obj = bpy.data.objects[name]
                if obj.type != 'LIGHT':
                    return {"status": "error", "message": f"对象 '{name}' 不是灯光"}
                
                obj.data.energy = float(energy)
                
                return {"status": "success", "result": {"name": name, "energy": float(energy)}}
            except Exception as e:
                return {"status": "error", "message": f"设置灯光能量失败: {str(e)}"}
        
        return self._run_in_main_thread(set_light_energy_in_blender)
    
    def _handle_set_active_camera(self, params):
        """设置活动相机"""
        name = params.get("object_name", params.get("name"))
        
        if not name:
            return {"status": "error", "message": "缺少相机名称参数"}
        
        def set_active_camera_in_blender():
            try:
                if name not in bpy.data.objects:
                    return {"status": "error", "message": f"对象 '{name}' 不存在"}
                
                obj = bpy.data.objects[name]
                if obj.type != 'CAMERA':
                    return {"status": "error", "message": f"对象 '{name}' 不是相机"}
                
                bpy.context.scene.camera = obj
                
                return {"status": "success", "result": {"name": name}}
            except Exception as e:
                return {"status": "error", "message": f"设置活动相机失败: {str(e)}"}
        
        return self._run_in_main_thread(set_active_camera_in_blender)
    
    def _handle_render_scene(self, params):
        """渲染当前场景并保存图像"""
        resolution_x = params.get("resolution_x", 1920)
        resolution_y = params.get("resolution_y", 1080)
        output_path = params.get("output_path", "//render.png")
        
        def render_scene_in_blender():
            try:
                logger.info(f"开始渲染场景，分辨率: {resolution_x}x{resolution_y}")
                
                # 检查活动相机
                if not bpy.context.scene.camera:
                    return {"status": "error", "message": "渲染失败：场景中没有活动相机"}
                
                # 设置渲染引擎 - 检测并使用可用的引擎
                engine_set = False
                for engine in ['CYCLES', 'BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'BLENDER_WORKBENCH']:
                    try:
                        bpy.context.scene.render.engine = engine
                        logger.info(f"使用渲染引擎: {engine}")
                        engine_set = True
                        break
                    except:
                        logger.warning(f"引擎 {engine} 不可用")
                
                if not engine_set:
                    return {"status": "error", "message": "渲染失败：无法设置任何渲染引擎"}
                
                # 设置渲染属性
                bpy.context.scene.render.resolution_x = resolution_x
                bpy.context.scene.render.resolution_y = resolution_y
                logger.info(f"设置渲染分辨率: {resolution_x}x{resolution_y}")
                
                # 处理输出路径
                render_path = output_path
                # 如果是相对路径（以//开头），转换为绝对路径
                if output_path.startswith("//"):
                    import tempfile
                    # 使用临时目录作为备选路径
                    temp_dir = tempfile.gettempdir()
                    file_name = output_path[2:]  # 去掉//前缀
                    render_path = os.path.join(temp_dir, file_name)
                
                logger.info(f"渲染输出将保存到: {render_path}")
                bpy.context.scene.render.filepath = render_path
                
                # 确保渲染前更新场景
                bpy.context.view_layer.update()
                
                # 执行渲染操作
                logger.info("执行渲染操作...")
                bpy.ops.render.render(write_still=True)
                logger.info("渲染操作完成")
                
                # 验证渲染是否成功
                import os
                if os.path.exists(render_path):
                    file_size = os.path.getsize(render_path)
                    logger.info(f"渲染文件已创建，大小: {file_size} 字节")
                else:
                    logger.warning(f"警告：渲染文件未创建 {render_path}")
                
                return {
                    "status": "success", 
                    "result": {
                        "resolution": [resolution_x, resolution_y],
                        "path": render_path  # 返回实际使用的路径
                    }
                }
            except Exception as e:
                logger.error(f"渲染场景失败: {str(e)}")
                traceback.print_exc()
                return {"status": "error", "message": f"渲染场景失败: {str(e)}"}
        
        return self._run_in_main_thread(render_scene_in_blender)
    
    def _handle_advanced_lighting(self, params):
        """创建高级照明设置"""
        name = params.get("name", "AdvancedLight")
        light_type = params.get("light_type", "AREA")
        location = params.get("location", [0, 0, 5])
        rotation = params.get("rotation", [0, 0, 0])  # 确保rotation始终有默认值
        energy = params.get("energy", 100)
        color = params.get("color", [1.0, 1.0, 1.0])
        size = params.get("size", 5.0)
        shadow = params.get("shadow", True)
        
        def create_advanced_lighting_in_blender():
            try:
                # 设置渲染引擎 - 先尝试设置一个兼容的渲染引擎以确保灯光效果正确
                engine_set = False
                for engine in ['CYCLES', 'BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'BLENDER_WORKBENCH']:
                    try:
                        bpy.context.scene.render.engine = engine
                        logger.info(f"使用渲染引擎: {engine}")
                        engine_set = True
                        break
                    except Exception as e:
                        logger.warning(f"引擎 {engine} 不可用: {str(e)}")
                
                if not engine_set:
                    logger.warning("无法设置任何渲染引擎，可能会影响灯光效果")
                
                # 创建灯光数据
                light_data = bpy.data.lights.new(name=name, type=light_type)
                
                # 设置灯光参数
                light_data.energy = energy
                light_data.color = color
                light_data.use_shadow = shadow
                
                # 根据类型设置特定参数
                if light_type == "SPOT":
                    light_data.spot_size = math.radians(45.0)  # 45度聚光角度
                    light_data.spot_blend = 0.15
                elif light_type == "SUN":
                    light_data.angle = math.radians(0.526)  # 太阳角度
                elif light_type == "AREA":
                    light_data.shape = 'RECTANGLE'
                    light_data.size = size
                    light_data.size_y = size if isinstance(size, (int, float)) else size[1] if len(size) > 1 else size[0]
                
                # 创建灯光对象
                light_obj = bpy.data.objects.new(name=name, object_data=light_data)
                
                # 设置位置和旋转
                light_obj.location = location
                
                # 完全重写rotation处理逻辑，确保安全
                rot_value = rotation  # 使用本地变量，避免引用外部变量
                if rot_value is not None and isinstance(rot_value, (list, tuple)) and len(rot_value) >= 3:
                    # 检查最大绝对值，确保安全使用max函数
                    max_abs = 0
                    for x in rot_value:
                        if abs(x) > max_abs:
                            max_abs = abs(x)
                    
                    # 将角度转换为弧度（如果提供的是角度）
                    if max_abs > 6.3:  # 如果角度大于2π，假设是角度制
                        rot_value = [math.radians(x) for x in rot_value]
                    
                    # 设置旋转值
                    light_obj.rotation_euler = rot_value
                else:
                    # 默认旋转
                    light_obj.rotation_euler = (0, 0, 0)
                
                # 添加到场景
                bpy.context.collection.objects.link(light_obj)
                
                return {
                    "status": "success",
                    "object": light_obj.name,  # 使用与set_material相同的格式
                    "type": "LIGHT",
                    "light_type": light_type,
                    "energy": energy,
                    "location": list(light_obj.location),
                    "rotation": list(light_obj.rotation_euler)
                }
            except Exception as e:
                logger.error(f"创建高级照明失败: {str(e)}")
                traceback.print_exc()
                return {"status": "error", "message": f"创建高级照明失败: {str(e)}"}
        
        return self._run_in_main_thread(create_advanced_lighting_in_blender)
    
    def _handle_execute_code(self, params):
        """执行任意Python代码，高级功能，谨慎使用"""
        code = params.get("code")
        
        if not code:
            return {"status": "error", "message": "缺少代码参数"}
        
        def execute_code_in_blender():
            try:
                # 创建局部和全局变量字典
                locals_dict = {}
                globals_dict = {"bpy": bpy}
                
                # 执行代码
                exec(code, globals_dict, locals_dict)
                
                # 提取可能的返回值
                result = locals_dict.get("result", "代码执行成功，无返回值")
                
                return {"status": "success", "result": result}
            except Exception as e:
                traceback.print_exc()
                return {"status": "error", "message": f"执行代码失败: {str(e)}"}
        
        return self._run_in_main_thread(execute_code_in_blender)
    
    def _handle_clear_scene(self, params):
        """清除场景中的所有对象"""
        def clear_scene_in_blender():
            try:
                # 删除所有对象
                bpy.ops.object.select_all(action='SELECT')
                bpy.ops.object.delete()
                
                # 确保Blender更新场景
                bpy.context.view_layer.update()
                
                return {"status": "success", "result": "场景已清除"}
            except Exception as e:
                return {"status": "error", "message": f"清除场景失败: {str(e)}"}
        
        return self._run_in_main_thread(clear_scene_in_blender)
    
    def _handle_render_scene_async(self, params):
        """异步渲染当前场景并保存图像"""
        resolution_x = params.get("resolution_x", 1920)
        resolution_y = params.get("resolution_y", 1080)
        output_path = params.get("output_path", "//render.png")
        
        # 定义任务函数
        def render_task(task, resolution_x=1920, resolution_y=1080, output_path="//render.png"):
            """在任务中执行渲染"""
            try:
                # 更新初始进度
                task.update_progress(0.1, "准备渲染...")
                
                # 检查活动相机
                if not bpy.context.scene.camera:
                    raise Exception("渲染失败：场景中没有活动相机")
                
                # 更新进度
                task.update_progress(0.2, "设置渲染引擎...")
                
                # 设置渲染引擎
                engine_set = False
                for engine in ['CYCLES', 'BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'BLENDER_WORKBENCH']:
                    try:
                        bpy.context.scene.render.engine = engine
                        logger.info(f"使用渲染引擎: {engine}")
                        engine_set = True
                        break
                    except:
                        logger.warning(f"引擎 {engine} 不可用")
                
                if not engine_set:
                    raise Exception("渲染失败：无法设置任何渲染引擎")
                
                # 更新进度
                task.update_progress(0.3, "配置渲染参数...")
                
                # 设置渲染属性
                bpy.context.scene.render.resolution_x = resolution_x
                bpy.context.scene.render.resolution_y = resolution_y
                
                # 处理输出路径
                render_path = output_path
                # 如果是相对路径（以//开头），转换为绝对路径
                if output_path.startswith("//"):
                    import tempfile
                    # 使用临时目录作为备选路径
                    temp_dir = tempfile.gettempdir()
                    file_name = output_path[2:]  # 去掉//前缀
                    render_path = os.path.join(temp_dir, file_name)
                
                logger.info(f"渲染输出将保存到: {render_path}")
                bpy.context.scene.render.filepath = render_path
                
                # 确保渲染前更新场景
                task.update_progress(0.4, "更新场景...")
                bpy.context.view_layer.update()
                
                # 执行渲染操作
                task.update_progress(0.5, "开始渲染...")
                logger.info("开始异步渲染...")
                bpy.ops.render.render(write_still=True)
                
                # 渲染完成后验证
                task.update_progress(0.9, "验证输出...")
                import os
                if os.path.exists(render_path):
                    file_size = os.path.getsize(render_path)
                    logger.info(f"渲染文件已创建，大小: {file_size} 字节")
                else:
                    logger.warning(f"警告：渲染文件未创建 {render_path}")
                
                # 渲染完成
                task.update_progress(1.0, "渲染完成")
                
                return {
                    "resolution": [resolution_x, resolution_y],
                    "path": render_path
                }
                
            except Exception as e:
                logger.error(f"异步渲染失败: {str(e)}")
                traceback.print_exc()
                raise
        
        # 使用任务管理器创建渲染任务
        task_id = task_manager.task_manager.create_task(
            render_task, 
            {
                "resolution_x": resolution_x,
                "resolution_y": resolution_y,
                "output_path": output_path
            },
            metadata={
                "type": "render",
                "description": f"渲染场景 ({resolution_x}x{resolution_y})"
            }
        )
        
        # 返回任务ID
        return {
            "status": "success", 
            "task_id": task_id,
            "message": "渲染任务已创建并添加到队列"
        }
    
    def _handle_get_task(self, params):
        """获取任务状态"""
        task_id = params.get("task_id")
        if not task_id:
            return {
                "status": "error", 
                "message": "缺少任务ID参数"
            }
        
        task_info = task_manager.task_manager.get_task(task_id)
        if not task_info:
            return {
                "status": "error", 
                "message": f"任务 '{task_id}' 不存在"
            }
        
        return {
            "status": "success", 
            "task": task_info
        }
    
    def _handle_get_task_detailed(self, params):
        """获取任务详细状态（包括进度历史）"""
        task_id = params.get("task_id")
        if not task_id:
            return {
                "status": "error", 
                "message": "缺少任务ID参数"
            }
        
        task_info = task_manager.task_manager.get_task_detailed(task_id)
        if not task_info:
            return {
                "status": "error", 
                "message": f"任务 '{task_id}' 不存在"
            }
        
        return {
            "status": "success", 
            "task": task_info
        }
    
    def _handle_list_tasks(self, params):
        """列出所有任务"""
        status_filter = params.get("status")  # 可选的状态过滤
        tasks = task_manager.task_manager.get_all_tasks()
        
        # 如果提供了状态过滤，则过滤任务列表
        if status_filter:
            tasks = [task for task in tasks if task["status"] == status_filter]
        
        return {
            "status": "success", 
            "tasks": tasks,
            "count": len(tasks)
        }
    
    def _handle_cancel_task(self, params):
        """取消任务"""
        task_id = params.get("task_id")
        if not task_id:
            return {
                "status": "error", 
                "message": "缺少任务ID参数"
            }
        
        success = task_manager.task_manager.cancel_task(task_id)
        if not success:
            return {
                "status": "error", 
                "message": f"无法取消任务 '{task_id}'，任务可能不存在或已在运行"
            }
        
        return {
            "status": "success", 
            "message": f"任务 '{task_id}' 已取消",
            "task_id": task_id
        }
    
    def _run_in_main_thread(self, func):
        """在Blender主线程中运行函数"""
        if threading.current_thread() is threading.main_thread():
            # 如果当前已在主线程，直接执行
            return func()
        else:
            # 否则，需要使用主线程执行并等待结果
            # 由于bpy.app.timers.register不会返回结果，我们需要使用事件来同步
            result_container = {"result": None, "done": False, "error": None}
            
            def wrapper():
                try:
                    result_container["result"] = func()
                    # 检查结果是否为字典类型
                    if isinstance(result_container["result"], dict):
                        # 确保字典中有status字段
                        if "status" not in result_container["result"]:
                            result_container["result"]["status"] = "success"
                except Exception as e:
                    logger.error(f"主线程执行失败: {str(e)}")
                    traceback.print_exc()
                    result_container["error"] = str(e)
                    result_container["result"] = {"status": "error", "message": f"执行操作失败: {str(e)}"}
                finally:
                    result_container["done"] = True
                return None  # 必须返回None以防止timer重复执行
            
            # 注册到主线程执行
            bpy.app.timers.register(wrapper, first_interval=0.0)
            
            # 获取调用函数的名称，用于判断是否是耗时操作
            func_name = func.__name__ if hasattr(func, '__name__') else str(func)
            
            # 根据操作类型设置不同的超时时间
            if 'render' in func_name.lower():
                timeout = 120.0  # 渲染需要更长时间
                logger.info(f"渲染操作超时时间设置为 {timeout} 秒")
            elif any(op in func_name.lower() for op in ['join', 'merge', 'combine']):
                timeout = 30.0  # 合并操作需要中等时间
                logger.info(f"合并操作超时时间设置为 {timeout} 秒")
            elif 'advanced_lighting' in func_name.lower() or 'material' in func_name.lower():
                timeout = 20.0  # 高级照明和材质设置需要一些时间
                logger.info(f"高级照明/材质操作超时时间设置为 {timeout} 秒")
            else:
                timeout = 10.0  # 其他操作的默认超时
                logger.info(f"标准操作超时时间设置为 {timeout} 秒")
            
            # 等待结果
            start_time = time.time()
            logger.info(f"开始等待主线程执行 {func_name}，超时时间: {timeout}秒")
            
            # 检查完成状态
            while not result_container["done"] and time.time() - start_time < timeout:
                time.sleep(0.05)
            
            # 超时处理
            if not result_container["done"]:
                logger.error(f"命令超时: {func_name}")
                # 注册一个函数来清理超时的操作(如果可能)
                def cleanup():
                    logger.info(f"清理超时操作: {func_name}")
                    return None
                
                bpy.app.timers.register(cleanup, first_interval=0.1)
                
                # 记录超时前的最后状态
                return {"status": "error", "message": f"操作超时: 等待 {func_name} 执行结果超过 {timeout} 秒"}
            
            # 检查并返回结果
            if result_container["error"]:
                logger.warning(f"执行{func_name}时发生错误: {result_container['error']}")
            
            # 返回结果（优先使用result字段，即使发生错误）
            if result_container["result"] is not None:
                return result_container["result"]
            else:
                # 兜底返回
                return {"status": "error", "message": "未知错误，未能获取有效结果"} 
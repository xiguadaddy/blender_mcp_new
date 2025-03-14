import bpy
import json
import threading
import socket
import time
from bpy.props import StringProperty, IntProperty
import bmesh
import mathutils
from math import radians
import math
import traceback

bl_info = {
    "name": "Blender MCP",
    "author": "BlenderMCP",
    "version": (0, 2),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > BlenderMCP",
    "description": "Connect Blender to LLMs via MCP for precise 3D modeling",
    "category": "Interface",
}

class BlenderMCPServer:
    def __init__(self, host='localhost', port=9876):
        self.host = host
        self.port = port
        self.running = False
        self.socket = None
        self.client = None
        self.command_queue = []
        self.buffer = b''  # Add buffer for incomplete data
    
    def start(self):
        self.running = True
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(1)
            self.socket.setblocking(False)
            # Register the timer
            bpy.app.timers.register(self._process_server, persistent=True)
            print(f"BlenderMCP server started on {self.host}:{self.port}")
        except Exception as e:
            print(f"Failed to start server: {str(e)}")
            self.stop()
            
    def stop(self):
        self.running = False
        if hasattr(bpy.app.timers, "unregister"):
            if bpy.app.timers.is_registered(self._process_server):
                bpy.app.timers.unregister(self._process_server)
        if self.socket:
            self.socket.close()
        if self.client:
            self.client.close()
        self.socket = None
        self.client = None
        print("BlenderMCP server stopped")

    def _process_server(self):
        """Timer callback to process server operations"""
        if not self.running:
            return None  # Unregister timer
            
        try:
            # Accept new connections
            if not self.client and self.socket:
                try:
                    self.client, address = self.socket.accept()
                    self.client.setblocking(False)
                    print(f"Connected to client: {address}")
                except BlockingIOError:
                    pass  # No connection waiting
                except Exception as e:
                    print(f"Error accepting connection: {str(e)}")
                
            # Process existing connection
            if self.client:
                try:
                    # Try to receive data
                    try:
                        data = self.client.recv(8192)
                        if data:
                            self.buffer += data
                            # Try to process complete messages
                            try:
                                # Attempt to parse the buffer as JSON
                                command = json.loads(self.buffer.decode('utf-8'))
                                # If successful, clear the buffer and process command
                                self.buffer = b''
                                response = self.execute_command(command)
                                response_json = json.dumps(response)
                                self.client.sendall(response_json.encode('utf-8'))
                            except json.JSONDecodeError:
                                # Incomplete data, keep in buffer
                                pass
                        else:
                            # Connection closed by client
                            print("Client disconnected")
                            self.client.close()
                            self.client = None
                            self.buffer = b''
                    except BlockingIOError:
                        pass  # No data available
                    except Exception as e:
                        print(f"Error receiving data: {str(e)}")
                        self.client.close()
                        self.client = None
                        self.buffer = b''
                        
                except Exception as e:
                    print(f"Error with client: {str(e)}")
                    if self.client:
                        self.client.close()
                        self.client = None
                    self.buffer = b''
                    
        except Exception as e:
            print(f"Server error: {str(e)}")
            
        return 0.1  # Continue timer with 0.1 second interval

    def execute_command(self, command):
        """Execute a command in the main Blender thread"""
        try:
            cmd_type = command.get("type")
            params = command.get("params", {})
            
            # Ensure we're in the right context
            if cmd_type in ["create_object", "modify_object", "delete_object"]:
                override = bpy.context.copy()
                override['area'] = [area for area in bpy.context.screen.areas if area.type == 'VIEW_3D'][0]
                with bpy.context.temp_override(**override):
                    return self._execute_command_internal(command)
            else:
                return self._execute_command_internal(command)
                
        except Exception as e:
            print(f"Error executing command: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

    def _execute_command_internal(self, command):
        """Internal command execution with proper context"""
        cmd_type = command.get("type")
        params = command.get("params", {})

        # Add a simple ping handler
        if cmd_type == "ping":
            print("Handling ping command")
            return {"status": "success", "result": {"pong": True}}
        
        handlers = {
            "ping": lambda **kwargs: {"pong": True},
            "get_simple_info": self.get_simple_info,
            "get_scene_info": self.get_scene_info,
            "create_object": lambda **kwargs: self.create_object(**kwargs),
            "modify_object": self.modify_object,
            "delete_object": self.delete_object,
            "get_object_info": self.get_object_info,
            "execute_code": self.execute_code,
            "set_material": self.set_material,
            "render_scene": self.render_scene,
            # 新增高级建模功能
            "extrude_faces": self.extrude_faces,
            "subdivide_mesh": self.subdivide_mesh,
            "loop_cut": self.loop_cut,
            "apply_modifier": self.apply_modifier,
            "set_vertex_position": self.set_vertex_position,
            "create_animation": self.create_animation,
            "create_node_material": self.create_node_material,
            "set_uv_mapping": self.set_uv_mapping,
            "join_objects": self.join_objects,
            "separate_mesh": self.separate_mesh,
            "create_text": self.create_text,
            "create_curve": self.create_curve,
            "create_particle_system": self.create_particle_system,
            "advanced_lighting": self.advanced_lighting,
        }
        
        handler = handlers.get(cmd_type)
        if handler:
            try:
                print(f"Executing handler for {cmd_type}")
                result = handler(**params)
                print(f"Handler execution complete")
                return {"status": "success", "result": result}
            except Exception as e:
                print(f"Error in handler: {str(e)}")
                import traceback
                traceback.print_exc()
                return {"status": "error", "message": str(e)}
        else:
            return {"status": "error", "message": f"Unknown command type: {cmd_type}"}

    
    def get_simple_info(self):
        """Get basic Blender information"""
        return {
            "blender_version": ".".join(str(v) for v in bpy.app.version),
            "scene_name": bpy.context.scene.name,
            "object_count": len(bpy.context.scene.objects)
        }
    
    def get_scene_info(self):
        """Get information about the current Blender scene"""
        try:
            print("Getting scene info...")
            # Simplify the scene info to reduce data size
            scene_info = {
                "name": bpy.context.scene.name,
                "object_count": len(bpy.context.scene.objects),
                "objects": [],
                "materials_count": len(bpy.data.materials),
            }
            
            # Collect minimal object information (limit to first 10 objects)
            for i, obj in enumerate(bpy.context.scene.objects):
                if i >= 10:  # Reduced from 20 to 10
                    break
                    
                obj_info = {
                    "name": obj.name,
                    "type": obj.type,
                    # Only include basic location data
                    "location": [round(float(obj.location.x), 2), 
                                round(float(obj.location.y), 2), 
                                round(float(obj.location.z), 2)],
                }
                scene_info["objects"].append(obj_info)
            
            print(f"Scene info collected: {len(scene_info['objects'])} objects")
            return scene_info
        except Exception as e:
            print(f"Error in get_scene_info: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    def create_object(self, type="CUBE", name=None, location=None, rotation=None, scale=None):
        """创建一个指定类型的对象
        
        参数:
            type: 对象类型（CUBE, SPHERE, CYLINDER, PLANE, CONE, TORUS, EMPTY等）
            name: 可选，对象名称
            location: 可选，[x, y, z]位置坐标
            rotation: 可选，[x, y, z]旋转（弧度）
            scale: 可选，[x, y, z]缩放因子
        """
        try:
            # 取消选择所有对象
            bpy.ops.object.select_all(action='DESELECT')
            
            # 设置默认值
            loc = location or (0, 0, 0)
            rot = rotation or (0, 0, 0)
            scl = scale or (1, 1, 1)
            
            # 根据类型创建对象
            if type == "EMPTY":
                bpy.ops.object.empty_add(location=loc)
                expected_type = "EMPTY"
            elif type == "CAMERA":
                bpy.ops.object.camera_add(location=loc, rotation=rot)
                expected_type = "CAMERA"
            elif type == "LIGHT":
                bpy.ops.object.light_add(type='POINT', location=loc, rotation=rot)
                expected_type = "LIGHT"
            elif type == "CUBE":
                bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot, scale=scl)
                expected_type = "MESH"
            elif type == "SPHERE":
                bpy.ops.mesh.primitive_uv_sphere_add(location=loc, rotation=rot, scale=scl)
                expected_type = "MESH"
            elif type == "CYLINDER":
                bpy.ops.mesh.primitive_cylinder_add(location=loc, rotation=rot, scale=scl)
                expected_type = "MESH"
            elif type == "PLANE":
                bpy.ops.mesh.primitive_plane_add(location=loc, rotation=rot, scale=scl)
                expected_type = "MESH"
            elif type == "CONE":
                bpy.ops.mesh.primitive_cone_add(location=loc, rotation=rot, scale=scl)
                expected_type = "MESH"
            elif type == "TORUS":
                bpy.ops.mesh.primitive_torus_add(location=loc, rotation=rot, scale=scl)
                expected_type = "MESH"
            else:
                return {"error": f"不支持的对象类型: {type}"}
                
            # 获取创建的对象
            obj = bpy.context.active_object
            
            # 验证对象类型
            if obj.type != expected_type:
                print(f"警告: 创建的对象类型 {obj.type} 与预期的 {expected_type} 不符")
                # 如果是关键对象（CUBE, LIGHT），尝试修复
                if expected_type in ["MESH", "LIGHT"] and obj.type != expected_type:
                    print(f"尝试修复对象类型: 删除错误对象并重新创建")
                    # 删除错误对象
                    bpy.ops.object.delete()
                    # 再次尝试创建
                    if expected_type == "MESH":
                        bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot, scale=scl)
                    elif expected_type == "LIGHT":
                        bpy.ops.object.light_add(type='POINT', location=loc, rotation=rot)
                    obj = bpy.context.active_object
                    print(f"修复后对象类型: {obj.type}")
            
            # 设置名称
            if name:
                obj.name = name
            
            # 设置旋转和缩放 (如果在创建时未设置)
            if rotation and not (type == "CAMERA" or type == "LIGHT"):
                obj.rotation_euler = rotation
            
            if scale and not (type in ["CUBE", "SPHERE", "CYLINDER", "PLANE", "CONE", "TORUS"]):
                obj.scale = scale
            
            # 返回对象属性
            result = {
                "name": obj.name,
                "type": obj.type,
                "location": [obj.location.x, obj.location.y, obj.location.z],
                "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
                "scale": [obj.scale.x, obj.scale.y, obj.scale.z]
            }
            
            return result  # 不用再包装在status和result中，由_execute_command_internal处理
        
        except Exception as e:
            print(f"创建对象错误: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def modify_object(self, name, location=None, rotation=None, scale=None, visible=None):
        """Modify an existing object in the scene"""
        # Find the object by name
        obj = bpy.data.objects.get(name)
        if not obj:
            raise ValueError(f"Object not found: {name}")
        
        # Modify properties as requested
        if location is not None:
            obj.location = location
        
        if rotation is not None:
            obj.rotation_euler = rotation
        
        if scale is not None:
            obj.scale = scale
        
        if visible is not None:
            obj.hide_viewport = not visible
            obj.hide_render = not visible
        
        return {
            "name": obj.name,
            "type": obj.type,
            "location": [obj.location.x, obj.location.y, obj.location.z],
            "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
            "scale": [obj.scale.x, obj.scale.y, obj.scale.z],
            "visible": obj.visible_get(),
        }
    
    def delete_object(self, name):
        """Delete an object from the scene"""
        obj = bpy.data.objects.get(name)
        if not obj:
            raise ValueError(f"Object not found: {name}")
        
        # Store the name to return
        obj_name = obj.name
        
        # Select and delete the object
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.ops.object.delete()
        
        return {"deleted": obj_name}
    
    def get_object_info(self, name):
        """Get detailed information about a specific object"""
        obj = bpy.data.objects.get(name)
        if not obj:
            raise ValueError(f"Object not found: {name}")
        
        # Basic object info
        obj_info = {
            "name": obj.name,
            "type": obj.type,
            "location": [obj.location.x, obj.location.y, obj.location.z],
            "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
            "scale": [obj.scale.x, obj.scale.y, obj.scale.z],
            "visible": obj.visible_get(),
            "materials": [],
        }
        
        # Add material slots
        for slot in obj.material_slots:
            if slot.material:
                obj_info["materials"].append(slot.material.name)
        
        # Add mesh data if applicable
        if obj.type == 'MESH' and obj.data:
            mesh = obj.data
            obj_info["mesh"] = {
                "vertices": len(mesh.vertices),
                "edges": len(mesh.edges),
                "polygons": len(mesh.polygons),
            }
        
        return obj_info
    
    def execute_code(self, code):
        """Execute arbitrary Blender Python code"""
        # This is powerful but potentially dangerous - use with caution
        try:
            # Create a local namespace for execution
            namespace = {"bpy": bpy}
            exec(code, namespace)
            return {"executed": True}
        except Exception as e:
            raise Exception(f"Code execution error: {str(e)}")
    
    def set_material(self, object_name, material_name=None, color=None):
        """为对象设置或创建材质
        
        参数:
            object_name: 要应用材质的对象名称
            material_name: 可选，要使用或创建的材质名称
            color: 可选，[R, G, B]颜色值（0.0-1.0）
        """
        try:
            # 尝试获取对象
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"未找到对象: {object_name}"}
            
            # 确定材质名称 (如果未提供)
            if not material_name:
                material_name = f"{object_name}_material"
            
            # 查找现有材质或创建新材质
            mat = bpy.data.materials.get(material_name)
            if not mat:
                mat = bpy.data.materials.new(name=material_name)
                print(f"创建新材质: {material_name}")
            else:
                print(f"使用现有材质: {material_name}")
            
            # 检查材质节点是否可用
            if not mat.use_nodes:
                mat.use_nodes = True
                print(f"启用材质节点: {material_name}")
            
            # 设置基本材质属性
            if hasattr(mat, "diffuse_color") and color:
                if len(color) == 3:
                    # 如果提供的是RGB，添加Alpha通道
                    color_with_alpha = color + [1.0]
                else:
                    color_with_alpha = color
                mat.diffuse_color = color_with_alpha
                print(f"设置diffuse_color: {color_with_alpha}")
            
            # 安全地设置其他材质属性
            try:
                # 尝试设置镜面反射（如果属性存在）
                if hasattr(mat, "specular_intensity"):
                    mat.specular_intensity = 0.5
                    print("设置specular_intensity: 0.5")
                
                # 尝试访问可能不存在的属性
                metallic_attr = getattr(mat, "metallic", None)
                if metallic_attr is not None:
                    mat.metallic = 0.0
                    print("设置metallic: 0.0")
                    
                roughness_attr = getattr(mat, "roughness", None)
                if roughness_attr is not None:
                    mat.roughness = 0.4
                    print("设置roughness: 0.4")
            except Exception as attr_e:
                print(f"设置材质属性警告 (非关键): {str(attr_e)}")
                # 继续处理，因为这些是非关键属性
            
            # 处理材质节点
            try:
                # 获取节点树和主要着色器节点
                nodes = mat.node_tree.nodes
                principled_bsdf = None
                
                # 查找或创建Principled BSDF节点
                for node in nodes:
                    if node.type == 'BSDF_PRINCIPLED':
                        principled_bsdf = node
                        break
                
                if not principled_bsdf:
                    # 如果找不到，创建一个
                    principled_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
                
                # 设置节点属性
                if color:
                    principled_bsdf.inputs["Base Color"].default_value = color + [1.0] if len(color) == 3 else color
                    print(f"设置Base Color: {color}")
                
                # 设置金属度和粗糙度
                principled_bsdf.inputs["Metallic"].default_value = 0.0
                principled_bsdf.inputs["Roughness"].default_value = 0.4
                principled_bsdf.inputs["Specular"].default_value = 0.5
                
                # 确保节点连接到输出
                output_node = None
                for node in nodes:
                    if node.type == 'OUTPUT_MATERIAL':
                        output_node = node
                        break
                
                if not output_node:
                    output_node = nodes.new(type='ShaderNodeOutputMaterial')
                
                # 连接主着色器到输出
                mat.node_tree.links.new(principled_bsdf.outputs["BSDF"], output_node.inputs["Surface"])
                
            except AttributeError as node_e:
                print(f"材质节点处理警告 (非关键): {str(node_e)}")
                # 继续处理，因为旧版本的Blender可能不支持节点
            except KeyError as key_e:
                print(f"材质节点键错误警告 (非关键): {str(key_e)}")
                # 继续处理，因为一些版本可能有不同的节点输入名称
            
            # 将材质分配给对象
            # 检查对象是否已经有材质插槽
            if len(obj.material_slots) == 0:
                obj.data.materials.append(mat)
                print(f"添加材质到对象 {object_name}: {material_name}")
            else:
                # 更新现有插槽
                obj.material_slots[0].material = mat
                print(f"更新对象 {object_name} 的材质: {material_name}")
            
            # 确保材质实际上已经应用
            for slot in obj.material_slots:
                if slot.material is None:
                    slot.material = mat
            
            # 返回成功结果
            return {
                "object_name": obj.name,
                "material_name": mat.name,
                "color": list(mat.diffuse_color) if hasattr(mat, "diffuse_color") else None
            }
            
        except Exception as e:
            print(f"设置材质错误: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def render_scene(self, output_path=None, resolution_x=None, resolution_y=None):
        """Render the current scene"""
        if resolution_x is not None:
            bpy.context.scene.render.resolution_x = resolution_x
        
        if resolution_y is not None:
            bpy.context.scene.render.resolution_y = resolution_y
        
        if output_path:
            bpy.context.scene.render.filepath = output_path
        
        # Render the scene
        bpy.ops.render.render(write_still=bool(output_path))
        
        return {
            "rendered": True,
            "output_path": output_path if output_path else "[not saved]",
            "resolution": [bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y],
        }

    def extrude_faces(self, object_name, face_indices, direction=None, distance=1.0):
        """精细化挤出操作"""
        try:
            # 获取对象
            obj = bpy.data.objects.get(object_name)
            if not obj or obj.type != 'MESH':
                return {"error": f"无效网格对象: {object_name}"}
            
            # 进入编辑模式
            bpy.context.view_layer.objects.active = obj
            current_mode = bpy.context.object.mode
            bpy.ops.object.mode_set(mode='EDIT')
            
            # 创建bmesh
            bm = bmesh.from_edit_mesh(obj.data)
            bm.faces.ensure_lookup_table()
            
            # 取消选择所有
            for face in bm.faces:
                face.select = False
                
            # 选择指定的面
            for idx in face_indices:
                if idx < len(bm.faces):
                    bm.faces[idx].select = True
            
            # 挤出操作
            ret = bmesh.ops.extrude_face_region(bm, geom=[f for f in bm.faces if f.select])
            extruded_verts = [v for v in ret["geom"] if isinstance(v, bmesh.types.BMVert)]
            
            # 移动挤出的顶点
            if direction is None:
                # 使用面法线
                bmesh.ops.translate(bm, 
                                   vec=mathutils.Vector((0, 0, distance)), 
                                   verts=extruded_verts)
            else:
                # 使用指定方向
                bmesh.ops.translate(bm, 
                                   vec=mathutils.Vector(direction) * distance, 
                                   verts=extruded_verts)
            
            # 更新网格
            bmesh.update_edit_mesh(obj.data)
            
            # 恢复之前的模式
            bpy.ops.object.mode_set(mode=current_mode)
            
            return {
                "status": "success",
                "extruded_faces": len(face_indices),
                "object": object_name
            }
            
        except Exception as e:
            if 'current_mode' in locals():
                bpy.ops.object.mode_set(mode=current_mode)
            return {"error": str(e)}
    
    def subdivide_mesh(self, object_name, cuts=1, smooth=0):
        """细分网格"""
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj or obj.type != 'MESH':
                return {"error": f"无效网格对象: {object_name}"}
                
            # 进入编辑模式
            bpy.context.view_layer.objects.active = obj
            current_mode = bpy.context.object.mode
            bpy.ops.object.mode_set(mode='EDIT')
            
            # 选择所有
            bpy.ops.mesh.select_all(action='SELECT')
            
            # 细分
            bpy.ops.mesh.subdivide(number_cuts=cuts, smoothness=smooth)
            
            # 恢复模式
            bpy.ops.object.mode_set(mode=current_mode)
            
            return {
                "status": "success", 
                "object": object_name,
                "cuts": cuts,
                "vertex_count": len(obj.data.vertices)
            }
            
        except Exception as e:
            if 'current_mode' in locals():
                bpy.ops.object.mode_set(mode=current_mode)
            return {"error": str(e)}
    
    def loop_cut(self, object_name, cuts=1, edge_index=None, factor=0.5):
        """环切操作"""
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj or obj.type != 'MESH':
                return {"error": f"无效网格对象: {object_name}"}
            
            # 使用bmesh进行精确控制
            bpy.context.view_layer.objects.active = obj
            current_mode = bpy.context.object.mode
            bpy.ops.object.mode_set(mode='EDIT')
            
            bm = bmesh.from_edit_mesh(obj.data)
            bm.edges.ensure_lookup_table()
            
            # 选择边
            if edge_index is not None:
                for edge in bm.edges:
                    edge.select = False
                if edge_index < len(bm.edges):
                    bm.edges[edge_index].select = True
                    
                    # 执行环切
                    result = bmesh.ops.subdivide_edges(
                        bm,
                        edges=[e for e in bm.edges if e.select],
                        cuts=cuts,
                        factor=factor
                    )
                    
                    bmesh.update_edit_mesh(obj.data)
                    
                    # 恢复模式
                    bpy.ops.object.mode_set(mode=current_mode)
                    
                    return {
                        "status": "success",
                        "object": object_name,
                        "cuts": cuts,
                        "new_edges": len(result.get('geom_inner', []))
                    }
                else:
                    bpy.ops.object.mode_set(mode=current_mode)
                    return {"error": f"边索引{edge_index}超出范围"}
            else:
                # 如果没有提供边索引，使用Blender的标准环切
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.loopcut_slide(number_cuts=cuts)
                bpy.ops.object.mode_set(mode=current_mode)
                return {
                    "status": "success",
                    "note": "使用了默认的环切操作，需要用户确认位置"
                }
                
        except Exception as e:
            if 'current_mode' in locals():
                bpy.ops.object.mode_set(mode=current_mode)
            return {"error": str(e)}
    
    def apply_modifier(self, object_name, modifier_type, params={}):
        """应用修改器"""
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"对象不存在: {object_name}"}
                
            # 创建新修改器
            mod = obj.modifiers.new(name=modifier_type, type=modifier_type)
            
            # 设置修改器参数
            for param, value in params.items():
                if hasattr(mod, param):
                    setattr(mod, param, value)
            
            return {
                "status": "success",
                "object": object_name,
                "modifier": modifier_type,
                "modifier_name": mod.name
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def set_vertex_position(self, object_name, vertex_indices, positions):
        """设置顶点位置"""
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj or obj.type != 'MESH':
                return {"error": f"无效网格对象: {object_name}"}
            
            if len(vertex_indices) != len(positions):
                return {"error": "顶点索引数量必须与位置数量匹配"}
                
            # 进入对象模式以确保可以修改顶点
            current_mode = bpy.context.object.mode
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # 修改顶点位置
            for i, idx in enumerate(vertex_indices):
                if idx < len(obj.data.vertices):
                    obj.data.vertices[idx].co = positions[i]
            
            # 更新网格
            obj.data.update()
            
            # 恢复模式
            bpy.ops.object.mode_set(mode=current_mode)
            
            return {
                "status": "success",
                "object": object_name,
                "modified_vertices": len(vertex_indices)
            }
            
        except Exception as e:
            if 'current_mode' in locals():
                bpy.ops.object.mode_set(mode=current_mode)
            return {"error": str(e)}
    
    def create_animation(self, object_name, keyframes, property_path="location"):
        """创建物体动画"""
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"对象不存在: {object_name}"}
            
            # 清除现有动画曲线
            if obj.animation_data and obj.animation_data.action:
                for fc in obj.animation_data.action.fcurves:
                    if fc.data_path == property_path:
                        obj.animation_data.action.fcurves.remove(fc)
            
            # 确保有animation_data
            if not obj.animation_data:
                obj.animation_data_create()
            
            # 确保有action
            if not obj.animation_data.action:
                action = bpy.data.actions.new(name=f"{object_name}Action")
                obj.animation_data.action = action
            
            # 设置关键帧
            for frame, value in keyframes.items():
                frame = int(frame)
                if property_path == "location":
                    obj.location = value
                    obj.keyframe_insert(data_path=property_path, frame=frame)
                elif property_path == "rotation_euler":
                    obj.rotation_euler = [radians(v) if isinstance(v, (int, float)) else v for v in value]
                    obj.keyframe_insert(data_path=property_path, frame=frame)
                elif property_path == "scale":
                    obj.scale = value
                    obj.keyframe_insert(data_path=property_path, frame=frame)
                else:
                    # 通用属性路径
                    parts = property_path.split('.')
                    target = obj
                    for part in parts[:-1]:
                        target = getattr(target, part)
                    setattr(target, parts[-1], value)
                    obj.keyframe_insert(data_path=property_path, frame=frame)
            
            return {
                "status": "success",
                "object": object_name,
                "property": property_path,
                "keyframes": len(keyframes)
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def create_node_material(self, name, node_setup):
        """创建节点材质"""
        try:
            # 创建新材质
            mat = bpy.data.materials.get(name)
            if not mat:
                mat = bpy.data.materials.new(name=name)
            
            mat.use_nodes = True
            node_tree = mat.node_tree
            
            # 清除现有节点
            for node in node_tree.nodes:
                node_tree.nodes.remove(node)
                
            # 创建节点
            nodes = {}
            for node_id, node_data in node_setup["nodes"].items():
                node_type = node_data["type"]
                node = node_tree.nodes.new(type=node_type)
                node.location = node_data.get("location", (0, 0))
                
                # 设置节点属性
                for prop, value in node_data.get("properties", {}).items():
                    if hasattr(node, prop):
                        setattr(node, prop, value)
                    elif "inputs" in node and prop in node.inputs:
                        if isinstance(value, (list, tuple)) and len(value) >= 3:
                            node.inputs[prop].default_value = value
                        else:
                            node.inputs[prop].default_value = value
                
                nodes[node_id] = node
            
            # 创建连接
            for link_data in node_setup.get("links", []):
                from_node = nodes[link_data["from_node"]]
                to_node = nodes[link_data["to_node"]]
                
                from_socket = from_node.outputs[link_data["from_socket"]]
                to_socket = to_node.inputs[link_data["to_socket"]]
                
                node_tree.links.new(from_socket, to_socket)
            
            return {
                "status": "success",
                "material": name,
                "node_count": len(nodes)
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def set_uv_mapping(self, object_name, projection='CUBE', scale=(1, 1, 1)):
        """设置UV映射"""
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj or obj.type != 'MESH':
                return {"error": f"无效网格对象: {object_name}"}
            
            # 确保对象激活且在编辑模式
            bpy.context.view_layer.objects.active = obj
            current_mode = bpy.context.object.mode
            bpy.ops.object.mode_set(mode='EDIT')
            
            # 选择所有
            bpy.ops.mesh.select_all(action='SELECT')
            
            # 应用UV展开
            if projection == 'CUBE':
                bpy.ops.uv.cube_project(scale_to_bounds=True, cube_size=scale[0])
            elif projection == 'CYLINDER':
                bpy.ops.uv.cylinder_project(scale_to_bounds=True, radius=scale[0])
            elif projection == 'SPHERE':
                bpy.ops.uv.sphere_project(scale_to_bounds=True, radius=scale[0])
            elif projection == 'PROJECT':
                bpy.ops.uv.project_from_view(scale_to_bounds=True)
            elif projection == 'UNWRAP':
                bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.001)
            else:
                bpy.ops.object.mode_set(mode=current_mode)
                return {"error": f"不支持的投影类型: {projection}"}
            
            # 恢复模式
            bpy.ops.object.mode_set(mode=current_mode)
            
            return {
                "status": "success",
                "object": object_name,
                "projection": projection
            }
            
        except Exception as e:
            if 'current_mode' in locals():
                bpy.ops.object.mode_set(mode=current_mode)
            return {"error": str(e)}
    
    def join_objects(self, objects, target_object=None):
        """合并多个对象，保留目标对象的材质
        
        参数:
            objects: 要合并的对象名称列表
            target_object: 可选，作为目标的对象名称（保留该对象的材质）
        """
        try:
            if len(objects) < 2:
                return {"error": "需要至少两个对象才能执行合并"}
            
            # 确定目标对象（默认为列表中的第一个）
            if not target_object:
                target_object = objects[0]
            
            # 获取目标对象
            target_obj = bpy.data.objects.get(target_object)
            if not target_obj:
                return {"error": f"找不到目标对象: {target_object}"}
            
            # 记录目标对象的材质
            original_materials = []
            if hasattr(target_obj.data, 'materials') and len(target_obj.data.materials) > 0:
                for mat_slot in target_obj.material_slots:
                    if mat_slot.material:
                        original_materials.append(mat_slot.material)
                print(f"记录目标对象 {target_object} 的 {len(original_materials)} 个材质")
            
            # 执行合并
            bpy.ops.object.select_all(action='DESELECT')
            
            # 记录所有要合并的有效对象
            valid_objects = []
            for obj_name in objects:
                obj = bpy.data.objects.get(obj_name)
                if obj and obj.type == target_obj.type:
                    obj.select_set(True)
                    valid_objects.append(obj)
                    print(f"选择对象以合并: {obj_name}")
                else:
                    print(f"跳过无效对象或类型不匹配: {obj_name}")
            
            if len(valid_objects) < 2:
                return {"error": "没有足够的有效对象进行合并"}
            
            # 设置目标对象为活动对象
            bpy.context.view_layer.objects.active = target_obj
            
            # 记录材质的引用计数
            material_users = {}
            for mat in original_materials:
                material_users[mat.name] = mat.users
                print(f"材质 {mat.name} 的初始引用计数: {mat.users}")
            
            # 执行合并
            print(f"执行对象合并，目标对象: {target_object}")
            bpy.ops.object.join()
            
            # 确保合并后重新应用原始材质
            if original_materials:
                print(f"重新应用原始材质到合并后的对象: {target_obj.name}")
                
                # 保存当前材质作为备份
                current_materials = []
                for i, mat_slot in enumerate(target_obj.material_slots):
                    if mat_slot.material:
                        current_materials.append(mat_slot.material)
                
                # 检查合并后的材质是否与原始材质相同
                materials_changed = False
                if len(current_materials) != len(original_materials):
                    materials_changed = True
                    print(f"材质数量改变: {len(current_materials)} vs 原始 {len(original_materials)}")
                else:
                    for i, mat in enumerate(original_materials):
                        if current_materials[i] != mat:
                            materials_changed = True
                            print(f"材质 #{i} 已改变: {current_materials[i].name} vs 原始 {mat.name}")
                
                # 如果材质发生变化，重新应用原始材质
                if materials_changed:
                    print("材质已改变，重新应用原始材质")
                    
                    # 清除所有现有材质
                    while len(target_obj.data.materials) > 0:
                        target_obj.data.materials.pop(index=0)
                    
                    # 重新应用原始材质
                    for mat in original_materials:
                        target_obj.data.materials.append(mat)
                    
                    # 检查材质的引用计数
                    for mat in original_materials:
                        new_users = mat.users
                        old_users = material_users.get(mat.name, 0)
                        print(f"材质 {mat.name} 的引用计数: {new_users} (之前: {old_users})")
                else:
                    print("材质保持不变，无需重新应用")
            
            # 确保视图更新
            bpy.context.view_layer.update()
            
            # 返回合并后的对象信息
            return {
                "name": target_obj.name,
                "type": target_obj.type,
                "materials": [m.name for m in target_obj.data.materials] if hasattr(target_obj.data, 'materials') else [],
                "vertex_count": len(target_obj.data.vertices) if hasattr(target_obj.data, 'vertices') else 0
            }
        except Exception as e:
            print(f"合并对象错误: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def separate_mesh(self, object_name, method='SELECTED'):
        """分离网格"""
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj or obj.type != 'MESH':
                return {"error": f"无效网格对象: {object_name}"}
            
            # 确保对象激活并在编辑模式
            bpy.context.view_layer.objects.active = obj
            current_mode = bpy.context.object.mode
            bpy.ops.object.mode_set(mode='EDIT')
            
            if method == 'SELECTED':
                # 默认使用已经选中的面
                pass
            elif method == 'MATERIAL':
                # 通过材质分离
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.separate(type='MATERIAL')
            elif method == 'LOOSE':
                # 分离松散部分
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.separate(type='LOOSE')
            else:
                bpy.ops.object.mode_set(mode=current_mode)
                return {"error": f"不支持的分离方法: {method}"}
            
            # 执行分离
            if method == 'SELECTED':
                bpy.ops.mesh.separate(type='SELECTED')
            
            # 恢复模式
            bpy.ops.object.mode_set(mode=current_mode)
            
            # 获取新创建的对象
            new_objects = [o for o in bpy.context.selected_objects if o != obj]
            
            return {
                "status": "success",
                "original_object": object_name,
                "new_objects": [o.name for o in new_objects],
                "method": method
            }
            
        except Exception as e:
            if 'current_mode' in locals():
                bpy.ops.object.mode_set(mode=current_mode)
            return {"error": str(e)}
    
    def create_text(self, text, location=(0,0,0), size=1.0, extrude=0.0, name=None):
        """创建3D文本对象"""
        try:
            # 创建文本数据
            text_data = bpy.data.curves.new(name="Text", type='FONT')
            text_data.body = text
            text_data.size = size
            text_data.extrude = extrude
            
            # 创建对象
            if not name:
                name = f"Text_{text[:10]}"
            text_obj = bpy.data.objects.new(name, text_data)
            
            # 设置位置
            text_obj.location = location
            
            # 添加到场景
            bpy.context.collection.objects.link(text_obj)
            
            return {
                "status": "success",
                "object": text_obj.name,
                "type": "TEXT",
                "text": text
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def create_curve(self, curve_type='BEZIER', points=None, location=(0,0,0), name=None):
        """创建曲线"""
        try:
            # 创建曲线数据
            curve_data = bpy.data.curves.new(name="Curve", type='CURVE')
            curve_data.dimensions = '3D'
            
            # 设置曲线类型
            spline = curve_data.splines.new(curve_type)
            
            # 添加点
            if points:
                if curve_type == 'BEZIER':
                    # 贝塞尔曲线需要设置更多的点属性
                    if len(points) > 1:
                        spline.bezier_points.add(len(points) - 1)
                    for i, point_data in enumerate(points):
                        pt = spline.bezier_points[i]
                        pt.co = point_data.get("co", (0, 0, 0))
                        pt.handle_left = point_data.get("handle_left", pt.co)
                        pt.handle_right = point_data.get("handle_right", pt.co)
                        pt.handle_left_type = point_data.get("handle_left_type", 'AUTO')
                        pt.handle_right_type = point_data.get("handle_right_type", 'AUTO')
                else:
                    # POLY曲线
                    if len(points) > 1:
                        spline.points.add(len(points) - 1)
                    for i, point_coords in enumerate(points):
                        # Poly点需要4D坐标 (x, y, z, w)
                        if len(point_coords) == 3:
                            point_coords = (*point_coords, 1.0)
                        spline.points[i].co = point_coords
            
            # 创建对象
            if not name:
                name = f"Curve_{curve_type}"
            curve_obj = bpy.data.objects.new(name, curve_data)
            
            # 设置位置
            curve_obj.location = location
            
            # 添加到场景
            bpy.context.collection.objects.link(curve_obj)
            
            return {
                "status": "success",
                "object": curve_obj.name,
                "type": "CURVE",
                "curve_type": curve_type,
                "points": len(points) if points else 0
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def create_particle_system(self, object_name, settings=None):
        """为对象创建粒子系统"""
        try:
            # 获取对象
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"对象不存在: {object_name}"}
            
            # 创建粒子系统
            if not obj.particle_systems:
                ps = obj.particle_systems.new("ParticleSystem")
            else:
                ps = obj.particle_systems[0]
                
            # 获取设置
            ps_settings = ps.settings
            
            # 应用设置
            if settings:
                for param, value in settings.items():
                    if hasattr(ps_settings, param):
                        setattr(ps_settings, param, value)
            
            # 设置常用默认值
            if not settings or "count" not in settings:
                ps_settings.count = 1000
            if not settings or "lifetime" not in settings:
                ps_settings.lifetime = 100
            
            return {
                "status": "success",
                "object": object_name,
                "particle_system": ps.name,
                "count": ps_settings.count
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def advanced_lighting(self, light_type="POINT", name=None, location=(0,0,0), energy=1000, color=(1,1,1), shadow=True):
        """创建高级灯光设置"""
        try:
            # 创建灯光数据
            light_data = bpy.data.lights.new(name=(name or f"{light_type}_Light"), type=light_type)
            
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
                light_data.size = 1.0
                light_data.size_y = 1.0
            
            # 创建灯光对象
            light_obj = bpy.data.objects.new(name=(name or f"{light_type}_Light"), object_data=light_data)
            
            # 设置位置
            light_obj.location = location
            
            # 添加到场景
            bpy.context.collection.objects.link(light_obj)
            
            return {
                "status": "success",
                "object": light_obj.name,
                "type": "LIGHT",
                "light_type": light_type,
                "energy": energy
            }
            
        except Exception as e:
            return {"error": str(e)}

# Blender UI Panel
class BLENDERMCP_PT_Panel(bpy.types.Panel):
    bl_label = "Blender MCP"
    bl_idname = "BLENDERMCP_PT_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlenderMCP'
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        layout.prop(scene, "blendermcp_port")
        
        if not scene.blendermcp_server_running:
            layout.operator("blendermcp.start_server", text="Start MCP Server")
        else:
            layout.operator("blendermcp.stop_server", text="Stop MCP Server")
            layout.label(text=f"Running on port {scene.blendermcp_port}")

# Operator to start the server
class BLENDERMCP_OT_StartServer(bpy.types.Operator):
    bl_idname = "blendermcp.start_server"
    bl_label = "Start BlenderMCP Server"
    bl_description = "Start the BlenderMCP server to connect with Claude"
    
    def execute(self, context):
        scene = context.scene
        
        # Create a new server instance
        if not hasattr(bpy.types, "blendermcp_server") or not bpy.types.blendermcp_server:
            bpy.types.blendermcp_server = BlenderMCPServer(port=scene.blendermcp_port)
        
        # Start the server
        bpy.types.blendermcp_server.start()
        scene.blendermcp_server_running = True
        
        return {'FINISHED'}

# Operator to stop the server
class BLENDERMCP_OT_StopServer(bpy.types.Operator):
    bl_idname = "blendermcp.stop_server"
    bl_label = "Stop BlenderMCP Server"
    bl_description = "Stop the BlenderMCP server"
    
    def execute(self, context):
        scene = context.scene
        
        # Stop the server if it exists
        if hasattr(bpy.types, "blendermcp_server") and bpy.types.blendermcp_server:
            bpy.types.blendermcp_server.stop()
            del bpy.types.blendermcp_server
        
        scene.blendermcp_server_running = False
        
        return {'FINISHED'}

# Registration functions
def register():
    bpy.types.Scene.blendermcp_port = IntProperty(
        name="Port",
        description="Port for the BlenderMCP server",
        default=9876,
        min=1024,
        max=65535
    )
    
    bpy.types.Scene.blendermcp_server_running = bpy.props.BoolProperty(
        name="Server Running",
        default=False
    )
    
    bpy.utils.register_class(BLENDERMCP_PT_Panel)
    bpy.utils.register_class(BLENDERMCP_OT_StartServer)
    bpy.utils.register_class(BLENDERMCP_OT_StopServer)
    
    print("BlenderMCP addon registered")

def unregister():
    # Stop the server if it's running
    if hasattr(bpy.types, "blendermcp_server") and bpy.types.blendermcp_server:
        bpy.types.blendermcp_server.stop()
        del bpy.types.blendermcp_server
    
    bpy.utils.unregister_class(BLENDERMCP_PT_Panel)
    bpy.utils.unregister_class(BLENDERMCP_OT_StartServer)
    bpy.utils.unregister_class(BLENDERMCP_OT_StopServer)
    
    del bpy.types.Scene.blendermcp_port
    del bpy.types.Scene.blendermcp_server_running
    
    print("BlenderMCP addon unregistered")

if __name__ == "__main__":
    register()
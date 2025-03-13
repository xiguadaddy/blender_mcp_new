import bpy
import json
import threading
import socket
import time
from bpy.props import StringProperty, IntProperty
import bmesh
import mathutils
from math import radians

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
            "create_object": self.create_object,
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
    
    def create_object(self, type="CUBE", name=None, location=(0, 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1)):
        """Create a new object in the scene"""
        # Deselect all objects
        bpy.ops.object.select_all(action='DESELECT')
        
        # Create the object based on type
        if type == "CUBE":
            bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation, scale=scale)
        elif type == "SPHERE":
            bpy.ops.mesh.primitive_uv_sphere_add(location=location, rotation=rotation, scale=scale)
        elif type == "CYLINDER":
            bpy.ops.mesh.primitive_cylinder_add(location=location, rotation=rotation, scale=scale)
        elif type == "PLANE":
            bpy.ops.mesh.primitive_plane_add(location=location, rotation=rotation, scale=scale)
        elif type == "CONE":
            bpy.ops.mesh.primitive_cone_add(location=location, rotation=rotation, scale=scale)
        elif type == "TORUS":
            bpy.ops.mesh.primitive_torus_add(location=location, rotation=rotation, scale=scale)
        elif type == "EMPTY":
            bpy.ops.object.empty_add(location=location, rotation=rotation, scale=scale)
        elif type == "CAMERA":
            bpy.ops.object.camera_add(location=location, rotation=rotation)
        elif type == "LIGHT":
            bpy.ops.object.light_add(type='POINT', location=location, rotation=rotation, scale=scale)
        else:
            raise ValueError(f"Unsupported object type: {type}")
        
        # Get the created object
        obj = bpy.context.active_object
        
        # Rename if name is provided
        if name:
            obj.name = name
        
        return {
            "name": obj.name,
            "type": obj.type,
            "location": [obj.location.x, obj.location.y, obj.location.z],
            "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
            "scale": [obj.scale.x, obj.scale.y, obj.scale.z],
        }
    
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
    
    def set_material(self, object_name, material_name=None, create_if_missing=True, color=None):
        """Set or create a material for an object"""
        try:
            # Get the object
            obj = bpy.data.objects.get(object_name)
            if not obj:
                raise ValueError(f"Object not found: {object_name}")
            
            # Make sure object can accept materials
            if not hasattr(obj, 'data') or not hasattr(obj.data, 'materials'):
                raise ValueError(f"Object {object_name} cannot accept materials")
            
            # Create or get material
            if material_name:
                mat = bpy.data.materials.get(material_name)
                if not mat and create_if_missing:
                    mat = bpy.data.materials.new(name=material_name)
                    print(f"Created new material: {material_name}")
            else:
                # Generate unique material name if none provided
                mat_name = f"{object_name}_material"
                mat = bpy.data.materials.get(mat_name)
                if not mat:
                    mat = bpy.data.materials.new(name=mat_name)
                material_name = mat_name
                print(f"Using material: {mat_name}")
            
            # Set up material nodes if needed
            if mat:
                if not mat.use_nodes:
                    mat.use_nodes = True
                
                # Get or create Principled BSDF
                principled = mat.node_tree.nodes.get('Principled BSDF')
                if not principled:
                    principled = mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
                    # Get or create Material Output
                    output = mat.node_tree.nodes.get('Material Output')
                    if not output:
                        output = mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
                    # Link if not already linked
                    if not principled.outputs[0].links:
                        mat.node_tree.links.new(principled.outputs[0], output.inputs[0])
                
                # Set color if provided
                if color and len(color) >= 3:
                    principled.inputs['Base Color'].default_value = (
                        color[0],
                        color[1],
                        color[2],
                        1.0 if len(color) < 4 else color[3]
                    )
                    print(f"Set material color to {color}")
            
            # Assign material to object if not already assigned
            if mat:
                if not obj.data.materials:
                    obj.data.materials.append(mat)
                else:
                    # Only modify first material slot
                    obj.data.materials[0] = mat
                
                print(f"Assigned material {mat.name} to object {object_name}")
                
                return {
                    "status": "success",
                    "object": object_name,
                    "material": mat.name,
                    "color": color if color else None
                }
            else:
                raise ValueError(f"Failed to create or find material: {material_name}")
            
        except Exception as e:
            print(f"Error in set_material: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "message": str(e),
                "object": object_name,
                "material": material_name if 'material_name' in locals() else None
            }
    
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
        """合并多个对象"""
        try:
            # 检查对象是否存在
            obj_list = []
            for obj_name in objects:
                obj = bpy.data.objects.get(obj_name)
                if obj:
                    obj_list.append(obj)
                else:
                    return {"error": f"对象不存在: {obj_name}"}
            
            if not obj_list:
                return {"error": "没有有效的对象可合并"}
            
            # 取消选择所有对象
            bpy.ops.object.select_all(action='DESELECT')
            
            # 设置目标对象
            if target_object:
                target = bpy.data.objects.get(target_object)
                if not target or target not in obj_list:
                    return {"error": f"目标对象无效: {target_object}"}
            else:
                target = obj_list[0]
            
            # 选择所有要合并的对象
            for obj in obj_list:
                obj.select_set(True)
            
            # 设置活动对象为目标
            bpy.context.view_layer.objects.active = target
            
            # 合并对象
            bpy.ops.object.join()
            
            return {
                "status": "success",
                "target_object": target.name,
                "joined_objects": len(obj_list) - 1
            }
            
        except Exception as e:
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
                light_data.spot_size = radians(45.0)  # 45度聚光角度
                light_data.spot_blend = 0.15
            elif light_type == "SUN":
                light_data.angle = radians(0.526)  # 太阳角度
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
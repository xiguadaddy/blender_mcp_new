"""
场景操作工具模块

包括场景的创建、获取、修改和渲染相关功能。
"""

import bpy
import logging
import os
import json
import tempfile
from pathlib import Path
from ..tool_handlers import execute_in_main_thread

# 设置日志
logger = logging.getLogger("BlenderMCP.SceneTools")

# 场景渲染函数
def render_scene(args):
    """渲染当前场景"""
    logger.debug(f"渲染场景: {args}")
    
    # 解析参数
    output_path = args.get("output_path", "")
    output_format = args.get("output_format", "PNG")
    resolution_x = args.get("resolution_x", 1920)
    resolution_y = args.get("resolution_y", 1080)
    samples = args.get("samples")
    engine = args.get("engine", "CYCLES")
    use_denoising = args.get("use_denoising", True)
    transparent_bg = args.get("transparent_bg", False)
    
    def exec_func():
        try:
            # 获取当前场景
            scene = bpy.context.scene
            
            # 保存原始设置用于后续恢复
            original_settings = {
                "engine": scene.render.engine,
                "resolution_x": scene.render.resolution_x,
                "resolution_y": scene.render.resolution_y,
                "resolution_percentage": scene.render.resolution_percentage,
                "file_format": scene.render.image_settings.file_format,
                "filepath": scene.render.filepath,
                "film_transparent": scene.render.film_transparent
            }
            
            if engine == "CYCLES" and hasattr(scene.cycles, "samples"):
                original_settings["cycles_samples"] = scene.cycles.samples
                original_settings["use_denoising"] = scene.cycles.use_denoising
            
            # 设置渲染引擎
            scene.render.engine = engine
            
            # 设置分辨率
            scene.render.resolution_x = resolution_x
            scene.render.resolution_y = resolution_y
            scene.render.resolution_percentage = 100
            
            # 设置输出格式
            scene.render.image_settings.file_format = output_format
            
            # 设置透明背景
            scene.render.film_transparent = transparent_bg
            
            # 如果使用Cycles引擎，设置相关参数
            if engine == "CYCLES":
                # 设置采样数
                if samples is not None and hasattr(scene.cycles, "samples"):
                    scene.cycles.samples = samples
                
                # 设置降噪
                if hasattr(scene.cycles, "use_denoising"):
                    scene.cycles.use_denoising = use_denoising
            
            # 处理输出路径
            if not output_path:
                # 创建临时文件夹
                temp_dir = tempfile.gettempdir()
                output_path = os.path.join(temp_dir, f"render_{hash(tuple(args.items()))}.{output_format.lower()}")
            
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            # 设置输出路径
            scene.render.filepath = output_path
            
            # 执行渲染
            bpy.ops.render.render(write_still=True)
            
            # 恢复原始设置
            scene.render.engine = original_settings["engine"]
            scene.render.resolution_x = original_settings["resolution_x"]
            scene.render.resolution_y = original_settings["resolution_y"]
            scene.render.resolution_percentage = original_settings["resolution_percentage"]
            scene.render.image_settings.file_format = original_settings["file_format"]
            scene.render.filepath = original_settings["filepath"]
            scene.render.film_transparent = original_settings["film_transparent"]
            
            if engine == "CYCLES" and "cycles_samples" in original_settings:
                scene.cycles.samples = original_settings["cycles_samples"]
                if "use_denoising" in original_settings:
                    scene.cycles.use_denoising = original_settings["use_denoising"]
            
            return {
                "status": "success",
                "render_path": output_path,
                "resolution": [resolution_x, resolution_y],
                "engine": engine
            }
            
        except Exception as e:
            logger.error(f"渲染场景时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

# 场景设置函数
def setup_scene_environment(args):
    """设置场景环境"""
    logger.debug(f"设置场景环境: {args}")
    
    # 解析参数
    world_color = args.get("world_color", [0.05, 0.05, 0.05])
    ambient_strength = args.get("ambient_strength", 1.0)
    use_environment_texture = args.get("use_environment_texture", False)
    environment_texture_path = args.get("environment_texture_path", "")
    environment_strength = args.get("environment_strength", 1.0)
    use_mist = args.get("use_mist", False)
    mist_settings = args.get("mist_settings", {})
    
    def exec_func():
        try:
            # 获取当前场景和世界
            scene = bpy.context.scene
            world = scene.world
            if not world:
                world = bpy.data.worlds.new("World")
                scene.world = world
            
            # 确保世界使用节点
            world.use_nodes = True
            nodes = world.node_tree.nodes
            links = world.node_tree.links
            
            # 清除现有节点
            for node in nodes:
                nodes.remove(node)
            
            # 创建基本节点
            background_node = nodes.new("ShaderNodeBackground")
            output_node = nodes.new("ShaderNodeOutputWorld")
            
            # 设置世界基本颜色和强度
            background_node.inputs["Color"].default_value = world_color + [1.0]  # RGBA
            background_node.inputs["Strength"].default_value = ambient_strength
            
            # 连接节点
            links.new(background_node.outputs["Background"], output_node.inputs["Surface"])
            
            # 如果使用环境纹理
            if use_environment_texture and environment_texture_path:
                if os.path.exists(environment_texture_path):
                    # 创建环境纹理节点
                    tex_coord_node = nodes.new("ShaderNodeTexCoord")
                    mapping_node = nodes.new("ShaderNodeMapping")
                    env_texture_node = nodes.new("ShaderNodeTexEnvironment")
                    
                    # 加载环境纹理
                    try:
                        env_texture = bpy.data.images.load(environment_texture_path, check_existing=True)
                        env_texture_node.image = env_texture
                    except Exception as e:
                        logger.error(f"加载环境纹理时出错: {str(e)}")
                        return {"error": f"加载环境纹理时出错: {str(e)}"}
                    
                    # 连接环境纹理节点
                    links.new(tex_coord_node.outputs["Generated"], mapping_node.inputs["Vector"])
                    links.new(mapping_node.outputs["Vector"], env_texture_node.inputs["Vector"])
                    
                    # 创建混合节点以混合环境纹理和背景
                    mix_node = nodes.new("ShaderNodeMixShader")
                    mix_node.inputs[0].default_value = environment_strength
                    
                    # 创建第二个背景节点用于环境纹理
                    env_background_node = nodes.new("ShaderNodeBackground")
                    env_background_node.inputs["Strength"].default_value = environment_strength
                    
                    # 连接纹理到背景节点
                    links.new(env_texture_node.outputs["Color"], env_background_node.inputs["Color"])
                    
                    # 连接到混合节点
                    links.new(background_node.outputs["Background"], mix_node.inputs[1])
                    links.new(env_background_node.outputs["Background"], mix_node.inputs[2])
                    
                    # 连接混合节点到输出
                    links.new(mix_node.outputs["Shader"], output_node.inputs["Surface"])
                else:
                    logger.warning(f"环境纹理文件不存在: {environment_texture_path}")
            
            # 设置雾气
            if use_mist:
                # 启用雾气通道
                scene.render.layers[0].use_pass_mist = True
                
                # 获取雾气设置
                mist = scene.world.mist_settings
                mist.use_mist = True
                
                # 应用雾气参数
                if "start" in mist_settings:
                    mist.start = mist_settings["start"]
                    
                if "depth" in mist_settings:
                    mist.depth = mist_settings["depth"]
                    
                if "falloff" in mist_settings:
                    mist.falloff = mist_settings["falloff"]
            else:
                # 禁用雾气
                if hasattr(scene.world, "mist_settings"):
                    scene.world.mist_settings.use_mist = False
            
            return {
                "status": "success",
                "world_color": world_color,
                "ambient_strength": ambient_strength,
                "use_environment_texture": use_environment_texture,
                "environment_texture_path": environment_texture_path if use_environment_texture else "",
                "use_mist": use_mist
            }
            
        except Exception as e:
            logger.error(f"设置场景环境时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def get_scene_info(args):
    """获取场景信息"""
    logger.debug(f"获取场景信息: {args}")
    
    def exec_func():
        try:
            scene = bpy.context.scene
            
            # 基本场景信息
            scene_info = {
                "name": scene.name,
                "frame_current": scene.frame_current,
                "frame_start": scene.frame_start,
                "frame_end": scene.frame_end,
                "fps": scene.render.fps,
                "resolution_x": scene.render.resolution_x,
                "resolution_y": scene.render.resolution_y,
                "resolution_percentage": scene.render.resolution_percentage,
                "render_engine": scene.render.engine,
                "active_camera": scene.camera.name if scene.camera else None
            }
            
            # 世界设置信息
            if scene.world:
                world = scene.world
                world_info = {"name": world.name}
                
                # 如果世界使用节点，尝试获取背景颜色
                if world.use_nodes:
                    for node in world.node_tree.nodes:
                        if node.type == 'BACKGROUND':
                            if 'Color' in node.inputs:
                                color = node.inputs['Color'].default_value
                                world_info["color"] = [
                                    float(color[0]),
                                    float(color[1]),
                                    float(color[2])
                                ]
                            if 'Strength' in node.inputs:
                                world_info["strength"] = float(node.inputs['Strength'].default_value)
                            break
                
                # 雾气设置
                if hasattr(world, "mist_settings"):
                    mist = world.mist_settings
                    world_info["mist"] = {
                        "use_mist": mist.use_mist,
                        "start": mist.start,
                        "depth": mist.depth,
                        "falloff": mist.falloff
                    }
                
                scene_info["world"] = world_info
            
            # 统计场景中的对象
            objects_count = {
                "MESH": 0,
                "LIGHT": 0,
                "CAMERA": 0,
                "EMPTY": 0,
                "CURVE": 0,
                "ARMATURE": 0,
                "OTHER": 0
            }
            
            for obj in scene.objects:
                if obj.type in objects_count:
                    objects_count[obj.type] += 1
                else:
                    objects_count["OTHER"] += 1
            
            scene_info["objects_count"] = objects_count
            scene_info["total_objects"] = len(scene.objects)
            
            # 获取场景的渲染设置
            render_settings = {
                "engine": scene.render.engine,
                "use_motion_blur": scene.render.use_motion_blur,
                "film_transparent": scene.render.film_transparent,
                "use_freestyle": scene.render.use_freestyle if hasattr(scene.render, "use_freestyle") else False,
                "file_format": scene.render.image_settings.file_format,
                "color_mode": scene.render.image_settings.color_mode
            }
            
            # 引擎特定设置
            if scene.render.engine == 'CYCLES':
                render_settings["cycles"] = {
                    "device": scene.cycles.device if hasattr(scene.cycles, "device") else "CPU",
                    "samples": scene.cycles.samples if hasattr(scene.cycles, "samples") else 128,
                    "use_denoising": scene.cycles.use_denoising if hasattr(scene.cycles, "use_denoising") else False
                }
            
            scene_info["render_settings"] = render_settings
            
            # 获取场景的视图层和集合
            view_layers = []
            for vl in scene.view_layers:
                view_layers.append(vl.name)
                
            scene_info["view_layers"] = view_layers
            
            # 获取场景的所有集合
            def get_collections(parent_collection):
                collections = [parent_collection.name]
                for child in parent_collection.children:
                    collections.extend(get_collections(child))
                return collections
            
            scene_info["collections"] = get_collections(scene.collection)
            
            return {
                "status": "success",
                "scene_info": scene_info
            }
            
        except Exception as e:
            logger.error(f"获取场景信息时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def update_scene(args):
    """更新场景属性"""
    logger.debug(f"更新场景属性: {args}")
    
    # 解析参数
    frame_current = args.get("frame_current")
    frame_start = args.get("frame_start")
    frame_end = args.get("frame_end")
    fps = args.get("fps")
    resolution_x = args.get("resolution_x")
    resolution_y = args.get("resolution_y")
    resolution_percentage = args.get("resolution_percentage")
    render_engine = args.get("render_engine")
    
    def exec_func():
        try:
            scene = bpy.context.scene
            changes = []
            
            # 更新帧相关设置
            if frame_current is not None:
                scene.frame_current = frame_current
                changes.append(f"当前帧: {frame_current}")
                
            if frame_start is not None:
                scene.frame_start = frame_start
                changes.append(f"起始帧: {frame_start}")
                
            if frame_end is not None:
                scene.frame_end = frame_end
                changes.append(f"结束帧: {frame_end}")
                
            if fps is not None:
                scene.render.fps = fps
                changes.append(f"FPS: {fps}")
            
            # 更新分辨率设置
            if resolution_x is not None:
                scene.render.resolution_x = resolution_x
                changes.append(f"分辨率X: {resolution_x}")
                
            if resolution_y is not None:
                scene.render.resolution_y = resolution_y
                changes.append(f"分辨率Y: {resolution_y}")
                
            if resolution_percentage is not None:
                scene.render.resolution_percentage = resolution_percentage
                changes.append(f"分辨率百分比: {resolution_percentage}%")
            
            # 更新渲染引擎
            if render_engine is not None:
                valid_engines = ['BLENDER_EEVEE', 'CYCLES', 'BLENDER_WORKBENCH']
                if render_engine in valid_engines:
                    scene.render.engine = render_engine
                    changes.append(f"渲染引擎: {render_engine}")
                else:
                    logger.warning(f"无效的渲染引擎: {render_engine}")
                    changes.append(f"无效的渲染引擎: {render_engine} (已忽略)")
            
            return {
                "status": "success",
                "scene": scene.name,
                "changes": changes
            }
            
        except Exception as e:
            logger.error(f"更新场景属性时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def export_scene(args):
    """导出场景到文件"""
    logger.debug(f"导出场景: {args}")
    
    # 解析参数
    filepath = args.get("filepath", "")
    file_format = args.get("format", "FBX").upper()
    selection_only = args.get("selection_only", False)
    
    def exec_func():
        try:
            if not filepath:
                return {"error": "未提供导出文件路径"}
            
            # 确保输出目录存在
            output_dir = os.path.dirname(filepath)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            # 根据格式确定导出函数
            result = {"status": "success", "format": file_format, "filepath": filepath}
            
            if file_format == "FBX":
                bpy.ops.export_scene.fbx(
                    filepath=filepath,
                    use_selection=selection_only,
                    use_active_collection=False,
                    axis_forward='-Z',
                    axis_up='Y'
                )
                
            elif file_format == "OBJ":
                bpy.ops.export_scene.obj(
                    filepath=filepath,
                    use_selection=selection_only,
                    axis_forward='-Z',
                    axis_up='Y'
                )
                
            elif file_format == "GLB" or file_format == "GLTF":
                bpy.ops.export_scene.gltf(
                    filepath=filepath,
                    export_format='GLB' if file_format == "GLB" else 'GLTF_SEPARATE',
                    use_selection=selection_only
                )
                
            elif file_format == "BLEND":
                # 保存为Blender文件
                bpy.ops.wm.save_as_mainfile(filepath=filepath, copy=True)
                
            else:
                return {"error": f"不支持的导出格式: {file_format}"}
            
            return result
            
        except Exception as e:
            logger.error(f"导出场景时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def import_file(args):
    """导入文件到场景"""
    logger.debug(f"导入文件: {args}")
    
    # 解析参数
    filepath = args.get("filepath", "")
    import_as = args.get("import_as", "")  # 可以是: "APPEND", "LINK", "AUTO"
    
    def exec_func():
        try:
            if not filepath or not os.path.exists(filepath):
                return {"error": f"文件不存在: {filepath}"}
            
            # 获取文件扩展名
            file_ext = os.path.splitext(filepath)[1].lower()
            
            # 根据文件类型确定导入函数
            result = {"status": "success", "filepath": filepath}
            
            if file_ext == ".fbx":
                bpy.ops.import_scene.fbx(filepath=filepath)
                result["format"] = "FBX"
                
            elif file_ext == ".obj":
                bpy.ops.import_scene.obj(filepath=filepath)
                result["format"] = "OBJ"
                
            elif file_ext in [".glb", ".gltf"]:
                bpy.ops.import_scene.gltf(filepath=filepath)
                result["format"] = "GLTF/GLB"
                
            elif file_ext == ".blend":
                # 根据导入方式决定如何导入.blend文件
                if import_as == "APPEND":
                    # 追加所有对象
                    bpy.ops.wm.append(
                        filepath="",
                        directory=filepath + "\\Object\\",
                        filename="",
                        link=False,
                        autoselect=True
                    )
                    result["import_method"] = "APPEND"
                    
                elif import_as == "LINK":
                    # 链接所有对象
                    bpy.ops.wm.link(
                        filepath="",
                        directory=filepath + "\\Object\\",
                        filename="",
                        autoselect=True
                    )
                    result["import_method"] = "LINK"
                    
                else:  # AUTO 或 其他
                    # 默认追加
                    bpy.ops.wm.append(
                        filepath="",
                        directory=filepath + "\\Object\\",
                        filename="",
                        link=False,
                        autoselect=True
                    )
                    result["import_method"] = "APPEND (AUTO)"
                
                result["format"] = "BLEND"
                
            else:
                return {"error": f"不支持的导入格式: {file_ext}"}
            
            # 统计导入的对象数量
            result["objects_imported"] = len(bpy.context.selected_objects)
            
            return result
            
        except Exception as e:
            logger.error(f"导入文件时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def create_collection(args):
    """创建新的集合"""
    logger.debug(f"创建集合: {args}")
    
    # 解析参数
    collection_name = args.get("name", "New_Collection")
    parent_collection = args.get("parent_collection", "")
    
    def exec_func():
        try:
            # 创建新集合
            new_collection = bpy.data.collections.new(collection_name)
            
            # 确定父集合
            if parent_collection and parent_collection in bpy.data.collections:
                # 添加到指定的父集合
                bpy.data.collections[parent_collection].children.link(new_collection)
            else:
                # 添加到场景的主集合
                bpy.context.scene.collection.children.link(new_collection)
                parent_collection = bpy.context.scene.collection.name
            
            return {
                "status": "success",
                "collection_name": new_collection.name,
                "parent_collection": parent_collection
            }
            
        except Exception as e:
            logger.error(f"创建集合时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def list_collections(args):
    """列出场景中的所有集合"""
    logger.debug(f"列出集合: {args}")
    
    def exec_func():
        try:
            collections = []
            
            # 递归获取集合及其子集合
            def get_collections(collection, parent=None, level=0):
                collection_info = {
                    "name": collection.name,
                    "parent": parent,
                    "level": level,
                    "objects_count": len(collection.objects)
                }
                
                collections.append(collection_info)
                
                # 遍历子集合
                for child in collection.children:
                    get_collections(child, collection.name, level + 1)
            
            # 从场景的主集合开始
            get_collections(bpy.context.scene.collection)
            
            return {
                "status": "success",
                "count": len(collections),
                "collections": collections
            }
            
        except Exception as e:
            logger.error(f"列出集合时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def delete_collection(args):
    """删除集合"""
    logger.debug(f"删除集合: {args}")
    
    # 解析参数
    collection_name = args.get("collection_name")
    remove_objects = args.get("remove_objects", False)  # 是否同时删除集合中的对象
    
    def exec_func():
        try:
            # 检查集合是否存在
            if collection_name not in bpy.data.collections:
                return {"error": f"找不到集合: {collection_name}"}
            
            collection = bpy.data.collections[collection_name]
            
            # 如果需要保留对象，先将它们移动到场景集合
            if not remove_objects:
                scene_collection = bpy.context.scene.collection
                for obj in collection.objects[:]:  # 使用切片创建副本，因为我们将修改集合
                    scene_collection.objects.link(obj)
                    collection.objects.unlink(obj)
            
            # 删除集合
            bpy.data.collections.remove(collection)
            
            return {
                "status": "success",
                "deleted_collection": collection_name,
                "objects_removed": remove_objects
            }
            
        except Exception as e:
            logger.error(f"删除集合时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

# 注册工具
TOOLS = {
    # 渲染类
    "render_scene": render_scene,
    
    # 环境设置类
    "setup_scene_environment": setup_scene_environment,
    
    # 信息获取类
    "get_scene_info": get_scene_info,
    
    # 场景修改类
    "update_scene": update_scene,
    
    # 导入导出类
    "export_scene": export_scene,
    "import_file": import_file,
    
    # 集合操作类
    "create_collection": create_collection,
    "list_collections": list_collections,
    "delete_collection": delete_collection
} 
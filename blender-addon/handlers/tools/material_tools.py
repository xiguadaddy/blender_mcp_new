"""
材质操作工具模块

包括材质的创建、获取、修改和删除相关功能。
"""

import bpy
import traceback
import json
from ..tool_handlers import execute_in_main_thread
from ...mcp_types import create_text_content, create_image_content
from ...logger import get_logger

# 设置日志
logger = get_logger("BlenderMCP.MaterialTools")

# 材质创建函数
def set_material(args):
    """为对象设置或创建材质
    
    参数:
        object_name: 要应用材质的对象名称
        material_name: 可选，要使用或创建的材质名称
        color: 可选，材质颜色 [R, G, B] 或 [R, G, B, A]
        metallic: 可选，金属度 (0.0-1.0)
        roughness: 可选，粗糙度 (0.0-1.0)
        specular: 可选，镜面反射强度 (0.0-1.0)
    """
    logger.debug(f"设置材质: {args}")
    object_name = args.get("object_name")
    material_name = args.get("material_name")  # 材质名称参数
    color = args.get("color", [0.8, 0.8, 0.8, 1.0])
    metallic = args.get("metallic", 0.0)
    roughness = args.get("roughness", 0.5)
    specular = args.get("specular", 0.5)  # 镜面反射参数
    
    def exec_func():
        try:
            # 获取对象
            obj = bpy.data.objects.get(object_name)
            if not obj:
                logger.error(f"找不到对象: {object_name}")
                return {"error": f"找不到对象: {object_name}"}
                
            # 添加强制更新
            bpy.context.view_layer.update()
            
            # 确定材质名称 (如果未提供)
            mat_name = material_name or f"{object_name}_material"
            
            # 查找现有材质或创建新材质
            mat = bpy.data.materials.get(mat_name)
            if not mat:
                mat = bpy.data.materials.new(name=mat_name)
                logger.debug(f"创建新材质: {mat_name}")
            else:
                logger.debug(f"使用现有材质: {mat_name}")
            
            # 启用节点编辑
            if not mat.use_nodes:
                mat.use_nodes = True
                logger.debug(f"启用材质节点: {mat_name}")
            
            # 获取主要着色器节点
            nodes = mat.node_tree.nodes
            principled_bsdf = None
            
            # 查找Principled BSDF节点
            for node in nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    principled_bsdf = node
                    break
            
            # 如果找不到主要着色器节点，创建一个
            if not principled_bsdf:
                principled_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
                logger.debug("创建新的Principled BSDF节点")
            
            # 设置颜色和属性
            try:
                # 确保颜色有Alpha通道
                if color:
                    if len(color) == 3:
                        color_with_alpha = color + [1.0]
                    else:
                        color_with_alpha = color
                    
                    # 设置主要材质属性
                    if principled_bsdf and "Base Color" in principled_bsdf.inputs:
                        principled_bsdf.inputs["Base Color"].default_value = color_with_alpha
                        logger.debug(f"设置Base Color: {color_with_alpha}")
                
                # 设置其他节点属性
                if principled_bsdf:
                    # 设置金属度
                    if "Metallic" in principled_bsdf.inputs:
                        principled_bsdf.inputs["Metallic"].default_value = metallic
                        logger.debug(f"设置Metallic: {metallic}")
                    
                    # 设置粗糙度
                    if "Roughness" in principled_bsdf.inputs:
                        principled_bsdf.inputs["Roughness"].default_value = roughness
                        logger.debug(f"设置Roughness: {roughness}")
                    
                    # 设置镜面反射
                    if "Specular" in principled_bsdf.inputs:
                        principled_bsdf.inputs["Specular"].default_value = specular
                        logger.debug(f"设置Specular: {specular}")
                
                # 设置老版本Blender材质属性（向后兼容）
                if hasattr(mat, "diffuse_color") and color:
                    mat.diffuse_color = color_with_alpha
                    logger.debug(f"设置diffuse_color: {color_with_alpha}")
                
                # 尝试设置其他向后兼容属性
                if hasattr(mat, "specular_intensity"):
                    mat.specular_intensity = specular
                    logger.debug(f"设置specular_intensity: {specular}")
                
                metallic_attr = getattr(mat, "metallic", None)
                if metallic_attr is not None:
                    mat.metallic = metallic
                    logger.debug(f"设置metallic属性: {metallic}")
                    
                roughness_attr = getattr(mat, "roughness", None)
                if roughness_attr is not None:
                    mat.roughness = roughness
                    logger.debug(f"设置roughness属性: {roughness}")
                
                # 确保输出节点连接
                output_node = None
                for node in nodes:
                    if node.type == 'OUTPUT_MATERIAL':
                        output_node = node
                        break
                
                if not output_node:
                    output_node = nodes.new(type='ShaderNodeOutputMaterial')
                    logger.debug("创建新的输出节点")
                
                # 连接着色器到输出
                if principled_bsdf and "BSDF" in principled_bsdf.outputs:
                    # 检查是否已经连接
                    if not output_node.inputs['Surface'].links:
                        mat.node_tree.links.new(principled_bsdf.outputs["BSDF"], output_node.inputs["Surface"])
                        logger.debug("连接BSDF到输出节点")
                
            except (AttributeError, KeyError) as e:
                logger.warning(f"设置材质属性时出现非关键错误: {str(e)}")
                # 继续执行，因为这些是非关键错误
                
            # 应用材质到对象
            if len(obj.material_slots) == 0:
                obj.data.materials.append(mat)
                logger.debug(f"添加材质到对象 {object_name}: {mat.name}")
            else:
                # 更新现有插槽
                obj.material_slots[0].material = mat
                logger.debug(f"更新对象 {object_name} 的材质: {mat.name}")
                
            # 确保所有插槽都有材质
            for slot in obj.material_slots:
                if slot.material is None:
                    slot.material = mat
                    logger.debug(f"填充空材质插槽: {mat.name}")
                
            # 修改后强制更新材质
            if mat.node_tree:
                mat.node_tree.update_tag()
            
            # 强制视图更新
            bpy.context.view_layer.update()
            
            color_str = "RGB({:.2f}, {:.2f}, {:.2f})".format(*color_with_alpha[:3]) if 'color_with_alpha' in locals() else "未指定"
            return {
                "status": "success", 
                "text": f"已为对象 '{object_name}' 设置材质 '{mat.name}' (颜色: {color_str})",
                "material_name": mat.name,
                "object_name": object_name,
                "color": list(color_with_alpha) if 'color_with_alpha' in locals() else None,
                "metallic": metallic,
                "roughness": roughness,
                "specular": specular
            }
        except Exception as e:
            error_msg = f"设置材质时出错: {str(e)}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            return {"error": error_msg}
            
    return execute_in_main_thread(exec_func)

def create_node_material(args):
    """创建节点材质"""
    logger.debug(f"创建节点材质: {args}")
    name = args.get("name")
    node_setup = args.get("node_setup", {})
    
    def exec_func():
        try:
            # 创建新材质或获取现有材质
            mat = bpy.data.materials.get(name)
            if not mat:
                mat = bpy.data.materials.new(name=name)
                logger.debug(f"创建新材质: {name}")
            else:
                logger.debug(f"使用现有材质: {name}")
            
            mat.use_nodes = True
            node_tree = mat.node_tree
            
            # 清除现有节点
            for node in node_tree.nodes:
                node_tree.nodes.remove(node)
                
            # 创建节点
            nodes = {}
            nodes_created = 0
            
            for node_id, node_data in node_setup.get("nodes", {}).items():
                node_type = node_data.get("type", "ShaderNodeBsdfPrincipled")
                
                # 必要时添加Shader前缀
                if not node_type.startswith("ShaderNode") and not node_type.startswith("NodeGroup"):
                    node_type = f"ShaderNode{node_type}"
                
                try:
                    node = node_tree.nodes.new(type=node_type)
                    nodes_created += 1
                    
                    # 设置位置
                    location = node_data.get("location", (0, 0))
                    node.location = location
                    
                    # 设置属性
                    for prop, value in node_data.get("properties", {}).items():
                        if hasattr(node, prop):
                            setattr(node, prop, value)
                        elif prop in node.inputs:
                            if isinstance(value, (list, tuple)) and len(value) >= 3:
                                node.inputs[prop].default_value = value
                            else:
                                node.inputs[prop].default_value = value
                    
                    nodes[node_id] = node
                    
                except Exception as e:
                    logger.warning(f"创建节点 {node_type} 时出错: {str(e)}")
            
            # 创建连接
            links_created = 0
            for link_data in node_setup.get("links", []):
                from_node_id = link_data.get("from_node")
                to_node_id = link_data.get("to_node")
                from_socket = link_data.get("from_socket", 0)
                to_socket = link_data.get("to_socket", 0)
                
                if from_node_id in nodes and to_node_id in nodes:
                    from_node = nodes[from_node_id]
                    to_node = nodes[to_node_id]
                    
                    # 处理索引或名称的插槽
                    if isinstance(from_socket, int) and from_socket < len(from_node.outputs):
                        out_socket = from_node.outputs[from_socket]
                    elif isinstance(from_socket, str) and from_socket in from_node.outputs:
                        out_socket = from_node.outputs[from_socket]
                    else:
                        logger.warning(f"输出插槽 {from_socket} 不存在")
                        continue
                        
                    if isinstance(to_socket, int) and to_socket < len(to_node.inputs):
                        in_socket = to_node.inputs[to_socket]
                    elif isinstance(to_socket, str) and to_socket in to_node.inputs:
                        in_socket = to_node.inputs[to_socket]
                    else:
                        logger.warning(f"输入插槽 {to_socket} 不存在")
                        continue
                    
                    # 创建连接
                    node_tree.links.new(out_socket, in_socket)
                    links_created += 1
            
            # 确保有输出节点
            output_node = None
            for node in node_tree.nodes:
                if node.type == 'OUTPUT_MATERIAL':
                    output_node = node
                    break
                    
            if not output_node:
                output_node = node_tree.nodes.new(type='ShaderNodeOutputMaterial')
                
            # 确保有着色器连接到输出
            if len(output_node.inputs['Surface'].links) == 0:
                # 查找Principled BSDF节点
                principled = None
                for node in node_tree.nodes:
                    if node.type == 'BSDF_PRINCIPLED':
                        principled = node
                        break
                        
                if principled:
                    node_tree.links.new(principled.outputs['BSDF'], output_node.inputs['Surface'])
            
            return {
                "status": "success",
                "material": name,
                "nodes_created": nodes_created,
                "links_created": links_created
            }
            
        except Exception as e:
            logger.error(f"创建节点材质时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

# 材质获取函数
def get_material_info(args):
    """获取材质信息"""
    logger.debug(f"获取材质信息: {args}")
    material_name = args.get("material_name")
    include_nodes = args.get("include_nodes", False)
    
    def exec_func():
        try:
            # 获取材质
            mat = bpy.data.materials.get(material_name)
            if not mat:
                return {"error": f"找不到材质: {material_name}"}
            
            # 基本材质信息
            mat_info = {
                "name": mat.name,
                "use_nodes": mat.use_nodes,
                "is_grease_pencil": getattr(mat, "is_grease_pencil", False)
            }
            
            # 尝试获取基本颜色
            if mat.use_nodes:
                principled = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
                if principled:
                    if "Base Color" in principled.inputs:
                        mat_info["color"] = list(principled.inputs["Base Color"].default_value)
                    if "Metallic" in principled.inputs:
                        mat_info["metallic"] = principled.inputs["Metallic"].default_value
                    if "Roughness" in principled.inputs:
                        mat_info["roughness"] = principled.inputs["Roughness"].default_value
                    if "Specular" in principled.inputs:
                        mat_info["specular"] = principled.inputs["Specular"].default_value
            elif hasattr(mat, "diffuse_color"):
                mat_info["color"] = list(mat.diffuse_color)
            
            # 附加节点数据
            if include_nodes and mat.use_nodes:
                nodes_data = {}
                for node in mat.node_tree.nodes:
                    node_info = {
                        "type": node.type,
                        "location": list(node.location),
                        "width": node.width,
                        "height": node.height
                    }
                    
                    # 获取输入和输出信息
                    inputs = {}
                    for i, input in enumerate(node.inputs):
                        if hasattr(input, "default_value"):
                            # 处理不同类型的值
                            if isinstance(input.default_value, (list, tuple)):
                                inputs[input.name] = list(input.default_value)
                            else:
                                inputs[input.name] = input.default_value
                    
                    node_info["inputs"] = inputs
                    nodes_data[node.name] = node_info
                
                # 获取连接
                links = []
                for link in mat.node_tree.links:
                    links.append({
                        "from_node": link.from_node.name,
                        "from_socket": link.from_socket.name,
                        "to_node": link.to_node.name,
                        "to_socket": link.to_socket.name
                    })
                
                mat_info["nodes"] = nodes_data
                mat_info["links"] = links
            
            # 获取使用该材质的对象
            used_by_objects = []
            for obj in bpy.data.objects:
                if obj.type == 'MESH':
                    for slot in obj.material_slots:
                        if slot.material == mat:
                            used_by_objects.append(obj.name)
                            break
            
            mat_info["used_by_objects"] = used_by_objects
            
            return {
                "status": "success",
                "text": f"获取材质 '{material_name}' 的信息",
                "material_info": mat_info
            }
            
        except Exception as e:
            logger.error(f"获取材质信息时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def list_materials(args):
    """列出所有材质"""
    logger.debug(f"列出材质: {args}")
    include_basic_info = args.get("include_basic_info", True)
    
    def exec_func():
        try:
            materials = []
            
            for mat in bpy.data.materials:
                # 基本材质信息
                mat_info = {"name": mat.name}
                
                # 附加基本信息
                if include_basic_info:
                    mat_info["use_nodes"] = mat.use_nodes
                    
                    # 尝试获取颜色信息
                    if mat.use_nodes:
                        principled = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
                        if principled and "Base Color" in principled.inputs:
                            mat_info["color"] = list(principled.inputs["Base Color"].default_value)
                    elif hasattr(mat, "diffuse_color"):
                        mat_info["color"] = list(mat.diffuse_color)
                
                materials.append(mat_info)
            
            return {
                "status": "success",
                "count": len(materials),
                "materials": materials
            }
            
        except Exception as e:
            logger.error(f"列出材质时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

# 材质修改函数
def update_material_property(args):
    """更新材质属性"""
    logger.debug(f"更新材质属性: {args}")
    material_name = args.get("material_name")
    property_name = args.get("property_name")
    value = args.get("value")
    
    def exec_func():
        try:
            # 获取材质
            mat = bpy.data.materials.get(material_name)
            if not mat:
                return {"error": f"找不到材质: {material_name}"}
            
            # 确保使用节点
            if not mat.use_nodes:
                mat.use_nodes = True
            
            # 处理常见属性
            if property_name == "color" or property_name == "base_color":
                # 确保颜色值完整
                if isinstance(value, list) and len(value) == 3:
                    value = value + [1.0]  # 添加alpha通道
                
                # 查找Principled BSDF节点
                principled = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
                if principled and "Base Color" in principled.inputs:
                    principled.inputs["Base Color"].default_value = value
                    
                # 同时更新旧材质系统的颜色
                if hasattr(mat, "diffuse_color") and len(value) >= 3:
                    mat.diffuse_color = value[:4] if len(value) >= 4 else value + [1.0]
                    
            elif property_name == "metallic":
                principled = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
                if principled and "Metallic" in principled.inputs:
                    principled.inputs["Metallic"].default_value = float(value)
                    
            elif property_name == "roughness":
                principled = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
                if principled and "Roughness" in principled.inputs:
                    principled.inputs["Roughness"].default_value = float(value)
                    
            elif property_name == "specular":
                principled = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
                if principled and "Specular" in principled.inputs:
                    principled.inputs["Specular"].default_value = float(value)
                    
            elif property_name == "alpha" or property_name == "transparency":
                # 设置材质透明度
                principled = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
                if principled and "Alpha" in principled.inputs:
                    principled.inputs["Alpha"].default_value = float(value)
                    
                # 启用混合
                if float(value) < 1.0:
                    mat.blend_method = 'BLEND'
                    
            elif property_name == "emission_color":
                # 设置发光颜色
                principled = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
                if principled and "Emission Color" in principled.inputs:
                    if isinstance(value, list) and len(value) >= 3:
                        if len(value) == 3:
                            value = value + [1.0]
                        principled.inputs["Emission Color"].default_value = value
                        
            elif property_name == "emission_strength":
                # 设置发光强度
                principled = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
                if principled and "Emission Strength" in principled.inputs:
                    principled.inputs["Emission Strength"].default_value = float(value)
                    
            else:
                return {"error": f"不支持的属性: {property_name}"}
            
            return {
                "status": "success",
                "material": material_name,
                "property": property_name,
                "value": value
            }
            
        except Exception as e:
            logger.error(f"更新材质属性时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def rename_material(args):
    """重命名材质"""
    logger.debug(f"重命名材质: {args}")
    material_name = args.get("material_name")
    new_name = args.get("new_name")
    
    def exec_func():
        try:
            # 获取材质
            mat = bpy.data.materials.get(material_name)
            if not mat:
                return {"error": f"找不到材质: {material_name}"}
            
            if not new_name:
                return {"error": "未提供新名称"}
                
            old_name = mat.name
            mat.name = new_name
            
            return {
                "status": "success",
                "old_name": old_name,
                "new_name": mat.name  # 返回实际名称（可能与请求的不同，如果名称已存在）
            }
            
        except Exception as e:
            logger.error(f"重命名材质时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

# 材质删除函数
def delete_material(args):
    """删除材质"""
    logger.debug(f"删除材质: {args}")
    material_names = args.get("material_names", [])
    material_name = args.get("material_name")
    
    # 确保我们有材质列表
    if material_name and not material_names:
        material_names = [material_name]
        
    def exec_func():
        try:
            if not material_names:
                return {"error": "未提供要删除的材质名称"}
                
            deleted_materials = []
            not_found_materials = []
            
            # 删除每个材质
            for name in material_names:
                mat = bpy.data.materials.get(name)
                if mat:
                    # 记录使用该材质的对象
                    used_by_objects = []
                    for obj in bpy.data.objects:
                        if obj.type == 'MESH':
                            for slot in obj.material_slots:
                                if slot.material == mat:
                                    used_by_objects.append(obj.name)
                                    break
                    
                    # 从对象中移除材质
                    for obj_name in used_by_objects:
                        obj = bpy.data.objects.get(obj_name)
                        if obj:
                            for i, slot in enumerate(obj.material_slots):
                                if slot.material == mat:
                                    obj.active_material_index = i
                                    bpy.ops.object.material_slot_remove({'object': obj})
                    
                    # 删除材质数据
                    bpy.data.materials.remove(mat)
                    deleted_materials.append(name)
                else:
                    not_found_materials.append(name)
            
            result = {
                "status": "success",
                "deleted_count": len(deleted_materials),
                "deleted_materials": deleted_materials
            }
            
            if not_found_materials:
                result["not_found_materials"] = not_found_materials
                result["warnings"] = f"未找到 {len(not_found_materials)} 个材质"
                
            return result
            
        except Exception as e:
            logger.error(f"删除材质时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def duplicate_material(args):
    """复制材质"""
    logger.debug(f"复制材质: {args}")
    material_name = args.get("material_name")
    new_name = args.get("new_name")
    
    def exec_func():
        try:
            # 获取材质
            mat = bpy.data.materials.get(material_name)
            if not mat:
                return {"error": f"找不到材质: {material_name}"}
            
            # 创建新名称（如果未提供）
            if not new_name:
                new_name = f"{material_name}_copy"
            
            # 复制材质
            new_mat = mat.copy()
            new_mat.name = new_name
            
            return {
                "status": "success",
                "original_material": material_name,
                "new_material": new_mat.name
            }
            
        except Exception as e:
            logger.error(f"复制材质时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

# 注册工具
TOOLS = {
    # 创建类
    "set_material": set_material,
    "create_node_material": create_node_material,
    "duplicate_material": duplicate_material,
    
    # 获取类
    "get_material_info": get_material_info,
    "list_materials": list_materials,
    
    # 修改类
    "update_material_property": update_material_property,
    "rename_material": rename_material,
    
    # 删除类
    "delete_material": delete_material
}
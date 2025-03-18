"""
灯光操作工具模块

包括灯光的创建、获取、修改和删除相关功能。
"""

import bpy
import logging
import math
from mathutils import Euler
from ..tool_handlers import execute_in_main_thread

# 设置日志
logger = logging.getLogger("BlenderMCP.LightingTools")

# 灯光创建函数
def add_light(args):
    """添加灯光到场景"""
    logger.debug(f"添加灯光: {args}")
    light_type = args.get("light_type")
    location = args.get("location", [0, 0, 0])
    name = args.get("name", f"New_{light_type}")
    color = args.get("color", [1.0, 1.0, 1.0])
    energy = args.get("energy", 1000.0)
    
    def exec_func():
        try:
            # 创建灯光数据
            light_data = bpy.data.lights.new(name=name, type=light_type)
            light_data.color = color
            light_data.energy = energy
            
            # 创建灯光对象
            light_obj = bpy.data.objects.new(name=name, object_data=light_data)
            light_obj.location = location
            
            # 添加到场景
            bpy.context.collection.objects.link(light_obj)
            
            # 特定灯光类型的额外设置
            if light_type == 'SPOT':
                light_data.spot_size = args.get("spot_size", 1.0)
                light_data.spot_blend = args.get("spot_blend", 0.15)
            
            return {
                "status": "success", 
                "light_name": name,
                "light_type": light_type,
                "location": list(light_obj.location)
            }
        except Exception as e:
            logger.error(f"添加灯光时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def advanced_lighting(args):
    """高级照明设置"""
    logger.debug(f"高级照明设置: {args}")
    light_type = args.get("light_type", "AREA")
    name = args.get("name")
    location = args.get("location", (0, 0, 4))
    rotation = args.get("rotation", (0, 0, 0))
    color = args.get("color", (1, 1, 1))
    energy = args.get("energy", 100)
    settings = args.get("settings", {})
    
    def exec_func():
        try:
            # 创建灯光对象
            bpy.ops.object.light_add(type=light_type, location=location, rotation=rotation)
            light_obj = bpy.context.object
            
            # 设置名称
            if name:
                light_obj.name = name
            
            # 获取灯光数据
            light_data = light_obj.data
            
            # 设置基本参数
            light_data.color = color
            light_data.energy = energy
            
            # 根据灯光类型设置特定参数
            if light_type == "POINT":
                light_data.shadow_soft_size = settings.get("shadow_soft_size", 0.1)
                
            elif light_type == "SUN":
                light_data.angle = settings.get("angle", 0.1)
                
            elif light_type == "SPOT":
                light_data.spot_size = settings.get("spot_size", math.radians(45))
                light_data.spot_blend = settings.get("spot_blend", 0.15)
                light_data.shadow_soft_size = settings.get("shadow_soft_size", 0.1)
                
            elif light_type == "AREA":
                light_data.shape = settings.get("shape", 'SQUARE')
                light_data.size = settings.get("size", 1.0)
                if light_data.shape in ('RECTANGLE', 'ELLIPSE'):
                    light_data.size_y = settings.get("size_y", 1.0)
            
            # 阴影设置
            light_data.use_shadow = settings.get("use_shadow", True)
            if hasattr(light_data, "shadow_buffer_clip_start"):
                light_data.shadow_buffer_clip_start = settings.get("shadow_clip_start", 0.1)
                light_data.shadow_buffer_clip_end = settings.get("shadow_clip_end", 100.0)
            
            # 创建节点材质（如果需要）
            if settings.get("use_nodes", False):
                light_data.use_nodes = True
                
                # 获取节点树
                node_tree = light_data.node_tree
                
                # 清除现有节点
                for node in node_tree.nodes:
                    node_tree.nodes.remove(node)
                
                # 创建发射节点
                emission_node = node_tree.nodes.new(type='ShaderNodeEmission')
                emission_node.inputs['Color'].default_value = color + (1.0,)  # RGBA
                emission_node.inputs['Strength'].default_value = energy
                
                # 创建输出节点
                output_node = node_tree.nodes.new(type='ShaderNodeOutputLight')
                
                # 连接节点
                node_tree.links.new(emission_node.outputs[0], output_node.inputs[0])
            
            return {
                "status": "success",
                "object": light_obj.name,
                "type": light_type,
                "energy": energy,
                "location": location
            }
            
        except Exception as e:
            logger.error(f"高级照明设置时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

# 灯光修改函数
def update_light(args):
    """更新灯光属性"""
    logger.debug(f"更新灯光属性: {args}")
    light_name = args.get("light_name")
    color = args.get("color")
    energy = args.get("energy")
    location = args.get("location")
    rotation = args.get("rotation")
    
    def exec_func():
        try:
            # 获取灯光对象
            light_obj = bpy.data.objects.get(light_name)
            if not light_obj or light_obj.type != 'LIGHT':
                return {"error": f"找不到灯光对象: {light_name}"}
            
            # 获取灯光数据
            light_data = light_obj.data
            
            # 更新各项属性
            if color is not None:
                light_data.color = color
                
            if energy is not None:
                light_data.energy = energy
                
            if location is not None:
                light_obj.location = location
                
            if rotation is not None:
                light_obj.rotation_euler = Euler(rotation, 'XYZ')
            
            return {
                "status": "success",
                "light": light_name,
                "color": list(light_data.color),
                "energy": light_data.energy,
                "location": list(light_obj.location),
                "rotation": list(light_obj.rotation_euler)
            }
            
        except Exception as e:
            logger.error(f"更新灯光属性时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

# 灯光获取函数
def get_light_info(args):
    """获取灯光信息"""
    logger.debug(f"获取灯光信息: {args}")
    light_name = args.get("light_name")
    
    def exec_func():
        try:
            # 获取灯光对象
            light_obj = bpy.data.objects.get(light_name)
            if not light_obj or light_obj.type != 'LIGHT':
                return {"error": f"找不到灯光对象: {light_name}"}
            
            # 获取灯光数据
            light_data = light_obj.data
            
            # 基本灯光信息
            light_info = {
                "name": light_obj.name,
                "type": light_data.type,
                "location": list(light_obj.location),
                "rotation": list(light_obj.rotation_euler),
                "color": list(light_data.color),
                "energy": light_data.energy,
                "use_shadow": light_data.use_shadow
            }
            
            # 根据灯光类型获取特定信息
            if light_data.type == 'POINT':
                light_info["shadow_soft_size"] = light_data.shadow_soft_size
                
            elif light_data.type == 'SUN':
                light_info["angle"] = light_data.angle
                
            elif light_data.type == 'SPOT':
                light_info["spot_size"] = light_data.spot_size
                light_info["spot_blend"] = light_data.spot_blend
                light_info["shadow_soft_size"] = light_data.shadow_soft_size
                
            elif light_data.type == 'AREA':
                light_info["shape"] = light_data.shape
                light_info["size"] = light_data.size
                if light_data.shape in ('RECTANGLE', 'ELLIPSE'):
                    light_info["size_y"] = light_data.size_y
            
            # 检查节点使用情况
            light_info["use_nodes"] = light_data.use_nodes
            
            return {
                "status": "success",
                "light_info": light_info
            }
            
        except Exception as e:
            logger.error(f"获取灯光信息时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

def list_lights(args):
    """列出场景中的所有灯光"""
    logger.debug(f"列出灯光: {args}")
    
    def exec_func():
        try:
            lights = []
            
            # 遍历场景中的所有对象
            for obj in bpy.context.scene.objects:
                if obj.type == 'LIGHT':
                    light_data = obj.data
                    
                    # 基本灯光信息
                    light_info = {
                        "name": obj.name,
                        "type": light_data.type,
                        "location": list(obj.location),
                        "color": list(light_data.color),
                        "energy": light_data.energy
                    }
                    
                    lights.append(light_info)
            
            return {
                "status": "success",
                "count": len(lights),
                "lights": lights
            }
            
        except Exception as e:
            logger.error(f"列出灯光时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

# 灯光删除函数
def delete_light(args):
    """删除灯光"""
    logger.debug(f"删除灯光: {args}")
    light_names = args.get("light_names", [])
    light_name = args.get("light_name")
    
    # 确保我们有灯光列表
    if light_name and not light_names:
        light_names = [light_name]
        
    def exec_func():
        try:
            if not light_names:
                return {"error": "未提供要删除的灯光名称"}
                
            deleted_lights = []
            not_found_lights = []
            
            # 收集需要删除的灯光对象
            lights_to_delete = []
            for name in light_names:
                obj = bpy.data.objects.get(name)
                if obj and obj.type == 'LIGHT':
                    lights_to_delete.append(obj)
                    deleted_lights.append(name)
                else:
                    not_found_lights.append(name)
            
            # 删除灯光对象
            if lights_to_delete:
                # 取消选择所有对象
                bpy.ops.object.select_all(action='DESELECT')
                
                # 选择要删除的灯光
                for obj in lights_to_delete:
                    obj.select_set(True)
                    
                # 删除选定的对象
                bpy.ops.object.delete()
            
            result = {
                "status": "success",
                "deleted_count": len(deleted_lights),
                "deleted_lights": deleted_lights
            }
            
            if not_found_lights:
                result["not_found_lights"] = not_found_lights
                result["warnings"] = f"未找到 {len(not_found_lights)} 个灯光"
                
            return result
            
        except Exception as e:
            logger.error(f"删除灯光时出错: {str(e)}")
            return {"error": str(e)}
            
    return execute_in_main_thread(exec_func)

# 注册工具
TOOLS = {
    # 创建类
    "add_light": add_light,
    "advanced_lighting": advanced_lighting,
    
    # 修改类
    "update_light": update_light,
    
    # 获取类
    "get_light_info": get_light_info,
    "list_lights": list_lights,
    
    # 删除类
    "delete_light": delete_light
} 
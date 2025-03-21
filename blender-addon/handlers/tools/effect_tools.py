"""
特效操作工具模块

包括粒子特效、烟雾模拟、流体模拟和合成节点控制等功能。
"""

import bpy
from ..tool_handlers import execute_in_main_thread
from ...mcp_types import create_text_content, create_image_content
from ...logger import get_logger

# 设置日志
logger = get_logger("BlenderMCP.EffectTools")

# ---------- 粒子特效 ----------

def create_particle_system(args):
    """创建粒子系统"""
    logger.debug(f"创建粒子系统: {args}")
    object_name = args.get("object_name")
    particles_count = args.get("count", 1000)
    particle_type = args.get("type", "EMITTER")  # EMITTER, HAIR
    settings = args.get("settings", {})

    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"对象不存在: {object_name}"}

            # 设置活动对象
            bpy.context.view_layer.objects.active = obj

            # 创建粒子系统
            if not obj.particle_systems:
                obj.modifiers.new("ParticleSystem", 'PARTICLE_SYSTEM')

            particle_system = obj.particle_systems[-1]
            particle_settings = particle_system.settings

            # 设置基本参数
            particle_settings.name = settings.get("name", f"{obj.name}_particles")
            particle_settings.type = particle_type
            particle_settings.count = particles_count

            # 设置发射参数
            if particle_type == "EMITTER":
                particle_settings.frame_start = settings.get("frame_start", 1)
                particle_settings.frame_end = settings.get("frame_end", 200)
                particle_settings.lifetime = settings.get("lifetime", 100)
                particle_settings.emit_from = settings.get("emit_from", 'FACE')

                # 速度设置
                if "velocity_factor" in settings:
                    particle_settings.normal_factor = settings["velocity_factor"]

                # 物理设置
                if "physics_type" in settings:
                    particle_settings.physics_type = settings["physics_type"]

                # 渲染设置
                if "render_type" in settings:
                    particle_settings.render_type = settings["render_type"]

                    # 对象渲染
                    if settings["render_type"] == 'OBJECT' and "instance_object" in settings:
                        instance_obj = bpy.data.objects.get(settings["instance_object"])
                        if instance_obj:
                            particle_settings.instance_object = instance_obj

                    # 集合渲染
                    elif settings["render_type"] == 'COLLECTION' and "instance_collection" in settings:
                        instance_col = bpy.data.collections.get(settings["instance_collection"])
                        if instance_col:
                            particle_settings.instance_collection = instance_col

            # 设置毛发参数
            elif particle_type == "HAIR":
                particle_settings.hair_length = settings.get("hair_length", 4.0)
                particle_settings.render_step = settings.get("render_step", 3)

                # 动力学设置
                if "use_dynamic_hair" in settings:
                    particle_settings.use_dynamic_hair = settings["use_dynamic_hair"]

            # 更新场景
            bpy.context.view_layer.update()

            return {
                "status": "success",
                "text": f"已为对象 '{object_name}' 创建含 {particles_count} 个粒子的 {particle_type} 粒子系统",
                "object_name": object_name,
                "particles_count": particles_count,
                "particle_type": particle_type,
                "system_name": particle_settings.name
            }
        except Exception as e:
            logger.error(f"创建粒子系统时出错: {str(e)}")
            return {"error": str(e)}

    return execute_in_main_thread(exec_func)

def modify_particle_system(args):
    """修改粒子系统属性 (占位符，可以扩展更多属性)"""
    logger.debug(f"修改粒子系统属性: {args}")
    object_name = args.get("object_name")
    system_name = args.get("system_name")
    settings = args.get("settings", {})

    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"找不到对象: {object_name}"}

            particle_system = obj.particle_systems.get(system_name)
            if not particle_system:
                return {"error": f"找不到粒子系统: {system_name}"}

            particle_settings = particle_system.settings
            if "count" in settings:
                particle_settings.count = settings["count"]
            # ... 可以添加更多可修改的粒子系统属性

            return {
                "status": "success",
                "object_name": object_name,
                "system_name": system_name,
                "modified_settings": list(settings.keys())
            }
        except Exception as e:
            logger.error(f"修改粒子系统属性出错: {str(e)}")
            return {"error": str(e)}

    return execute_in_main_thread(exec_func)

# ---------- 烟雾模拟 ----------

def create_smoke_domain(args):
    """创建烟雾域"""
    logger.debug(f"创建烟雾域: {args}")
    object_name = args.get("object_name")
    smoke_type = args.get("smoke_type", 'DOMAIN') # 'DOMAIN', 'FLOW', 'COLLISION'
    settings = args.get("settings", {})

    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"找不到对象: {object_name}"}

            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.modifier_add(type='SMOKE')
            smoke_modifier = obj.modifiers["Smoke"]
            smoke_modifier.smoke_type = smoke_type

            if smoke_type == 'DOMAIN':
                smoke_settings = smoke_modifier.domain_settings
                if "resolution_factor" in settings:
                    smoke_settings.resolution_factor = settings["resolution_factor"]
                if "domain_type" in settings:
                    smoke_settings.domain_type = settings["domain_type"]
                # ... 更多烟雾域设置

            elif smoke_type == 'FLOW':
                flow_settings = smoke_modifier.flow_settings
                if "flow_type" in settings:
                    flow_settings.flow_type = settings["flow_type"]
                if "smoke_color" in settings:
                    flow_settings.smoke_color = settings["smoke_color"]
                # ... 更多烟雾流设置

            return {
                "status": "success",
                "object_name": object_name,
                "smoke_type": smoke_type
            }
        except Exception as e:
            logger.error(f"创建烟雾域出错: {str(e)}")
            return {"error": str(e)}

    return execute_in_main_thread(exec_func)

def modify_smoke_domain(args):
    """修改烟雾域属性 (占位符，可以扩展更多属性)"""
    logger.debug(f"修改烟雾域属性: {args}")
    object_name = args.get("object_name")
    settings = args.get("settings", {})

    def exec_func():
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"找不到对象: {object_name}"}

            smoke_modifier = obj.modifiers.get("Smoke")
            if not smoke_modifier or smoke_modifier.type != 'SMOKE' or smoke_modifier.smoke_type != 'DOMAIN':
                return {"error": f"对象上找不到烟雾域修改器: {object_name}"}

            smoke_domain_settings = smoke_modifier.domain_settings
            if "resolution_factor" in settings:
                smoke_domain_settings.resolution_factor = settings["resolution_factor"]
            # ... 可以添加更多可修改的烟雾域属性

            return {
                "status": "success",
                "object_name": object_name,
                "modified_settings": list(settings.keys())
            }
        except Exception as e:
            logger.error(f"修改烟雾域属性出错: {str(e)}")
            return {"error": str(e)}

    return execute_in_main_thread(exec_func)

# ---------- 流体模拟 ----------

def create_fluid_domain(args):
    """创建流体域 (占位符，流体模拟设置非常复杂)"""
    logger.debug(f"创建流体域: {args}")
    object_name = args.get("object_name")
    fluid_type = args.get("fluid_type", 'DOMAIN') # 'DOMAIN', 'FLOW', 'COLLISION'
    settings = args.get("settings", {})

    def exec_func():
        try:
            # 流体模拟的设置非常复杂，这里只做基本框架
            return {
                "status": "success",
                "message": "流体域创建功能待完善，当前为占位符",
                "object_name": object_name,
                "fluid_type": fluid_type
            }
        except Exception as e:
            logger.error(f"创建流体域出错: {str(e)}")
            return {"error": str(e)}

    return execute_in_main_thread(exec_func)

def modify_fluid_domain(args):
    """修改流体域属性 (占位符，流体模拟属性非常多)"""
    logger.debug(f"修改流体域属性: {args}")
    object_name = args.get("object_name")
    settings = args.get("settings", {})

    def exec_func():
        try:
            # 流体模拟属性非常多，这里只做占位符
            return {
                "status": "success",
                "message": "修改流体域属性功能待完善，当前为占位符",
                "object_name": object_name,
                "modified_settings": list(settings.keys())
            }
        except Exception as e:
            logger.error(f"修改流体域属性出错: {str(e)}")
            return {"error": str(e)}

    return execute_in_main_thread(exec_func)

# ---------- 合成 (Compositing) 节点控制 ----------

def get_compositing_node_tree(args):
    """获取合成节点树 (占位符，需要考虑如何序列化节点树)"""
    logger.debug(f"获取合成节点树: {args}")

    def exec_func():
        try:
            # 获取场景的合成节点树
            scene = bpy.context.scene
            if not scene.use_nodes:
                scene.use_nodes = True
            node_tree = scene.node_tree

            # 节点树的序列化和反序列化是一个复杂的问题，需要仔细设计
            return {
                "status": "success",
                "message": "获取合成节点树功能待完善，当前为占位符",
                "node_tree_name": node_tree.name,
                "nodes_count": len(node_tree.nodes)
            }
        except Exception as e:
            logger.error(f"获取合成节点树出错: {str(e)}")
            return {"error": str(e)}

    return execute_in_main_thread(exec_func)

def add_compositing_node(args):
    """添加合成节点 (占位符，需要定义节点类型和属性)"""
    logger.debug(f"添加合成节点: {args}")
    node_type = args.get("node_type")
    settings = args.get("settings", {})

    def exec_func():
        try:
            # 添加合成节点需要定义节点类型和各种属性
            return {
                "status": "success",
                "message": "添加合成节点功能待完善，当前为占位符",
                "node_type": node_type
            }
        except Exception as e:
            logger.error(f"添加合成节点出错: {str(e)}")
            return {"error": str(e)}

    return execute_in_main_thread(exec_func)

def connect_compositing_nodes(args):
    """连接合成节点 (占位符，需要指定节点和插槽)"""
    logger.debug(f"连接合成节点: {args}")
    from_node_name = args.get("from_node_name")
    from_socket_name = args.get("from_socket_name")
    to_node_name = args.get("to_node_name")
    to_socket_name = args.get("to_socket_name")

    def exec_func():
        try:
            # 连接合成节点需要指定节点名称和插槽名称
            return {
                "status": "success",
                "message": "连接合成节点功能待完善，当前为占位符",
                "from_node_name": from_node_name,
                "to_node_name": to_node_name
            }
        except Exception as e:
            logger.error(f"连接合成节点出错: {str(e)}")
            return {"error": str(e)}

    return execute_in_main_thread(exec_func)


# 注册工具
TOOLS = {
    # 粒子特效
    "create_particle_system": create_particle_system,
    "modify_particle_system": modify_particle_system, # 占位符

    # 烟雾模拟
    "create_smoke_domain": create_smoke_domain,
    "modify_smoke_domain": modify_smoke_domain, # 占位符

    # 流体模拟
    "create_fluid_domain": create_fluid_domain, # 占位符
    "modify_fluid_domain": modify_fluid_domain, # 占位符

    # 合成节点控制
    "get_compositing_node_tree": get_compositing_node_tree, # 占位符
    "add_compositing_node": add_compositing_node, # 占位符
    "connect_compositing_nodes": connect_compositing_nodes, # 占位符
}

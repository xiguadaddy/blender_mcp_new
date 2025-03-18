import mcp.types as types
from pydantic import AnyUrl
import json

def register_resource_handlers(server, ipc_client):
    """注册资源相关的处理程序"""
    
    @server.list_resources()
    async def handle_list_resources():
        """列出可用的Blender资源"""
        print("===== MCP服务器：开始处理list_resources请求 =====")
        resources = [
            types.Resource(
                uri="blender://scene/info",
                description="当前Blender场景信息"
            ),
            types.Resource(
                uri="blender://objects/list",
                description="场景中的所有对象列表"
            ),
            types.Resource(
                uri="blender://object/{name}",
                description="指定对象的详细信息"
            ),
            types.Resource(
                uri="blender://render/settings",
                description="渲染设置信息"
            )
        ]
        
        # 移除可能导致错误的IPC调用部分
        # 确保足够的基本资源被正确返回
        
        print(f"MCP服务器：返回 {len(resources)} 个资源")
        # 直接返回资源列表，不要包装在字典中
        return resources
    
    @server.list_resource_templates()
    async def handle_list_resource_templates():
        """列出资源URI模板"""
        return [
            types.ResourceTemplate(
                uriTemplate="blender://mesh/{id}",
                name="Blender Mesh",
                description="3D mesh object in Blender"
            ),
            types.ResourceTemplate(
                uriTemplate="blender://material/{id}",
                name="Blender Material",
                description="Material in Blender"
            ),
            types.ResourceTemplate(
                uriTemplate="blender://light/{id}",
                name="Blender Light",
                description="Light source in Blender"
            ),
            types.ResourceTemplate(
                uriTemplate="blender://camera/{id}",
                name="Blender Camera",
                description="Camera in Blender"
            ),
            types.ResourceTemplate(
                uriTemplate="blender://scene/current",
                name="Current Scene",
                description="Current Blender scene information"
            ),
        ]
    
    @server.read_resource()
    async def handle_read_resource(uri: str, path_params: dict | None = None):
        """读取资源内容"""
        print(f"MCP服务器：读取资源 {uri}")
        path_params = path_params or {}
        
        try:
            # 场景信息
            if uri == "blender://scene/info":
                code = """
import bpy
result = {
    "scene_name": bpy.context.scene.name,
    "frame_current": bpy.context.scene.frame_current,
    "frame_start": bpy.context.scene.frame_start,
    "frame_end": bpy.context.scene.frame_end,
    "fps": bpy.context.scene.render.fps,
    "objects_count": len(bpy.data.objects),
    "blender_version": ".".join(map(str, bpy.app.version))
}
result
"""
                info = await ipc_client.execute_in_blender(code)
                return types.TextContent(
                    type="text",
                    text=json.dumps(info, indent=2)
                )
            
            # 对象列表
            elif uri == "blender://objects/list":
                code = """
import bpy
result = []

for obj in bpy.data.objects:
    result.append({
        "name": obj.name,
        "type": obj.type,
        "visible": obj.visible_get(),
        "location": [round(obj.location.x, 3), round(obj.location.y, 3), round(obj.location.z, 3)]
    })

result
"""
                objects_list = await ipc_client.execute_in_blender(code)
                return types.TextContent(
                    type="text",
                    text=json.dumps(objects_list, indent=2)
                )
            
            # 特定对象信息
            elif uri.startswith("blender://object/"):
                obj_name = path_params.get("name", "")
                if not obj_name:
                    return types.TextContent(
                        type="text",
                        text=json.dumps({"error": "未指定对象名称"})
                    )
                
                code = f"""
import bpy
result = {{"error": "对象 '{obj_name}' 不存在"}}

if "{obj_name}" in bpy.data.objects:
    obj = bpy.data.objects["{obj_name}"]
    materials = []
    
    if hasattr(obj.data, "materials"):
        for mat in obj.data.materials:
            if mat:
                # 尝试获取材质颜色
                color = [0, 0, 0, 1]  # 默认黑色
                if mat.use_nodes:
                    for node in mat.node_tree.nodes:
                        if node.type == 'BSDF_PRINCIPLED':
                            color = [node.inputs[0].default_value[0],
                                     node.inputs[0].default_value[1],
                                     node.inputs[0].default_value[2],
                                     node.inputs[0].default_value[3]]
                            break
                
                materials.append({{
                    "name": mat.name,
                    "color": color
                }})
    
    result = {{
        "name": obj.name,
        "type": obj.type,
        "location": [round(obj.location.x, 3), round(obj.location.y, 3), round(obj.location.z, 3)],
        "rotation": [round(r, 3) for r in obj.rotation_euler],
        "scale": [round(obj.scale.x, 3), round(obj.scale.y, 3), round(obj.scale.z, 3)],
        "dimensions": [round(obj.dimensions.x, 3), round(obj.dimensions.y, 3), round(obj.dimensions.z, 3)],
        "materials": materials
    }}

result
"""
                obj_info = await ipc_client.execute_in_blender(code)
                return types.TextContent(
                    type="text",
                    text=json.dumps(obj_info, indent=2)
                )
            
            # 渲染设置
            elif uri == "blender://render/settings":
                code = """
import bpy
render = bpy.context.scene.render
result = {
    "engine": render.engine,
    "resolution": {
        "x": render.resolution_x,
        "y": render.resolution_y,
        "percentage": render.resolution_percentage
    },
    "file_format": render.image_settings.file_format,
    "samples": getattr(bpy.context.scene.cycles, "samples", 0) if render.engine == 'CYCLES' else 0,
    "output_path": bpy.context.scene.render.filepath
}
result
"""
                render_info = await ipc_client.execute_in_blender(code)
                return types.TextContent(
                    type="text",
                    text=json.dumps(render_info, indent=2)
                )
            
            # 未知资源
            else:
                return types.TextContent(
                    type="text",
                    text=json.dumps({"error": f"未知资源: {uri}"})
                )
                
        except Exception as e:
            error_message = f"资源读取错误: {str(e)}"
            print(error_message)
            return types.TextContent(
                type="text",
                text=json.dumps({"error": error_message})
            )
    
    # 添加一个辅助函数来发送资源更新通知
    async def notify_resource_updated(uri):
        """通知客户端资源已更新"""
        try:
            # 使用与SQLite示例相同的方法发送资源更新通知
            await server.request_context.session.send_resource_updated(uri)
        except Exception as e:
            print(f"Error sending resource update notification: {e}")
    
    # 存储这个函数以便在需要时使用
    server.notify_resource_updated = notify_resource_updated

import mcp.types as types
from pydantic import AnyUrl
import json

def register_resource_handlers(server, ipc_client):
    """注册资源相关的处理程序"""
    
    @server.list_resources()
    async def handle_list_resources():
        """列出可用的Blender资源"""
        print("===== MCP服务器：开始处理list_resources请求 =====")
        
        try:
            # 通过IPC获取实际资源列表
            blender_resources = await ipc_client.send_request({"action": "list_resources"})
            print(f"MCP服务器：获取到的资源列表: {blender_resources}")
            
            # 资源列表必须包含至少一个有效资源
            resources = []
            
            if not blender_resources or "error" in blender_resources:
                print(f"获取资源列表时出错或资源列表为空，使用默认资源")
                # 返回默认资源列表
                resources = [
                    types.Resource(
                        uri="blender://scene/current",
                        name="当前Blender场景",
                        description="当前Blender场景信息"
                    ),
                    types.Resource(
                        uri="blender://mesh/default",
                        name="默认网格对象",
                        description="默认网格对象"
                    )
                ]
            else:
                # 将Blender资源转换为MCP资源
                for res in blender_resources:
                    # 确保资源类型和ID是有效的
                    if 'type' in res and 'id' in res and 'name' in res:
                        resources.append(
                            types.Resource(
                                uri=f"blender://{res['type']}/{res['id']}",
                                name=res['name'],
                                description=f"Blender {res['type']}: {res['name']}"
                            )
                        )
            
            # 如果资源列表为空，添加一个默认资源
            if not resources:
                resources.append(
                    types.Resource(
                        uri="blender://scene/current",
                        name="当前Blender场景",
                        description="当前Blender场景信息"
                    )
                )
            
            print(f"MCP服务器：返回 {len(resources)} 个资源")
            return resources
            
        except Exception as e:
            print(f"处理资源列表请求时出错: {str(e)}")
            # 返回最小资源列表作为回退选项
            return [
                types.Resource(
                    uri="blender://scene/current",
                    name="当前Blender场景",
                    description="当前Blender场景信息"
                )
            ]
    
    @server.list_resource_templates()
    async def handle_list_resource_templates():
        """列出资源URI模板"""
        return [
            types.ResourceTemplate(
                uriTemplate="blender://mesh/{id}",
                name="Blender Mesh",
                description="Blender中的3D网格对象"
            ),
            types.ResourceTemplate(
                uriTemplate="blender://material/{id}",
                name="Blender Material",
                description="Blender中的材质"
            ),
            types.ResourceTemplate(
                uriTemplate="blender://light/{id}",
                name="Blender Light",
                description="Blender中的光源"
            ),
            types.ResourceTemplate(
                uriTemplate="blender://camera/{id}",
                name="Blender Camera",
                description="Blender中的相机"
            ),
            types.ResourceTemplate(
                uriTemplate="blender://scene/{id}",
                name="Blender Scene",
                description="Blender场景"
            )
        ]
    
    @server.read_resource()
    async def handle_read_resource(uri: str, path_params: dict | None = None):
        """读取资源内容"""
        print(f"MCP服务器：读取资源 {uri}")
        path_params = path_params or {}
        
        try:
            # 解析URI
            parts = uri.split('/')
            
            if len(parts) < 3:
                return types.TextContent(
                    type="text",
                    text=json.dumps({"error": f"无效的资源URI: {uri}"})
                )
            
            # 提取资源类型和ID
            resource_type = parts[2]  # 例如从blender://mesh/Cube中提取mesh
            resource_id = parts[3] if len(parts) > 3 else None
            
            # 检查对象是否存在（如果是mesh类型资源）
            if resource_type == "mesh" and resource_id:
                exists = await ipc_client.check_object_exists(resource_id)
                if not exists:
                    return types.TextContent(
                        type="text",
                        text=json.dumps({"error": f"对象不存在: {resource_id}"})
                    )
            
            # 通过IPC请求获取资源数据
            request = {
                "action": "read_resource",
                "type": resource_type,
                "id": resource_id
            }
            
            resource_data = await ipc_client.send_request(request)
            
            if "error" in resource_data:
                return types.TextContent(
                    type="text",
                    text=json.dumps({"error": resource_data["error"]})
                )
            
            # 处理特定类型资源的格式化
            if resource_type == "mesh":
                # 为网格数据添加额外信息，使其更易读
                if "vertices_count" in resource_data:
                    resource_data["description"] = f"网格对象，包含 {resource_data['vertices_count']} 个顶点和 {resource_data['faces_count']} 个面"
            
            elif resource_type == "scene":
                # 为场景数据添加汇总信息
                if "objects" in resource_data:
                    object_types = {}
                    for obj in resource_data["objects"]:
                        obj_type = obj.get("type", "UNKNOWN")
                        object_types[obj_type] = object_types.get(obj_type, 0) + 1
                    
                    summary = "场景包含: " + ", ".join([f"{count} 个 {obj_type}" for obj_type, count in object_types.items()])
                    resource_data["summary"] = summary
            
            return types.TextContent(
                type="text",
                text=json.dumps(resource_data, indent=2)
            )
                
        except Exception as e:
            error_message = f"资源读取错误: {str(e)}"
            print(error_message)
            return types.TextContent(
                type="text",
                text=json.dumps({"error": error_message})
            )
    
    @server.subscribe_resource()
    async def handle_subscribe_resources():
        """实现资源订阅功能"""
        # 返回可订阅资源的列表
        return [
            types.Resource(
                uri="blender://scene/current",
                name="当前Blender场景",
                description="当前Blender场景及其所有对象和属性"
            )
        ]
    
    # 添加一个辅助函数来发送资源更新通知
    async def notify_resource_updated(uri):
        """通知客户端资源已更新"""
        try:
            # 使用MCP协议发送资源更新通知
            await server.request_context.session.send_resource_updated(uri)
            print(f"已发送资源更新通知: {uri}")
        except Exception as e:
            print(f"发送资源更新通知时出错: {e}")
    
    # 存储这个函数以便在需要时使用
    server.notify_resource_updated = notify_resource_updated

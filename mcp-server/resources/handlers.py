import logging
import json
from mcp.server import Server
import mcp.types as types
from pydantic import AnyUrl

# 配置日志
logger = logging.getLogger("BlenderMCP.Server")

def register_resource_handlers(server, ipc_client):
    """注册所有Blender资源处理器"""
    
    @server.list_resources()
    async def handle_list_resources():
        """处理资源列表请求"""
        logger.debug("处理资源列表请求")
        
        try:
            # 通过IPC获取Blender中的所有资源
            resources_data = ipc_client.send_request({"action": "list_resources"})
            
            # 转换为MCP资源格式
            mcp_resources = []
            for res in resources_data:
                # 构建资源URI
                uri = f"blender://{res['type']}/{res['id']}"
                
                # 获取MIME类型
                mime_type = "application/json"
                if res['type'] == 'image':
                    mime_type = "image/png"
                elif res['type'] == 'video':
                    mime_type = "video/mp4"
                elif res['type'] == 'audio':
                    mime_type = "audio/wav"
                
                # 构建MCP资源对象
                mcp_resource = types.Resource(
                    uri=uri,
                    name=res["name"],
                    mimeType=mime_type
                )
                mcp_resources.append(mcp_resource)
            
            logger.info(f"返回 {len(mcp_resources)} 个可用资源")
            return mcp_resources
        except Exception as e:
            logger.error(f"获取资源列表时出错: {str(e)}")
            return []
    
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
    async def handle_read_resource(uri):
        """处理资源读取请求"""
        logger.debug(f"读取资源: {uri}")
        
        try:
            # 解析URI
            # 例如: blender://mesh/Cube
            parts = uri.split('/')
            if len(parts) < 4 or parts[0] != "blender:":
                raise ValueError(f"无效的资源URI: {uri}")
            
            resource_type = parts[2]
            resource_id = parts[3]
            
            # 通过IPC获取资源数据
            resource_data = ipc_client.send_request({
                "action": "read_resource",
                "type": resource_type,
                "id": resource_id
            })
            
            # 检查是否有错误
            if "error" in resource_data:
                logger.error(f"读取资源出错: {resource_data['error']}")
                return types.ReadResourceResult(
                    isError=True,
                    content=[types.TextContent(
                        type="text",
                        text=f"读取资源出错: {resource_data['error']}"
                    )]
                )
            
            # 将资源数据转换为适当的内容类型
            if resource_type == "image":
                # 如果是图像数据，返回图像内容
                if "base64_data" in resource_data:
                    return types.ReadResourceResult(
                        content=[types.ImageContent(
                            type="image",
                            data=resource_data["base64_data"]
                        )]
                    )
            
            # 默认情况下，返回JSON格式的资源数据
            resource_text = json.dumps(resource_data, ensure_ascii=False, indent=2)
            
            logger.debug(f"资源 {uri} 读取成功")
            return types.ReadResourceResult(
                content=[types.TextContent(
                    type="text",
                    text=resource_text
                )]
            )
            
        except Exception as e:
            logger.error(f"读取资源时出错: {str(e)}")
            return types.ReadResourceResult(
                isError=True,
                content=[types.TextContent(
                    type="text",
                    text=f"读取资源时出错: {str(e)}"
                )]
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

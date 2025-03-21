import logging
import json
from mcp.server import Server
import mcp.types as types
from pydantic import AnyUrl
from typing import List, Dict, Any, Optional, Union
import re
import traceback

# 配置日志
logger = logging.getLogger("BlenderMCP.Server")

# 添加预定义资源列表，在无法从Blender获取资源时使用
PREDEFINED_RESOURCES = [
    {
        "id": "default_cube",
        "type": "mesh",
        "name": "Default Cube",
        "description": "Blender默认立方体网格"
    },
    {
        "id": "default_light",
        "type": "light",
        "name": "Default Light",
        "description": "Blender默认点光源"
    },
    {
        "id": "default_camera",
        "type": "camera",
        "name": "Default Camera",
        "description": "Blender默认相机"
    },
    {
        "id": "default_material",
        "type": "material",
        "name": "Default Material",
        "description": "Blender默认材质"
    },
    {
        "id": "main_scene",
        "type": "scene",
        "name": "Main Scene",
        "description": "Blender主场景"
    }
]

def register_resource_handlers(server, ipc_client):
    """注册所有Blender资源处理器"""
    
    @server.list_resources()
    async def handle_list_resources() -> List[types.Resource]:
        """处理资源列表请求
        
        首先返回预定义资源确保快速响应，同时尝试从Blender获取更多资源
        
        Returns:
            List[types.Resource]: MCP资源对象列表
        """
        logger.debug("处理资源列表请求")
        
        try:
            # 首先准备预定义资源列表 - 总是可用
            mcp_resources = []
            for res in PREDEFINED_RESOURCES:
                try:
                    resource_id = str(res['id'])
                    resource_type = str(res['type'])
                    
                    # 清理ID以避免URI问题，只保留字母、数字、下划线和连字符
                    safe_id = re.sub(r'[^\w\-]', '_', resource_id)
                    uri = f"blender://{resource_type}/{safe_id}"
                    
                    # 获取MIME类型
                    mime_type = "application/json"
                    if resource_type == 'image':
                        mime_type = "image/png"
                    elif resource_type == 'video':
                        mime_type = "video/mp4"
                    elif resource_type == 'audio':
                        mime_type = "audio/wav"
                    
                    # 使用资源的名称，如果没有则使用ID
                    name = res.get("name", safe_id)
                    if not isinstance(name, str):
                        name = str(name)
                    
                    # 构建MCP资源对象
                    mcp_resource = types.Resource(
                        uri=uri,
                        name=name,
                        mimeType=mime_type,
                        description=res.get("description", None)
                    )
                    mcp_resources.append(mcp_resource)
                    logger.debug(f"添加预定义资源: {uri}")
                except Exception as res_err:
                    logger.error(f"创建预定义资源时出错: {str(res_err)}")
            
            logger.info(f"已准备 {len(mcp_resources)} 个预定义资源")
            
            # 通过IPC获取Blender中的更多资源
            try:
                logger.info("尝试使用MCP标准格式获取资源...")
                results = await ipc_client.send_request_with_retry(
                    {
                        "method": "mcp/listResources",
                        "params": {}
                    }
                )
                
                # 检查返回结果
                logger.info(f"MCP标准格式获取资源结果: {results}")
                resources_data = results['result'].get('resources', [])
                if isinstance(resources_data, list) and len(resources_data) > 0:
                    logger.debug(f"从Blender获取到 {len(resources_data)} 个额外资源")
                    
                    # 创建资源URI集合以避免重复
                    existing_uris = {res.uri for res in mcp_resources}
                    
                    # 添加Blender提供的资源
                    for res in resources_data:
                        try:
                            # 确保资源数据是字典类型
                            if not isinstance(res, dict):
                                continue
                                
                            # 检查必要的字段
                            if "id" not in res or "type" not in res:
                                continue
                                
                            # 构建资源URI，确保格式正确
                            resource_id = str(res['id'])
                            resource_type = str(res['type'])
                            
                            # 清理ID以避免URI问题，只保留字母、数字、下划线和连字符
                            safe_id = re.sub(r'[^\w\-]', '_', resource_id)
                            uri = f"blender://{resource_type}/{safe_id}"
                            
                            # 检查是否已存在
                            if uri in existing_uris:
                                continue
                            
                            # 获取MIME类型
                            mime_type = "application/json"
                            if resource_type == 'image':
                                mime_type = "image/png"
                            elif resource_type == 'video':
                                mime_type = "video/mp4"
                            elif resource_type == 'audio':
                                mime_type = "audio/wav"
                            
                            # 使用资源的名称，如果没有则使用ID
                            name = res.get("name", safe_id)
                            if not isinstance(name, str):
                                name = str(name)
                            
                            # 获取资源描述（如果有）
                            description = res.get("description", None)
                            
                            # 构建MCP资源对象
                            mcp_resource = types.Resource(
                                uri=uri,
                                name=name,
                                mimeType=mime_type,
                                description=description
                            )
                            mcp_resources.append(mcp_resource)
                            existing_uris.add(uri)
                            logger.debug(f"添加Blender资源: {uri}")
                        except Exception as res_err:
                            logger.error(f"处理Blender资源时出错: {str(res_err)}")
                            continue
                else:
                    logger.warning("从Blender获取资源列表失败或为空，仅使用预定义资源")
            except Exception as e:
                logger.error(f"获取Blender资源列表时出错: {str(e)}")
                logger.warning("仅使用预定义资源列表")
            
            logger.info(f"最终返回 {len(mcp_resources)} 个可用资源")
            return mcp_resources
        except Exception as e:
            logger.error(f"列出资源时发生错误: {str(e)}")
            
            # 在出错时确保至少返回预定义资源列表
            try:
                backup_resources = []
                for res in PREDEFINED_RESOURCES:
                    try:
                        resource_id = str(res['id'])
                        resource_type = str(res['type'])
                        safe_id = re.sub(r'[^\w\-]', '_', resource_id)
                        uri = f"blender://{resource_type}/{safe_id}"
                        
                        backup_resources.append(types.Resource(
                            uri=uri,
                            name=res.get("name", safe_id),
                            mimeType="application/json",
                            description=res.get("description", None)
                        ))
                    except Exception:
                        pass
                
                logger.info(f"返回 {len(backup_resources)} 个预定义资源作为后备方案")
                return backup_resources
            except Exception as final_err:
                logger.error(f"创建后备资源列表也失败: {str(final_err)}")
                return []
    
    @server.list_resource_templates()
    async def handle_list_resource_templates() -> List[types.ResourceTemplate]:
        """列出资源URI模板
        
        Returns:
            List[types.ResourceTemplate]: 资源模板列表
        """
        templates = [
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
        logger.debug(f"返回 {len(templates)} 个资源模板")
        return templates
    
    @server.read_resource()
    async def handle_read_resource(uri: Union[str, AnyUrl]) -> types.ReadResourceResult:
        """处理资源读取请求
        
        Args:
            uri: 资源URI
            
        Returns:
            types.ReadResourceResult: 资源读取结果
        """
        logger.debug(f"读取资源: {uri}")
        
        try:
            # 将URI转换为字符串
            uri_str = str(uri)
            
            # 解析URI
            # 例如: blender://mesh/Cube
            match = re.match(r'blender://([^/]+)/(.+)', uri_str)
            if not match:
                logger.error(f"无效的资源URI格式: {uri_str}")
                error_text = f"无效的资源URI格式，应为 blender://类型/ID"
                
                # 创建错误数据
                error_data = types.ErrorData(
                    code=types.INVALID_PARAMS,
                    message="无效的资源URI格式",
                    data=f"提供的URI '{uri_str}' 不匹配所需格式"
                )
                
                # 创建资源内容
                text_resource = types.TextResourceContents(
                    uri=uri_str,
                    text=error_text,
                    mimeType="text/plain"
                )
                
                # 返回错误结果
                return types.ReadResourceResult(
                    contents=[text_resource],
                    error=error_data,
                    isError=True
                )
            
            resource_type = match.group(1)
            resource_id = match.group(2)
            
            # 通过IPC获取资源数据，使用重试机制
            resource_data = await ipc_client.send_request_with_retry({
                "action": "read_resource",
                "type": resource_type,
                "id": resource_id
            })
            
            # 检查是否有错误
            if isinstance(resource_data, dict) and "error" in resource_data:
                error_msg = resource_data['error']
                logger.error(f"读取资源出错: {error_msg}")
                
                # 创建错误数据
                error_data = types.ErrorData(
                    code=types.INTERNAL_ERROR,
                    message="读取资源失败",
                    data=error_msg
                )
                
                # 创建资源内容
                text_resource = types.TextResourceContents(
                    uri=uri_str,
                    text=f"读取资源出错: {error_msg}",
                    mimeType="text/plain"
                )
                
                # 返回错误结果
                return types.ReadResourceResult(
                    contents=[text_resource],
                    error=error_data,
                    isError=True
                )
            
            # 将资源数据转换为适当的内容类型
            if resource_type == "image" and isinstance(resource_data, dict) and "base64_data" in resource_data:
                # 如果是图像数据，返回图像内容
                mime_type = resource_data.get("mime_type", "image/png")
                
                # 创建二进制资源内容
                blob_resource = types.BlobResourceContents(
                    uri=uri_str,
                    blob=resource_data["base64_data"],
                    mimeType=mime_type
                )
                
                # 返回成功结果
                return types.ReadResourceResult(
                    contents=[blob_resource]
                )
            
            # 默认情况下，返回JSON格式的资源数据
            try:
                resource_text = json.dumps(resource_data, ensure_ascii=False, indent=2)
            except Exception as json_err:
                logger.error(f"将资源转换为JSON时出错: {json_err}")
                resource_text = str(resource_data)
            
            logger.debug(f"资源 {uri} 读取成功")
            
            # 创建文本资源内容
            text_resource = types.TextResourceContents(
                uri=uri_str,
                text=resource_text,
                mimeType="application/json"
            )
            
            # 返回成功结果
            return types.ReadResourceResult(
                contents=[text_resource]
            )
            
        except Exception as e:
            logger.error(f"读取资源时出错: {str(e)}")
            logger.error(f"异常详情: {traceback.format_exc()}")
            
            # 创建错误数据
            error_data = types.ErrorData(
                code=types.INTERNAL_ERROR,
                message="读取资源时发生内部错误",
                data=str(e)
            )
            
            # 确保URI字符串可用
            uri_str = str(uri) if uri else "unknown://resource"
            
            # 创建资源内容
            text_resource = types.TextResourceContents(
                uri=uri_str,
                text=f"读取资源时出错: {str(e)}",
                mimeType="text/plain"
            )
            
            # 返回错误结果
            return types.ReadResourceResult(
                contents=[text_resource],
                error=error_data,
                isError=True
            )
    
    @server.subscribe_resource()
    async def handle_subscribe_resources() -> List[types.Resource]:
        """实现资源订阅功能
        
        Returns:
            List[types.Resource]: 可订阅资源列表
        """
        # 返回可订阅资源的列表
        subscriptions = [
            types.Resource(
                uri="blender://scene/current",
                name="当前Blender场景",
                mimeType="application/json",
                description="当前Blender场景及其所有对象和属性"
            )
        ]
        logger.debug(f"返回 {len(subscriptions)} 个可订阅资源")
        return subscriptions
    
    # 添加一个辅助函数来发送资源更新通知
    async def notify_resource_updated(uri: Union[str, AnyUrl]) -> bool:
        """通知客户端资源已更新
        
        Args:
            uri: 资源URI
            
        Returns:
            bool: 通知成功返回True，否则返回False
        """
        try:
            # 转换为字符串
            uri_str = str(uri)
            
            # 使用MCP协议发送资源更新通知
            await server.request_context.session.send_resource_updated(uri_str)
            logger.info(f"已发送资源更新通知: {uri_str}")
            return True
        except Exception as e:
            logger.error(f"发送资源更新通知时出错: {e}")
            return False
    
    # 存储这个函数以便在需要时使用
    server.notify_resource_updated = notify_resource_updated

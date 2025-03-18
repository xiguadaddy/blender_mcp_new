import mcp.types as types
import os

# 提示模板目录
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

def register_prompt_handlers(server, ipc_client):
    """注册提示相关的处理程序"""
    
    @server.list_prompts()
    async def handle_list_prompts():
        """列出可用的提示模板"""
        prompts = [
            types.Prompt(
                name="create_scene",
                description="创建一个基本场景，包含对象、材质和灯光",
                arguments=[
                    types.PromptArgument(
                        name="scene_type",
                        description="场景类型（如室内、室外、抽象）",
                        required=True
                    ),
                    types.PromptArgument(
                        name="complexity",
                        description="场景复杂度（简单、中等、复杂）",
                        required=False
                    )
                ]
            ),
            types.Prompt(
                name="animate_object",
                description="为对象创建简单动画",
                arguments=[
                    types.PromptArgument(
                        name="object_name",
                        description="要动画的对象名称",
                        required=True
                    ),
                    types.PromptArgument(
                        name="animation_type",
                        description="动画类型（旋转、移动、缩放）",
                        required=True
                    )
                ]
            ),
            types.Prompt(
                name="material_tutorial",
                description="创建和应用材质的教程",
                arguments=[
                    types.PromptArgument(
                        name="material_type",
                        description="材质类型（金属、玻璃、木材等）",
                        required=True
                    )
                ]
            )
        ]
        
        return prompts
    
    @server.get_prompt()
    async def handle_get_prompt(name: str, arguments: dict):
        """获取提示内容"""
        
        if name not in ["create_scene", "animate_object", "material_tutorial"]:
            raise ValueError(f"未知提示: {name}")
        
        # 验证必需参数
        if name == "create_scene" and "scene_type" not in arguments:
            raise ValueError("缺少必需参数: scene_type")
        elif name == "animate_object" and ("object_name" not in arguments or "animation_type" not in arguments):
            raise ValueError("缺少必需参数: object_name 或 animation_type")
        elif name == "material_tutorial" and "material_type" not in arguments:
            raise ValueError("缺少必需参数: material_type")
        
        # 设置默认值
        if name == "create_scene" and "complexity" not in arguments:
            arguments["complexity"] = "中等"
        
        # 读取并填充模板
        template_path = os.path.join(TEMPLATES_DIR, f"{name}.txt")
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
        
        # 格式化模板
        prompt_text = template_content.format(**arguments)
        
        # 准备场景信息
        if name == "animate_object":
            # 检查对象是否存在
            object_exists = ipc_client.send_request({
                "action": "check_object_exists",
                "object_name": arguments["object_name"]
            })
            
            if not object_exists.get("exists", False):
                prompt_text += f"\n\n注意：对象 '{arguments['object_name']}' 不存在于当前场景中。你可能需要先创建它。"
        
        # 创建提示结果
        return types.GetPromptResult(
            description=f"{name} 提示",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(type="text", text=prompt_text.strip())
                )
            ]
        )

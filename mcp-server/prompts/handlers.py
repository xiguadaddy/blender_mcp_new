import mcp.types as types
import json
import os

# 提示模板目录
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

def register_prompt_handlers(server, ipc_client):
    """注册提示相关的处理程序"""
    
    @server.list_prompts()
    async def handle_list_prompts():
        """列出可用的Blender提示"""
        print("MCP服务器：处理list_prompts请求")
        prompts = [
            types.Prompt(
                name="create_scene",
                description="创建一个基础场景",
                arguments=[
                    types.PromptArgument(
                        name="scene_type",
                        description="场景类型 (interior/exterior/abstract)",
                        required=True
                    ),
                    types.PromptArgument(
                        name="complexity",
                        description="场景复杂度 (simple/medium/complex)",
                        required=False
                    )
                ]
            ),
            types.Prompt(
                name="create_character",
                description="创建一个角色模型",
                arguments=[
                    types.PromptArgument(
                        name="character_type",
                        description="角色类型 (human/animal/fantasy)",
                        required=True
                    ),
                    types.PromptArgument(
                        name="style",
                        description="风格 (realistic/cartoon/stylized)",
                        required=False
                    )
                ]
            ),
            types.Prompt(
                name="create_animation",
                description="创建一个简单的动画",
                arguments=[
                    types.PromptArgument(
                        name="object_name",
                        description="要动画的对象名称",
                        required=True
                    ),
                    types.PromptArgument(
                        name="animation_type",
                        description="动画类型 (rotation/movement/scale)",
                        required=True
                    ),
                    types.PromptArgument(
                        name="duration",
                        description="动画时长(秒)",
                        required=False
                    )
                ]
            )
        ]
        
        print(f"MCP服务器：返回 {len(prompts)} 个提示")
        return prompts
        
    @server.get_prompt()
    async def handle_get_prompt(name: str, arguments: dict | None = None):
        """获取提示内容"""
        print(f"MCP服务器：获取提示 {name}，参数: {arguments}")
        arguments = arguments or {}
        
        try:
            if name == "create_scene":
                scene_type = arguments.get("scene_type", "interior")
                complexity = arguments.get("complexity", "simple")
                
                # 构建提示内容
                prompt_text = f"""
# 创建{scene_type}类型的{complexity}复杂度场景

我将帮助你在Blender中创建一个{scene_type}类型的{complexity}复杂度场景。

## 步骤

1. 首先，让我们创建基本对象:
   - 使用create_object工具创建主体结构
   - 添加地面/底座
   - 添加环境元素

2. 然后，设置材质:
   - 为主要对象设置适当的材质
   - 调整材质参数以获得合适的外观

3. 添加光照:
   - 主光源
   - 填充光
   - 环境光

4. 设置相机:
   - 放置在合适的位置以获得最佳视角
   - 调整镜头参数

5. 最后渲染场景

让我们开始吧！你想在这个{scene_type}场景中包含哪些主要元素？
                """
                
                return types.GetPromptResult(
                    description=f"{scene_type.capitalize()}场景创建指南",
                    messages=[
                        types.PromptMessage(
                            role="user",
                            content=[types.TextContent(type="text", text=prompt_text.strip())]
                        )
                    ]
                )
                
            elif name == "create_character":
                character_type = arguments.get("character_type", "human")
                style = arguments.get("style", "realistic")
                
                prompt_text = f"""
# 创建{style}风格的{character_type}角色模型

我将引导你在Blender中创建一个{style}风格的{character_type}角色模型。

## 步骤

1. 创建基本形状:
   - 创建身体主要部分
   - 添加头部和四肢
   - 建立角色的基本比例

2. 添加细节:
   - 根据{style}风格调整细节级别
   - 添加面部特征
   - 添加服装/毛发等元素

3. 材质设置:
   - 创建皮肤/表面材质
   - 添加服装材质
   - 调整反射和纹理属性

4. 姿势和表情:
   - 设置角色的基本姿势
   - 调整面部表情(如适用)

5. 最终渲染和调整

请告诉我你希望这个{character_type}角色有哪些特定特征？
                """
                
                return types.GetPromptResult(
                    description=f"{style.capitalize()} {character_type}角色创建指南",
                    messages=[
                        types.PromptMessage(
                            role="user",
                            content=[types.TextContent(type="text", text=prompt_text.strip())]
                        )
                    ]
                )
                
            elif name == "create_animation":
                object_name = arguments.get("object_name", "Object")
                animation_type = arguments.get("animation_type", "rotation")
                duration = arguments.get("duration", 5)
                
                # 检查对象是否存在
                exists = await ipc_client.check_object_exists(object_name)
                if not exists:
                    return types.GetPromptResult(
                        description="对象不存在",
                        messages=[
                            types.PromptMessage(
                                role="user",
                                content=[types.TextContent(
                                    type="text", 
                                    text=f"对象 '{object_name}' 不存在，请先创建此对象或选择一个已存在的对象。"
                                )]
                            )
                        ]
                    )
                
                prompt_text = f"""
# 为 '{object_name}' 创建{animation_type}动画

我将帮助你为 '{object_name}' 对象创建一个持续{duration}秒的{animation_type}动画。

## 步骤

1. 设置动画参数:
   - 设置帧率和动画范围
   - 确定起始和结束帧

2. 创建关键帧:
   - 设置初始状态关键帧
   - 创建中间状态
   - 设置结束状态关键帧

3. 调整动画曲线:
   - 设置合适的插值方式
   - 调整缓入缓出效果

4. 预览和调整动画:
   - 测试动画效果
   - 根据需要进行微调

5. 最终渲染动画

你希望'{object_name}'的{animation_type}动画具有什么特性？例如速度、方向、范围等。
                """
                
                return types.GetPromptResult(
                    description=f"{object_name} {animation_type}动画创建指南",
                    messages=[
                        types.PromptMessage(
                            role="user",
                            content=[types.TextContent(type="text", text=prompt_text.strip())]
                        )
                    ]
                )
            
            # 未知提示
            else:
                return types.GetPromptResult(
                    description="未知提示",
                    messages=[
                        types.PromptMessage(
                            role="user",
                            content=[types.TextContent(
                                type="text", 
                                text=f"未找到名为 '{name}' 的提示。请使用有效的提示名称。"
                            )]
                        )
                    ]
                )
                
        except Exception as e:
            error_message = f"获取提示时出错: {str(e)}"
            print(error_message)
            return types.GetPromptResult(
                description="错误",
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=[types.TextContent(type="text", text=error_message)]
                    )
                ]
            )

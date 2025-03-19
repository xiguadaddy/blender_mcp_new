import mcp.types as types
import json
import os
import logging
import traceback
from mcp.server import Server
from typing import List, Dict, Any, Optional, Union

# 提示模板目录
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

# 配置日志
logger = logging.getLogger("BlenderMCP.Server")

# 预定义提示模板
PREDEFINED_TEMPLATES = [
    {
        "id": "create_scene",
        "name": "Create 3D Scene",
        "description": "Create a detailed 3D scene with specified parameters",
        "parameters": [
            {
                "id": "scene_type",
                "name": "Scene Type",
                "description": "Type of scene to create",
                "type": "string",
                "options": ["interior", "exterior", "abstract", "fantasy"],
                "required": True
            },
            {
                "id": "complexity",
                "name": "Complexity Level",
                "description": "Complexity level of the scene",
                "type": "string",
                "options": ["simple", "medium", "complex"],
                "required": False,
                "default": "medium"
            },
            {
                "id": "style",
                "name": "Visual Style",
                "description": "Visual style of the scene",
                "type": "string",
                "options": ["realistic", "stylized", "cartoon", "abstract"],
                "required": False
            }
        ]
    },
    {
        "id": "create_character",
        "name": "Create Character Model",
        "description": "Create a 3D character model with specified characteristics",
        "parameters": [
            {
                "id": "character_type",
                "name": "Character Type",
                "description": "Type of character to create",
                "type": "string",
                "options": ["human", "animal", "creature", "robot"],
                "required": True
            },
            {
                "id": "style",
                "name": "Style",
                "description": "Visual style of the character",
                "type": "string",
                "options": ["realistic", "stylized", "cartoon"],
                "required": False,
                "default": "stylized"
            },
            {
                "id": "pose",
                "name": "Pose",
                "description": "Initial pose of the character",
                "type": "string",
                "options": ["t-pose", "a-pose", "idle", "action"],
                "required": False,
                "default": "t-pose"
            }
        ]
    },
    {
        "id": "create_animation",
        "name": "Create Animation",
        "description": "Create an animation for existing objects",
        "parameters": [
            {
                "id": "object_name",
                "name": "Object Name",
                "description": "Name of the object to animate",
                "type": "string",
                "required": True
            },
            {
                "id": "animation_type",
                "name": "Animation Type",
                "description": "Type of animation to create",
                "type": "string",
                "options": ["rotation", "movement", "scale", "deformation"],
                "required": True
            },
            {
                "id": "duration",
                "name": "Duration (seconds)",
                "description": "Duration of the animation in seconds",
                "type": "number",
                "required": False,
                "default": 5.0
            },
            {
                "id": "keyframes",
                "name": "Number of Keyframes",
                "description": "Number of keyframes to generate",
                "type": "integer",
                "required": False,
                "default": 10
            }
        ]
    },
    {
        "id": "create_material",
        "name": "Create Material",
        "description": "Create a material with specified properties",
        "parameters": [
            {
                "id": "material_type",
                "name": "Material Type",
                "description": "Type of material to create",
                "type": "string",
                "options": ["principled", "glass", "emission", "toon"],
                "required": True
            },
            {
                "id": "base_color",
                "name": "Base Color",
                "description": "Base color in RGB format (e.g., '0.8,0.2,0.2')",
                "type": "string",
                "required": False,
                "default": "0.8,0.8,0.8"
            },
            {
                "id": "metallic",
                "name": "Metallic",
                "description": "Metallic property (0.0-1.0)",
                "type": "number",
                "required": False,
                "default": 0.0
            },
            {
                "id": "roughness",
                "name": "Roughness",
                "description": "Roughness property (0.0-1.0)",
                "type": "number",
                "required": False,
                "default": 0.5
            }
        ]
    },
    {
        "id": "render_scene",
        "name": "Render Scene",
        "description": "Render the current scene with specified settings",
        "parameters": [
            {
                "id": "resolution_x",
                "name": "Resolution X",
                "description": "Horizontal resolution in pixels",
                "type": "integer",
                "required": False,
                "default": 1920
            },
            {
                "id": "resolution_y",
                "name": "Resolution Y",
                "description": "Vertical resolution in pixels",
                "type": "integer",
                "required": False,
                "default": 1080
            },
            {
                "id": "render_engine",
                "name": "Render Engine",
                "description": "Rendering engine to use",
                "type": "string",
                "options": ["cycles", "eevee", "workbench"],
                "required": False,
                "default": "cycles"
            },
            {
                "id": "samples",
                "name": "Samples",
                "description": "Number of render samples",
                "type": "integer",
                "required": False,
                "default": 128
            }
        ]
    }
]

# 模板内容生成函数
def generate_template_content(template_id, params):
    """生成模板内容
    
    Args:
        template_id: 模板ID
        params: 模板参数
        
    Returns:
        str: 生成的内容
    """
    if template_id == "create_scene":
        scene_type = params.get("scene_type", "interior")
        complexity = params.get("complexity", "medium")
        style = params.get("style", "realistic")
        
        return f"""
# Creating a {complexity} {style} {scene_type} scene in Blender

I'll help you create a {scene_type} scene with {complexity} complexity in {style} style.

## Step-by-step guide:

1. **First, set up the basic structure:**
   - Create main objects for the {scene_type} scene
   - Add ground/base surfaces
   - Add environment elements

2. **Add materials and textures:**
   - Apply appropriate materials for {scene_type} environment
   - Adjust material parameters for {style} look
   - Configure texture maps if needed

3. **Set up lighting:**
   - Add primary light sources appropriate for {scene_type}
   - Add additional lights for highlights and fill
   - Adjust light intensity and color temperature

4. **Configure camera:**
   - Position camera for optimal composition
   - Set appropriate focal length and depth of field
   - Frame the scene effectively

5. **Final touches:**
   - Add atmospheric effects if needed
   - Configure world settings for appropriate background
   - Apply any final adjustments for the {style} style

## Tools you can use:
- create_object: To create basic shapes and objects
- set_material: To apply materials to objects
- add_light: To add lighting to the scene
- set_camera: To configure camera settings
- set_world: To adjust environment settings
"""
    
    elif template_id == "create_character":
        character_type = params.get("character_type", "human")
        style = params.get("style", "stylized")
        pose = params.get("pose", "t-pose")
        
        return f"""
# Creating a {style} {character_type} character in Blender

I'll help you create a {character_type} character in {style} style with an initial {pose}.

## Step-by-step guide:

1. **Create the basic shape:**
   - Set up the character's proportions for {character_type} type
   - Create the primary body structure
   - Add character-specific features

2. **Add details:**
   - Create facial features appropriate for {character_type}
   - Add body details and appendages
   - Refine the mesh for {style} style

3. **Rigging (optional):**
   - Create a simple armature for the character
   - Set up bone structure for animation
   - Configure weights for proper deformation

4. **Apply materials:**
   - Create skin/surface materials
   - Add clothing/feature materials
   - Adjust material properties for {style} look

5. **Set up the {pose}:**
   - Position the character in the specified pose
   - Make any final adjustments

## Tools you can use:
- create_object: To create basic shapes and objects
- set_material: To apply materials to parts
- add_armature: To create a skeleton for animation
- add_shape_key: To create facial expressions
- set_pose: To position the character
"""
    
    elif template_id == "create_animation":
        object_name = params.get("object_name", "Untitled")
        animation_type = params.get("animation_type", "rotation")
        duration = params.get("duration", 5.0)
        keyframes = params.get("keyframes", 10)
        
        return f"""
# Creating a {animation_type} animation for {object_name}

I'll help you create a {duration}-second {animation_type} animation for {object_name} with {keyframes} keyframes.

## Step-by-step guide:

1. **Set up animation timeline:**
   - Configure animation frame range based on {duration} seconds
   - Set frame rate as needed
   - Prepare object {object_name} for animation

2. **Create keyframes:**
   - Set initial keyframe at start position
   - Create intermediate keyframes throughout animation
   - Set final keyframe at end position
   - Total keyframes: approximately {keyframes}

3. **Refine animation curves:**
   - Open graph editor to view animation curves
   - Adjust curves for smooth {animation_type} motion
   - Modify easing and timing as needed

4. **Add animation details:**
   - Include additional motion details if needed
   - Combine with other animations if necessary
   - Refine timing for best results

5. **Preview and export:**
   - Play back animation to verify
   - Make any necessary adjustments
   - Prepare for rendering or export

## Tools you can use:
- set_keyframe: To create animation keyframes
- set_animation_length: To configure animation duration
- set_frames_per_second: To adjust frame rate
- adjust_f_curve: To modify animation curves
- playback_animation: To preview the animation
"""
    
    elif template_id == "create_material":
        material_type = params.get("material_type", "principled")
        base_color = params.get("base_color", "0.8,0.8,0.8")
        metallic = params.get("metallic", 0.0)
        roughness = params.get("roughness", 0.5)
        
        return f"""
# Creating a {material_type} material in Blender

I'll help you create a {material_type} material with the following properties:
- Base color: {base_color}
- Metallic: {metallic}
- Roughness: {roughness}

## Step-by-step guide:

1. **Create new material:**
   - Add a new material node tree
   - Name it appropriately
   - Set up {material_type} shader nodes

2. **Configure main properties:**
   - Set base color to {base_color}
   - Set metallic value to {metallic}
   - Set roughness value to {roughness}

3. **Add texture maps (if needed):**
   - Create/import texture maps
   - Connect texture nodes to appropriate inputs
   - Adjust texture mapping and scale

4. **Set up additional properties:**
   - Configure specialized {material_type} properties
   - Adjust transparency if needed
   - Set up reflectivity parameters

5. **Test and refine:**
   - Apply material to test object
   - Verify appearance in different lighting
   - Make final adjustments

## Tools you can use:
- create_material: To create a new material
- set_material_property: To adjust material parameters
- add_texture: To add texture maps
- apply_material: To apply to objects
- preview_material: To check appearance
"""
    
    elif template_id == "render_scene":
        resolution_x = params.get("resolution_x", 1920)
        resolution_y = params.get("resolution_y", 1080)
        render_engine = params.get("render_engine", "cycles")
        samples = params.get("samples", 128)
        
        return f"""
# Rendering the scene in Blender

I'll help you render the current scene with the following settings:
- Resolution: {resolution_x}x{resolution_y}
- Render engine: {render_engine}
- Samples: {samples}

## Step-by-step guide:

1. **Configure render settings:**
   - Set resolution to {resolution_x}x{resolution_y}
   - Select {render_engine} render engine
   - Set sample count to {samples}

2. **Optimize scene for rendering:**
   - Check for any issues that might affect render quality
   - Verify lighting setup
   - Ensure materials are properly configured

3. **Configure output settings:**
   - Set file format (PNG recommended for quality)
   - Configure output path
   - Set color management settings

4. **Render settings optimization:**
   - Adjust specific {render_engine} settings
   - Configure denoising if applicable
   - Set appropriate bounces for light

5. **Execute render:**
   - Start render process
   - Monitor progress
   - Save final output

## Tools you can use:
- set_render_resolution: To set pixel dimensions
- set_render_engine: To select render engine
- set_render_samples: To configure sample count
- set_output_format: To select file format
- execute_render: To start the rendering process
"""
    
    else:
        # Default generic response
        param_list = ", ".join([f"{k}: {v}" for k, v in params.items()])
        return f"""
# Using template: {template_id}

Parameters provided:
{param_list}

I'll help you work with these parameters in Blender. Let me know what specific actions you'd like to take with this template.
"""

def register_prompt_handlers(server, ipc_client):
    """注册所有Blender提示处理器"""
    
    try:
        # 检查是否支持提示模板功能
        logger.info("检查服务器提示功能支持...")
        
        # 使用list_prompts替代list_prompt_templates
        @server.list_prompts()
        async def handle_list_prompt_templates():
            """返回预定义的提示模板列表
            
            Returns:
                List: 提示模板列表
            """
            logger.debug("处理提示模板列表请求")
            
            try:
                # 使用预定义的模板而不是从Blender获取
                mcp_templates = []
                
                for tmpl in PREDEFINED_TEMPLATES:
                    try:
                        template_id = str(tmpl['id'])
                        name = str(tmpl['name'])
                        description = tmpl.get('description', '')
                        
                        # 创建输入schema
                        input_schema = {}
                        if "parameters" in tmpl and isinstance(tmpl["parameters"], list):
                            properties = {}
                            required = []
                            
                            for param in tmpl["parameters"]:
                                if not isinstance(param, dict) or "id" not in param:
                                    continue
                                    
                                param_id = str(param["id"])
                                param_type = param.get("type", "string")
                                param_title = param.get("name", param_id)
                                param_desc = param.get("description", "")
                                
                                # 构建参数属性
                                param_prop = {
                                    "type": param_type,
                                    "title": param_title
                                }
                                
                                if param_desc:
                                    param_prop["description"] = param_desc
                                    
                                # 添加默认值（如果存在）
                                if "default" in param:
                                    param_prop["default"] = param["default"]
                                    
                                # 添加枚举值（如果存在）
                                if "options" in param and isinstance(param["options"], list):
                                    param_prop["enum"] = [str(opt) for opt in param["options"]]
                                
                                properties[param_id] = param_prop
                                
                                # 如果参数是必需的
                                if param.get("required", False):
                                    required.append(param_id)
                            
                            # 创建JSON Schema
                            if properties:
                                input_schema = {
                                    "type": "object",
                                    "properties": properties
                                }
                                
                                if required:
                                    input_schema["required"] = required
                        
                        # 使用字典格式而不是PromptTemplate类
                        mcp_template = {
                            "id": template_id,
                            "name": name,
                            "description": description if description else None,
                            "inputSchema": input_schema if input_schema else None
                        }
                        
                        mcp_templates.append(mcp_template)
                        logger.debug(f"添加提示模板: {template_id}")
                    except Exception as e:
                        logger.error(f"处理提示模板时出错: {str(e)}, 模板数据: {tmpl}")
                        continue
                
                logger.info(f"返回 {len(mcp_templates)} 个可用提示模板")
                return mcp_templates
            except Exception as e:
                logger.error(f"获取提示模板列表时出错: {str(e)}")
                return []
       
                
        @server.get_prompt()
        async def handle_get_prompt(name: str, arguments: Optional[Dict[str, Any]] = None):
            """获取提示内容
            
            Args:
                name: 提示模板ID
                arguments: 提示参数
                
            Returns:
                Dict: 提示内容结果
            """
            logger.debug(f"获取提示: {name}, 参数: {arguments}")
            
            try:
                # 处理参数（如果未提供）
                if arguments is None:
                    arguments = {}
                    
                # 查找匹配的模板
                template = None
                for tmpl in PREDEFINED_TEMPLATES:
                    if tmpl["id"] == name:
                        template = tmpl
                        break
                        
                if not template:
                    logger.warning(f"未找到模板: {name}")
                    return {
                        "isError": True,
                        "content": [
                            {
                                "type": "text",
                                "text": f"Template '{name}' not found"
                            }
                        ]
                    }
                
                # 生成响应内容
                response_text = generate_template_content(name, arguments)
                
                # 返回结果
                return {
                    "isError": False,
                    "content": [
                        {
                            "type": "text",
                            "text": response_text
                        }
                    ]
                }
            except Exception as e:
                logger.error(f"获取提示时出错: {str(e)}")
                return {
                    "isError": True,
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error getting prompt: {str(e)}"
                        }
                    ]
                }
                
        logger.info("成功注册提示处理程序")
        return True
        
    except Exception as e:
        logger.error(f"注册提示处理程序时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return False

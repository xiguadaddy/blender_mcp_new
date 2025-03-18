import mcp.types as types

# 创建对象的输入模式
CREATE_OBJECT_SCHEMA = {
    "type": "object",
    "properties": {
        "object_type": {
            "type": "string",
            "enum": ["cube", "sphere", "plane", "cylinder", "cone", "torus"],
            "description": "要创建的对象类型"
        },
        "location": {
            "type": "array",
            "items": {"type": "number"},
            "description": "对象位置坐标 [x, y, z]"
        },
        "name": {
            "type": "string",
            "description": "对象名称"
        },
        "size": {
            "type": "number",
            "description": "对象尺寸",
            "default": 2.0
        }
    },
    "required": ["object_type"]
}

# 设置材质的输入模式
SET_MATERIAL_SCHEMA = {
    "type": "object",
    "properties": {
        "object_name": {
            "type": "string", 
            "description": "目标对象名称"
        },
        "color": {
            "type": "array",
            "items": {"type": "number"},
            "description": "RGBA颜色值 [r, g, b, a]"
        },
        "metallic": {
            "type": "number",
            "description": "金属度 (0-1)",
            "default": 0.0
        },
        "roughness": {
            "type": "number",
            "description": "粗糙度 (0-1)",
            "default": 0.5
        }
    },
    "required": ["object_name", "color"]
}

# 添加灯光的输入模式
ADD_LIGHT_SCHEMA = {
    "type": "object",
    "properties": {
        "light_type": {
            "type": "string",
            "enum": ["POINT", "SUN", "SPOT", "AREA"],
            "description": "灯光类型"
        },
        "location": {
            "type": "array",
            "items": {"type": "number"},
            "description": "灯光位置坐标 [x, y, z]"
        },
        "name": {
            "type": "string",
            "description": "灯光名称"
        },
        "color": {
            "type": "array",
            "items": {"type": "number"},
            "description": "RGB颜色值 [r, g, b]",
            "default": [1.0, 1.0, 1.0]
        },
        "energy": {
            "type": "number",
            "description": "灯光强度",
            "default": 1000.0
        }
    },
    "required": ["light_type"]
}

# 设置摄像机的输入模式
SET_CAMERA_SCHEMA = {
    "type": "object",
    "properties": {
        "location": {
            "type": "array",
            "items": {"type": "number"},
            "description": "摄像机位置坐标 [x, y, z]"
        },
        "rotation": {
            "type": "array",
            "items": {"type": "number"},
            "description": "摄像机旋转欧拉角 [x, y, z] (弧度)"
        },
        "name": {
            "type": "string",
            "description": "摄像机名称"
        },
        "lens": {
            "type": "number",
            "description": "镜头焦距(mm)",
            "default": 50.0
        }
    },
    "required": ["location", "rotation"]
}

# 渲染场景的输入模式
RENDER_SCENE_SCHEMA = {
    "type": "object",
    "properties": {
        "output_path": {
            "type": "string",
            "description": "输出文件路径"
        },
        "resolution_x": {
            "type": "integer",
            "description": "渲染宽度(像素)",
            "default": 1920
        },
        "resolution_y": {
            "type": "integer",
            "description": "渲染高度(像素)",
            "default": 1080
        },
        "samples": {
            "type": "integer",
            "description": "采样数量",
            "default": 128
        }
    },
    "required": ["output_path"]
}

# 应用修改器的输入模式
APPLY_MODIFIER_SCHEMA = {
    "type": "object",
    "properties": {
        "object_name": {
            "type": "string",
            "description": "目标对象名称"
        },
        "modifier_type": {
            "type": "string",
            "enum": ["SUBSURF", "BEVEL", "SOLIDIFY", "ARRAY", "MIRROR"],
            "description": "修改器类型"
        },
        "parameters": {
            "type": "object",
            "description": "修改器参数"
        }
    },
    "required": ["object_name", "modifier_type"]
}

# 转换对象的输入模式
TRANSFORM_OBJECT_SCHEMA = {
    "type": "object",
    "properties": {
        "object_name": {
            "type": "string",
            "description": "目标对象名称"
        },
        "location": {
            "type": "array",
            "items": {"type": "number"},
            "description": "新位置坐标 [x, y, z]"
        },
        "rotation": {
            "type": "array",
            "items": {"type": "number"},
            "description": "新旋转欧拉角 [x, y, z] (弧度)"
        },
        "scale": {
            "type": "array",
            "items": {"type": "number"},
            "description": "新缩放 [x, y, z]"
        }
    },
    "required": ["object_name"]
}

# 导入模型的输入模式
IMPORT_MODEL_SCHEMA = {
    "type": "object",
    "properties": {
        "file_path": {
            "type": "string",
            "description": "模型文件路径"
        },
        "import_type": {
            "type": "string",
            "enum": ["OBJ", "FBX", "GLB", "STL"],
            "description": "导入文件类型"
        }
    },
    "required": ["file_path", "import_type"]
}

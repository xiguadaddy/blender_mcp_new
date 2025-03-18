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
        "material_name": {
            "type": "string",
            "description": "材质名称（如果不提供则自动生成）"
        },
        "color": {
            "type": "array",
            "items": {"type": "number"},
            "description": "RGBA颜色值 [r, g, b, a]，或RGB颜色值 [r, g, b]"
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
        },
        "specular": {
            "type": "number",
            "description": "镜面反射强度 (0-1)",
            "default": 0.5
        }
    },
    "required": ["object_name"]
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

# 添加挤出面的输入模式
EXTRUDE_FACES_SCHEMA = {
    "type": "object",
    "properties": {
        "object_name": {
            "type": "string",
            "description": "目标对象名称"
        },
        "face_indices": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "要挤出的面索引"
        },
        "direction": {
            "type": "array",
            "items": {"type": "number"},
            "description": "挤出方向 [x, y, z]"
        },
        "distance": {
            "type": "number",
            "description": "挤出距离",
            "default": 1.0
        }
    },
    "required": ["object_name", "face_indices"]
}

# 添加细分网格的输入模式
SUBDIVIDE_MESH_SCHEMA = {
    "type": "object",
    "properties": {
        "object_name": {
            "type": "string",
            "description": "目标对象名称"
        },
        "cuts": {
            "type": "integer",
            "description": "细分次数",
            "default": 1
        },
        "smooth": {
            "type": "number",
            "description": "平滑度",
            "default": 0.0
        }
    },
    "required": ["object_name"]
}

# 添加环切的输入模式
LOOP_CUT_SCHEMA = {
    "type": "object",
    "properties": {
        "object_name": {
            "type": "string",
            "description": "目标对象名称"
        },
        "cuts": {
            "type": "integer",
            "description": "环切数量",
            "default": 1
        },
        "edge_index": {
            "type": "integer",
            "description": "边索引"
        },
        "factor": {
            "type": "number",
            "description": "位置因子 (0-1)",
            "default": 0.5
        }
    },
    "required": ["object_name"]
}

# 添加设置顶点位置的输入模式
SET_VERTEX_POSITION_SCHEMA = {
    "type": "object",
    "properties": {
        "object_name": {
            "type": "string",
            "description": "目标对象名称"
        },
        "vertex_indices": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "要修改的顶点索引"
        },
        "positions": {
            "type": "array",
            "items": {
                "type": "array",
                "items": {"type": "number"}
            },
            "description": "新位置坐标列表 [[x, y, z], ...]"
        }
    },
    "required": ["object_name", "vertex_indices", "positions"]
}

# 添加创建动画的输入模式
CREATE_ANIMATION_SCHEMA = {
    "type": "object",
    "properties": {
        "object_name": {
            "type": "string",
            "description": "目标对象名称"
        },
        "keyframes": {
            "type": "object",
            "description": "帧号和对应的值 {帧号: 值}"
        },
        "property_path": {
            "type": "string",
            "description": "要设置动画的属性",
            "enum": ["location", "rotation_euler", "scale"],
            "default": "location"
        }
    },
    "required": ["object_name", "keyframes"]
}

# 添加创建节点材质的输入模式
CREATE_NODE_MATERIAL_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "description": "材质名称"
        },
        "node_setup": {
            "type": "object",
            "description": "节点设置",
            "properties": {
                "nodes": {
                    "type": "object",
                    "description": "节点定义"
                },
                "links": {
                    "type": "array",
                    "description": "节点连接"
                }
            },
            "required": ["nodes"]
        }
    },
    "required": ["name", "node_setup"]
}

# 添加设置UV映射的输入模式
SET_UV_MAPPING_SCHEMA = {
    "type": "object",
    "properties": {
        "object_name": {
            "type": "string",
            "description": "目标对象名称"
        },
        "projection": {
            "type": "string",
            "description": "投影类型",
            "enum": ["CUBE", "CYLINDER", "SPHERE", "PROJECT", "UNWRAP"],
            "default": "CUBE"
        },
        "scale": {
            "type": "array",
            "items": {"type": "number"},
            "description": "缩放因子 [x, y, z]",
            "default": [1, 1, 1]
        }
    },
    "required": ["object_name"]
}

# 添加合并对象的输入模式
JOIN_OBJECTS_SCHEMA = {
    "type": "object",
    "properties": {
        "objects": {
            "type": "array",
            "items": {"type": "string"},
            "description": "要合并的对象名称列表"
        },
        "target_object": {
            "type": "string",
            "description": "目标对象（保留此对象的材质）"
        }
    },
    "required": ["objects"]
}

# 添加分离网格的输入模式
SEPARATE_MESH_SCHEMA = {
    "type": "object",
    "properties": {
        "object_name": {
            "type": "string",
            "description": "目标对象名称"
        },
        "method": {
            "type": "string",
            "description": "分离方法",
            "enum": ["SELECTED", "MATERIAL", "LOOSE"],
            "default": "SELECTED"
        }
    },
    "required": ["object_name"]
}

# 添加创建文本的输入模式
CREATE_TEXT_SCHEMA = {
    "type": "object",
    "properties": {
        "text": {
            "type": "string",
            "description": "文本内容"
        },
        "location": {
            "type": "array",
            "items": {"type": "number"},
            "description": "位置坐标 [x, y, z]",
            "default": [0, 0, 0]
        },
        "size": {
            "type": "number",
            "description": "文本大小",
            "default": 1.0
        },
        "extrude": {
            "type": "number",
            "description": "文本挤出深度",
            "default": 0.0
        },
        "name": {
            "type": "string",
            "description": "对象名称（可选）"
        }
    },
    "required": ["text"]
}

# 添加创建曲线的输入模式
CREATE_CURVE_SCHEMA = {
    "type": "object",
    "properties": {
        "curve_type": {
            "type": "string",
            "description": "曲线类型",
            "enum": ["BEZIER", "POLY"],
            "default": "BEZIER"
        },
        "points": {
            "type": "array",
            "items": {
                "type": "object"
            },
            "description": "曲线点数据"
        },
        "location": {
            "type": "array",
            "items": {"type": "number"},
            "description": "位置坐标 [x, y, z]",
            "default": [0, 0, 0]
        },
        "name": {
            "type": "string",
            "description": "对象名称（可选）"
        }
    },
    "required": ["points"]
}

# 添加创建粒子系统的输入模式
CREATE_PARTICLE_SYSTEM_SCHEMA = {
    "type": "object",
    "properties": {
        "object_name": {
            "type": "string",
            "description": "目标对象名称"
        },
        "settings": {
            "type": "object",
            "description": "粒子系统设置"
        }
    },
    "required": ["object_name"]
}

# 添加高级灯光的输入模式
ADVANCED_LIGHTING_SCHEMA = {
    "type": "object",
    "properties": {
        "light_type": {
            "type": "string",
            "description": "灯光类型",
            "enum": ["POINT", "SUN", "SPOT", "AREA"],
            "default": "POINT"
        },
        "name": {
            "type": "string",
            "description": "灯光名称（可选）"
        },
        "location": {
            "type": "array",
            "items": {"type": "number"},
            "description": "位置坐标 [x, y, z]",
            "default": [0, 0, 0]
        },
        "energy": {
            "type": "number",
            "description": "灯光强度",
            "default": 1000.0
        },
        "color": {
            "type": "array",
            "items": {"type": "number"},
            "description": "RGB颜色值 [r, g, b]",
            "default": [1.0, 1.0, 1.0]
        },
        "shadow": {
            "type": "boolean",
            "description": "是否启用阴影",
            "default": True
        }
    },
    "required": ["light_type"]
}

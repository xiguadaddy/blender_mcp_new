# BlenderMCP 命令示例集

本文档包含一系列使用BlenderMCP API的示例，演示如何通过API完成各种3D建模任务。这些示例可以帮助语言模型理解如何使用API进行实际操作。

## 目录
1. [基本流程](#基本流程)
2. [创建简单场景](#创建简单场景)
3. [精细建模](#精细建模)
4. [材质与纹理](#材质与纹理)
5. [动画控制](#动画控制)
6. [高级照明](#高级照明)
7. [复杂项目示例](#复杂项目示例)

## 基本流程
// ...existing code...

## 创建简单场景
// ...existing code...

## 精细建模
// ...existing code...

## 材质与纹理
// ...existing code...

## 动画控制
// ...existing code...

## 高级照明
// ...existing code...

## 复杂项目示例

### 创建简易小房子

```python
# 通过一系列命令创建小房子
commands = [
    # 创建地面
    {
        "type": "create_object",
        "params": {
            "type": "PLANE",
            "name": "地面",
            "location": [0, 0, 0],
            "scale": [10, 10, 1]
        }
    },
    # 创建房子主体
    {
        "type": "create_object",
        "params": {
            "type": "CUBE",
            "name": "房屋主体",
            "location": [0, 0, 1],
            "scale": [2, 3, 1]
        }
    },
    # 创建屋顶
    {
        "type": "create_object",
        "params": {
            "type": "CONE",
            "name": "屋顶",
            "location": [0, 0, 3],
            "scale": [2.5, 3.5, 1.5],
            "rotation": [0, 0, 0]
        }
    },
    # 创建门
    {
        "type": "create_object",
        "params": {
            "type": "CUBE",
            "name": "门",
            "location": [0, 3.01, 0.7],
            "scale": [0.5, 0.05, 0.7]
        }
    },
    # 创建窗户1
    {
        "type": "create_object",
        "params": {
            "type": "CUBE",
            "name": "窗户1",
            "location": [-1.01, 1.5, 1.2],
            "scale": [0.05, 0.5, 0.5]
        }
    },
    # 创建窗户2
    {
        "type": "create_object",
        "params": {
            "type": "CUBE",
            "name": "窗户2",
            "location": [1.01, 1.5, 1.2],
            "scale": [0.05, 0.5, 0.5]
        }
    },
    # 设置材质
    {
        "type": "set_material",
        "params": {
            "object_name": "地面",
            "material_name": "草地",
            "color": [0.1, 0.5, 0.1]
        }
    },
    {
        "type": "set_material",
        "params": {
            "object_name": "房屋主体",
            "material_name": "墙壁",
            "color": [0.8, 0.8, 0.7]
        }
    },
    {
        "type": "set_material",
        "params": {
            "object_name": "屋顶",
            "material_name": "屋顶瓦片",
            "color": [0.6, 0.3, 0.2]
        }
    },
    {
        "type": "set_material",
        "params": {
            "object_name": "门",
            "material_name": "木门",
            "color": [0.4, 0.2, 0.1]
        }
    },
    {
        "type": "set_material",
        "params": {
            "object_name": "窗户1",
            "material_name": "玻璃",
            "color": [0.8, 0.9, 1.0, 0.3]
        }
    },
    {
        "type": "set_material",
        "params": {
            "object_name": "窗户2",
            "material_name": "玻璃",
            "color": [0.8, 0.9, 1.0, 0.3]
        }
    },
    # 添加灯光
    {
        "type": "advanced_lighting",
        "params": {
            "light_type": "SUN",
            "name": "日光",
            "location": [5, 5, 10],
            "energy": 1.5,
            "color": [1.0, 0.95, 0.9]
        }
    }
]

# 发送命令序列
for cmd in commands:
    response = client.send_command(cmd["type"], cmd["params"])
    print(f"执行 {cmd['type']} - 结果: {response['status']}")
```

### 创建一个雪人模型

```python
# 创建雪人模型
commands = [
    # 创建地面
    {
        "type": "create_object",
        "params": {
            "type": "PLANE",
            "name": "雪地",
            "location": [0, 0, 0],
            "scale": [5, 5, 1]
        }
    },
    # 设置雪地材质
    {
        "type": "set_material",
        "params": {
            "object_name": "雪地",
            "material_name": "雪",
            "color": [0.95, 0.95, 0.98]
        }
    },
    # 创建雪人底部
    {
        "type": "create_object",
        "params": {
            "type": "SPHERE",
            "name": "雪人底部",
            "location": [0, 0, 1],
            "scale": [1, 1, 0.8]
        }
    },
    # 创建雪人中部
    {
        "type": "create_object",
        "params": {
            "type": "SPHERE",
            "name": "雪人中部",
            "location": [0, 0, 2.2],
            "scale": [0.7, 0.7, 0.6]
        }
    },
    # 创建雪人头部
    {
        "type": "create_object",
        "params": {
            "type": "SPHERE",
            "name": "雪人头部",
            "location": [0, 0, 3.1],
            "scale": [0.5, 0.5, 0.5]
        }
    },
    # 设置雪人材质
    {
        "type": "set_material",
        "params": {
            "object_name": "雪人底部",
            "material_name": "雪球",
            "color": [1, 1, 1]
        }
    },
    {
        "type": "set_material",
        "params": {
            "object_name": "雪人中部",
            "material_name": "雪球",
            "color": [1, 1, 1]
        }
    },
    {
        "type": "set_material",
        "params": {
            "object_name": "雪人头部",
            "material_name": "雪球",
            "color": [1, 1, 1]
        }
    },
    # 创建鼻子
    {
        "type": "create_object",
        "params": {
            "type": "CONE",
            "name": "胡萝卜鼻子",
            "location": [0, 0.5, 3.1],
            "rotation": [1.57, 0, 0],
            "scale": [0.1, 0.1, 0.2]
        }
    },
    # 设置鼻子材质
    {
        "type": "set_material",
        "params": {
            "object_name": "胡萝卜鼻子",
            "material_name": "胡萝卜",
            "color": [0.9, 0.4, 0.1]
        }
    },
    # 创建左眼
    {
        "type": "create_object",
        "params": {
            "type": "SPHERE",
            "name": "左眼",
            "location": [-0.15, 0.4, 3.2],
            "scale": [0.05, 0.05, 0.05]
        }
    },
    # 创建右眼
    {
        "type": "create_object",
        "params": {
            "type": "SPHERE",
            "name": "右眼",
            "location": [0.15, 0.4, 3.2],
            "scale": [0.05, 0.05, 0.05]
        }
    },
    # 设置眼睛材质
    {
        "type": "set_material",
        "params": {
            "object_name": "左眼",
            "material_name": "煤炭",
            "color": [0.02, 0.02, 0.02]
        }
    },
    {
        "type": "set_material",
        "params": {
            "object_name": "右眼",
            "material_name": "煤炭",
            "color": [0.02, 0.02, 0.02]
        }
    },
    # 创建帽子
    {
        "type": "create_object",
        "params": {
            "type": "CYLINDER",
            "name": "帽子",
            "location": [0, 0, 3.5],
            "scale": [0.4, 0.4, 0.3]
        }
    },
    {
        "type": "create_object",
        "params": {
            "type": "CYLINDER",
            "name": "帽檐",
            "location": [0, 0, 3.2],
            "scale": [0.5, 0.5, 0.05]
        }
    },
    # 设置帽子材质
    {
        "type": "set_material",
        "params": {
            "object_name": "帽子",
            "material_name": "黑布",
            "color": [0.05, 0.05, 0.05]
        }
    },
    {
        "type": "set_material",
        "params": {
            "object_name": "帽檐",
            "material_name": "黑布",
            "color": [0.05, 0.05, 0.05]
        }
    }
]

for cmd in commands:
    print(f"执行命令: {cmd['type']}")
    response = client.send_command(cmd["type"], cmd["params"])
    print(f"结果: {response['status']}")
```

### 创建一个城市街区

```python
# 创建一个城市街区场景
import random

# 基础设置
client.send_command("create_object", {
    "type": "PLANE",
    "name": "地面",
    "location": [0, 0, 0],
    "scale": [50, 50, 1]
})

client.send_command("set_material", {
    "object_name": "地面",
    "material_name": "沥青",
    "color": [0.1, 0.1, 0.1]
})

# 创建道路
client.send_command("create_object", {
    "type": "PLANE",
    "name": "主道路",
    "location": [0, 0, 0.01],
    "scale": [50, 5, 1]
})

client.send_command("set_material", {
    "object_name": "主道路",
    "material_name": "路面",
    "color": [0.3, 0.3, 0.3]
})

client.send_command("create_object", {
    "type": "PLANE",
    "name": "十字路",
    "location": [0, 0, 0.02],
    "rotation": [0, 0, 1.5708],
    "scale": [50, 5, 1]
})

client.send_command("set_material", {
    "object_name": "十字路",
    "material_name": "路面",
    "color": [0.3, 0.3, 0.3]
})

# 创建多个建筑物
building_positions = [
    [-15, -15], [-15, 15], [15, -15], [15, 15],
    [-30, -15], [-30, 15], [30, -15], [30, 15],
    [-15, -30], [15, -30], [-15, 30], [15, 30]
]

for i, pos in enumerate(building_positions):
    # 随机生成建筑物参数
    height = random.uniform(5, 20)
    width = random.uniform(4, 10)
    depth = random.uniform(4, 10)
    
    # 创建建筑物本体
    client.send_command("create_object", {
        "type": "CUBE",
        "name": f"建筑物_{i+1}",
        "location": [pos[0], pos[1], height/2],
        "scale": [width/2, depth/2, height/2]
    })
    
    # 设置材质
    r = random.uniform(0.2, 0.8)
    g = random.uniform(0.2, 0.8)
    b = random.uniform(0.2, 0.8)
    
    client.send_command("set_material", {
        "object_name": f"建筑物_{i+1}",
        "material_name": f"建筑材质_{i+1}",
        "color": [r, g, b]
    })
    
    # 有些建筑物添加修改器
    if random.random() > 0.5:
        client.send_command("apply_modifier", {
            "object_name": f"建筑物_{i+1}",
            "modifier_type": "BEVEL",
            "params": {
                "width": 0.2,
                "segments": 3
            }
        })

# 添加环境灯光
client.send_command("advanced_lighting", {
    "light_type": "SUN",
    "name": "太阳光",
    "location": [20, 20, 40],
    "energy": 2.0,
    "color": [1.0, 0.95, 0.9]
})

# 添加几个路灯
lamp_positions = [
    [-15, -5], [-15, 5], [15, -5], [15, 5],
    [-5, -15], [5, -15], [-5, 15], [5, 15]
]

for i, pos in enumerate(lamp_positions):
    # 创建灯柱
    client.send_command("create_object", {
        "type": "CYLINDER",
        "name": f"路灯柱_{i+1}",
        "location": [pos[0], pos[1], 2],
        "scale": [0.2, 0.2, 2]
    })
    
    # 创建灯头
    client.send_command("create_object", {
        "type": "SPHERE",
        "name": f"路灯头_{i+1}",
        "location": [pos[0], pos[1], 4.5],
        "scale": [0.5, 0.5, 0.5]
    })
    
    # 添加灯光
    client.send_command("advanced_lighting", {
        "light_type": "POINT",
        "name": f"路灯光源_{i+1}",
        "location": [pos[0], pos[1], 4.5],
        "energy": 500,
        "color": [1.0, 0.9, 0.7]
    })
    
    # 设置材质
    client.send_command("set_material", {
        "object_name": f"路灯柱_{i+1}",
        "material_name": "金属",
        "color": [0.2, 0.2, 0.2]
    })
    
    client.send_command("set_material", {
        "object_name": f"路灯头_{i+1}",
        "material_name": "灯罩",
        "color": [0.9, 0.9, 0.7, 0.8]
    })

print("城市街区构建完成！")
```

### 创建精细的花瓶模型

```python
# 创建一个花瓶模型 - 展示精细建模方法

# 1. 首先创建基础圆柱体
client.send_command("create_object", {
    "type": "CYLINDER",
    "name": "花瓶基础",
    "location": [0, 0, 0],
    "scale": [1, 1, 1.5]
})

# 2. 细分网格以获取更多可编辑点
client.send_command("subdivide_mesh", {
    "object_name": "花瓶基础",
    "cuts": 3,
    "smooth": 0
})

# 3. 设置顶部和底部的顶点以形成花瓶轮廓
# 注意：顶点索引可能根据细分情况有所不同，这里使用示例索引
positions = [
    # 底部顶点 - 收窄底座
    {"index": 0, "position": [0.5, 0, 0]},
    {"index": 1, "position": [0.35, 0.35, 0]},
    {"index": 2, "position": [0, 0.5, 0]},
    {"index": 3, "position": [-0.35, 0.35, 0]},
    {"index": 4, "position": [-0.5, 0, 0]},
    {"index": 5, "position": [-0.35, -0.35, 0]},
    {"index": 6, "position": [0, -0.5, 0]},
    {"index": 7, "position": [0.35, -0.35, 0]},
    
    # 中下部 - 扩大
    {"index": 8, "position": [0.8, 0, 0.5]},
    {"index": 9, "position": [0.57, 0.57, 0.5]},
    {"index": 10, "position": [0, 0.8, 0.5]},
    {"index": 11, "position": [-0.57, 0.57, 0.5]},
    {"index": 12, "position": [-0.8, 0, 0.5]},
    {"index": 13, "position": [-0.57, -0.57, 0.5]},
    {"index": 14, "position": [0, -0.8, 0.5]},
    {"index": 15, "position": [0.57, -0.57, 0.5]},
    
    # 中部 - 最宽处
    {"index": 16, "position": [1.2, 0, 1.2]},
    {"index": 17, "position": [0.85, 0.85, 1.2]},
    {"index": 18, "position": [0, 1.2, 1.2]},
    {"index": 19, "position": [-0.85, 0.85, 1.2]},
    {"index": 20, "position": [-1.2, 0, 1.2]},
    {"index": 21, "position": [-0.85, -0.85, 1.2]},
    {"index": 22, "position": [0, -1.2, 1.2]},
    {"index": 23, "position": [0.85, -0.85, 1.2]},
    
    # 上部 - 收窄
    {"index": 24, "position": [0.9, 0, 2.0]},
    {"index": 25, "position": [0.64, 0.64, 2.0]},
    {"index": 26, "position": [0, 0.9, 2.0]},
    {"index": 27, "position": [-0.64, 0.64, 2.0]},
    {"index": 28, "position": [-0.9, 0, 2.0]},
    {"index": 29, "position": [-0.64, -0.64, 2.0]},
    {"index": 30, "position": [0, -0.9, 2.0]},
    {"index": 31, "position": [0.64, -0.64, 2.0]},
    
    # 顶部开口 - 略微外翻
    {"index": 32, "position": [1.1, 0, 3.0]},
    {"index": 33, "position": [0.78, 0.78, 3.0]},
    {"index": 34, "position": [0, 1.1, 3.0]},
    {"index": 35, "position": [-0.78, 0.78, 3.0]},
    {"index": 36, "position": [-1.1, 0, 3.0]},
    {"index": 37, "position": [-0.78, -0.78, 3.0]},
    {"index": 38, "position": [0, -1.1, 3.0]},
    {"index": 39, "position": [0.78, -0.78, 3.0]}
]

# 逐个调整顶点位置
for vertex in positions:
    client.send_command("set_vertex_position", {
        "object_name": "花瓶基础",
        "vertex_indices": [vertex["index"]],
        "positions": [vertex["position"]]
    })

# 4. 添加细分曲面修改器使表面平滑
client.send_command("apply_modifier", {
    "object_name": "花瓶基础",
    "modifier_type": "SUBSURF",
    "params": {
        "levels": 2,
        "render_levels": 2
    }
})

# 5. 创建一个装饰图案
client.send_command("create_object", {
    "type": "TORUS",
    "name": "花瓶装饰",
    "location": [0, 0, 1.2],
    "rotation": [0, 0, 0],
    "scale": [1.21, 1.21, 0.1]
})

# 6. 设置材质
client.send_command("create_node_material", {
    "name": "陶瓷材质",
    "node_setup": {
        "nodes": {
            "output": {
                "type": "ShaderNodeOutputMaterial",
                "location": [300, 0]
            },
            "principled": {
                "type": "ShaderNodeBsdfPrincipled",
                "location": [0, 0],
                "properties": {
                    "Base Color": [0.8, 0.7, 0.5, 1.0],
                    "Metallic": 0.0,
                    "Roughness": 0.25,
                    "Specular": 0.5
                }
            },
            "noise": {
                "type": "ShaderNodeTexNoise",
                "location": [-300, 100],
                "properties": {
                    "Scale": 8.0,
                    "Detail": 10.0,
                    "Roughness": 0.7
                }
            },
            "colorramp": {
                "type": "ShaderNodeValToRGB",
                "location": [-150, 100],
                "properties": {}
            }
        },
        "links": [
            {
                "from_node": "principled",
                "from_socket": "BSDF",
                "to_node": "output",
                "to_socket": "Surface"
            },
            {
                "from_node": "noise",
                "from_socket": "Color",
                "to_node": "colorramp",
                "to_socket": "Fac"
            },
            {
                "from_node": "colorramp",
                "from_socket": "Color",
                "to_node": "principled",
                "to_socket": "Base Color"
            }
        ]
    }
})

client.send_command("set_material", {
    "object_name": "花瓶基础",
    "material_name": "陶瓷材质"
})

client.send_command("set_material", {
    "object_name": "花瓶装饰",
    "material_name": "金属装饰",
    "color": [0.83, 0.69, 0.21],
    "create_if_missing": True
})

# 7. 添加环境灯光进行优雅的照明
client.send_command("advanced_lighting", {
    "light_type": "AREA",
    "name": "主灯光",
    "location": [5, 5, 5],
    "energy": 400,
    "color": [1.0, 0.95, 0.9]
})

client.send_command("advanced_lighting", {
    "light_type": "AREA",
    "name": "补光",
    "location": [-3, -3, 2],
    "energy": 200,
    "color": [0.9, 0.9, 1.0]
})

# 8. 渲染最终结果
client.send_command("render_scene", {
    "resolution_x": 1920,
    "resolution_y": 1080
})

print("精细花瓶模型已完成！")
```
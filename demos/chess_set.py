#!/usr/bin/env python3
"""
BlenderMCP 示例脚本 - 创建国际象棋棋盘和棋子
演示如何使用BlenderMCP API创建一个完整的场景
"""

import sys
import os
import json
import socket
import time

# 确保可以导入客户端类
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client import BlenderMCPClient

# 创建客户端
client = BlenderMCPClient()
if not client.connect():
    print("无法连接到BlenderMCP服务器")
    sys.exit(1)

try:
    print("开始创建国际象棋套装...")
    
    # 清除现有场景
    scene_info = client.get_scene_info()
    if "result" in scene_info and "objects" in scene_info["result"]:
        for obj in scene_info["result"]["objects"]:
            client.delete_object(obj["name"])
    
    # 创建棋盘
    board = client.create_object(
        "CUBE", 
        name="棋盘", 
        location=[0, 0, -0.1], 
        scale=[4, 4, 0.1]
    )
    
    # 创建棋盘格子
    square_size = 0.5
    colors = {
        "white": [0.9, 0.9, 0.9],
        "black": [0.2, 0.2, 0.2]
    }
    
    print("创建棋盘格子...")
    for row in range(8):
        for col in range(8):
            # 确定格子颜色
            color_name = "white" if (row + col) % 2 == 0 else "black"
            
            # 计算格子位置
            x = col * square_size - 3.5 * square_size
            y = row * square_size - 3.5 * square_size
            
            # 创建格子
            square = client.create_object(
                "CUBE",
                name=f"格子_{row}_{col}",
                location=[x, y, 0],
                scale=[square_size/2 * 0.95, square_size/2 * 0.95, 0.01]
            )
            
            # 设置格子材质
            client.set_material(
                square["result"]["name"],
                color=colors[color_name],
                material_name=f"{color_name}_square"
            )
    
    # 创建棋子函数
    def create_pawn(color, col):
        x = col * square_size - 3.5 * square_size
        y = 2.5 * square_size if color == "white" else -2.5 * square_size
        
        # 创建基座
        base = client.create_object(
            "CYLINDER",
            name=f"{color}_pawn_{col}",
            location=[x, y, 0.1],
            scale=[0.2, 0.2, 0.05]
        )
        
        # 创建身体
        body = client.create_object(
            "CYLINDER",
            name=f"{color}_pawn_body_{col}",
            location=[x, y, 0.25],
            scale=[0.15, 0.15, 0.15]
        )
        
        # 创建头部
        head = client.create_object(
            "SPHERE",
            name=f"{color}_pawn_head_{col}",
            location=[x, y, 0.5],
            scale=[0.12, 0.12, 0.12]
        )
        
        # 设置材质
        piece_color = [1, 1, 1] if color == "white" else [0.1, 0.1, 0.1]
        client.set_material(base["result"]["name"], color=piece_color)
        client.set_material(body["result"]["name"], color=piece_color)
        client.set_material(head["result"]["name"], color=piece_color)
        
        # 合并部件
        client.send_command("join_objects", {
            "objects": [
                base["result"]["name"],
                body["result"]["name"],
                head["result"]["name"]
            ],
            "target_object": base["result"]["name"]
        })
        
        return base
    
    def create_rook(color, col):
        x = col * square_size - 3.5 * square_size
        y = 3.5 * square_size if color == "white" else -3.5 * square_size
        
        # 创建基座
        base = client.create_object(
            "CYLINDER",
            name=f"{color}_rook_{col}",
            location=[x, y, 0.1],
            scale=[0.2, 0.2, 0.05]
        )
        
        # 创建身体
        body = client.create_object(
            "CYLINDER",
            name=f"{color}_rook_body_{col}",
            location=[x, y, 0.35],
            scale=[0.18, 0.18, 0.25]
        )
        
        # 创建顶部
        top = client.create_object(
            "CYLINDER",
            name=f"{color}_rook_top_{col}",
            location=[x, y, 0.65],
            scale=[0.2, 0.2, 0.05]
        )
        
        # 设置材质
        piece_color = [1, 1, 1] if color == "white" else [0.1, 0.1, 0.1]
        client.set_material(base["result"]["name"], color=piece_color)
        client.set_material(body["result"]["name"], color=piece_color)
        client.set_material(top["result"]["name"], color=piece_color)
        
        # 合并部件
        client.send_command("join_objects", {
            "objects": [
                base["result"]["name"],
                body["result"]["name"],
                top["result"]["name"]
            ],
            "target_object": base["result"]["name"]
        })
        
        return base
    
    def create_knight(color, col):
        x = col * square_size - 3.5 * square_size
        y = 3.5 * square_size if color == "white" else -3.5 * square_size
        
        # 创建基座
        base = client.create_object(
            "CYLINDER",
            name=f"{color}_knight_{col}",
            location=[x, y, 0.1],
            scale=[0.2, 0.2, 0.05]
        )
        
        # 创建身体
        body = client.create_object(
            "CONE",
            name=f"{color}_knight_body_{col}",
            location=[x, y, 0.4],
            scale=[0.15, 0.15, 0.3]
        )
        
        # 创建头部
        head = client.create_object(
            "CUBE",
            name=f"{color}_knight_head_{col}",
            location=[x, y + 0.1, 0.6],
            rotation=[0.3, 0, 0],
            scale=[0.1, 0.2, 0.1]
        )
        
        # 设置材质
        piece_color = [1, 1, 1] if color == "white" else [0.1, 0.1, 0.1]
        client.set_material(base["result"]["name"], color=piece_color)
        client.set_material(body["result"]["name"], color=piece_color)
        client.set_material(head["result"]["name"], color=piece_color)
        
        # 合并部件
        client.send_command("join_objects", {
            "objects": [
                base["result"]["name"],
                body["result"]["name"],
                head["result"]["name"]
            ],
            "target_object": base["result"]["name"]
        })
        
        return base
    
    def create_bishop(color, col):
        x = col * square_size - 3.5 * square_size
        y = 3.5 * square_size if color == "white" else -3.5 * square_size
        
        # 创建基座
        base = client.create_object(
            "CYLINDER",
            name=f"{color}_bishop_{col}",
            location=[x, y, 0.1],
            scale=[0.2, 0.2, 0.05]
        )
        
        # 创建身体
        body = client.create_object(
            "CONE",
            name=f"{color}_bishop_body_{col}",
            location=[x, y, 0.4],
            scale=[0.15, 0.15, 0.3]
        )
        
        # 创建顶部
        top = client.create_object(
            "SPHERE",
            name=f"{color}_bishop_top_{col}",
            location=[x, y, 0.65],
            scale=[0.05, 0.05, 0.05]
        )
        
        # 设置材质
        piece_color = [1, 1, 1] if color == "white" else [0.1, 0.1, 0.1]
        client.set_material(base["result"]["name"], color=piece_color)
        client.set_material(body["result"]["name"], color=piece_color)
        client.set_material(top["result"]["name"], color=piece_color)
        
        # 合并部件
        client.send_command("join_objects", {
            "objects": [
                base["result"]["name"],
                body["result"]["name"],
                top["result"]["name"]
            ],
            "target_object": base["result"]["name"]
        })
        
        return base
    
    def create_queen(color):
        x = -0.5 * square_size
        y = 3.5 * square_size if color == "white" else -3.5 * square_size
        
        # 创建基座
        base = client.create_object(
            "CYLINDER",
            name=f"{color}_queen",
            location=[x, y, 0.1],
            scale=[0.2, 0.2, 0.05]
        )
        
        # 创建身体
        body = client.create_object(
            "CONE",
            name=f"{color}_queen_body",
            location=[x, y, 0.45],
            scale=[0.18, 0.18, 0.4]
        )
        
        # 创建皇冠
        crown = client.create_object(
            "CYLINDER",
            name=f"{color}_queen_crown",
            location=[x, y, 0.7],
            scale=[0.15, 0.15, 0.05]
        )
        
        # 创建顶部球体
        top = client.create_object(
            "SPHERE",
            name=f"{color}_queen_top",
            location=[x, y, 0.8],
            scale=[0.08, 0.08, 0.08]
        )
        
        # 设置材质
        piece_color = [1, 1, 1] if color == "white" else [0.1, 0.1, 0.1]
        client.set_material(base["result"]["name"], color=piece_color)
        client.set_material(body["result"]["name"], color=piece_color)
        client.set_material(crown["result"]["name"], color=piece_color)
        client.set_material(top["result"]["name"], color=piece_color)
        
        # 合并部件
        client.send_command("join_objects", {
            "objects": [
                base["result"]["name"],
                body["result"]["name"],
                crown["result"]["name"],
                top["result"]["name"]
            ],
            "target_object": base["result"]["name"]
        })
        
        return base
    
    def create_king(color):
        x = 0.5 * square_size
        y = 3.5 * square_size if color == "white" else -3.5 * square_size
        
        # 创建基座
        base = client.create_object(
            "CYLINDER",
            name=f"{color}_king",
            location=[x, y, 0.1],
            scale=[0.2, 0.2, 0.05]
        )
        
        # 创建身体
        body = client.create_object(
            "CONE",
            name=f"{color}_king_body",
            location=[x, y, 0.45],
            scale=[0.18, 0.18, 0.4]
        )
        
        # 创建皇冠
        crown = client.create_object(
            "CYLINDER",
            name=f"{color}_king_crown",
            location=[x, y, 0.7],
            scale=[0.15, 0.15, 0.05]
        )
        
        # 创建十字架
        cross_v = client.create_object(
            "CUBE",
            name=f"{color}_king_cross_v",
            location=[x, y, 0.85],
            scale=[0.03, 0.03, 0.15]
        )
        
        cross_h = client.create_object(
            "CUBE",
            name=f"{color}_king_cross_h",
            location=[x, y, 0.9],
            scale=[0.1, 0.03, 0.03]
        )
        
        # 设置材质
        piece_color = [1, 1, 1] if color == "white" else [0.1, 0.1, 0.1]
        client.set_material(base["result"]["name"], color=piece_color)
        client.set_material(body["result"]["name"], color=piece_color)
        client.set_material(crown["result"]["name"], color=piece_color)
        client.set_material(cross_v["result"]["name"], color=piece_color)
        client.set_material(cross_h["result"]["name"], color=piece_color)
        
        # 合并部件
        client.send_command("join_objects", {
            "objects": [
                base["result"]["name"],
                body["result"]["name"],
                crown["result"]["name"],
                cross_v["result"]["name"],
                cross_h["result"]["name"]
            ],
            "target_object": base["result"]["name"]
        })
        
        return base
    
    # 创建所有棋子
    print("创建白色棋子...")
    for col in range(8):
        create_pawn("white", col)
    
    create_rook("white", 0)
    create_knight("white", 1)
    create_bishop("white", 2)
    create_queen("white")
    create_king("white")
    create_bishop("white", 5)
    create_knight("white", 6)
    create_rook("white", 7)
    
    print("创建黑色棋子...")
    for col in range(8):
        create_pawn("black", col)
    
    create_rook("black", 0)
    create_knight("black", 1)
    create_bishop("black", 2)
    create_queen("black")
    create_king("black")
    create_bishop("black", 5)
    create_knight("black", 6)
    create_rook("black", 7)
    
    # 创建棋盘边框
    border = client.create_object(
        "CUBE",
        name="棋盘边框",
        location=[0, 0, -0.15],
        scale=[4.2, 4.2, 0.05]
    )
    client.set_material(border["result"]["name"], color=[0.4, 0.2, 0.1], material_name="wood_border")
    
    # 设置棋盘材质
    client.set_material(board["result"]["name"], color=[0.3, 0.15, 0.1], material_name="board_base")
    
    # 添加灯光
    print("创建灯光...")
    client.send_command("advanced_lighting", {
        "light_type": "SUN",
        "name": "主光源",
        "location": [5, 5, 10],
        "energy": 1.0,
        "color": [1, 0.9, 0.8]
    })
    
    client.send_command("advanced_lighting", {
        "light_type": "AREA",
        "name": "填充光",
        "location": [-5, -5, 5],
        "energy": 100,
        "color": [0.8, 0.9, 1.0]
    })
    
    # 设置相机
    print("设置相机...")
    client.create_object(
        "CAMERA",
        name="棋盘相机",
        location=[0, -8, 6],
        rotation=[0.8, 0, 0]
    )

    # 渲染场景
    print("渲染场景...")
    client.send_command("render_scene", {
        "resolution_x": 1920,
        "resolution_y": 1080
    })
    
    print("国际象棋场景创建完成！")

except Exception as e:
    print(f"发生错误: {str(e)}")
finally:
    client.disconnect()

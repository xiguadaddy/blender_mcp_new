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
import traceback  # 添加traceback模块用于详细错误信息
import random

# 确保可以导入客户端类
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.blender_mcp.client import BlenderMCPClient

# 设置调试级别
DEBUG = True  # 可以控制是否输出详细日志

def debug_print(message):
    """调试信息输出函数"""
    if DEBUG:
        print(f"[DEBUG] {message}")

def check_response(response, operation_name):
    """检查响应状态，如有错误则打印"""
    if not response:
        print(f"警告: {operation_name} - 响应为空")
        return False
    
    if "error" in response:
        print(f"错误: {operation_name} - {response['error']}")
        return False
    
    if "status" in response and response["status"] == "error":
        print(f"错误: {operation_name} - {response.get('message', '未知错误')}")
        return False
    
    debug_print(f"{operation_name} - 成功")
    return True

def get_object_name(response):
    """从响应中获取对象名称，处理不同的响应格式"""
    if response is None:
        debug_print("警告: 响应为None")
        return None
        
    debug_print(f"响应类型: {type(response)}, 内容: {json.dumps(response, ensure_ascii=False)[:100]}")
    
    if isinstance(response, dict):
        if "status" in response and response["status"] == "error":
            debug_print(f"错误响应: {response.get('message', '未知错误')}")
            return None
            
        if "result" in response and isinstance(response["result"], dict):
            if "name" in response["result"]:
                return response["result"]["name"]
            if "object" in response["result"]:
                return response["result"]["object"]
                
        if "name" in response:
            return response["name"]
    
    debug_print(f"无法从响应中提取对象名称: {json.dumps(response, ensure_ascii=False)[:100]}")
    return None

def create_chess_set():
    """创建国际象棋棋盘和棋子"""
    # 创建客户端
    client = BlenderMCPClient()
    if not client.connect():
        print("无法连接到BlenderMCP服务器")
        sys.exit(1)
        
    try:
        # 测试服务器连接
        ping_response = client.ping()
        debug_print(f"服务器Ping响应: {json.dumps(ping_response, ensure_ascii=False)}")
        
        # 清除现有场景
        debug_print("清除现有场景...")
        scene_info = client.get_scene_info()
        if "result" in scene_info and "objects" in scene_info["result"]:
            for obj in scene_info["result"]["objects"]:
                if obj.get("name") != "Camera":  # 保留相机
                    client.delete_object(obj["name"])
        
        # 1. 创建棋盘底座
        debug_print("创建棋盘底座...")
        board_response = client.create_object("CUBE", name="棋盘", 
                                              location=[0, 0, 0], 
                                              scale=[4, 4, 0.2])
        debug_print(f"棋盘响应: {json.dumps(board_response, ensure_ascii=False)}")
        
        # 使用辅助方法获取棋盘名称
        board_name = get_object_name(board_response)
        if not board_name:
            # 创建失败，重试一次
            debug_print("注意: 棋盘创建失败，尝试重新创建...")
            time.sleep(0.5)  # 等待一段时间
            board_response = client.create_object("CUBE", name="棋盘", 
                                                  location=[0, 0, 0], 
                                                  scale=[4, 4, 0.2])
            debug_print(f"重试棋盘响应: {json.dumps(board_response, ensure_ascii=False)}")
            board_name = get_object_name(board_response)
            
            if not board_name:
                print("错误: 棋盘创建失败，无法继续创建国际象棋场景")
                return
        
        # 验证棋盘是否真的存在
        verify_response = client.send_command("get_object_info", {"name": board_name})
        if "status" not in verify_response or verify_response["status"] != "success":
            print(f"错误: 棋盘 {board_name} 不存在于场景中，无法继续创建国际象棋场景")
            return
        
        debug_print(f"棋盘名称: {board_name}")
        
        # 为棋盘设置棕色材质
        client.set_material(board_name, color=[0.4, 0.2, 0.1])
        
        # 2. 创建64个棋盘格子
        squares = []
        for row in range(8):
            for col in range(8):
                # 计算位置
                x = (col - 3.5) * 0.8
                y = (row - 3.5) * 0.8
                z = 0.2  # 放在棋盘表面
                
                # 确定颜色（交替的黑白格子）
                is_white = (row + col) % 2 == 0
                color = [0.9, 0.9, 0.9] if is_white else [0.1, 0.1, 0.1]
                
                # 创建棋盘格
                square_name = f"格子_{row}_{col}"
                debug_print(f"创建{square_name}...")
                square_response = client.create_object("CUBE", name=square_name, 
                                                      location=[x, y, z], 
                                                      scale=[0.4, 0.4, 0.02])
                
                # 获取格子名称
                square_obj_name = get_object_name(square_response)
                if not square_obj_name:
                    # 使用预期的名称继续而不跳过
                    square_obj_name = square_name
                    print(f"注意：无法获取格子名称，使用默认名称 '{square_obj_name}' 继续")
                
                # 设置材质
                client.set_material(square_obj_name, color=color)
                squares.append(square_obj_name)
        
        # 3. 创建棋子
        debug_print("开始创建棋子...")
        
        # 创建白方小兵（第2行）
        white_pawns = []
        for col in range(8):
            x = (col - 3.5) * 0.8
            y = -2 * 0.8  # 第2行
            z = 0.3  # 棋盘表面上方
            
            pawn_name = f"白兵_{col}"
            white_pawn = create_pawn(client, pawn_name, [x, y, z], is_white=True)
            if white_pawn:
                white_pawns.append(white_pawn)
        
        # 创建黑方小兵（第7行）
        black_pawns = []
        for col in range(8):
            x = (col - 3.5) * 0.8
            y = 2 * 0.8  # 第7行
            z = 0.3  # 棋盘表面上方
            
            pawn_name = f"黑兵_{col}"
            black_pawn = create_pawn(client, pawn_name, [x, y, z], is_white=False)
            if black_pawn:
                black_pawns.append(black_pawn)
        
        # 创建白方城堡（第1行角落）
        rook1_pos = [(-3.5) * 0.8, (-3.5) * 0.8, 0.3]  # 左下角
        white_rook1 = create_rook(client, "白车_1", rook1_pos, is_white=True)
        
        rook2_pos = [(3.5) * 0.8, (-3.5) * 0.8, 0.3]  # 右下角
        white_rook2 = create_rook(client, "白车_2", rook2_pos, is_white=True)
        
        # 创建黑方城堡（第8行角落）
        rook3_pos = [(-3.5) * 0.8, (3.5) * 0.8, 0.3]  # 左上角
        black_rook1 = create_rook(client, "黑车_1", rook3_pos, is_white=False)
        
        rook4_pos = [(3.5) * 0.8, (3.5) * 0.8, 0.3]  # 右上角
        black_rook2 = create_rook(client, "黑车_2", rook4_pos, is_white=False)
        
        # 4. 设置灯光
        debug_print("设置场景灯光...")
        
        # 添加日光以提供整体照明
        sun_light = client.send_command("create_object", {"type": "LIGHT", "name": "Sun", "location": [5, 5, 10]})
        sun_name = get_object_name(sun_light) or "Sun"
        debug_print(f"使用的阳光名称: {sun_name}")
        
        # 设置灯光类型和能量
        client.send_command("set_light_type", {"name": sun_name, "light_type": "SUN"})
        client.send_command("set_light_energy", {"name": sun_name, "energy": 3.0})
        
        # 添加高级区域光照为场景增添气氛
        debug_print("创建区域光照...")
        area_light = client.send_command("advanced_lighting", {
            "name": "Chess_Light",
            "light_type": "AREA",
            "location": [0, 0, 5],
            "energy": 50,
            "color": [1.0, 0.95, 0.9]
        })
        debug_print(f"区域光响应: {json.dumps(area_light, ensure_ascii=False)[:100]}")
        
        # 5. 设置相机
        debug_print("设置相机...")
        camera = client.send_command("create_object", {"type": "CAMERA", "name": "ChessCamera"})
        camera_name = get_object_name(camera) or "ChessCamera"
        debug_print(f"使用的相机名称: {camera_name}")
        
        # 放置相机在一个好的角度
        client.modify_object(camera_name, location=[8, -6, 6], rotation=[0.9, 0, 0.8])
        # 设为活动相机
        client.send_command("set_active_camera", {"name": camera_name})
        
        # 6. 渲染场景
        debug_print("渲染最终场景...")
        render_result = client.render_scene(resolution_x=1920, resolution_y=1080)
        if check_response(render_result, "渲染场景"):
            print("国际象棋场景创建并渲染成功！")
        else:
            print("场景渲染失败，但棋盘和棋子可能已创建成功。")
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
        traceback.print_exc()
    finally:
        # 断开连接
        client.disconnect()

def create_pawn(client, name, location, is_white=True):
    """创建一个小兵棋子"""
    try:
        debug_print(f"创建小兵: {name}")
        
        # 创建小兵底座（圆柱体）
        base_name = f"{name}_base"
        base_response = client.create_object("CYLINDER", name=base_name, 
                                            location=[location[0], location[1], location[2]], 
                                            scale=[0.2, 0.2, 0.05])
        debug_print(f"小兵底座响应: {json.dumps(base_response, ensure_ascii=False)[:100]}")
        
        base_obj_name = get_object_name(base_response) or base_name
        debug_print(f"使用的底座名称: {base_obj_name}")
        
        # 创建小兵主体（圆柱体）
        body_name = f"{name}_body"
        body_location = [location[0], location[1], location[2] + 0.15]
        body_response = client.create_object("CYLINDER", name=body_name, 
                                            location=body_location, 
                                            scale=[0.15, 0.15, 0.2])
        
        body_obj_name = get_object_name(body_response) or body_name
        debug_print(f"使用的主体名称: {body_obj_name}")
        
        # 创建小兵头部（球体）
        head_name = f"{name}_head"
        head_location = [location[0], location[1], location[2] + 0.4]
        head_response = client.create_object("SPHERE", name=head_name, 
                                            location=head_location, 
                                            scale=[0.12, 0.12, 0.12])
        
        head_obj_name = get_object_name(head_response) or head_name
        debug_print(f"使用的头部名称: {head_obj_name}")
        
        # 设置材质颜色
        color = [0.9, 0.9, 0.9] if is_white else [0.1, 0.1, 0.1]
        client.set_material(base_obj_name, color=color)
        client.set_material(body_obj_name, color=color)
        client.set_material(head_obj_name, color=color)
        
        # 合并小兵的组件
        debug_print(f"合并小兵组件: {base_obj_name}, {body_obj_name}, {head_obj_name}")
        merge_response = client.join_objects(
            objects=[base_obj_name, body_obj_name, head_obj_name],
            target_object=base_obj_name
        )
        debug_print(f"合并响应: {json.dumps(merge_response, ensure_ascii=False)[:100]}")
        
        if check_response(merge_response, f"合并小兵组件"):
            return base_obj_name
        else:
            print(f"警告：无法合并小兵组件，但各部分已创建: {name}")
            return base_obj_name
    
    except Exception as e:
        print(f"创建小兵时发生错误: {str(e)}")
        return None

def create_rook(client, name, location, is_white=True):
    """创建一个城堡棋子"""
    try:
        debug_print(f"创建城堡: {name}")
        
        # 创建城堡底座（圆柱体）
        base_name = f"{name}_base"
        base_response = client.create_object("CYLINDER", name=base_name, 
                                            location=[location[0], location[1], location[2]], 
                                            scale=[0.25, 0.25, 0.06])
        debug_print(f"城堡底座响应: {json.dumps(base_response, ensure_ascii=False)[:100]}")
        
        base_obj_name = get_object_name(base_response) or base_name
        debug_print(f"使用的底座名称: {base_obj_name}")
        
        # 创建城堡主体（圆柱体）
        body_name = f"{name}_body"
        body_location = [location[0], location[1], location[2] + 0.2]
        body_response = client.create_object("CYLINDER", name=body_name, 
                                            location=body_location, 
                                            scale=[0.2, 0.2, 0.25])
        
        body_obj_name = get_object_name(body_response) or body_name
        debug_print(f"使用的主体名称: {body_obj_name}")
        
        # 创建城堡顶部（立方体）
        top_name = f"{name}_top"
        top_location = [location[0], location[1], location[2] + 0.5]
        top_response = client.create_object("CUBE", name=top_name, 
                                           location=top_location, 
                                           scale=[0.25, 0.25, 0.05])
        
        top_obj_name = get_object_name(top_response) or top_name
        debug_print(f"使用的顶部名称: {top_obj_name}")
        
        # 设置材质颜色
        color = [0.9, 0.9, 0.9] if is_white else [0.1, 0.1, 0.1]
        client.set_material(base_obj_name, color=color)
        client.set_material(body_obj_name, color=color)
        client.set_material(top_obj_name, color=color)
        
        # 合并城堡的组件
        debug_print(f"合并城堡组件: {base_obj_name}, {body_obj_name}, {top_obj_name}")
        merge_response = client.join_objects(
            objects=[base_obj_name, body_obj_name, top_obj_name],
            target_object=base_obj_name
        )
        debug_print(f"合并响应: {json.dumps(merge_response, ensure_ascii=False)[:100]}")
        
        if check_response(merge_response, f"合并城堡组件"):
            return base_obj_name
        else:
            print(f"警告：无法合并城堡组件，但各部分已创建: {name}")
            return base_obj_name
    
    except Exception as e:
        print(f"创建城堡时发生错误: {str(e)}")
        return None

if __name__ == "__main__":
    create_chess_set()

import asyncio
import json
import sys
import argparse
from server.ipc_client import IPCClient

async def test_connection(client):
    """测试与Blender的基本连接"""
    code = """
import bpy
result = {
    "blender_version": bpy.app.version_string,
    "status": "连接成功",
    "active_objects": [obj.name for obj in bpy.context.scene.objects]
}
result
"""
    print("=== 测试基本连接 ===")
    print("发送代码...")
    return await client.execute_in_blender(code)

async def create_cube(client, name="测试立方体", size=2, location=(0,0,0)):
    """创建立方体测试"""
    code = f"""
import bpy
bpy.ops.mesh.primitive_cube_add(
    size={size}, 
    location=({location[0]}, {location[1]}, {location[2]})
)
if bpy.context.active_object:
    bpy.context.active_object.name = "{name}"
    result = {{"name": bpy.context.active_object.name, "status": "success"}}
else:
    result = {{"error": "创建对象失败", "status": "error"}}
result
"""
    print(f"=== 创建立方体: {name} ===")
    return await client.execute_in_blender(code)

async def list_objects(client, type_filter=""):
    """列出场景中的对象"""
    code = f"""
import bpy
result = []

for obj in bpy.data.objects:
    if not "{type_filter}" or obj.type == "{type_filter}":
        result.append({{
            "name": obj.name,
            "type": obj.type,
            "location": [round(obj.location.x, 3), round(obj.location.y, 3), round(obj.location.z, 3)]
        }})

result
"""
    print("=== 列出场景对象 ===")
    return await client.execute_in_blender(code)

async def set_material(client, object_name, color=(0.8, 0.2, 0.2)):
    """为对象设置材质"""
    code = f"""
import bpy
result = {{"status": "error", "message": "对象未找到"}}

if "{object_name}" in bpy.data.objects:
    obj = bpy.data.objects["{object_name}"]
    
    # 创建新材质
    mat_name = "{object_name}_材质"
    mat = bpy.data.materials.get(mat_name)
    if not mat:
        mat = bpy.data.materials.new(name=mat_name)
    
    # 启用节点
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    
    # 清除现有节点
    for node in nodes:
        nodes.remove(node)
    
    # 创建材质节点
    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    bsdf_node = nodes.new(type='ShaderNodeBsdfPrincipled')
    
    # 设置颜色
    bsdf_node.inputs[0].default_value = ({color[0]}, {color[1]}, {color[2]}, 1.0)
    
    # 连接节点
    mat.node_tree.links.new(bsdf_node.outputs[0], output_node.inputs[0])
    
    # 为对象指定材质
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    
    result = {{"status": "success", "message": "材质已应用", "material_name": mat.name}}

result
"""
    print(f"=== 为 {object_name} 设置材质 ===")
    return await client.execute_in_blender(code)

async def custom_code(client, code):
    """执行自定义代码"""
    print("=== 执行自定义代码 ===")
    return await client.execute_in_blender(code)

async def test_different_formats(client):
    """测试不同格式的请求"""
    # 格式1: 直接发送Python代码字符串
    request1 = "import bpy; {'result': bpy.app.version_string}"
    print("=== 测试格式1: 直接发送Python代码 ===")
    result1 = await client.send_request(request1)
    print(f"结果1: {result1}")
    
    # 格式2: 使用命令+数据格式
    request2 = {
        "command": "run_python",
        "code": "import bpy; {'result': bpy.app.version_string}"
    }
    print("=== 测试格式2: 命令+代码 ===")
    result2 = await client.send_request(request2)
    print(f"结果2: {result2}")
    
    # 格式3: 完整的RPC格式
    request3 = {
        "jsonrpc": "2.0",
        "method": "execute_python",
        "params": {
            "code": "import bpy; {'result': bpy.app.version_string}"
        },
        "id": 1
    }
    print("=== 测试格式3: RPC格式 ===")
    result3 = await client.send_request(request3)
    print(f"结果3: {result3}")
    
    # 格式4: 自定义类型字段
    request4 = {
        "type": "python",
        "data": "import bpy; {'result': bpy.app.version_string}"
    }
    print("=== 测试格式4: type+data ===")
    result4 = await client.send_request(request4)
    print(f"结果4: {result4}")
    
    return [result1, result2, result3, result4]

async def debug_ipc_server(client):
    """尝试多种请求格式，发现正确的通信方式"""
    formats = [
        {"command": "exec", "data": "import bpy; {'test': True}"},
        {"cmd": "exec", "data": "import bpy; {'test': True}"},
        {"method": "exec", "params": {"code": "import bpy; {'test': True}"}},
        {"action": "exec", "code": "import bpy; {'test': True}"},
        {"type": "exec", "data": "import bpy; {'test': True}"},
        "import bpy; {'test': True}"
    ]
    
    results = []
    for i, fmt in enumerate(formats):
        print(f"测试格式 {i+1}: {fmt}")
        try:
            resp = await client.send_request(fmt)
            results.append({"format": i+1, "response": resp, "success": "error" not in str(resp).lower()})
        except Exception as e:
            results.append({"format": i+1, "error": str(e), "success": False})
    
    return results

async def main():
    parser = argparse.ArgumentParser(description='测试Blender MCP通信')
    parser.add_argument('--port', type=int, default=27015, help='Blender IPC服务器端口')
    parser.add_argument('--test', type=str, default='all', 
                        choices=['connection', 'cube', 'list', 'material', 'custom', 'all'],
                        help='要运行的测试')
    parser.add_argument('--code', type=str, help='要执行的自定义代码')
    args = parser.parse_args()
    
    # 创建IPC客户端
    client = IPCClient(f"port:{args.port}")
    try:
        # 连接到Blender
        await client.connect()
        
        # 根据选项运行测试
        if args.test in ['connection', 'all']:
            result = await test_connection(client)
            print(f"连接测试结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
        if args.test in ['cube', 'all']:
            result = await create_cube(client, "测试立方体", 2, (0, 0, 0))
            print(f"创建立方体结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
        if args.test in ['list', 'all']:
            result = await list_objects(client)
            print(f"场景对象列表: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
        if args.test in ['material', 'all']:
            result = await set_material(client, "测试立方体", (0.8, 0.2, 0.2))
            print(f"设置材质结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
        if args.test in ['custom'] and args.code:
            result = await custom_code(client, args.code)
            print(f"自定义代码执行结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
        if args.test in ['different_formats', 'all']:
            results = await test_different_formats(client)
            print(f"不同格式请求结果: {json.dumps(results, indent=2, ensure_ascii=False)}")
            
        if args.test in ['debug_ipc_server', 'all']:
            results = await debug_ipc_server(client)
            print(f"不同格式请求结果: {json.dumps(results, indent=2, ensure_ascii=False)}")
            
        # 简单的测试脚本
        test_code = """
import bpy
result = {
    "blender_version": bpy.app.version_string,
    "status": "success",
    "message": "Blender通信测试成功"
}
"""

        test_request = {
            "action": "call_tool",
            "tool": "execute_python",
            "arguments": {"code": test_code}
        }

        # 发送请求并打印结果
        result = await client.send_request(test_request)
        print(f"测试结果: {result}")
            
    except Exception as e:
        print(f"测试过程中出错: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(main())

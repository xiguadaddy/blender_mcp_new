# BlenderMCP 迁移指南

本文档提供从旧版BlenderMCP到新版模块化架构的迁移指南。

## 主要变更

1. **模块化架构**：将代码分为客户端和服务器两个独立模块
2. **客户端不依赖bpy**：客户端模块可在任何Python环境中运行
3. **服务器作为Blender插件**：服务器模块作为Blender插件运行
4. **标准化API响应**：统一所有API响应格式
5. **增强的错误处理**：改进错误捕获和处理机制
6. **添加安全对象操作**：添加如`safe_join_objects`等安全操作功能

## 从旧版迁移

### 1. 目录结构变更

旧版结构:
```
blender-mcp/
├── src/
│   └── blender_mcp/
│       ├── __init__.py
│       ├── client.py
│       └── server.py
└── demos/
    └── chess_set.py
```

新版结构:
```
blender_mcp_new/
├── __init__.py
├── client/
│   ├── __init__.py
│   └── client.py
├── server/
│   ├── __init__.py
│   └── server.py
├── examples/
│   └── chess_set.py
└── install_blender_server.py
```

### 2. 导入方式变更

旧版导入:
```python
from src.blender_mcp import BlenderMCPClient
```

新版导入:
```python
from blender_mcp_new import BlenderMCPClient
```

### 3. 服务器安装变更

旧版服务器安装:
手动复制`server.py`到Blender插件目录

新版服务器安装:
使用安装脚本
```bash
python blender_mcp_new/install_blender_server.py
```

### 4. 客户端API变更

#### 主要变更的方法:

| 旧版方法                            | 新版方法                             | 说明                    |
|-----------------------------------|------------------------------------|-----------------------|
| `client.join_objects(objects)`    | `client.safe_join_objects(objects)` | 增加了对象验证步骤         |
| `client.verify_object_exists(name)` | `client.verify_object_exists(object_name)` | 参数名称统一   |
| `client.clear_scene()`            | `client.clear_scene()`             | 实现方式从执行代码改为命令   |

#### 响应格式变更:

旧版响应格式不统一，新版统一使用以下格式:
```python
{
    "status": "success" | "error",
    "result": { ... }  # 成功时的结果数据
    # 或
    "message": "错误信息"  # 错误时的消息
}
```

### 5. 脚本修改示例

以下是修改脚本以适应新版API的示例:

```python
# 旧版脚本
from src.blender_mcp import BlenderMCPClient

client = BlenderMCPClient()
client.connect()
cube = client.create_object("CUBE")
# 无错误处理

# 新版脚本
from blender_mcp_new import BlenderMCPClient

client = BlenderMCPClient(debug=True)
if not client.connect():
    print("连接失败")
    exit(1)

try:
    response = client.create_object("CUBE")
    if response["status"] == "success":
        cube_name = response["result"]["name"]
        print(f"创建立方体: {cube_name}")
    else:
        print(f"创建失败: {response.get('message', '未知错误')}")
finally:
    client.disconnect()
```

## 新增功能

1. **安全对象合并**：
   ```python
   client.safe_join_objects([obj1, obj2, obj3], target_object=obj1)
   ```

2. **响应处理助手**：
   ```python
   from blender_mcp_new.examples.chess_set import check_response, get_object_name
   
   response = client.create_object("CUBE")
   if check_response(response, "创建立方体"):
       cube_name = get_object_name(response)
       print(f"创建成功: {cube_name}")
   ```

3. **操作安全包装器**：
   ```python
   from blender_mcp_new.examples.chess_set import safe_operation
   
   # 自动处理延迟、错误和重试
   response = safe_operation(client, client.create_object, "CUBE", 
                           operation_name="创建立方体")
   ```

## 服务器插件

新版服务器作为独立的Blender插件运行，提供UI界面控制服务器启停。

1. 安装插件:
   ```bash
   python blender_mcp_new/install_blender_server.py
   ```

2. 在Blender中启用插件：
   编辑 > 偏好设置 > 插件 > 搜索"BlenderMCP"

3. 使用界面：
   在3D视图 > 侧边栏 > BlenderMCP选项卡中控制服务器 
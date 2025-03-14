# BlenderMCP

通过网络API控制Blender的工具包，提供客户端-服务器架构实现远程控制Blender。

## 项目结构

该项目采用清晰的模块化结构:

```
blender_mcp_new/
├── __init__.py          # 主包初始化
├── client/              # 客户端模块 (不依赖bpy)
│   ├── __init__.py
│   └── client.py        # BlenderMCPClient实现
├── server/              # 服务器模块 (依赖bpy，只能在Blender中运行)
│   ├── __init__.py
│   └── server.py        # BlenderMCPServer实现
├── examples/            # 示例脚本
│   ├── chess_set.py     # 国际象棋示例
│   └── ...
└── README.md            # 本文件
```

## 使用方法

### 服务器端 (在Blender中运行)

1. 在Blender中安装插件 (详见安装说明)
2. 启用插件并启动服务器
3. 服务器默认在端口8000上监听连接

### 客户端 (可在任何Python环境中运行)

```python
from blender_mcp_new import BlenderMCPClient

# 创建客户端连接
client = BlenderMCPClient(host="localhost", port=8000, debug=True)
if not client.connect():
    print("无法连接到Blender服务器")
    exit(1)

# 基本操作示例
try:
    # 创建一个立方体
    response = client.create_object("CUBE", location=[0, 0, 0])
    print(f"创建立方体响应: {response}")
    
    # 获取场景信息
    scene_info = client.get_scene_info()
    print(f"场景信息: {scene_info}")
finally:
    # 断开连接
    client.disconnect()
```

## 示例脚本

项目包含多个示例脚本，展示如何使用BlenderMCP:

- `chess_set.py` - 创建国际象棋棋盘和棋子
- 更多示例脚本会陆续添加...

## API功能

BlenderMCP客户端提供以下主要功能:

- 场景管理: 清空场景、获取场景信息
- 对象操作: 创建、修改、删除对象
- 材质设置: 为对象设置颜色、金属度、粗糙度等属性
- 灯光控制: 创建和管理各种类型的灯光
- 相机控制: 设置相机位置和属性
- 渲染功能: 渲染当前场景

## 安装说明

### 在任何Python环境中使用客户端

```bash
# 克隆仓库
git clone https://github.com/yourusername/blender-mcp.git

# 安装依赖
cd blender-mcp
pip install -e .
```

### 在Blender中安装服务器插件

1. 打开Blender
2. 转到编辑 > 偏好设置 > 插件
3. 点击"安装"按钮
4. 导航到`server/addon`文件夹，选择插件文件
5. 启用插件

## 版本兼容性

- 客户端模块兼容Python 3.6+
- 服务器模块已在Blender 2.93+上测试通过

## 错误处理

BlenderMCP客户端包含内置的错误处理和重试机制:

- 自动重试连接
- 验证对象创建
- 安全对象合并操作
- 响应格式标准化

## 开发者注意事项

- 客户端和服务器模块被有意分离，以确保客户端代码可以在没有Blender的环境中运行
- 所有服务器端代码都在`server`模块中，依赖于`bpy`
- 客户端代码在`client`模块中，不依赖于任何Blender特定的库

## 许可证

[适当的开源许可证] 
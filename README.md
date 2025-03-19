# Blender MCP - Model Context Protocol与Blender集成

Blender MCP项目实现了[Model Context Protocol (MCP)](https://modelcontextprotocol.io/)与Blender之间的集成，使AI模型（如Claude）能够直接与Blender交互，进行3D建模、渲染和场景操作。

## 项目架构

项目采用进程分离架构，包含两个主要组件：

```
┌────────────────────┐    IPC    ┌───────────────────┐
│ MCP服务器核心       │◄────── ──►│ Blender插件       │
│ (独立Python进程)    │  通信通道  │ (Blender内部环境) │
└────────────────────┘           └───────────────────┘
        ▲                                ▲
        │ MCP协议                        │
        │                                │
        ▼                                ▼
┌────────────────────┐           ┌───────────────────┐
│ MCP客户端           │           │ Blender API       │
│ (Claude等LLM客户端) │           │ (bpy模块)         │
└────────────────────┘           └───────────────────┘
```

- **MCP服务器核心**：独立Python进程，实现MCP协议，为AI模型提供Blender资源和工具访问
- **Blender插件**：在Blender内部运行，提供UI界面和Blender操作实现

这种架构解决了Blender Python环境的限制问题，使MCP服务器可以使用现代Python特性，同时通过IPC与Blender进行通信。

## 功能特点

### 资源访问
- 查看和访问Blender场景中的对象、材质、灯光和相机
- 以JSON格式获取资源详细信息
- 支持资源订阅和更新通知

### 工具操作
- 创建各种3D对象（立方体、球体、平面等）
- 设置材质和属性
- 添加和控制灯光
- 配置相机
- 渲染场景
- 应用修改器
- 转换对象（位置、旋转、缩放）
- 导入外部模型

### 提示模板
- 场景创建引导
- 动画制作引导
- 材质教程

## 安装指南

### 系统要求
- Blender 3.0+
- Python 3.7+
- MCP支持的AI客户端（如Claude）

### 安装步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/xiguadaddy/blender_mcp_new.git
   cd blender_mcp_new
   ```

2. **安装MCP服务器核心**
   ```bash
   cd mcp-server
   pip install -r requirements.txt
   ```

3. **安装Blender插件**
   - 打开Blender
   - 进入编辑 > 首选项 > 附加组件
   - 点击"安装..."，选择`blender-addon`目录生成的ZIP文件
   - 勾选插件以激活它

## API调用格式

Blender MCP服务器支持两种类型的API请求格式：

### 1. 方法请求 (Method)

用于MCP标准操作，如获取工具列表和资源列表：

```json
{
    "method": "mcp/listTools",
    "params": {}
}
```

```json
{
    "method": "mcp/listResources",
    "params": {}
}
```

### 2. 操作请求 (Action)

用于直接工具操作，如调用Blender工具：

```json
{
    "action": "call_tool",
    "tool": "create_object",
    "arguments": {
        "object_type": "cube",
        "name": "TestCube",
        "location": [0, 0, 0],
        "size": 2.0
    }
}
```

### API请求注意事项

- **工具调用**：必须使用`action`字段，不要使用`method`字段
- **消息格式**：所有请求和响应都是JSON格式，需要添加长度前缀
- **长度前缀**：消息以`{长度}:`为前缀，如`125:{"action":"call_tool",...}`
- **工具参数**：参数格式取决于特定工具，请参考工具列表获取详情

## 使用方法

### 启动服务

1. **在Blender中启动插件服务器**
   - 打开Blender并加载插件
   - 在3D视图侧边栏找到"MCP"标签
   - 点击"启动服务器"按钮

2. **启动MCP服务器核心**
   ```bash
   python start_server.py
   ```

### 配置Claude客户端

在Claude的MCP配置中添加：
```json
{
  "mcpServers": {
    "blender": {
      "command": "python",
      "args": ["/path/to/blender-mcp_new/start_server.py"]
    }
  }
}
```

### 使用示例

通过Claude与Blender交互：
```
我想在场景中创建一个红色立方体，位置在坐标(0, 0, 2)，然后添加一个点光源。
```

Claude会使用MCP工具与Blender交互，创建所需的对象。

## 测试示例

我们提供了一些测试脚本来演示如何直接与MCP服务器通信：

### 创建红色立方体测试

`tests/test_cube.py`是一个完整的测试示例，演示了：
1. 如何连接到MCP服务器
2. 如何发送创建立方体的请求
3. 如何为立方体设置红色材质

运行测试：
```bash
python tests/test_cube.py
```

测试代码示例：
```python
async def test_create_cube():
    """测试创建立方体"""
    params = {
        "action": "call_tool",
        "tool": "create_object",
        "arguments": {
            "object_type": "cube",
            "name": "TestCube",
            "location": [0, 0, 0],
            "size": 2.0
        }
    }
    
    response = await send_request(None, params)
    
    if response and not response.get("error"):
        return "TestCube"  # 返回对象名称
    else:
        return None

async def test_set_material(object_name):
    """测试设置红色材质"""
    params = {
        "action": "call_tool",
        "tool": "set_material",
        "arguments": {
            "object_name": object_name,
            "material_name": "RedMaterial",
            "color": [1.0, 0.0, 0.0, 1.0],  # 红色 RGBA
            "metallic": 0.0,
            "roughness": 0.5
        }
    }
    
    response = await send_request(None, params)
    
    if response and not response.get("error"):
        return True
    else:
        return False
```

### 获取工具列表

查看Blender MCP中所有可用的工具：
```bash
python tests/test_list_tools.py tools
```

### 获取资源列表

查看当前场景中所有可用的资源：
```bash
python tests/test_list_tools.py resources
```

## 项目结构

```
blender-mcp/
│
├── mcp-server/                      # MCP服务器核心
│   ├── main.py                      # 主入口点
│   ├── server/                      # 服务器实现
│   ├── resources/                   # 资源处理
│   ├── tools/                       # 工具实现
│   └── prompts/                     # 提示模板
│
├── blender-addon/                   # Blender插件
│   ├── __init__.py                  # 插件入口点
│   ├── addon/                       # 插件UI和操作符
│   ├── ipc/                         # IPC通信
│   ├── handlers/                    # 请求处理
│   └── utils/                       # 辅助工具
│
└── tests/                           # 测试脚本
    ├── test_list_tools.py           # 测试工具列表
    └── test_cube.py                 # 测试创建立方体
```

## 调试与测试

1. **启用调试模式**
   - 在Blender插件首选项中启用"调试模式"
   - 日志会输出到Blender控制台

2. **测试工具**
   - 插件UI中包含测试工具部分
   - "创建测试对象"按钮可快速创建测试立方体
   - "查看资源"按钮可列出当前场景中的资源

3. **日志文件**
   - Blender插件日志: `%TEMP%/blender_mcp_ui.log`
   - 测试脚本日志: `%TEMP%/blender_mcp_test.log`
   - MCP服务器日志: 控制台输出

## 已知问题和限制

- Windows平台路径兼容性：Unix socket路径在Windows上需使用命名管道
- 大型网格数据传输性能：大型模型的资源数据可能受IPC通信限制
- 多线程渲染支持有限：某些高级渲染功能可能不完全支持
- 资源列表获取可能较慢：已添加超时保护，但大型场景仍可能需要较长时间

## 未来计划

- 添加更多专业工具（节点材质编辑、动画控制）
- 改进资源订阅机制，实现实时更新
- 添加高级渲染选项
- WebSocket支持，实现远程控制
- 多Blender实例支持

## 贡献指南

欢迎提交PR和Issue！

1. Fork项目
2. 创建分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启Pull Request

## 许可证

本项目采用MIT许可证 - 详情见 [LICENSE](LICENSE) 文件

## 致谢

- [Model Context Protocol](https://modelcontextprotocol.io/) 团队提供的协议规范
- Blender基金会提供的强大3D软件
- Claude和其他AI模型使这种交互成为可能

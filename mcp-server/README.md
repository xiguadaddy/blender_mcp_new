# Blender MCP 服务器

这是Blender MCP项目的服务器组件，负责实现MCP协议并与Blender插件通信。

## IPC通信协议

服务器和Blender插件之间使用IPC（进程间通信）进行交互。通信协议如下：

### 消息格式

所有消息使用JSON格式，并在发送前添加消息长度前缀：

```
<length>:<json_data>
```

例如:
```
25:{"action":"list_resources"}
```

### 请求类型

1. **列出资源**
   ```json
   {"action": "list_resources"}
   ```

2. **读取资源**
   ```json
   {
     "action": "read_resource",
     "type": "mesh",
     "id": "Cube"
   }
   ```

3. **调用工具**
   ```json
   {
     "action": "call_tool",
     "tool": "create_object",
     "arguments": {
       "type": "CUBE",
       "location": [0, 0, 0],
       "scale": [1, 1, 1]
     }
   }
   ```

4. **检查对象是否存在**
   ```json
   {
     "action": "check_object_exists",
     "object_name": "Cube"
   }
   ```

### 平台差异

- **Windows**：使用TCP套接字，默认端口27015
  - 连接格式: `port:27015`
  
- **Unix/Linux/macOS**：使用Unix域套接字
  - 默认路径: `/tmp/blender-mcp.sock`

## 使用方法

1. 确保Blender插件已启动并运行IPC服务器
2. 启动MCP服务器：

```bash
python3 main.py --socket-path <路径或端口>
```

例如:
```bash
# Unix/Linux/macOS
python3 main.py --socket-path /tmp/blender-mcp.sock

# Windows
python3 main.py --socket-path port:27015
```

## MCP协议实现

服务器实现了以下MCP核心功能：

1. **资源(Resources)**
   - 列出Blender中的资源
   - 读取资源内容

2. **工具(Tools)**
   - 列出可用工具
   - 调用工具执行Blender操作

3. **提示(Prompts)**
   - 提供任务相关的提示模板

## 调试和排错

如果连接出现问题，请检查：

1. Blender插件是否已启动并正确初始化IPC服务器
2. 是否使用了正确的连接路径/端口
3. 防火墙是否允许本地连接(Windows)
4. 临时目录权限是否正确(Unix域套接字)

查看Blender控制台和MCP服务器输出以获取详细错误信息。

# BlenderMCP 错误处理指南

本文档提供了BlenderMCP项目中常见错误的处理方法和最佳实践，帮助您编写更健壮的脚本。

## 目录

1. [错误处理基础](#错误处理基础)
2. [常见错误类型](#常见错误类型)
3. [最佳实践](#最佳实践)
4. [辅助函数](#辅助函数)
5. [故障排除](#故障排除)

## 错误处理基础

BlenderMCP的API设计遵循以下原则：

1. 所有命令响应都包含一个`status`字段，可能的值为`success`或`error`
2. 当`status`为`error`时，还会包含一个`message`字段，说明错误原因
3. 当`status`为`success`时，`result`字段包含返回数据

基本的错误检查应该是：

```python
response = client.send_command("some_command", params)
if response.get("status") == "error":
    print(f"错误: {response.get('message', '未知错误')}")
    # 处理错误...
else:
    # 处理成功响应...
    result = response.get("result", {})
```

## 常见错误类型

### 1. 连接错误

```
无法连接到BlenderMCP服务器
```

**可能原因：**
- Blender未启动
- BlenderMCP插件未启用
- 服务器端口不匹配

**解决方案：**
- 确保Blender已启动并加载了BlenderMCP插件
- 检查端口设置（默认9876）
- 尝试重启Blender

### 2. 对象创建失败

```
'NoneType' object has no attribute 'name'
```

**可能原因：**
- 服务器响应格式不一致
- Blender内部错误导致对象创建失败
- 内存不足

**解决方案：**
- 使用`get_object_name`辅助函数解析响应
- 实现重试机制
- 每次创建对象后验证其是否存在

### 3. 对象不存在错误

```
错误: 对象 '某对象名' 不存在
```

**可能原因：**
- 对象尚未创建或已被删除
- 引用了错误的对象名称

**解决方案：**
- 在操作对象前使用`get_object_info`验证其存在性
- 保存和检查返回的对象名称

### 4. 参数错误

```
错误: 参数不正确 - 缺少必需参数'light_type'
```

**可能原因：**
- 缺少必需参数
- 参数类型错误
- 参数值范围错误

**解决方案：**
- 确保提供所有必需参数
- 参考API文档确认参数格式和范围

## 最佳实践

### 1. 总是检查响应状态

每次API调用后，检查响应状态：

```python
response = client.create_object("CUBE", name="MyCube")
if response.get("status") == "error":
    print(f"创建对象失败: {response.get('message', '未知错误')}")
    # 执行错误恢复逻辑...
```

### 2. 对象存在性验证

在执行依赖特定对象的操作前，验证该对象存在：

```python
verify_response = client.send_command("get_object_info", {"name": object_name})
if verify_response.get("status") != "success":
    print(f"警告: 对象 {object_name} 不存在")
    # 处理不存在情况...
```

### 3. 实现重试机制

对关键操作实现重试机制：

```python
max_retries = 3
for attempt in range(max_retries):
    response = client.create_object("CUBE", name="MyCube")
    if response.get("status") == "success":
        break
    print(f"尝试 {attempt+1}/{max_retries} 失败，正在重试...")
    time.sleep(0.5)
```

### 4. 使用异常处理

包装整个API交互流程在异常处理块中：

```python
try:
    # API调用...
except socket.error as e:
    print(f"网络错误: {e}")
except json.JSONDecodeError:
    print("响应解析错误")
except Exception as e:
    print(f"未预期错误: {e}")
finally:
    client.disconnect()  # 确保断开连接
```

### 5. 使用辅助函数处理不一致的响应

API响应格式可能因命令类型而异，使用辅助函数标准化处理：

```python
def get_object_name(response):
    """从响应中提取对象名称"""
    # 见下方辅助函数部分
```

## 辅助函数

### 对象名称提取

```python
def get_object_name(response):
    """从响应中获取对象名称，处理不同的响应格式"""
    if response is None:
        print("警告: 响应为None")
        return None
        
    if isinstance(response, dict):
        if "status" in response and response["status"] == "error":
            print(f"错误响应: {response.get('message', '未知错误')}")
            return None
            
        if "result" in response and isinstance(response["result"], dict):
            if "name" in response["result"]:
                return response["result"]["name"]
            if "object" in response["result"]:
                return response["result"]["object"]
                
        if "name" in response:
            return response["name"]
    
    print("无法从响应中提取对象名称")
    return None
```

### 响应检查

```python
def check_response(response, operation_name):
    """检查响应状态，如有错误则打印"""
    if not response:
        print(f"警告: {operation_name} - 响应为空")
        return False
    
    if isinstance(response, dict):
        if "error" in response:
            print(f"错误: {operation_name} - {response['error']}")
            return False
        
        if "status" in response and response["status"] == "error":
            print(f"错误: {operation_name} - {response.get('message', '未知错误')}")
            return False
    
    return True
```

### 带重试的对象创建

```python
def create_object_with_retry(client, obj_type, name, location, scale=None, max_retries=3):
    """创建对象并在失败时重试"""
    params = {"type": obj_type, "name": name, "location": location}
    if scale:
        params["scale"] = scale
        
    for attempt in range(max_retries):
        response = client.send_command("create_object", params)
        obj_name = get_object_name(response)
        
        if obj_name:
            # 验证对象是否真的存在
            verify = client.send_command("get_object_info", {"name": obj_name})
            if verify.get("status") == "success":
                print(f"成功创建对象: {obj_name} (尝试 {attempt+1})")
                return obj_name
        
        print(f"创建 {name} 尝试 {attempt+1}/{max_retries} 失败，正在重试...")
        time.sleep(0.5)  # 短暂等待后重试
    
    print(f"无法创建 {name}，已达到最大重试次数")
    return None
```

## 故障排除

### 1. 用于调试的服务器信息

如果遇到不明确的错误，可以获取服务器信息进行诊断：

```python
info = client.get_simple_info()
print(f"Blender版本: {info.get('result', {}).get('blender_version')}")
```

### 2. 打印详细日志

启用调试模式并打印详细日志：

```python
DEBUG = True

def debug_print(message):
    if DEBUG:
        print(f"[DEBUG] {message}")
        
# 使用
debug_print(f"响应: {json.dumps(response, ensure_ascii=False)}")
```

### 3. 对象合并问题

如果`join_objects`操作失败，检查：

- 所有对象是否存在
- 对象类型是否兼容（通常需要是MESH类型）
- 目标对象是否在objects列表中

### 4. 高级照明问题

使用`advanced_lighting`时，确保：

- 始终指定`light_type`参数
- 对于AREA类型，不要传递不支持的参数（如rotation和size）
- 参数值的类型必须正确（例如，location必须是三元素列表或元组）

### 5. 场景同步问题

有时Blender内部状态可能与API响应不同步。如遇此问题：

- 在关键操作之间添加短暂延迟（`time.sleep(0.1)`）
- 使用`get_scene_info`检查整个场景状态
- 尝试将复杂操作分解为更简单的步骤 
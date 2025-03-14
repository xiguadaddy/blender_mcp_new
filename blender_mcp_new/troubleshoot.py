#!/usr/bin/env python3
"""
BlenderMCP故障排除工具
提供了一系列功能来诊断和修复BlenderMCP插件中的常见问题
"""

import os
import sys
import socket
import shutil
import importlib
import traceback

# Blender相关导入可能会失败，如果在Blender外运行
try:
    import bpy
    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False
    print("警告: 未在Blender环境中运行，部分功能将不可用")

def print_section(title):
    """打印带格式的章节标题"""
    print("\n" + "="*50)
    print(f"  {title}")
    print("="*50)

def check_port(host='localhost', port=9876):
    """检查端口是否可用"""
    print(f"检查端口: {host}:{port}")
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.bind((host, port))
            print(f"✅ 端口 {host}:{port} 可用")
            return True
    except socket.error as e:
        print(f"❌ 端口 {host}:{port} 不可用: {e}")
        return False
        
def check_multiple_ports():
    """检查多个常用主机和端口组合"""
    print_section("端口可用性检查")
    
    configs = [
        ('localhost', 9876),
        ('127.0.0.1', 9876),
        ('0.0.0.0', 9876),
        ('localhost', 9877),
        ('127.0.0.1', 9877),
        ('0.0.0.0', 9877),
    ]
    
    available_configs = []
    for host, port in configs:
        if check_port(host, port):
            available_configs.append((host, port))
        print("-"*50)
    
    if available_configs:
        print("\n✅ 找到可用配置:")
        for host, port in available_configs:
            print(f"  - {host}:{port}")
        print(f"\n建议: 尝试使用 {available_configs[0][0]}:{available_configs[0][1]} 配置")
    else:
        print("\n❌ 没有找到可用的端口配置")
        print("建议: 请关闭其他使用这些端口的程序或选择其他端口")

def check_addon_files():
    """检查插件文件是否存在和完整"""
    print_section("插件文件检查")
    
    # 检查是否在Blender中运行
    if not IN_BLENDER:
        print("❌ 未在Blender环境中运行，无法检查插件文件")
        return False
    
    # 确定插件目录
    addon_dirs = []
    for path in bpy.utils.script_paths(subdir="addons"):
        addon_dirs.append(path)
        if os.path.isdir(os.path.join(path, "blender_mcp")):
            addon_dirs.append(os.path.join(path, "blender_mcp"))
    
    if not addon_dirs:
        print("❌ 无法找到Blender插件目录")
        return False
    
    print(f"找到以下插件目录:")
    for directory in addon_dirs:
        print(f"  - {directory}")
        
    # 检查必要的文件
    blender_mcp_found = False
    for directory in addon_dirs:
        if os.path.isdir(os.path.join(directory, "blender_mcp")):
            plugin_dir = os.path.join(directory, "blender_mcp")
            blender_mcp_found = True
        elif os.path.basename(directory) == "blender_mcp":
            plugin_dir = directory
            blender_mcp_found = True
        else:
            continue
            
        print(f"\n检查BlenderMCP目录: {plugin_dir}")
        
        required_files = ["__init__.py", "server.py", "response_utils.py", "task_manager.py"]
        all_files_exist = True
        
        for filename in required_files:
            filepath = os.path.join(plugin_dir, filename)
            if os.path.exists(filepath):
                print(f"✅ 文件存在: {filename}")
            else:
                print(f"❌ 缺少文件: {filename}")
                all_files_exist = False
                
        if all_files_exist:
            print("\n✅ 所有必要的文件都存在")
        else:
            print("\n❌ 缺少一些必要的文件")
            print("建议: 重新安装插件")
            
    if not blender_mcp_found:
        print("\n❌ 未找到BlenderMCP目录")
        print("建议: 插件可能未正确安装，请重新安装")
        return False
        
    return True

def reinstall_plugin():
    """重新安装插件"""
    print_section("插件重新安装")
    
    if not IN_BLENDER:
        print("❌ 未在Blender环境中运行，无法重新安装插件")
        return False
        
    # 确定当前脚本的路径
    current_file = os.path.abspath(__file__)
    base_dir = os.path.dirname(current_file)
    
    # 检查安装脚本是否存在
    install_script = os.path.join(base_dir, "install_blender_server.py")
    if not os.path.exists(install_script):
        install_script = os.path.join(base_dir, "install_simple.py")
        if not os.path.exists(install_script):
            print("❌ 找不到安装脚本")
            return False
    
    print(f"找到安装脚本: {install_script}")
    
    # 导入并运行安装脚本
    try:
        print("导入安装脚本...")
        spec = importlib.util.spec_from_file_location("install_script", install_script)
        install_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(install_module)
        
        print("执行安装...")
        result = install_module.main()
        
        if result:
            print("\n✅ 插件重新安装成功")
            print("请重启Blender并在首选项中启用插件")
        else:
            print("\n❌ 插件重新安装失败")
            
        return result
    except Exception as e:
        print(f"❌ 安装过程中发生错误: {str(e)}")
        traceback.print_exc()
        return False

def check_preferences():
    """检查插件首选项设置"""
    print_section("插件首选项检查")
    
    if not IN_BLENDER:
        print("❌ 未在Blender环境中运行，无法检查首选项")
        return
        
    try:
        # 检查插件是否启用
        addon_enabled = False
        for addon in bpy.context.preferences.addons:
            if addon.module == "blender_mcp":
                addon_enabled = True
                break
                
        if not addon_enabled:
            print("❌ BlenderMCP插件未启用")
            print("建议: 在Blender首选项中启用插件 Edit > Preferences > Add-ons")
            return
            
        # 获取插件首选项
        try:
            addon_prefs = bpy.context.preferences.addons["blender_mcp"].preferences
            print("插件首选项:")
            print(f"  - 主机: {addon_prefs.host}")
            print(f"  - 端口: {addon_prefs.port}")
            print(f"  - 调试模式: {'启用' if addon_prefs.debug else '禁用'}")
            
            # 检查端口配置
            if check_port(addon_prefs.host, addon_prefs.port):
                print(f"\n✅ 当前配置的端口 {addon_prefs.host}:{addon_prefs.port} 可用")
            else:
                print(f"\n❌ 当前配置的端口 {addon_prefs.host}:{addon_prefs.port} 不可用")
                print("建议: 更改端口或关闭使用该端口的其他程序")
                
            # 建议启用调试模式
            if not addon_prefs.debug:
                print("\n建议: 启用调试模式以获取更详细的错误信息")
        except Exception as e:
            print(f"❌ 无法访问插件首选项: {str(e)}")
            
    except Exception as e:
        print(f"❌ 检查首选项时发生错误: {str(e)}")
        traceback.print_exc()

def test_import_modules():
    """测试导入服务器模块"""
    print_section("模块导入测试")
    
    if not IN_BLENDER:
        print("❌ 未在Blender环境中运行，无法测试模块导入")
        return
        
    try:
        # 尝试导入模块
        modules = [
            "blender_mcp.response_utils",
            "blender_mcp.task_manager",
            "blender_mcp.server"
        ]
        
        for module_name in modules:
            try:
                print(f"尝试导入: {module_name}")
                module = importlib.import_module(module_name)
                print(f"✅ 成功导入模块: {module_name}")
            except ImportError as e:
                print(f"❌ 无法导入模块: {module_name}")
                print(f"  错误: {str(e)}")
            except Exception as e:
                print(f"❌ 导入模块时发生未知错误: {module_name}")
                print(f"  错误: {str(e)}")
                traceback.print_exc()
    except Exception as e:
        print(f"❌ 测试模块导入时发生错误: {str(e)}")
        traceback.print_exc()

def run_all_checks():
    """运行所有诊断检查"""
    print_section("BlenderMCP故障排除")
    print("正在运行所有诊断检查...")
    
    check_multiple_ports()
    check_addon_files()
    check_preferences()
    test_import_modules()
    
    print("\n完成所有检查。如果需要重新安装插件，请运行:")
    print("reinstall_plugin()")

if __name__ == "__main__":
    # 如果直接运行脚本（非导入），执行所有检查
    run_all_checks()
else:
    # 如果导入到另一个脚本中，打印使用说明
    print("""
BlenderMCP故障排除工具已加载。可用的功能:
- check_multiple_ports() - 检查端口可用性
- check_addon_files() - 检查插件文件是否存在
- check_preferences() - 检查插件首选项设置
- test_import_modules() - 测试导入服务器模块
- reinstall_plugin() - 重新安装插件
- run_all_checks() - 运行所有检查

请在Blender的Python控制台中调用这些函数来诊断问题。
""") 
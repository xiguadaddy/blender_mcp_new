#!/usr/bin/env python3
"""
Blender MCP 服务器插件安装脚本
将服务器组件安装为Blender插件
"""

import os
import sys
import shutil
from pathlib import Path

def main():
    """安装BlenderMCP插件到用户的Blender插件目录"""
    print("开始安装BlenderMCP服务器插件...")
    
    # 确定平台
    if sys.platform == "darwin":  # macOS
        plugin_dir = install_macos()
    elif sys.platform == "win32":  # Windows
        plugin_dir = install_windows()
    elif sys.platform.startswith("linux"):  # Linux
        plugin_dir = install_linux()
    else:
        print(f"不支持的操作系统: {sys.platform}")
        return False
    
    if plugin_dir:
        print(f"插件安装成功: {plugin_dir}")
        print("请在Blender中启用插件: Edit > Preferences > Add-ons > 搜索'BlenderMCP'")
        return True
    else:
        print("插件安装失败")
        return False

def install_macos():
    """在macOS上安装插件"""
    # 查找用户的Blender插件目录 - 尝试多个版本
    for blender_version in ["4.3", "4.2", "4.1", "4.0", "3.6", "3.5", "3.4", "3.3", "3.2", "3.1", "3.0", "2.93"]:
        user_addon_dir = os.path.expanduser(f"~/Library/Application Support/Blender/{blender_version}/scripts/addons")
        if os.path.exists(os.path.dirname(user_addon_dir)):
            break
    else:
        # 如果没找到任何版本目录，使用最新版本并创建目录
        user_addon_dir = os.path.expanduser("~/Library/Application Support/Blender/4.3/scripts/addons")
        os.makedirs(os.path.dirname(user_addon_dir), exist_ok=True)
    
    # 创建插件目录
    os.makedirs(user_addon_dir, exist_ok=True)
    plugin_dir = os.path.join(user_addon_dir, "blender_mcp")
    os.makedirs(plugin_dir, exist_ok=True)
    
    # 复制文件
    copy_plugin_files(plugin_dir)
    
    return plugin_dir

def install_windows():
    """在Windows上安装插件"""
    # 查找用户的Blender插件目录 - 尝试多个版本
    appdata = os.environ.get("APPDATA", "")
    for blender_version in ["4.3", "4.2", "4.1", "4.0", "3.6", "3.5", "3.4", "3.3", "3.2", "3.1", "3.0", "2.93"]:
        user_addon_dir = os.path.join(appdata, "Blender Foundation", "Blender", blender_version, "scripts", "addons")
        if os.path.exists(os.path.dirname(user_addon_dir)):
            break
    else:
        # 如果没找到任何版本目录，使用最新版本并创建目录
        user_addon_dir = os.path.join(appdata, "Blender Foundation", "Blender", "4.3", "scripts", "addons")
        os.makedirs(os.path.dirname(user_addon_dir), exist_ok=True)
    
    # 创建插件目录
    os.makedirs(user_addon_dir, exist_ok=True)
    plugin_dir = os.path.join(user_addon_dir, "blender_mcp")
    os.makedirs(plugin_dir, exist_ok=True)
    
    # 复制文件
    copy_plugin_files(plugin_dir)
    
    return plugin_dir

def install_linux():
    """在Linux上安装插件"""
    # 查找用户的Blender插件目录 - 尝试多个版本
    for blender_version in ["4.3", "4.2", "4.1", "4.0", "3.6", "3.5", "3.4", "3.3", "3.2", "3.1", "3.0", "2.93"]:
        user_addon_dir = os.path.expanduser(f"~/.config/blender/{blender_version}/scripts/addons")
        if os.path.exists(os.path.dirname(user_addon_dir)):
            break
    else:
        # 如果没找到任何版本目录，使用最新版本并创建目录
        user_addon_dir = os.path.expanduser("~/.config/blender/4.3/scripts/addons")
        os.makedirs(os.path.dirname(user_addon_dir), exist_ok=True)
    
    # 创建插件目录
    os.makedirs(user_addon_dir, exist_ok=True)
    plugin_dir = os.path.join(user_addon_dir, "blender_mcp")
    os.makedirs(plugin_dir, exist_ok=True)
    
    # 复制文件
    copy_plugin_files(plugin_dir)
    
    return plugin_dir

def copy_plugin_files(plugin_dir):
    """复制插件文件到目标目录"""
    try:
        # 获取当前脚本的目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        server_dir = os.path.join(current_dir, "server")
        
        # 复制所有需要的Python文件
        required_files = ["server.py", "response_utils.py", "task_manager.py"]
        for file_name in required_files:
            source_file = os.path.join(server_dir, file_name)
            dest_file = os.path.join(plugin_dir, file_name)
            
            if os.path.exists(source_file):
                shutil.copy2(source_file, dest_file)
                print(f"已复制 {file_name} 到 {dest_file}")
            else:
                print(f"错误: 找不到源文件: {source_file}")
                return False
        
        # 创建__init__.py文件
        init_code = """
\"\"\"
BlenderMCP 服务器插件
允许通过网络API远程控制Blender
\"\"\"

bl_info = {
    "name": "BlenderMCP Server",
    "author": "BlenderMCP Team",
    "version": (0, 2, 0),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > BlenderMCP",
    "description": "通过网络API远程控制Blender",
    "warning": "",
    "doc_url": "https://github.com/xiguadaddy/blender_mcp_new",
    "category": "3D View",
}

import bpy
from bpy.props import BoolProperty, StringProperty, IntProperty
from bpy.types import Panel, Operator, AddonPreferences

# 首先导入辅助模块，避免循环导入
from . import response_utils
from . import task_manager
# 然后导入主服务器模块
from . import server

# 服务器实例
mcp_server = None

# 插件首选项
class BlenderMCPPreferences(AddonPreferences):
    bl_idname = __name__
    
    host: StringProperty(
        name="主机",
        description="服务器主机地址",
        default="localhost"
    )
    
    port: IntProperty(
        name="端口",
        description="服务器端口",
        default=9876,
        min=1024,
        max=65535
    )
    
    debug: BoolProperty(
        name="调试模式",
        description="启用详细日志输出",
        default=False
    )
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "host")
        layout.prop(self, "port")
        layout.prop(self, "debug")

# 启动服务器操作
class BLENDERMCP_OT_start_server(Operator):
    bl_idname = "blendermcp.start_server"
    bl_label = "启动服务器"
    bl_description = "启动BlenderMCP服务器"
    
    def execute(self, context):
        global mcp_server
        
        # 获取插件首选项
        addon_prefs = context.preferences.addons[__name__].preferences
        host = addon_prefs.host
        port = addon_prefs.port
        debug = addon_prefs.debug
        
        # 如果服务器已经运行，先停止
        if mcp_server and mcp_server.is_running():
            mcp_server.stop()
        
        # 创建并启动服务器
        try:
            mcp_server = server.BlenderMCPServer(host=host, port=port, debug=debug)
            success = mcp_server.start()
            
            if success.get("status", "") == "success":
                self.report({'INFO'}, f"BlenderMCP服务器已启动在 {host}:{port}")
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "无法启动BlenderMCP服务器")
                return {'CANCELLED'}
                
        except Exception as e:
            self.report({'ERROR'}, f"启动服务器时出错: {str(e)}")
            return {'CANCELLED'}

# 停止服务器操作
class BLENDERMCP_OT_stop_server(Operator):
    bl_idname = "blendermcp.stop_server"
    bl_label = "停止服务器"
    bl_description = "停止BlenderMCP服务器"
    
    def execute(self, context):
        global mcp_server
        
        if mcp_server:
            try:
                mcp_server.stop()
                self.report({'INFO'}, "BlenderMCP服务器已停止")
            except Exception as e:
                self.report({'ERROR'}, f"停止服务器时出错: {str(e)}")
        else:
            self.report({'WARNING'}, "服务器未运行")
            
        return {'FINISHED'}

# UI面板
class BLENDERMCP_PT_panel(Panel):
    bl_label = "BlenderMCP 服务器"
    bl_idname = "BLENDERMCP_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BlenderMCP"
    
    def draw(self, context):
        layout = self.layout
        
        # 服务器状态
        global mcp_server
        is_running = mcp_server and mcp_server.is_running()
        
        # 显示状态
        status_box = layout.box()
        status_row = status_box.row()
        status_row.label(text="状态: " + ("运行中" if is_running else "已停止"))
        
        # 服务器设置
        addon_prefs = context.preferences.addons[__name__].preferences
        settings_box = layout.box()
        settings_box.label(text="服务器设置:")
        settings_box.prop(addon_prefs, "host")
        settings_box.prop(addon_prefs, "port")
        settings_box.prop(addon_prefs, "debug")
        
        # 控制按钮
        control_box = layout.box()
        if is_running:
            control_box.operator("blendermcp.stop_server")
        else:
            control_box.operator("blendermcp.start_server")

# 注册/注销插件
classes = (
    BlenderMCPPreferences,
    BLENDERMCP_OT_start_server,
    BLENDERMCP_OT_stop_server,
    BLENDERMCP_PT_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    global mcp_server
    
    # 停止服务器
    if mcp_server and mcp_server.is_running():
        mcp_server.stop()
    
    # 注销类
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
"""
        
        init_py = os.path.join(plugin_dir, "__init__.py")
        with open(init_py, "w", encoding="utf-8") as f:
            f.write(init_code)
        print(f"已创建 __init__.py 在 {init_py}")
        return True
    except Exception as e:
        print(f"复制文件时出错: {str(e)}")
        return False

if __name__ == "__main__":
    main() 
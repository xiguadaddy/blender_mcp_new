#!/usr/bin/env python3
"""
Blender MCP 服务器插件安装脚本 - 改进版
将服务器组件安装为Blender插件

使用方法:
1. 启动Blender
2. 打开Text Editor窗口
3. 打开此文件
4. 点击"Run Script"按钮
5. 查看控制台输出
"""

import os
import sys
import shutil
import traceback

def get_blender_version():
    """获取Blender版本"""
    try:
        import bpy
        version = bpy.app.version
        return ".".join(map(str, version[:2]))  # 例如：4.3 或 2.93
    except ImportError:
        print("警告: 未在Blender环境中运行，将使用默认版本4.3")
        return "4.3"

def get_platform_addon_path():
    """根据平台获取Blender插件路径"""
    print(f"检测平台: {sys.platform}")
    blender_version = get_blender_version()
    print(f"检测到Blender版本: {blender_version}")
    
    if sys.platform == "darwin":  # macOS
        base_path = os.path.expanduser(f"~/Library/Application Support/Blender/{blender_version}/scripts/addons")
    elif sys.platform == "win32":  # Windows
        appdata = os.environ.get("APPDATA", "")
        base_path = os.path.join(appdata, "Blender Foundation", "Blender", blender_version, "scripts", "addons")
    elif sys.platform.startswith("linux"):  # Linux
        base_path = os.path.expanduser(f"~/.config/blender/{blender_version}/scripts/addons")
    else:
        print(f"不支持的操作系统: {sys.platform}")
        return None
    
    print(f"插件路径: {base_path}")
    return base_path

def create_init_file(plugin_dir):
    """创建__init__.py文件，包含插件定义"""
    init_code = """\"\"\"
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
import traceback
import sys
import logging
from bpy.props import BoolProperty, StringProperty, IntProperty
from bpy.types import Panel, Operator, AddonPreferences

# 设置日志
addon_logger = logging.getLogger("BlenderMCP")
addon_logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
addon_logger.addHandler(console_handler)
addon_logger.info("BlenderMCP插件初始化中...")

# 首先导入辅助模块，避免循环导入
try:
    from . import response_utils
    from . import task_manager
    # 然后导入主服务器模块
    from . import server
    addon_logger.info("所有模块导入成功")
except Exception as e:
    addon_logger.error(f"导入模块时出错: {str(e)}")
    addon_logger.error(traceback.format_exc())

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
        default=True  # 默认启用调试模式，帮助排查问题
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
        
        try:
            # 获取插件首选项
            addon_prefs = context.preferences.addons[__name__].preferences
            host = addon_prefs.host
            port = addon_prefs.port
            debug = addon_prefs.debug
            
            addon_logger.debug(f"准备启动服务器: {host}:{port}, 调试模式: {debug}")
            
            # 如果服务器已经运行，先停止
            if mcp_server and mcp_server.is_running():
                addon_logger.debug("服务器已在运行，将先停止")
                mcp_server.stop()
            
            # 创建并启动服务器
            try:
                addon_logger.debug("创建服务器实例")
                mcp_server = server.BlenderMCPServer(host=host, port=port, debug=debug)
                
                addon_logger.debug("启动服务器")
                success = mcp_server.start()
                
                if success.get("status", "") == "success":
                    addon_logger.info(f"服务器成功启动在 {host}:{port}")
                    self.report({'INFO'}, f"BlenderMCP服务器已启动在 {host}:{port}")
                    return {'FINISHED'}
                else:
                    error_msg = success.get("message", "未知错误")
                    addon_logger.error(f"启动服务器失败: {error_msg}")
                    self.report({'ERROR'}, f"无法启动BlenderMCP服务器: {error_msg}")
                    return {'CANCELLED'}
                    
            except Exception as e:
                addon_logger.error(f"启动服务器时发生异常: {str(e)}")
                addon_logger.error(traceback.format_exc())
                self.report({'ERROR'}, f"启动服务器时出错: {str(e)}")
                return {'CANCELLED'}
                
        except Exception as e:
            addon_logger.error(f"执行启动操作时发生异常: {str(e)}")
            addon_logger.error(traceback.format_exc())
            self.report({'ERROR'}, f"操作执行错误: {str(e)}")
            return {'CANCELLED'}

# 停止服务器操作
class BLENDERMCP_OT_stop_server(Operator):
    bl_idname = "blendermcp.stop_server"
    bl_label = "停止服务器"
    bl_description = "停止BlenderMCP服务器"
    
    def execute(self, context):
        global mcp_server
        
        try:
            if mcp_server:
                try:
                    addon_logger.debug("停止服务器")
                    mcp_server.stop()
                    addon_logger.info("服务器已停止")
                    self.report({'INFO'}, "BlenderMCP服务器已停止")
                except Exception as e:
                    addon_logger.error(f"停止服务器时出错: {str(e)}")
                    addon_logger.error(traceback.format_exc())
                    self.report({'ERROR'}, f"停止服务器时出错: {str(e)}")
            else:
                addon_logger.warning("服务器未运行")
                self.report({'WARNING'}, "服务器未运行")
            
            return {'FINISHED'}
        except Exception as e:
            addon_logger.error(f"执行停止操作时发生异常: {str(e)}")
            addon_logger.error(traceback.format_exc())
            self.report({'ERROR'}, f"操作执行错误: {str(e)}")
            return {'CANCELLED'}

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
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"注册类 {cls.__name__} 时出错: {str(e)}")
            traceback.print_exc()
            raise

def unregister():
    global mcp_server
    
    # 停止服务器
    if mcp_server and mcp_server.is_running():
        try:
            mcp_server.stop()
        except Exception as e:
            print(f"停止服务器时出错: {str(e)}")
    
    # 注销类
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"注销类 {cls.__name__} 时出错: {str(e)}")

def install_plugin():
    """安装BlenderMCP插件"""
    try:
        print("="*60)
        print("  BlenderMCP 服务器插件安装")
        print("="*60)
        
        # 1. 获取Blender插件目录
        plugin_base = get_platform_addon_path()
        if not plugin_base:
            return False
        
        # 2. 创建插件目录
        os.makedirs(plugin_base, exist_ok=True)
        plugin_dir = os.path.join(plugin_base, "blender_mcp")
        if os.path.exists(plugin_dir):
            print(f"⚠️ 插件目录已存在: {plugin_dir}")
            print("将删除现有目录并重新安装...")
            try:
                shutil.rmtree(plugin_dir)
                print("✅ 移除旧插件目录成功")
            except Exception as e:
                print(f"❌ 无法移除旧插件目录: {str(e)}")
                print("请尝试手动删除目录后再运行安装脚本")
                return False
        
        os.makedirs(plugin_dir, exist_ok=True)
        print(f"✅ 创建插件目录: {plugin_dir}")
        
        # 3. 查找源文件
        current_dir = os.path.dirname(os.path.abspath(__file__))
        server_dir = os.path.join(current_dir, "server")
        
        if not os.path.exists(server_dir):
            print(f"⚠️ 服务器源目录不存在: {server_dir}")
            print("尝试在当前目录查找服务器文件...")
            server_dir = current_dir
        
        print(f"源文件目录: {server_dir}")
        
        # 4. 复制所需文件
        required_files = ["server.py", "response_utils.py", "task_manager.py"]
        all_files_copied = True
        
        for file_name in required_files:
            source_file = os.path.join(server_dir, file_name)
            dest_file = os.path.join(plugin_dir, file_name)
            
            if os.path.exists(source_file):
                shutil.copy2(source_file, dest_file)
                print(f"✅ 已复制 {file_name}")
            else:
                print(f"❌ 找不到源文件: {source_file}")
                all_files_copied = False
        
        if not all_files_copied:
            print("❌ 有一些必要的文件未找到, 安装可能不完整")
            
        # 5. 创建__init__.py文件
        if create_init_file(plugin_dir):
            print("✅ 创建插件初始化文件成功")
        else:
            print("❌ 创建插件初始化文件失败")
            return False
        
        # 6. 完成安装
        print("\n"+"="*60)
        print("✅ BlenderMCP 插件安装完成!")
        print(f"📁 插件目录: {plugin_dir}")
        print("\n🔧 请在Blender中启用插件:")
        print("   Edit > Preferences > Add-ons > 搜索 'BlenderMCP'")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 安装过程中出错: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """主函数, 执行安装"""
    result = install_plugin()
    if not result:
        print("\n❌ 安装失败. 请查看上面的错误信息.")
        return False
    return True

if __name__ == "__main__":
    main() 
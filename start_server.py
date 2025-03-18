import os
import sys
import subprocess
import platform

# 设置工作目录
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# 根据操作系统确定虚拟环境路径
system = platform.system()
venv_dir = os.path.join(script_dir, ".venv")

if system == "Windows":
    python_executable = os.path.join(venv_dir, "Scripts", "python.exe")
else:  # Linux, macOS等Unix类系统
    python_executable = os.path.join(venv_dir, "bin", "python")

# 如果虚拟环境不存在，使用系统Python
if not os.path.exists(python_executable):
    print(f"虚拟环境Python未找到: {python_executable}")
    print("使用系统Python...")
    python_executable = sys.executable

# MCP服务器脚本路径
script_path = os.path.join("mcp-server", "main.py")

print(f"使用Python解释器: {python_executable}")
print(f"启动MCP服务器: {script_path}")

# 启动服务器，并确保输出被转发
try:
    process = subprocess.Popen(
        [python_executable, script_path], 
        stdout=sys.stdout, 
        stderr=sys.stderr
    )
    
    # 等待进程完成
    process.wait()
    
except Exception as e:
    print(f"启动服务器时出错: {e}")
    sys.exit(1)

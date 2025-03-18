import os
import sys
import subprocess

# 设置工作目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 使用虚拟环境的Python
python_executable = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "Scripts", "python.exe")
script_path = os.path.join("mcp-server", "main.py")

# 启动服务器，并确保输出被转发
process = subprocess.Popen([python_executable, script_path], 
                          stdout=sys.stdout, 
                          stderr=sys.stderr)

# 等待进程完成
process.wait()

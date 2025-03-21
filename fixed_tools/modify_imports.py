#!/usr/bin/env python
"""
修改导入语句脚本 - 将相对导入从 .registry 改为 ..registry
"""

import os
import re
import glob
from pathlib import Path

def modify_import_statement(file_path):
    """修改文件中的导入语句"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找导入语句并替换
    old_import = r'from \.registry import register_tool'
    new_import = 'from ..registry import register_tool'
    
    if re.search(old_import, content):
        modified_content = re.sub(old_import, new_import, content)
        
        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        
        return True
    
    return False

def process_all_tool_files():
    """处理所有工具类文件"""
    # 从上一层目录的handlers/tools目录开始
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "blender-addon", "handlers", "tools")
    
    # 获取所有工具Python文件
    tool_files = []
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.py') and not file.startswith('__') and any(sub in root for sub in ["_tools"]):
                tool_files.append(os.path.join(root, file))
    
    print(f"找到 {len(tool_files)} 个工具文件")
    
    modified_count = 0
    
    for file_path in tool_files:
        if modify_import_statement(file_path):
            print(f"已修改导入语句: {file_path}")
            modified_count += 1
    
    print(f"\n修改完成: 共修改了 {modified_count} 个文件的导入语句")

if __name__ == "__main__":
    print("开始修改导入语句...")
    process_all_tool_files() 
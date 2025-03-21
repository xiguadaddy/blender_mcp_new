#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复Python和JSON文件中JavaScript风格的布尔值
将所有"default": true替换为"default": True (Python)
将所有"default": false替换为"default": False (Python)
注意：JSON文件中的布尔值保持小写
"""

import os
import re
import glob

def fix_boolean_values():
    # 编译匹配JavaScript布尔值的正则表达式 - 双引号版本
    pattern_true_double = re.compile(r'"default"[ \t]*:[ \t]*true\b')
    pattern_false_double = re.compile(r'"default"[ \t]*:[ \t]*false\b')
    
    # 编译匹配JavaScript布尔值的正则表达式 - 单引号版本
    pattern_true_single = re.compile(r"'default'[ \t]*:[ \t]*true\b")
    pattern_false_single = re.compile(r"'default'[ \t]*:[ \t]*false\b")
    
    # 查找所有Python文件
    py_files = glob.glob('./handlers/tools/**/*.py', recursive=True)
    
    # 查找所有JSON文件
    json_files = glob.glob('../../mcp-server/tools/schemas/*.json', recursive=True)
    
    # 计数器
    total_py_files = 0
    total_json_files = 0
    modified_py_files = 0
    modified_json_files = 0
    
    # 检查已知存在问题的文件
    known_problem_files = [
        './handlers/tools/animation_tools/create_armature.py',
        './handlers/tools/animation_tools/set_frame_range.py',
        './handlers/tools/animation_tools/create_motion_path.py',
        './handlers/tools/mesh_tools/set_vertex_position.py'
    ]
    
    for file_path in known_problem_files:
        if os.path.exists(file_path):
            print(f"检查已知问题文件: {file_path}")
    
    # 遍历所有找到的Python文件
    for py_file in py_files:
        total_py_files += 1
        
        try:
            # 读取文件内容
            with open(py_file, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
            
            # 检查是否包含JavaScript布尔值
            has_js_true_double = pattern_true_double.search(content) is not None
            has_js_false_double = pattern_false_double.search(content) is not None
            has_js_true_single = pattern_true_single.search(content) is not None
            has_js_false_single = pattern_false_single.search(content) is not None
            
            # 如果包含JavaScript布尔值，修复并保存
            if has_js_true_double or has_js_false_double or has_js_true_single or has_js_false_single:
                print(f"修复Python文件中的JavaScript布尔值: {py_file}")
                
                # 打印匹配到的值
                if has_js_true_double:
                    matches = pattern_true_double.findall(content)
                    print(f"  - 找到双引号true: {matches}")
                
                if has_js_false_double:
                    matches = pattern_false_double.findall(content)
                    print(f"  - 找到双引号false: {matches}")
                
                if has_js_true_single:
                    matches = pattern_true_single.findall(content)
                    print(f"  - 找到单引号true: {matches}")
                
                if has_js_false_single:
                    matches = pattern_false_single.findall(content)
                    print(f"  - 找到单引号false: {matches}")
                
                # 进行替换 - 对Python文件使用Python的True/False
                modified_content = content
                modified_content = pattern_true_double.sub('"default": True', modified_content)
                modified_content = pattern_false_double.sub('"default": False', modified_content)
                modified_content = pattern_true_single.sub("'default': True", modified_content)
                modified_content = pattern_false_single.sub("'default': False", modified_content)
                
                # 保存修改后的文件
                with open(py_file, 'w', encoding='utf-8') as file:
                    file.write(modified_content)
                
                modified_py_files += 1
                
        except Exception as e:
            print(f"处理Python文件时出错 {py_file}: {str(e)}")
    
    # 检查JSON文件中的JavaScript布尔值
    # 注意：JSON中布尔值应该保持小写
    for json_file in json_files:
        total_json_files += 1
        
        try:
            # 查看文件是否存在
            if not os.path.exists(json_file):
                print(f"JSON文件不存在: {json_file}")
                continue
                
            # 读取文件内容
            with open(json_file, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
            
            # 检查JSON文件是否正确（布尔值应为小写）
            # 在JSON文件中，我们不需要替换任何内容，只需确认格式是否正确
            has_js_true = '"default": true' in content
            has_js_false = '"default": false' in content
            
            # JSON文件中，true/false应保持小写
            if has_js_true or has_js_false:
                print(f"检查JSON文件: {json_file} - 布尔值格式正确")
            
        except Exception as e:
            print(f"处理JSON文件时出错 {json_file}: {str(e)}")
    
    print("\n处理完成！")
    print(f"共处理 {total_py_files} 个Python文件")
    print(f"修复了 {modified_py_files} 个Python文件中的JavaScript布尔值")
    print(f"检查了 {total_json_files} 个JSON文件")

if __name__ == "__main__":
    fix_boolean_values() 
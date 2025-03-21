import os
import re
import glob
import sys
import traceback
import argparse

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="自动为Blender工具类添加注册代码",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--tools-dir", 
        dest="tools_dir",
        help="指定工具目录的路径，如果不提供，脚本将自动尝试检测"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="仅检查要进行的修改，不实际写入文件"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细输出信息"
    )
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_args()
    
    try:
        # 检测环境 - 可以是独立运行或在Blender中作为插件运行
        try:
            import bpy
            # 如果能导入bpy，说明在Blender环境中运行
            in_blender = True
            print("在Blender环境中运行")
        except ImportError:
            in_blender = False
            print("作为独立脚本运行")
            
        # 获取路径
        if args.tools_dir:
            tools_dir = args.tools_dir
            print(f"使用指定的工具目录: {tools_dir}")
        elif in_blender:
            # 在Blender中，脚本可能是作为插件的一部分运行
            # 尝试获取插件目录
            addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            tools_dir = os.path.join(addon_dir, "handlers", "tools")
        else:
            # 独立运行
            base_dir = os.path.dirname(os.path.abspath(__file__))
            addon_dir = os.path.normpath(os.path.join(base_dir, ".."))
            tools_dir = os.path.join(addon_dir, "blender-addon", "handlers", "tools")
            
            # 如果路径不存在，尝试其他常见布局
            if not os.path.exists(tools_dir):
                alternative_tools_dir = os.path.join(addon_dir, "handlers", "tools")
                if os.path.exists(alternative_tools_dir):
                    tools_dir = alternative_tools_dir
                    print(f"使用替代工具目录: {tools_dir}")
        
        if not os.path.exists(tools_dir):
            print(f"错误: 工具目录不存在: {tools_dir}")
            print(f"当前目录: {os.getcwd()}")
            print(f"脚本位置: {__file__}")
            return
        
        print(f"工具目录: {tools_dir}")
        
        # 获取所有工具类文件
        tool_files = []
        for root, dirs, files in os.walk(tools_dir):
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    tool_files.append(os.path.join(root, file))
        
        if not tool_files:
            print(f"警告: 没有找到任何工具类文件")
            return
            
        print(f"找到 {len(tool_files)} 个工具类文件")
        
        # 正则表达式模式，用于匹配工具类声明
        class_pattern = re.compile(r'class\s+([A-Za-z0-9_]+)\s*\(\s*BaseToolHandler\s*\)\s*:')
        registration_pattern = re.compile(r'register_tool\s*\(\s*[A-Za-z0-9_]+\(\s*\)\s*\)')
        
        count_modified = 0
        count_already_registered = 0
        count_errors = 0
        
        # 处理每个文件
        for file_path in tool_files:
            try:
                if args.verbose:
                    print(f"处理文件: {file_path}")
                    
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 寻找类名
                matches = class_pattern.findall(content)
                if not matches:
                    if args.verbose:
                        print(f"  跳过: 没有找到工具处理器类")
                    continue  # 没有找到工具处理器类
                
                # 检查是否已经有注册代码
                if registration_pattern.search(content):
                    print(f"{file_path}: 已经包含注册代码")
                    count_already_registered += 1
                    continue
                
                # 为每个找到的类添加注册代码
                added_imports = False
                modified_content = content
                
                # 添加导入语句
                if "from ..registry import register_tool" not in content:
                    first_import_match = re.search(r'(^from|^import)', content, re.MULTILINE)
                    if first_import_match:
                        # 在第一个导入语句之后添加
                        import_pos = first_import_match.start()
                        lines = content[:import_pos].split('\n')
                        for i, line in enumerate(lines):
                            if line.strip() and not line.startswith('#'):
                                import_pos = content.find('\n', import_pos) + 1
                                break
                        
                        modified_content = (content[:import_pos] + 
                                          "from ..registry import register_tool\n" +
                                          content[import_pos:])
                        added_imports = True
                        if args.verbose:
                            print(f"  添加导入: from ..registry import register_tool")
                
                # 对于每个找到的类，添加注册代码
                for class_name in matches:
                    if args.verbose:
                        print(f"  处理类: {class_name}")
                        
                    # 查找类的结尾（通过查找下一个类声明或者文件结尾）
                    class_start = modified_content.find(f"class {class_name}")
                    if class_start == -1:
                        if args.verbose:
                            print(f"  警告: 无法找到类 {class_name} 的定义位置")
                        continue
                    
                    # 查找类的结尾（下一个类或文件结尾）
                    next_class = re.search(r'class\s+[A-Za-z0-9_]+', modified_content[class_start+10:])
                    if next_class:
                        next_class_pos = class_start + 10 + next_class.start()
                        class_content = modified_content[class_start:next_class_pos]
                    else:
                        class_content = modified_content[class_start:]
                    
                    # 检查类内部是否已有注册代码
                    if f"register_tool({class_name}())" in class_content:
                        if args.verbose:
                            print(f"  跳过: 类 {class_name} 已包含注册代码")
                        continue
                    
                    # 添加注册代码到文件末尾或类声明之后
                    if next_class:
                        registration_code = f"\n# 在导入时自动注册工具实例\nregister_tool({class_name}())\n\n"
                        modified_content = modified_content[:next_class_pos] + registration_code + modified_content[next_class_pos:]
                    else:
                        registration_code = f"\n\n# 在导入时自动注册工具实例\nregister_tool({class_name}())"
                        modified_content += registration_code
                    
                    if args.verbose:
                        print(f"  添加注册代码: register_tool({class_name}())")
                
                # 如果内容被修改，写回文件
                if modified_content != content:
                    if args.dry_run:
                        print(f"{file_path}: 需要添加注册代码 (dry run - 未写入)")
                        count_modified += 1
                    else:
                        try:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(modified_content)
                            print(f"{file_path}: 已添加注册代码")
                            count_modified += 1
                        except Exception as e:
                            print(f"错误: 无法写入文件 {file_path}: {str(e)}")
                            count_errors += 1
            except Exception as e:
                print(f"处理文件 {file_path} 时出错: {str(e)}")
                traceback.print_exc()
                count_errors += 1
        
        print(f"处理完成: 修改了 {count_modified} 个文件，{count_already_registered} 个文件已包含注册代码，{count_errors} 个错误")
        
        # 打印结果摘要
        print("\n" + "="*50)
        print("处理结果摘要:")
        print(f"- 扫描工具目录: {tools_dir}")
        print(f"- 找到工具类文件: {len(tool_files)} 个")
        print(f"- 修改的文件: {count_modified} 个")
        print(f"- 已包含注册代码的文件: {count_already_registered} 个")
        if count_errors > 0:
            print(f"- 处理错误: {count_errors} 个")
        
        if args.dry_run:
            print("\n注意: 这是一个'dry run'操作，实际上没有修改任何文件。")
            print("如需实际修改文件，请去掉 --dry-run 参数重新运行脚本。")
        
        if count_modified > 0 and not args.dry_run:
            print("\n提示: 已成功为工具类添加注册代码。请重启Blender以应用更改。")
        
        print("="*50)
        return 0
    except Exception as e:
        print(f"\n错误: 脚本执行出错: {str(e)}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
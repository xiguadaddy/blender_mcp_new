"""
更新所有工具目录中的__init__.py文件
"""

import os
import glob

# 要更新的目录模式
tool_dirs = "blender-addon/handlers/tools/*_tools"

# 新的__init__.py内容模板
init_template = """\"\"\"
{category}工具模块
\"\"\"

# 导出工具映射，保持这个变量供其他模块导入
# 但工具现在直接通过各个工具类中的注册代码注册到注册表
tool_map = {{}}
"""

def main():
    """主函数"""
    print("开始更新__init__.py文件...")
    
    # 获取所有工具目录
    dirs = glob.glob(tool_dirs)
    print(f"找到 {len(dirs)} 个工具目录")
    
    for dir_path in dirs:
        # 获取目录名称作为分类名
        dir_name = os.path.basename(dir_path)
        category = dir_name.replace("_tools", "")
        
        # 生成该目录的__init__.py内容
        content = init_template.format(category=category)
        
        # 写入文件
        init_path = os.path.join(dir_path, "__init__.py")
        with open(init_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f"已更新: {init_path}")
    
    print("所有__init__.py文件更新完成!")

if __name__ == "__main__":
    main() 
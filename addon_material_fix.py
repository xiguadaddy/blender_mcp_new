"""
BlenderMCP addon.py 的材质修复补丁
此补丁提供了改进的set_material函数，解决了合并对象后材质不正确显示的问题。
使用方法：
1. 备份原始addon.py文件
2. 将此函数复制到addon.py中替换原始set_material函数
"""

# 导入Blender Python API
import bpy
import traceback

def set_material(self, object_name, material_name=None, create_if_missing=True, color=None):
    """设置或创建物体的材质，修复版本"""
    try:
        print(f"应用材质到对象: {object_name}, 材质: {material_name}, 颜色: {color}")
        
        # 获取对象
        obj = bpy.data.objects.get(object_name)
        if not obj:
            raise ValueError(f"找不到对象: {object_name}")
        
        # 确保对象可以接受材质
        if not hasattr(obj, 'data') or not hasattr(obj.data, 'materials'):
            raise ValueError(f"对象 {object_name} 不能接受材质")
        
        # 创建或获取材质
        if material_name:
            mat = bpy.data.materials.get(material_name)
            if not mat and create_if_missing:
                mat = bpy.data.materials.new(name=material_name)
                print(f"创建新材质: {material_name}")
        else:
            # 如果未提供材质名称，则生成唯一名称
            mat_name = f"{object_name}_material"
            mat = bpy.data.materials.get(mat_name)
            if not mat:
                mat = bpy.data.materials.new(name=mat_name)
            material_name = mat_name
            print(f"使用材质: {mat_name}")
        
        # 设置材质节点
        if mat:
            if not mat.use_nodes:
                mat.use_nodes = True
            
            # 获取或创建Principled BSDF节点
            principled = mat.node_tree.nodes.get('Principled BSDF')
            if not principled:
                # 清理现有节点以避免冲突
                mat.node_tree.nodes.clear()
                
                # 创建新的Principled BSDF节点
                principled = mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
                principled.location = (0, 0)
                
                # 创建新的输出节点
                output = mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
                output.location = (300, 0)
                
                # 连接节点
                mat.node_tree.links.new(principled.outputs[0], output.inputs[0])
            
            # 设置颜色（如果提供）
            if color and len(color) >= 3:
                alpha = 1.0 if len(color) < 4 else color[3]
                
                # 使用RGBA值直接设置，确保颜色正确应用
                principled.inputs['Base Color'].default_value = (
                    float(color[0]),
                    float(color[1]),
                    float(color[2]),
                    float(alpha)
                )
                print(f"设置材质颜色为 {color}")
                
                # 增加明显的金属感和粗糙度差异以增强视觉对比
                if color[0] > 0.8 and color[1] > 0.8 and color[2] > 0.8:
                    # 白色棋子 - 更光滑、更低金属感
                    principled.inputs['Metallic'].default_value = 0.1
                    principled.inputs['Roughness'].default_value = 0.2
                    principled.inputs['Specular'].default_value = 0.8
                    print("应用白色棋子的材质特性")
                elif color[0] < 0.2 and color[1] < 0.2 and color[2] < 0.2:
                    # 黑色棋子 - 更高金属感、中等粗糙度
                    principled.inputs['Metallic'].default_value = 0.7
                    principled.inputs['Roughness'].default_value = 0.4
                    principled.inputs['Specular'].default_value = 0.5
                    print("应用黑色棋子的材质特性")
        
        # 分配材质给对象
        if mat:
            # 清除所有现有材质槽
            while len(obj.data.materials) > 0:
                obj.data.materials.pop(index=0)
            
            # 添加新材质
            obj.data.materials.append(mat)
            
            # 确保材质正确应用
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            
            # 强制更新视图层以确保材质应用
            bpy.context.view_layer.update()
            
            print(f"已将材质 {mat.name} 分配给对象 {object_name}")
            
            return {
                "status": "success",
                "object": object_name,
                "material": mat.name,
                "color": color if color else None
            }
        else:
            raise ValueError(f"无法创建或找到材质: {material_name}")
        
    except Exception as e:
        print(f"set_material 错误: {str(e)}")
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(e),
            "object": object_name,
            "material": material_name if 'material_name' in locals() else None
        } 
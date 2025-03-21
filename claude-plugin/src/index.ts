// 导入新的工具处理函数
import {
  handleCreateObject,
  handleAddLight,
  handleSetMaterial,
  handleRenderScene,
  handleCreateText,
  handleCreateCurve,
  handleListObjects,
  handleGetObjectInfo,
  handleDeleteObject,
  handleDuplicateObject
} from './tools';

// 定义插件类型接口
interface ClaudePlugin {
  registerTool: (name: string, handler: any) => void;
}

// 注册工具处理器
function registerToolHandlers(plugin: ClaudePlugin) {
  // 注册Blender工具处理器
  plugin.registerTool('mcp_blender_create_object', handleCreateObject);
  plugin.registerTool('mcp_blender_add_light', handleAddLight);
  plugin.registerTool('mcp_blender_set_material', handleSetMaterial);
  plugin.registerTool('mcp_blender_render_scene', handleRenderScene);
  plugin.registerTool('mcp_blender_create_text', handleCreateText);
  plugin.registerTool('mcp_blender_create_curve', handleCreateCurve);
  plugin.registerTool('mcp_blender_list_objects', handleListObjects);
  plugin.registerTool('mcp_blender_get_object_info', handleGetObjectInfo);
  plugin.registerTool('mcp_blender_delete_object', handleDeleteObject);
  plugin.registerTool('mcp_blender_duplicate_object', handleDuplicateObject);
} 
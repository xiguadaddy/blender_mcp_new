import axios from 'axios';
import { logger } from "./logger";

// 定义所需的接口
interface TextContent {
  type: string;
  text: string;
}

interface CallToolResult {
  content: Array<TextContent>;
  isError: boolean;
}

// 定义工具处理器类型接口
interface ToolHandler {
  (params: { arguments: Record<string, any> }): Promise<CallToolResult>;
}

// 工具处理函数
// 创建HTTP客户端
const httpClient = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 30000, // 30秒超时
  headers: {
    'Content-Type': 'application/json'
  }
});

// 直接工具请求函数，绕过MCP库的序列化问题
async function makeDirectToolRequest(tool: string, params: Record<string, any>): Promise<CallToolResult> {
  try {
    console.log(`Making direct tool request for ${tool}`, params);
    
    // 发送HTTP请求到Blender服务器
    const response = await httpClient.post('/jsonrpc', {
      jsonrpc: '2.0',
      id: `direct_${Date.now()}`,
      method: 'tools/call',
      params: {
        name: tool,
        arguments: params
      }
    });
    
    console.log(`Got response for ${tool}:`, response.data);
    
    // 检查响应是否成功
    if (response.data && response.data.result) {
      const result = response.data.result;
      
      // 处理MCP库的元组列表格式
      // 检查是否是[['meta', null], ['content', [...]], ['isError', false]]格式
      if (Array.isArray(result) && result.length > 0 && Array.isArray(result[0])) {
        console.log("检测到元组格式响应");
        
        // 从元组中提取内容和错误标志
        let content = null;
        let isError = false;
        
        for (const item of result) {
          if (Array.isArray(item) && item.length === 2) {
            const [key, value] = item;
            if (key === 'content') {
              content = value;
            } else if (key === 'isError') {
              isError = !!value; // 转换为布尔值
            }
          }
        }
        
        // 如果找到内容，创建标准响应
        if (content) {
          // 确保content是数组
          const contentArray = Array.isArray(content) ? content : [content];
          
          // 创建标准化的内容数组
          const formattedContent = contentArray.map(item => {
            // 如果已经是正确的格式，直接使用
            if (typeof item === 'object' && item !== null && 'type' in item && 'text' in item) {
              return item;
            }
            // 否则将其转换为文本
            return {
              type: 'text',
              text: typeof item === 'string' ? item : JSON.stringify(item, null, 2)
            };
          });
          
          return {
            content: formattedContent,
            isError: isError
          };
        }
      }
      
      // 常规响应格式处理
      // 如果响应是已经格式化的CallToolResult
      if (result.content) {
        return {
          content: Array.isArray(result.content) ? result.content : [result.content],
          isError: result.isError || false
        };
      }
      
      // 如果响应是普通对象，转换为文本内容
      return {
        content: [{
          type: 'text',
          text: typeof result === 'string' ? result : JSON.stringify(result, null, 2)
        }],
        isError: false
      };
    }
    
    // 处理错误响应
    return {
      content: [{
        type: 'text',
        text: `Error: Unexpected response format: ${JSON.stringify(response.data)}`
      }],
      isError: true
    };
  } catch (error: any) {
    console.error(`Error making direct request for ${tool}:`, error);
    
    // 返回错误结果
    return {
      content: [{
        type: 'text',
        text: `Error: ${error.message || 'Unknown error occurred'}`
      }],
      isError: true
    };
  }
}

// 立方体创建工具
export const handleCreateObject: ToolHandler = async ({ arguments: args }) => {
  return makeDirectToolRequest('create_object', args);
};

// 添加灯光工具
export const handleAddLight: ToolHandler = async ({ arguments: args }) => {
  return makeDirectToolRequest('add_light', args);
};

// 设置材质工具
export const handleSetMaterial: ToolHandler = async ({ arguments: args }) => {
  return makeDirectToolRequest('set_material', args);
};

// 渲染场景工具
export const handleRenderScene: ToolHandler = async ({ arguments: args }) => {
  return makeDirectToolRequest('render_scene', args);
};

// 创建文本工具
export const handleCreateText: ToolHandler = async ({ arguments: args }) => {
  return makeDirectToolRequest('create_text', args);
};

// 创建曲线工具
export const handleCreateCurve: ToolHandler = async ({ arguments: args }) => {
  return makeDirectToolRequest('create_curve', args);
};

// 列出对象工具
export const handleListObjects: ToolHandler = async ({ arguments: args }) => {
  return makeDirectToolRequest('list_objects', args);
};

// 获取对象信息工具
export const handleGetObjectInfo: ToolHandler = async ({ arguments: args }) => {
  return makeDirectToolRequest('get_object_info', args);
};

// 删除对象工具
export const handleDeleteObject: ToolHandler = async ({ arguments: args }) => {
  return makeDirectToolRequest('delete_object', args);
};

// 复制对象工具
export const handleDuplicateObject: ToolHandler = async ({ arguments: args }) => {
  return makeDirectToolRequest('duplicate_object', args);
}; 
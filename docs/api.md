# Invoice OCR MCP API 文档

## 概述

Invoice OCR MCP 提供了一套完整的发票识别API，基于Model Context Protocol (MCP)规范，支持单张和批量发票识别。

## 工具列表

### 1. recognize_single_invoice - 单张发票识别

识别单张发票并提取结构化信息。

#### 参数

| 参数名 | 类型 | 必需 | 描述 |
|--------|------|------|------|
| image_data | string | 是* | Base64编码的发票图像数据 |
| image_url | string | 是* | 发票图像URL地址 |
| output_format | string | 否 | 输出格式：standard(默认)/detailed/raw |

*注：`image_data` 和 `image_url` 二选一

#### 示例请求

```json
{
  "tool": "recognize_single_invoice",
  "arguments": {
    "image_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk...",
    "output_format": "standard"
  }
}
```

#### 示例响应

```json
{
  "success": true,
  "data": {
    "invoice_type": {
      "code": "01",
      "name": "增值税专用发票",
      "confidence": 0.98
    },
    "basic_info": {
      "invoice_number": "12345678",
      "invoice_date": "2024-01-15",
      "total_amount": "1000.00",
      "tax_amount": "130.00",
      "amount_without_tax": "870.00"
    },
    "seller_info": {
      "name": "某某科技有限公司",
      "tax_id": "91110000123456789X",
      "address": "北京市朝阳区xxx街道xxx号",
      "phone": "010-12345678",
      "bank_account": "1234567890123456789"
    },
    "buyer_info": {
      "name": "购买方名称",
      "tax_id": "91110000987654321Y",
      "address": "购买方地址",
      "phone": "购买方电话",
      "bank_account": "购买方账号"
    },
    "items": [
      {
        "name": "商品名称",
        "specification": "规格型号",
        "unit": "台",
        "quantity": "1",
        "unit_price": "870.00",
        "amount": "870.00",
        "tax_rate": "13%",
        "tax_amount": "130.00"
      }
    ],
    "verification": {
      "check_code": "123456789",
      "machine_number": "499098765432",
      "is_valid": true
    },
    "meta": {
      "processing_time": 1.23,
      "model_version": "v1.0.0",
      "confidence_score": 0.95
    }
  }
}
```

### 2. recognize_batch_invoices - 批量发票识别

批量识别多张发票。

#### 参数

| 参数名 | 类型 | 必需 | 描述 |
|--------|------|------|------|
| images | array | 是 | 发票图像数组，每个元素包含id和图像数据 |
| parallel_count | integer | 否 | 并行处理数量，默认3，最大10 |

#### images数组元素结构

| 参数名 | 类型 | 必需 | 描述 |
|--------|------|------|------|
| id | string | 是 | 发票唯一标识 |
| image_data | string | 是* | Base64编码的图像数据 |
| image_url | string | 是* | 图像URL地址 |

#### 示例请求

```json
{
  "tool": "recognize_batch_invoices",
  "arguments": {
    "images": [
      {
        "id": "invoice_001",
        "image_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk..."
      },
      {
        "id": "invoice_002",
        "image_url": "https://example.com/invoice2.jpg"
      }
    ],
    "parallel_count": 3
  }
}
```

#### 示例响应

```json
{
  "success": true,
  "data": {
    "total_count": 2,
    "success_count": 2,
    "failed_count": 0,
    "results": [
      {
        "id": "invoice_001",
        "status": "success",
        "data": {
          "invoice_type": {
            "code": "01",
            "name": "增值税专用发票",
            "confidence": 0.98
          },
          // ... 完整的识别结果
        }
      },
      {
        "id": "invoice_002",
        "status": "success",
        "data": {
          // ... 识别结果
        }
      }
    ],
    "meta": {
      "total_processing_time": 2.45,
      "average_processing_time": 1.23
    }
  }
}
```

### 3. detect_invoice_type - 发票类型检测

仅检测发票类型，不进行完整识别。

#### 参数

| 参数名 | 类型 | 必需 | 描述 |
|--------|------|------|------|
| image_data | string | 是* | Base64编码的发票图像数据 |
| image_url | string | 是* | 发票图像URL地址 |

#### 示例请求

```json
{
  "tool": "detect_invoice_type",
  "arguments": {
    "image_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk..."
  }
}
```

#### 示例响应

```json
{
  "success": true,
  "data": {
    "invoice_type": {
      "code": "01",
      "name": "增值税专用发票",
      "confidence": 0.98
    },
    "candidates": [
      {
        "code": "01",
        "name": "增值税专用发票",
        "confidence": 0.98
      },
      {
        "code": "04",
        "name": "增值税普通发票",
        "confidence": 0.02
      }
    ],
    "meta": {
      "processing_time": 0.25,
      "model_version": "v1.0.0"
    }
  }
}
```

## 支持的发票类型

| 代码 | 名称 |
|------|------|
| 01 | 增值税专用发票 |
| 03 | 机动车增值税专用发票 |
| 04 | 增值税普通发票 |
| 10 | 增值税电子普通发票 |
| 11 | 增值税普通发票（卷式） |
| 14 | 增值税普通发票（通行费） |
| 15 | 二手车发票 |
| 20 | 增值税电子专用发票 |
| 99 | 数电发票（增值税专用发票） |
| 09 | 数电发票（普通发票） |
| 61 | 数电发票（航空运输电子客票行程单） |
| 83 | 数电发票（铁路电子客票） |
| 100 | 区块链发票（支持深圳、北京和云南地区） |

## 错误处理

### 错误响应格式

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": {
      // 详细错误信息
    }
  }
}
```

### 常见错误代码

| 错误代码 | 描述 | 解决方案 |
|----------|------|----------|
| INVALID_IMAGE_FORMAT | 不支持的图像格式 | 使用JPG、PNG、WebP格式 |
| IMAGE_TOO_LARGE | 图像尺寸过大 | 压缩图像至4096x4096以下 |
| IMAGE_DECODE_ERROR | 图像解码失败 | 检查图像数据完整性 |
| MODEL_LOAD_ERROR | 模型加载失败 | 检查ModelScope连接 |
| PROCESSING_TIMEOUT | 处理超时 | 重试或减小图像尺寸 |
| RATE_LIMIT_EXCEEDED | 请求频率超限 | 降低请求频率 |
| INVALID_INVOICE_TYPE | 无法识别的发票类型 | 确认图像为标准发票格式 |

## 性能指标

- **单张识别速度**: < 3秒
- **批量平均速度**: < 2秒/张
- **识别准确率**: > 99%
- **并发支持**: 最大10个并行任务
- **图像尺寸限制**: 4096x4096像素
- **文件大小限制**: 50MB

## 最佳实践

### 1. 图像质量要求

- 分辨率：建议300DPI以上
- 格式：JPG、PNG、WebP
- 清晰度：无模糊、无严重倾斜
- 光线：光线充足，无反光

### 2. 批量处理建议

- 单批次不超过50张图片
- 合理设置并行数量（建议3-5）
- 对失败的图片进行重试

### 3. 错误重试策略

```javascript
async function recognizeWithRetry(imageData, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const result = await callTool('recognize_single_invoice', {
        image_data: imageData
      });
      return result;
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await sleep(1000 * (i + 1)); // 指数退避
    }
  }
}
```

### 4. 缓存策略

相同图像的识别结果会被缓存24小时，重复识别会直接返回缓存结果。

## SDK示例

### Python客户端

```python
import asyncio
import base64
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

async def recognize_invoice(image_path):
    # 读取图像并转换为base64
    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode()
    
    async with stdio_client(["python", "server.py"]) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            
            result = await session.call_tool(
                "recognize_single_invoice",
                {"image_data": image_data}
            )
            
            return result

# 使用示例
result = asyncio.run(recognize_invoice("invoice.jpg"))
print(result)
```

### JavaScript客户端

```javascript
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';

async function recognizeInvoice(imageBase64) {
  const transport = new StdioClientTransport({
    command: 'python',
    args: ['server.py']
  });
  
  const client = new Client(
    { name: "invoice-client", version: "1.0.0" },
    { capabilities: {} }
  );
  
  await client.connect(transport);
  
  const result = await client.request(
    { method: "tools/call" },
    {
      name: "recognize_single_invoice",
      arguments: { image_data: imageBase64 }
    }
  );
  
  await client.close();
  return result;
}
```

## 版本历史

### v1.0.0 (2024-01-15)
- 初始版本发布
- 支持13种发票类型识别
- 实现单张和批量处理
- 添加发票类型检测功能 
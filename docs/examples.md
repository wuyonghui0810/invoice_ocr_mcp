# 使用示例

本文档提供了Invoice OCR MCP的详细使用示例，包括Python、JavaScript等多种语言的客户端实现。

## 基础示例

### Python客户端示例

#### 单张发票识别

```python
import asyncio
import base64
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

async def recognize_single_invoice():
    """识别单张发票示例"""
    
    # 读取发票图像
    with open("invoice.jpg", "rb") as f:
        image_data = base64.b64encode(f.read()).decode()
    
    # 连接MCP服务器
    async with stdio_client(["python", "src/invoice_ocr_mcp/server.py"]) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            # 初始化会话
            await session.initialize()
            
            # 调用识别工具
            result = await session.call_tool(
                "recognize_single_invoice",
                {
                    "image_data": image_data,
                    "output_format": "standard"
                }
            )
            
            # 处理结果
            if result.get("success"):
                invoice_data = result["data"]
                print(f"发票类型: {invoice_data['invoice_type']['name']}")
                print(f"发票号码: {invoice_data['basic_info']['invoice_number']}")
                print(f"总金额: {invoice_data['basic_info']['total_amount']}")
                print(f"销售方: {invoice_data['seller_info']['name']}")
            else:
                print(f"识别失败: {result['error']['message']}")

# 运行示例
asyncio.run(recognize_single_invoice())
```

#### 批量发票识别

```python
import asyncio
import base64
import os
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

async def recognize_batch_invoices():
    """批量识别发票示例"""
    
    # 准备图像数据
    invoice_dir = "invoices/"
    images = []
    
    for filename in os.listdir(invoice_dir):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            filepath = os.path.join(invoice_dir, filename)
            with open(filepath, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
            
            images.append({
                "id": filename,
                "image_data": image_data
            })
    
    # 连接MCP服务器
    async with stdio_client(["python", "src/invoice_ocr_mcp/server.py"]) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            
            # 批量识别
            result = await session.call_tool(
                "recognize_batch_invoices",
                {
                    "images": images,
                    "parallel_count": 3
                }
            )
            
            # 处理结果
            if result.get("success"):
                batch_data = result["data"]
                print(f"总计: {batch_data['total_count']} 张")
                print(f"成功: {batch_data['success_count']} 张")
                print(f"失败: {batch_data['failed_count']} 张")
                
                for item in batch_data["results"]:
                    if item["status"] == "success":
                        invoice = item["data"]
                        print(f"\n{item['id']}:")
                        print(f"  类型: {invoice['invoice_type']['name']}")
                        print(f"  金额: {invoice['basic_info']['total_amount']}")
                    else:
                        print(f"\n{item['id']}: 识别失败")

asyncio.run(recognize_batch_invoices())
```

#### 带错误处理和重试的示例

```python
import asyncio
import base64
import time
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

class InvoiceOCRClient:
    def __init__(self, server_command=None):
        self.server_command = server_command or ["python", "src/invoice_ocr_mcp/server.py"]
    
    async def recognize_with_retry(self, image_data, max_retries=3):
        """带重试机制的发票识别"""
        
        for attempt in range(max_retries):
            try:
                async with stdio_client(self.server_command) as streams:
                    async with ClientSession(streams[0], streams[1]) as session:
                        await session.initialize()
                        
                        result = await session.call_tool(
                            "recognize_single_invoice",
                            {"image_data": image_data}
                        )
                        
                        if result.get("success"):
                            return result["data"]
                        else:
                            error = result.get("error", {})
                            if error.get("code") == "RATE_LIMIT_EXCEEDED":
                                wait_time = 2 ** attempt  # 指数退避
                                print(f"请求频率超限，等待 {wait_time} 秒后重试...")
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                raise Exception(f"识别失败: {error.get('message', '未知错误')}")
                                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                print(f"第 {attempt + 1} 次尝试失败: {e}")
                await asyncio.sleep(1)
        
        raise Exception("达到最大重试次数")
    
    async def batch_recognize_with_progress(self, image_files, batch_size=10):
        """带进度显示的批量识别"""
        
        results = []
        total_files = len(image_files)
        
        for i in range(0, total_files, batch_size):
            batch = image_files[i:i + batch_size]
            batch_images = []
            
            # 准备批次数据
            for file_path in batch:
                with open(file_path, "rb") as f:
                    image_data = base64.b64encode(f.read()).decode()
                batch_images.append({
                    "id": os.path.basename(file_path),
                    "image_data": image_data
                })
            
            # 处理批次
            try:
                async with stdio_client(self.server_command) as streams:
                    async with ClientSession(streams[0], streams[1]) as session:
                        await session.initialize()
                        
                        batch_result = await session.call_tool(
                            "recognize_batch_invoices",
                            {
                                "images": batch_images,
                                "parallel_count": 3
                            }
                        )
                        
                        if batch_result.get("success"):
                            results.extend(batch_result["data"]["results"])
                        
                        # 显示进度
                        processed = min(i + batch_size, total_files)
                        progress = (processed / total_files) * 100
                        print(f"进度: {processed}/{total_files} ({progress:.1f}%)")
                        
            except Exception as e:
                print(f"批次 {i//batch_size + 1} 处理失败: {e}")
        
        return results

# 使用示例
async def main():
    client = InvoiceOCRClient()
    
    # 单张识别
    with open("invoice.jpg", "rb") as f:
        image_data = base64.b64encode(f.read()).decode()
    
    try:
        result = await client.recognize_with_retry(image_data)
        print("识别成功:", result["basic_info"]["invoice_number"])
    except Exception as e:
        print("识别失败:", e)

asyncio.run(main())
```

### JavaScript客户端示例

#### Node.js 客户端

```javascript
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import fs from 'fs/promises';

class InvoiceOCRClient {
  constructor(serverCommand = ['python', 'src/invoice_ocr_mcp/server.py']) {
    this.serverCommand = serverCommand;
  }

  async recognizeInvoice(imagePath) {
    // 读取图像文件
    const imageBuffer = await fs.readFile(imagePath);
    const imageBase64 = imageBuffer.toString('base64');

    // 创建MCP客户端
    const transport = new StdioClientTransport({
      command: this.serverCommand[0],
      args: this.serverCommand.slice(1)
    });

    const client = new Client(
      { name: "invoice-client", version: "1.0.0" },
      { capabilities: {} }
    );

    try {
      await client.connect(transport);

      // 调用识别工具
      const result = await client.request(
        { method: "tools/call" },
        {
          name: "recognize_single_invoice",
          arguments: { 
            image_data: imageBase64,
            output_format: "standard"
          }
        }
      );

      return result;
    } finally {
      await client.close();
    }
  }

  async recognizeBatch(imagePaths) {
    // 准备图像数据
    const images = await Promise.all(
      imagePaths.map(async (path, index) => {
        const imageBuffer = await fs.readFile(path);
        const imageBase64 = imageBuffer.toString('base64');
        return {
          id: `invoice_${index + 1}`,
          image_data: imageBase64
        };
      })
    );

    const transport = new StdioClientTransport({
      command: this.serverCommand[0],
      args: this.serverCommand.slice(1)
    });

    const client = new Client(
      { name: "invoice-client", version: "1.0.0" },
      { capabilities: {} }
    );

    try {
      await client.connect(transport);

      const result = await client.request(
        { method: "tools/call" },
        {
          name: "recognize_batch_invoices",
          arguments: {
            images: images,
            parallel_count: 3
          }
        }
      );

      return result;
    } finally {
      await client.close();
    }
  }
}

// 使用示例
async function main() {
  const client = new InvoiceOCRClient();

  try {
    // 单张识别
    const result = await client.recognizeInvoice('invoice.jpg');
    console.log('识别结果:', result);

    // 批量识别
    const batchResult = await client.recognizeBatch([
      'invoice1.jpg',
      'invoice2.jpg',
      'invoice3.jpg'
    ]);
    console.log('批量识别结果:', batchResult);

  } catch (error) {
    console.error('识别失败:', error);
  }
}

main();
```

#### Web前端示例

```html
<!DOCTYPE html>
<html>
<head>
    <title>发票OCR识别</title>
    <style>
        .container { max-width: 800px; margin: 0 auto; padding: 20px; }
        .upload-area { 
            border: 2px dashed #ccc; 
            padding: 40px; 
            text-align: center; 
            margin: 20px 0;
        }
        .result { margin-top: 20px; padding: 20px; background: #f5f5f5; }
        .loading { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>发票OCR识别系统</h1>
        
        <div class="upload-area" id="uploadArea">
            <p>点击选择发票图片或拖拽到此处</p>
            <input type="file" id="fileInput" accept="image/*" multiple style="display: none;">
        </div>
        
        <div class="loading" id="loading">
            <p>正在识别中，请稍候...</p>
        </div>
        
        <div class="result" id="result" style="display: none;">
            <h3>识别结果</h3>
            <div id="resultContent"></div>
        </div>
    </div>

    <script>
        class WebInvoiceOCR {
            constructor(apiEndpoint) {
                this.apiEndpoint = apiEndpoint;
                this.setupEventListeners();
            }

            setupEventListeners() {
                const uploadArea = document.getElementById('uploadArea');
                const fileInput = document.getElementById('fileInput');

                uploadArea.addEventListener('click', () => fileInput.click());
                uploadArea.addEventListener('dragover', (e) => {
                    e.preventDefault();
                    uploadArea.style.backgroundColor = '#e8f5e8';
                });
                uploadArea.addEventListener('dragleave', () => {
                    uploadArea.style.backgroundColor = '';
                });
                uploadArea.addEventListener('drop', (e) => {
                    e.preventDefault();
                    uploadArea.style.backgroundColor = '';
                    this.handleFiles(e.dataTransfer.files);
                });

                fileInput.addEventListener('change', (e) => {
                    this.handleFiles(e.target.files);
                });
            }

            async handleFiles(files) {
                if (files.length === 0) return;

                this.showLoading(true);
                this.hideResult();

                try {
                    if (files.length === 1) {
                        const result = await this.recognizeSingle(files[0]);
                        this.displaySingleResult(result);
                    } else {
                        const results = await this.recognizeBatch(Array.from(files));
                        this.displayBatchResults(results);
                    }
                } catch (error) {
                    this.displayError(error.message);
                } finally {
                    this.showLoading(false);
                }
            }

            async recognizeSingle(file) {
                const imageBase64 = await this.fileToBase64(file);
                
                const response = await fetch(`${this.apiEndpoint}/recognize`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        tool: 'recognize_single_invoice',
                        arguments: {
                            image_data: imageBase64,
                            output_format: 'standard'
                        }
                    })
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                return await response.json();
            }

            async recognizeBatch(files) {
                const images = await Promise.all(
                    files.map(async (file, index) => ({
                        id: `invoice_${index + 1}`,
                        image_data: await this.fileToBase64(file)
                    }))
                );

                const response = await fetch(`${this.apiEndpoint}/recognize`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        tool: 'recognize_batch_invoices',
                        arguments: {
                            images: images,
                            parallel_count: 3
                        }
                    })
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                return await response.json();
            }

            fileToBase64(file) {
                return new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onload = () => {
                        const base64 = reader.result.split(',')[1];
                        resolve(base64);
                    };
                    reader.onerror = reject;
                    reader.readAsDataURL(file);
                });
            }

            displaySingleResult(result) {
                const content = document.getElementById('resultContent');
                
                if (result.success) {
                    const invoice = result.data;
                    content.innerHTML = `
                        <h4>${invoice.invoice_type.name}</h4>
                        <p><strong>发票号码:</strong> ${invoice.basic_info.invoice_number}</p>
                        <p><strong>开票日期:</strong> ${invoice.basic_info.invoice_date}</p>
                        <p><strong>总金额:</strong> ¥${invoice.basic_info.total_amount}</p>
                        <p><strong>销售方:</strong> ${invoice.seller_info.name}</p>
                        <p><strong>购买方:</strong> ${invoice.buyer_info.name}</p>
                        <p><strong>置信度:</strong> ${(invoice.meta.confidence_score * 100).toFixed(1)}%</p>
                    `;
                } else {
                    content.innerHTML = `<p style="color: red;">识别失败: ${result.error.message}</p>`;
                }

                this.showResult();
            }

            displayBatchResults(results) {
                const content = document.getElementById('resultContent');
                
                if (results.success) {
                    const data = results.data;
                    let html = `
                        <h4>批量识别结果</h4>
                        <p>总计: ${data.total_count} 张，成功: ${data.success_count} 张，失败: ${data.failed_count} 张</p>
                        <div>
                    `;

                    data.results.forEach(item => {
                        if (item.status === 'success') {
                            const invoice = item.data;
                            html += `
                                <div style="border: 1px solid #ddd; margin: 10px 0; padding: 10px;">
                                    <h5>${item.id} - ${invoice.invoice_type.name}</h5>
                                    <p>发票号码: ${invoice.basic_info.invoice_number}</p>
                                    <p>金额: ¥${invoice.basic_info.total_amount}</p>
                                </div>
                            `;
                        } else {
                            html += `
                                <div style="border: 1px solid #f00; margin: 10px 0; padding: 10px;">
                                    <h5>${item.id} - 识别失败</h5>
                                </div>
                            `;
                        }
                    });

                    html += '</div>';
                    content.innerHTML = html;
                } else {
                    content.innerHTML = `<p style="color: red;">批量识别失败: ${results.error.message}</p>`;
                }

                this.showResult();
            }

            displayError(message) {
                const content = document.getElementById('resultContent');
                content.innerHTML = `<p style="color: red;">错误: ${message}</p>`;
                this.showResult();
            }

            showLoading(show) {
                document.getElementById('loading').style.display = show ? 'block' : 'none';
            }

            showResult() {
                document.getElementById('result').style.display = 'block';
            }

            hideResult() {
                document.getElementById('result').style.display = 'none';
            }
        }

        // 初始化应用
        const ocr = new WebInvoiceOCR('http://localhost:8000/api');
    </script>
</body>
</html>
```

## 高级用例

### 企业级集成示例

```python
import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime
import json

class EnterpriseInvoiceProcessor:
    """企业级发票处理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.client = InvoiceOCRClient(config.get('server_command'))
        
    async def process_invoice_batch(self, file_paths: List[str]) -> Dict[str, Any]:
        """处理发票批次"""
        
        start_time = datetime.now()
        self.logger.info(f"开始处理 {len(file_paths)} 张发票")
        
        try:
            # 批量识别
            results = await self.client.batch_recognize_with_progress(
                file_paths, 
                batch_size=self.config.get('batch_size', 10)
            )
            
            # 数据验证和清洗
            validated_results = self.validate_results(results)
            
            # 数据标准化
            standardized_results = self.standardize_data(validated_results)
            
            # 保存结果
            await self.save_results(standardized_results)
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            summary = {
                'total_files': len(file_paths),
                'successful': len([r for r in results if r.get('status') == 'success']),
                'failed': len([r for r in results if r.get('status') != 'success']),
                'processing_time': processing_time,
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info(f"批次处理完成: {summary}")
            return summary
            
        except Exception as e:
            self.logger.error(f"批次处理失败: {e}")
            raise
    
    def validate_results(self, results: List[Dict]) -> List[Dict]:
        """验证识别结果"""
        validated = []
        
        for result in results:
            if result.get('status') != 'success':
                continue
                
            data = result.get('data', {})
            basic_info = data.get('basic_info', {})
            
            # 验证必要字段
            if not all([
                basic_info.get('invoice_number'),
                basic_info.get('total_amount'),
                basic_info.get('invoice_date')
            ]):
                self.logger.warning(f"发票 {result.get('id')} 缺少必要字段")
                continue
            
            # 验证金额格式
            try:
                amount = float(basic_info['total_amount'])
                if amount <= 0:
                    self.logger.warning(f"发票 {result.get('id')} 金额异常: {amount}")
                    continue
            except ValueError:
                self.logger.warning(f"发票 {result.get('id')} 金额格式错误")
                continue
            
            validated.append(result)
        
        return validated
    
    def standardize_data(self, results: List[Dict]) -> List[Dict]:
        """数据标准化"""
        standardized = []
        
        for result in results:
            data = result['data']
            
            # 标准化日期格式
            invoice_date = data['basic_info']['invoice_date']
            try:
                # 尝试解析日期并标准化格式
                parsed_date = datetime.strptime(invoice_date, '%Y-%m-%d')
                data['basic_info']['invoice_date'] = parsed_date.strftime('%Y-%m-%d')
            except ValueError:
                self.logger.warning(f"日期格式异常: {invoice_date}")
            
            # 标准化金额格式
            for field in ['total_amount', 'tax_amount', 'amount_without_tax']:
                if field in data['basic_info']:
                    amount_str = data['basic_info'][field]
                    try:
                        amount = float(amount_str)
                        data['basic_info'][field] = f"{amount:.2f}"
                    except ValueError:
                        pass
            
            # 添加处理元数据
            data['processing_meta'] = {
                'processed_at': datetime.now().isoformat(),
                'processor_version': '1.0.0',
                'validation_passed': True
            }
            
            standardized.append(result)
        
        return standardized
    
    async def save_results(self, results: List[Dict]):
        """保存处理结果"""
        # 保存到数据库
        if self.config.get('save_to_database'):
            await self.save_to_database(results)
        
        # 保存到文件
        if self.config.get('save_to_file'):
            await self.save_to_file(results)
        
        # 发送到外部系统
        if self.config.get('webhook_url'):
            await self.send_webhook(results)
    
    async def save_to_database(self, results: List[Dict]):
        """保存到数据库（示例实现）"""
        # 这里是数据库保存逻辑的示例
        self.logger.info(f"保存 {len(results)} 条记录到数据库")
        
    async def save_to_file(self, results: List[Dict]):
        """保存到JSON文件"""
        filename = f"invoice_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"结果已保存到文件: {filename}")
    
    async def send_webhook(self, results: List[Dict]):
        """发送到Webhook"""
        import aiohttp
        
        webhook_url = self.config['webhook_url']
        payload = {
            'event': 'invoice_batch_processed',
            'data': results,
            'timestamp': datetime.now().isoformat()
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        self.logger.info("Webhook发送成功")
                    else:
                        self.logger.error(f"Webhook发送失败: {response.status}")
            except Exception as e:
                self.logger.error(f"Webhook发送异常: {e}")

# 使用示例
async def main():
    config = {
        'server_command': ['python', 'src/invoice_ocr_mcp/server.py'],
        'batch_size': 20,
        'save_to_database': True,
        'save_to_file': True,
        'webhook_url': 'https://api.example.com/webhook/invoices'
    }
    
    processor = EnterpriseInvoiceProcessor(config)
    
    file_paths = [
        'invoices/invoice_001.jpg',
        'invoices/invoice_002.jpg',
        # ... 更多文件
    ]
    
    summary = await processor.process_invoice_batch(file_paths)
    print("处理完成:", summary)

if __name__ == "__main__":
    asyncio.run(main())
```

## 错误处理最佳实践

```python
class RobustInvoiceOCR:
    """健壮的发票OCR客户端"""
    
    def __init__(self):
        self.max_retries = 3
        self.base_delay = 1
        self.max_delay = 60
        
    async def recognize_with_fallback(self, image_data: str) -> Dict[str, Any]:
        """带降级策略的识别"""
        
        # 尝试标准识别
        try:
            return await self.standard_recognize(image_data)
        except Exception as e:
            self.logger.warning(f"标准识别失败: {e}")
        
        # 降级到基础OCR
        try:
            return await self.basic_ocr_recognize(image_data)
        except Exception as e:
            self.logger.error(f"基础OCR也失败: {e}")
            
        # 最后返回人工处理标记
        return {
            'success': False,
            'requires_manual_processing': True,
            'error': 'All OCR methods failed'
        }
    
    async def exponential_backoff_retry(self, func, *args, **kwargs):
        """指数退避重试"""
        
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise e
                
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                self.logger.info(f"第 {attempt + 1} 次尝试失败，{delay}秒后重试")
                await asyncio.sleep(delay)
```

这些示例展示了Invoice OCR MCP的各种使用场景，从简单的单张识别到复杂的企业级批量处理系统。根据你的具体需求，可以选择合适的示例作为起点进行开发。 
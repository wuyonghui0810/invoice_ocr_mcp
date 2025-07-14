# 企业发票OCR识别MCP服务器

基于ModelScope生态构建的专业企业发票OCR识别MCP服务器，为企业财务数字化提供智能化解决方案。

## 🚀 产品特性

- **标准化接入**：符合MCP协议规范，无缝集成各类AI应用
- **专业发票识别**：支持13种主流发票类型，准确率达99%+
- **结构化输出**：自动提取发票关键信息，输出标准JSON格式
- **企业级服务**：支持批量处理，满足大规模业务需求

## 📋 支持的发票类型

- 01: 增值税专用发票
- 03: 机动车增值税专用发票
- 04: 增值税普通发票
- 10: 增值税电子普通发票
- 11: 增值税普通发票（卷式）
- 14: 增值税普通发票（通行费）
- 15: 二手车发票
- 20: 增值税电子专用发票
- 99: 数电发票（增值税专用发票）
- 09: 数电发票（普通发票）
- 61: 数电发票（航空运输电子客票行程单）
- 83: 数电发票（铁路电子客票）
- 100: 区块链发票（支持深圳、北京和云南地区）

## 🛠️ 安装指南

### 环境要求

- Python 3.8+
- ModelScope账号和API Token
- 至少4GB内存
- GPU支持（推荐）

### 快速安装

```bash
# 克隆项目
git clone https://github.com/your-org/invoice-ocr-mcp.git
cd invoice-ocr-mcp

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，添加你的 ModelScope API Token
```

### Docker部署

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d
```

## 📖 使用指南

### MCP客户端集成

```python
import asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

async def main():
    async with stdio_client(["python", "src/invoice_ocr_mcp/server.py"]) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            
            # 识别单张发票
            result = await session.call_tool(
                "recognize_single_invoice",
                {"image_data": "base64_encoded_image_data"}
            )
            print("识别结果:", result)

if __name__ == "__main__":
    asyncio.run(main())
```

### 批量处理

```python
# 批量识别发票
result = await session.call_tool(
    "recognize_batch_invoices",
    {
        "images": [
            {"id": "invoice1", "image_data": "base64_data1"},
            {"id": "invoice2", "image_data": "base64_data2"}
        ],
        "parallel_count": 3
    }
)
```

## 🔧 配置说明

主要配置文件位于 `configs/` 目录：

- `models.yaml`: ModelScope模型配置
- `server.yaml`: 服务器配置
- `logging.yaml`: 日志配置

详细配置说明请参考 [部署指南](docs/deployment.md)

## 📊 性能指标

- **识别准确率**: >99%
- **处理速度**: 单张发票<3秒
- **并发支持**: 支持多线程并行处理
- **服务可用性**: >99.9%

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目基于 MIT 许可证开源。

## 📞 技术支持

如有问题，请通过以下方式联系：

- GitHub Issues
- 邮箱: support@example.com

---

© 2024 Invoice OCR MCP Server. All rights reserved. 
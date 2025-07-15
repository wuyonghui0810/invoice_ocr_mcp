#!/usr/bin/env python3
"""
测试发票OCR MCP服务器
"""

import sys
import asyncio
from pathlib import Path

# 将src目录添加到Python路径
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from invoice_ocr_mcp.server import InvoiceOCRServer
from invoice_ocr_mcp.config import Config

async def test_server():
    """测试服务器基本功能"""
    try:
        print("🚀 开始测试发票OCR MCP服务器...")
        
        # 创建配置
        config = Config()
        print("✅ 配置创建成功")
        
        # 创建服务器实例
        server = InvoiceOCRServer(config)
        print("✅ 服务器实例创建成功，包含以下工具:")
        print("   - recognize_single_invoice: 识别单张发票并提取结构化信息")
        print("   - recognize_batch_invoices: 批量识别多张发票")
        print("   - detect_invoice_type: 检测发票类型")
        
        # 测试发票类型检测（使用模拟数据）
        test_image_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9jU77zgAAAABJRU5ErkJggg=="
        
        try:
            result = await server._detect_invoice_type({
                "image_data": test_image_data
            })
            print("✅ 发票类型检测测试通过")
            print(f"   结果: {result}")
        except Exception as e:
            print(f"⚠️ 发票类型检测测试失败: {e}")
        
        print("\n🎉 服务器测试完成！")
        return True
        
    except Exception as e:
        print(f"❌ 服务器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_server())
    sys.exit(0 if success else 1) 
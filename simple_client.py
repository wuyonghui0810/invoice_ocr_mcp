#!/usr/bin/env python3
"""
发票OCR 简单客户端测试脚本
直接调用服务器功能，无需通过MCP协议
"""

import sys
import asyncio
from pathlib import Path

# 将src目录添加到Python路径
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# 导入服务器模块
from invoice_ocr_mcp.server import InvoiceOCRServer
from invoice_ocr_mcp.config import Config

async def test_invoice_ocr():
    """测试发票OCR服务的各个功能"""
    print("🚀 开始测试发票OCR客户端...")
    
    try:
        # 创建配置和服务器实例
        config = Config()
        server = InvoiceOCRServer(config)
        print("✅ 服务器实例创建成功")
        
        # 1. 测试发票类型检测
        print("\n📄 测试发票类型检测...")
        # 使用一个示例Base64图像数据（1x1像素的透明PNG）
        sample_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+P+/HgAFhAJ/wlseKgAAAABJRU5ErkJggg=="
        
        try:
            result = await server._detect_invoice_type({
                "image_data": sample_image
            })
            print(f"✅ 发票类型检测结果: {result}")
        except Exception as e:
            print(f"❌ 发票类型检测失败: {e}")
        
        # 2. 测试单张发票识别
        print("\n📄 测试单张发票识别...")
        try:
            result = await server._recognize_single_invoice({
                "image_data": sample_image,
                "output_format": "standard"
            })
            print(f"✅ 单张发票识别结果: {result}")
        except Exception as e:
            print(f"❌ 单张发票识别失败: {e}")
        
        # 3. 测试批量发票识别
        print("\n📄 测试批量发票识别...")
        try:
            result = await server._recognize_batch_invoices({
                "images": [
                    {"image_data": sample_image},
                    {"image_data": sample_image}
                ],
                "output_format": "standard"
            })
            print(f"✅ 批量发票识别结果: {result}")
        except Exception as e:
            print(f"❌ 批量发票识别失败: {e}")
            
        print("\n🎉 客户端测试完成！")
        
    except Exception as e:
        print(f"❌ 服务器初始化失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_invoice_ocr()) 
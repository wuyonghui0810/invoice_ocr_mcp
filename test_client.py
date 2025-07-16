#!/usr/bin/env python3
"""
发票OCR MCP客户端测试脚本
"""

import asyncio
import base64
from pathlib import Path
import httpx

async def test_invoice_ocr():
    """测试发票OCR服务的各个功能"""
    print("🚀 开始测试发票OCR客户端...")
    
    # 使用httpx客户端
    async with httpx.AsyncClient() as client:
        print("✅ HTTP客户端创建成功")
        
        # 1. 测试发票类型检测
        print("\n📄 测试发票类型检测...")
        # 使用一个示例Base64图像数据
        sample_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+P+/HgAFhAJ/wlseKgAAAABJRU5ErkJggg=="
        
        try:
            response = await client.post(
                "http://localhost:8000/tools/detect_invoice_type",
                json={
                    "image_data": sample_image
                }
            )
            result = response.json()
            print(f"✅ 发票类型检测结果: {result}")
        except Exception as e:
            print(f"❌ 发票类型检测失败: {e}")
        
        # 2. 测试单张发票识别
        print("\n📄 测试单张发票识别...")
        try:
            response = await client.post(
                "http://localhost:8000/tools/recognize_single_invoice",
                json={
                    "image_data": sample_image,
                    "output_format": "standard"
                }
            )
            result = response.json()
            print(f"✅ 单张发票识别结果: {result}")
        except Exception as e:
            print(f"❌ 单张发票识别失败: {e}")
        
        # 3. 测试批量发票识别
        print("\n📄 测试批量发票识别...")
        try:
            response = await client.post(
                "http://localhost:8000/tools/recognize_batch_invoices",
                json={
                    "images": [
                        {"image_data": sample_image},
                        {"image_data": sample_image}
                    ],
                    "output_format": "standard"
                }
            )
            result = response.json()
            print(f"✅ 批量发票识别结果: {result}")
        except Exception as e:
            print(f"❌ 批量发票识别失败: {e}")

if __name__ == "__main__":
    asyncio.run(test_invoice_ocr()) 
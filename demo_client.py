#!/usr/bin/env python3
"""
发票OCR 演示客户端
展示如何调用发票OCR服务
"""

import sys
import asyncio
import base64
from pathlib import Path
from PIL import Image
import io

# 将src目录添加到Python路径
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# 导入服务器模块
from invoice_ocr_mcp.server import InvoiceOCRServer
from invoice_ocr_mcp.config import Config

def create_sample_invoice_image():
    """创建一个示例发票图像的Base64编码"""
    # 创建一个简单的白色背景图像，模拟发票
    # img = Image.new('RGB', (400, 600), color='white')
    img = Image.open('tests/image/fp.png')
    # 转换为Base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_bytes = buffer.getvalue()
    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
    
    return img_base64

async def demo_invoice_ocr():
    """演示发票OCR功能"""
    print("🚀 发票OCR演示客户端启动...")
    print("=" * 50)
    
    try:
        # 创建配置和服务器实例
        config = Config()
        server = InvoiceOCRServer(config)
        print("✅ 发票OCR服务器初始化成功")
        
        # 创建示例发票图像
        sample_image = create_sample_invoice_image()
        print("✅ 示例发票图像创建成功")
        
        print("\n" + "=" * 50)
        print("📋 测试1: 发票类型检测")
        print("=" * 50)
        
        try:
            result = await server._detect_invoice_type({
                "image_data": sample_image
            })
            
            if result.get('success'):
                print(f"✅ 检测成功!")
                print(f"   发票类型: {result.get('invoice_type', '未知')}")
                print(f"   置信度: {result.get('confidence', 0):.2%}")
            else:
                print(f"ℹ️ 检测结果: {result.get('error', {}).get('message', '未知错误')}")
                
        except Exception as e:
            print(f"❌ 发票类型检测失败: {e}")
        
        print("\n" + "=" * 50)
        print("📋 测试2: 单张发票识别")
        print("=" * 50)
        
        try:
            result = await server._recognize_single_invoice({
                "image_data": sample_image,
                "output_format": "standard"
            })
            
            if result.get('success'):
                print(f"✅ 识别成功!")
                print(f"   发票号码: {result.get('invoice_number', '未识别')}")
                print(f"   开票日期: {result.get('invoice_date', '未识别')}")
                print(f"   金额: {result.get('amount', '未识别')}")
                print(f"   销售方: {result.get('seller_name', '未识别')}")
            else:
                print(f"ℹ️ 识别结果: {result.get('error', {}).get('message', '未知错误')}")
                
        except Exception as e:
            print(f"❌ 单张发票识别失败: {e}")
        
        print("\n" + "=" * 50)
        print("📋 测试3: 批量发票识别")
        print("=" * 50)
        
        try:
            result = await server._recognize_batch_invoices({
                "images": [
                    {"image_data": sample_image, "filename": "发票1.png"},
                    {"image_data": sample_image, "filename": "发票2.png"}
                ],
                "output_format": "standard"
            })
            
            if result.get('success'):
                results = result.get('results', [])
                print(f"✅ 批量识别成功! 共处理 {len(results)} 张发票")
                for i, invoice_result in enumerate(results, 1):
                    print(f"   发票{i}: {invoice_result.get('filename', f'发票{i}')}")
                    if invoice_result.get('success'):
                        print(f"      ✓ 识别成功")
                    else:
                        print(f"      ✗ 识别失败: {invoice_result.get('error', {}).get('message', '未知')}")
            else:
                print(f"ℹ️ 批量识别结果: {result.get('error', {}).get('message', '未知错误')}")
                
        except Exception as e:
            print(f"❌ 批量发票识别失败: {e}")
            
        print("\n" + "=" * 50)
        print("🎉 演示完成!")
        print("=" * 50)
        print("\n💡 使用说明:")
        print("1. 将真实发票图像转换为Base64格式")
        print("2. 调用相应的API接口")
        print("3. 处理返回的结果数据")
        print("\n📚 支持的发票类型:")
        print("- 增值税专用发票")
        print("- 增值税普通发票") 
        print("- 机动车销售统一发票")
        print("- 二手车销售统一发票")
        print("- 等13种发票类型...")
        
    except Exception as e:
        print(f"❌ 服务器初始化失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(demo_invoice_ocr()) 
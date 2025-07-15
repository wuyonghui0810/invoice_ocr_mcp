#!/usr/bin/env python3
"""
真实发票OCR测试客户端
使用用户提供的真实发票图片进行测试
"""

import sys
import asyncio
import base64
import json
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

def image_to_base64(image_path):
    """将图片文件转换为Base64编码"""
    try:
        with open(image_path, "rb") as image_file:
            # 读取图片数据
            image_data = image_file.read()
            # 转换为Base64
            base64_str = base64.b64encode(image_data).decode('utf-8')
            return base64_str
    except Exception as e:
        print(f"❌ 图片转换失败: {e}")
        return None

async def test_real_invoice():
    """测试真实发票图片"""
    print("🚀 真实发票OCR测试启动...")
    print("=" * 60)
    
    try:
        # 创建配置和服务器实例
        config = Config()
        server = InvoiceOCRServer(config)
        print("✅ 发票OCR服务器初始化成功")
        
        # 读取真实发票图片
        image_path = "fp.png"  # 用户上传的发票图片
        if not Path(image_path).exists():
            print(f"⚠️ 找不到图片文件: {image_path}")
            print("📝 正在创建示例发票图片进行测试...")
            
            # 创建一个示例发票图片
            from PIL import Image, ImageDraw, ImageFont
            
            # 创建白色背景图片
            img = Image.new('RGB', (800, 1000), color='white')
            draw = ImageDraw.Draw(img)
            
            # 添加发票内容（模拟用户提供的发票信息）
            try:
                # 尝试使用系统字体
                font = ImageFont.truetype("arial.ttf", 20)
            except:
                # 如果找不到字体，使用默认字体
                font = ImageFont.load_default()
            
            # 绘制发票信息
            lines = [
                "深圳电子普通发票",
                "发票代码: 144032509110",
                "发票号码: 08527037", 
                "开票日期: 2025年03月19日",
                "校验码: c7c7c",
                "",
                "购买方信息:",
                "名称: 深圳微众信用科技股份有限公司",
                "纳税人识别号: 91440300319331004W",
                "",
                "销售方信息:",
                "名称: 深圳市正君餐饮管理顾问有限公司",
                "纳税人识别号: 914403006641668556",
                "",
                "商品信息:",
                "*餐饮服务*餐费",
                "单价: 469.91  数量: 1",
                "金额: ¥469.91",
                "税率: 6%  税额: ¥28.19",
                "",
                "价税合计(大写): 肆佰玖拾捌元壹角整",
                "价税合计(小写): ¥498.10"
            ]
            
            y_position = 50
            for line in lines:
                draw.text((50, y_position), line, fill='black', font=font)
                y_position += 35
            
            # 保存图片
            img.save(image_path)
            print(f"✅ 示例发票图片已创建: {image_path}")
            print("💡 提示: 您可以将此文件替换为真实的发票图片进行测试")
            
        print(f"📄 正在处理发票图片: {image_path}")
        invoice_image_base64 = image_to_base64(image_path)
        
        if not invoice_image_base64:
            print("❌ 图片处理失败")
            return
            
        print("✅ 发票图片转换为Base64成功")
        print(f"   图片大小: {len(invoice_image_base64)} 字符")
        
        print("\n" + "=" * 60)
        print("📋 测试1: 发票类型检测")
        print("=" * 60)
        
        try:
            result = await server._detect_invoice_type({
                "image_data": invoice_image_base64
            })
            
            print("🔍 发票类型检测结果:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
        except Exception as e:
            print(f"❌ 发票类型检测失败: {e}")
        
        print("\n" + "=" * 60)
        print("📋 测试2: 单张发票识别 (标准格式)")
        print("=" * 60)
        
        try:
            result = await server._recognize_single_invoice({
                "image_data": invoice_image_base64,
                "output_format": "standard"
            })
            
            print("📄 单张发票识别结果 (标准格式):")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
        except Exception as e:
            print(f"❌ 单张发票识别失败: {e}")
            
        print("\n" + "=" * 60)
        print("📋 测试3: 单张发票识别 (详细格式)")
        print("=" * 60)
        
        try:
            result = await server._recognize_single_invoice({
                "image_data": invoice_image_base64,
                "output_format": "detailed"
            })
            
            print("📄 单张发票识别结果 (详细格式):")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
        except Exception as e:
            print(f"❌ 单张发票识别失败: {e}")
            
        print("\n" + "=" * 60)
        print("📋 测试4: 单张发票识别 (原始格式)")
        print("=" * 60)
        
        try:
            result = await server._recognize_single_invoice({
                "image_data": invoice_image_base64,
                "output_format": "raw"
            })
            
            print("📄 单张发票识别结果 (原始格式):")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
        except Exception as e:
            print(f"❌ 单张发票识别失败: {e}")
        
        print("\n" + "=" * 60)
        print("📋 测试5: 批量发票识别")
        print("=" * 60)
        
        try:
            result = await server._recognize_batch_invoices({
                "images": [
                    {
                        "image_data": invoice_image_base64,
                        "filename": "深圳电子普通发票.png"
                    }
                ],
                "output_format": "standard"
            })
            
            print("📊 批量发票识别结果:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
        except Exception as e:
            print(f"❌ 批量发票识别失败: {e}")
            
        print("\n" + "=" * 60)
        print("🎉 真实发票测试完成!")
        print("=" * 60)
        
        # 分析发票内容
        print("\n📊 从图片中可以看到的发票信息:")
        print("- 发票类型: 深圳电子普通发票")
        print("- 发票代码: 144032509110")
        print("- 发票号码: 08527037")
        print("- 开票日期: 2025年03月19日")
        print("- 校验码: c7c7c")
        print("- 购买方: 深圳微众信用科技股份有限公司")
        print("- 销售方: 深圳市正君餐饮管理顾问有限公司")
        print("- 商品名称: *餐饮服务*餐费")
        print("- 单价: 469.91")
        print("- 数量: 1")
        print("- 金额: ¥469.91")
        print("- 税率: 6%")
        print("- 税额: ¥28.19")
        print("- 价税合计: ¥498.10")
        
    except Exception as e:
        print(f"❌ 服务器初始化失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_real_invoice()) 
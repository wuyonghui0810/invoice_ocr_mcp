#!/usr/bin/env python3
"""
RapidOCR发票识别演示客户端

展示如何使用RapidOCR引擎进行发票OCR识别
"""

import asyncio
import sys
import os
import base64
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from invoice_ocr_mcp.server import InvoiceOCRServer
from invoice_ocr_mcp.config import Config


def analyze_text_content(text: str) -> str:
    """分析文本内容，识别其可能的含义"""
    import re
    
    text = text.strip().replace(':', '').replace(' ', '')
    
    # 发票代码模式 (通常10-12位数字)
    if re.match(r'^\d{10,12}$', text):
        return "可能是发票代码"
    
    # 发票号码模式 (通常6-8位数字)
    if re.match(r'^\d{6,8}$', text):
        return "可能是发票号码"
        
    # 日期模式
    if re.match(r'^\d{8}$', text) or re.match(r'^\d{4}[\s-]\d{2}[\s-]\d{2}$', text):
        return "可能是日期"
        
    # 金额模式
    if re.match(r'^\d+\.?\d*$', text) and len(text) >= 3:
        try:
            amount = float(text)
            if 0.01 <= amount <= 999999:
                return f"可能是金额 (¥{amount})"
        except:
            pass
            
    # 纳税人识别号模式
    if re.match(r'^[0-9A-Z]{15,20}$', text):
        return "可能是纳税人识别号"
        
    # 校验码模式
    if re.match(r'^[a-zA-Z0-9]{4,6}$', text) and len(text) <= 6:
        return "可能是校验码"
        
    return None


async def demo_invoice_recognition():
    """演示发票识别功能"""
    print("🚀 RapidOCR发票识别演示")
    print("=" * 50)
    
    # 创建配置，使用RapidOCR引擎
    config = Config()
    config.ocr_engine.engine_type = "rapidocr"
    
    # 创建服务器实例
    server = InvoiceOCRServer(config)
    
    try:
        print("📊 服务器已初始化完成!")
        print()
        
        # 测试发票图像
        test_image_path = "fp.png"  # 更改为正确的路径
        if not os.path.exists(test_image_path):
            print(f"❌ 测试图像 {test_image_path} 不存在")
            return
        
        # 读取并编码图像
        with open(test_image_path, 'rb') as f:
            image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        print(f"📷 正在识别发票图像: {test_image_path}")
        print(f"🖼️ 图像大小: {len(image_data)/1024:.1f} KB")
        print()
        
        # 1. 测试发票类型检测
        print("🏷️ 发票类型检测")
        print("-" * 30)
        
        detection_args = {
            "image_data": image_base64
        }
        
        detection_result = await server._detect_invoice_type(detection_args)
        
        if detection_result.get("success"):
            data = detection_result["data"]
            print(f"✅ 检测成功!")
            invoice_type = data.get('invoice_type', {})
            print(f"   发票类型: {invoice_type.get('name', '未知')}")
            print(f"   置信度: {invoice_type.get('confidence', 0):.3f}")
            candidates = data.get('candidates', [])
            if candidates:
                print(f"   候选类型:")
                for candidate in candidates[:3]:  # 显示前3个
                    print(f"     - {candidate.get('name')}: {candidate.get('confidence', 0):.3f}")
            # 添加检测关键词显示
            detected_keywords = data.get('detected_keywords', [])
            if detected_keywords:
                print(f"   检测关键词: {detected_keywords}")
        else:
            print(f"❌ 检测失败: {detection_result.get('error')}")
        
        print()
        
        # 2. 测试单张发票识别
        print("📝 单张发票识别")
        print("-" * 30)
        
        recognition_args = {
            "image_data": image_base64,
            "output_format": "detailed"
        }
        
        recognition_result = await server._recognize_single_invoice(recognition_args)
        
        if recognition_result.get("success"):
            data = recognition_result["data"]
            print(f"✅ 识别成功!{data}")
            invoice_type = data.get('invoice_type', {})
            print(f"   发票类型: {invoice_type.get('name', '未知')} (置信度: {invoice_type.get('confidence', 0):.3f})")
            
            # 显示提取的关键信息
            extracted_info = data.get('extracted_info', {})
            basic_info = data.get('basic_info', {})
            if extracted_info or basic_info:
                print(f"   📋 提取的发票信息:")
                all_info = {**extracted_info, **basic_info}
                for key, value in all_info.items():
                    if value:  # 只显示有值的字段
                        print(f"     ✓ {key}: {value}")
            
            # 显示检测的关键词
            detected_keywords = data.get('detected_keywords', [])
            if detected_keywords:
                print(f"   🔍 检测关键词: {detected_keywords}")
            
            # 分析识别的文本区域
            text_regions = data.get('text_regions', [])
            print(f"   📄 OCR识别详情 ({len(text_regions)}个文本区域):")
            
            if text_regions:
                # 尝试从识别文本中提取有用信息
                print(f"   🔢 识别到的关键数据:")
                for i, region in enumerate(text_regions, 1):
                    text = region.get('text', '')
                    confidence = region.get('confidence', 0)
                    
                    # 分析文本内容
                    analysis = analyze_text_content(text)
                    if analysis:
                        print(f"     {i}. {text} → {analysis} (置信度: {confidence:.3f})")
                    elif i <= 20:  # 只显示前10个普通文本
                        print(f"     {i}. {text} (置信度: {confidence:.3f})")
                
                if len(text_regions) > 20:
                    print(f"     ... 还有 {len(text_regions) - 20} 个文本区域")
            else:
                print(f"     ⚠️  未识别到文本内容")
                
        else:
            print(f"❌ 识别失败: {recognition_result.get('error')}")
        
        print()
        
        # 3. 测试批量识别（单张）
        # print("🔄 批量发票识别")
        # print("-" * 30)
        
        # batch_args = {
        #     "images": [
        #         {
        #             "id": "test_invoice_001",
        #             "image_data": image_base64
        #         }
        #     ],
        #     "parallel_count": 1,
        #     "output_format": "standard"
        # }
        
        # batch_result = await server._recognize_batch_invoices(batch_args)
        
        # if batch_result.get("success"):
        #     data = batch_result["data"]
        #     statistics = data.get("statistics", {})
        #     results = data.get("results", [])
            
        #     print(f"✅ 批量识别完成!")
        #     print(f"   总数量: {statistics.get('total_count', 0)}")
        #     print(f"   成功: {statistics.get('success_count', 0)}")
        #     print(f"   失败: {statistics.get('failed_count', 0)}")
        #     print(f"   处理时间: {statistics.get('total_time', 0):.2f}秒")
            
        #     if results:
        #         result = results[0]
        #         if result.get("success"):
        #             invoice_data = result.get("data", {})
        #             print(f"   识别结果:")
        #             print(f"     类型: {invoice_data.get('invoice_type')}")
        #             print(f"     置信度: {invoice_data.get('confidence', 0):.3f}")
                    
        #             basic_info = invoice_data.get('basic_info', {})
        #             if basic_info:
        #                 print(f"     基本信息:")
        #                 for key, value in basic_info.items():
        #                     print(f"       {key}: {value}")
                
        # else:
        #     print(f"❌ 批量识别失败: {batch_result.get('error')}")
        
        # print()
        # print("🎉 演示完成!")
        
    except Exception as e:
        print(f"❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理资源
        if hasattr(server, 'ocr_engine') and hasattr(server.ocr_engine, 'cleanup'):
            await server.ocr_engine.cleanup()


async def main():
    """主函数"""
    print("=" * 60)
    print("🌟 发票识别系统演示")
    print("=" * 60)
    print()
    
    await demo_invoice_recognition()
    
    print()
    print("=" * 60)
    print("✨ 演示结束!")
if __name__ == "__main__":
    asyncio.run(main()) 
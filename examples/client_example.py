#!/usr/bin/env python3
"""
Invoice OCR MCP 客户端使用示例

演示如何使用MCP客户端连接到发票OCR服务器并进行识别
"""

import asyncio
import base64
import logging
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InvoiceOCRClient:
    """发票OCR客户端"""
    
    def __init__(self, server_command=None):
        """初始化客户端
        
        Args:
            server_command: 服务器启动命令，默认使用本地服务器
        """
        if server_command is None:
            server_path = project_root / "src" / "invoice_ocr_mcp" / "server.py"
            server_command = ["python", str(server_path)]
        
        self.server_command = server_command
        logger.info(f"初始化客户端，服务器命令: {' '.join(server_command)}")
    
    async def recognize_single_invoice(self, image_path, output_format="standard"):
        """识别单张发票
        
        Args:
            image_path: 发票图像文件路径
            output_format: 输出格式 (standard/detailed/raw)
        
        Returns:
            识别结果
        """
        logger.info(f"开始识别发票: {image_path}")
        
        # 读取图像文件
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图像文件不存在: {image_path}")
        
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()
        
        # 连接MCP服务器
        async with stdio_client(self.server_command) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                # 初始化会话
                await session.initialize()
                
                # 调用识别工具
                result = await session.call_tool(
                    "recognize_single_invoice",
                    {
                        "image_data": image_data,
                        "output_format": output_format
                    }
                )
                
                return result
    
    async def recognize_batch_invoices(self, image_paths, parallel_count=3):
        """批量识别发票
        
        Args:
            image_paths: 图像文件路径列表
            parallel_count: 并行处理数量
        
        Returns:
            批量识别结果
        """
        logger.info(f"开始批量识别 {len(image_paths)} 张发票")
        
        # 准备图像数据
        images = []
        for i, image_path in enumerate(image_paths):
            if not os.path.exists(image_path):
                logger.warning(f"图像文件不存在，跳过: {image_path}")
                continue
            
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
            
            images.append({
                "id": f"invoice_{i+1}_{Path(image_path).name}",
                "image_data": image_data
            })
        
        if not images:
            raise ValueError("没有有效的图像文件")
        
        # 连接MCP服务器
        async with stdio_client(self.server_command) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                
                # 调用批量识别工具
                result = await session.call_tool(
                    "recognize_batch_invoices",
                    {
                        "images": images,
                        "parallel_count": parallel_count
                    }
                )
                
                return result
    
    async def detect_invoice_type(self, image_path):
        """检测发票类型
        
        Args:
            image_path: 发票图像文件路径
        
        Returns:
            发票类型检测结果
        """
        logger.info(f"开始检测发票类型: {image_path}")
        
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图像文件不存在: {image_path}")
        
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()
        
        async with stdio_client(self.server_command) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                
                result = await session.call_tool(
                    "detect_invoice_type",
                    {"image_data": image_data}
                )
                
                return result


def print_recognition_result(result):
    """打印识别结果"""
    if result.get("success"):
        data = result["data"]
        print("\n" + "="*50)
        print("📄 发票识别结果")
        print("="*50)
        
        # 发票类型
        invoice_type = data.get("invoice_type", {})
        print(f"🏷️  发票类型: {invoice_type.get('name', 'Unknown')} ({invoice_type.get('code', 'N/A')})")
        print(f"🎯 置信度: {invoice_type.get('confidence', 0):.2%}")
        
        # 基本信息
        basic_info = data.get("basic_info", {})
        print(f"\n📋 基本信息:")
        print(f"   发票号码: {basic_info.get('invoice_number', 'N/A')}")
        print(f"   开票日期: {basic_info.get('invoice_date', 'N/A')}")
        print(f"   总金额: ¥{basic_info.get('total_amount', 'N/A')}")
        print(f"   税额: ¥{basic_info.get('tax_amount', 'N/A')}")
        print(f"   不含税金额: ¥{basic_info.get('amount_without_tax', 'N/A')}")
        
        # 销售方信息
        seller_info = data.get("seller_info", {})
        print(f"\n🏢 销售方信息:")
        print(f"   名称: {seller_info.get('name', 'N/A')}")
        print(f"   税号: {seller_info.get('tax_id', 'N/A')}")
        print(f"   地址: {seller_info.get('address', 'N/A')}")
        print(f"   电话: {seller_info.get('phone', 'N/A')}")
        
        # 购买方信息
        buyer_info = data.get("buyer_info", {})
        print(f"\n🛒 购买方信息:")
        print(f"   名称: {buyer_info.get('name', 'N/A')}")
        print(f"   税号: {buyer_info.get('tax_id', 'N/A')}")
        
        # 商品明细
        items = data.get("items", [])
        if items:
            print(f"\n📦 商品明细 ({len(items)}项):")
            for i, item in enumerate(items[:3], 1):  # 只显示前3项
                print(f"   {i}. {item.get('name', 'N/A')} - ¥{item.get('amount', 'N/A')}")
            if len(items) > 3:
                print(f"   ... 还有 {len(items) - 3} 项")
        
        # 处理信息
        meta = data.get("meta", {})
        print(f"\n⚡ 处理信息:")
        print(f"   处理时间: {meta.get('processing_time', 0):.2f}秒")
        print(f"   总体置信度: {meta.get('confidence_score', 0):.2%}")
        
    else:
        error = result.get("error", {})
        print(f"\n❌ 识别失败: {error.get('message', '未知错误')}")
        print(f"错误代码: {error.get('code', 'N/A')}")


def print_batch_results(result):
    """打印批量识别结果"""
    if result.get("success"):
        data = result["data"]
        print("\n" + "="*60)
        print("📄 批量发票识别结果")
        print("="*60)
        
        print(f"📊 统计信息:")
        print(f"   总计: {data['total_count']} 张")
        print(f"   成功: {data['success_count']} 张")
        print(f"   失败: {data['failed_count']} 张")
        print(f"   成功率: {data['success_count']/data['total_count']:.1%}")
        
        meta = data.get("meta", {})
        print(f"\n⚡ 性能信息:")
        print(f"   总处理时间: {meta.get('total_processing_time', 0):.2f}秒")
        print(f"   平均处理时间: {meta.get('average_processing_time', 0):.2f}秒/张")
        
        print(f"\n📋 详细结果:")
        for item in data["results"]:
            status_icon = "✅" if item["status"] == "success" else "❌"
            print(f"   {status_icon} {item['id']}: {item['status']}")
            
            if item["status"] == "success":
                invoice_data = item.get("data", {})
                invoice_type = invoice_data.get("invoice_type", {})
                basic_info = invoice_data.get("basic_info", {})
                print(f"      类型: {invoice_type.get('name', 'Unknown')}")
                print(f"      金额: ¥{basic_info.get('total_amount', 'N/A')}")
            else:
                print(f"      错误: {item.get('error', 'Unknown error')}")
    else:
        error = result.get("error", {})
        print(f"\n❌ 批量识别失败: {error.get('message', '未知错误')}")


async def demo_single_recognition():
    """单张识别演示"""
    print("\n🚀 单张发票识别演示")
    print("-" * 30)
    
    client = InvoiceOCRClient()
    
    # 这里使用示例图片路径，实际使用时替换为真实路径
    test_image_path = "test_invoice.jpg"
    
    # 检查测试图片是否存在
    if not os.path.exists(test_image_path):
        print(f"⚠️  测试图片不存在: {test_image_path}")
        print("请将发票图片重命名为 'test_invoice.jpg' 并放在当前目录下")
        return
    
    try:
        result = await client.recognize_single_invoice(test_image_path)
        print_recognition_result(result)
    except Exception as e:
        logger.error(f"识别失败: {e}")
        print(f"❌ 识别过程中出现错误: {e}")


async def demo_batch_recognition():
    """批量识别演示"""
    print("\n🚀 批量发票识别演示")
    print("-" * 30)
    
    client = InvoiceOCRClient()
    
    # 查找当前目录下的图片文件
    image_extensions = ['.jpg', '.jpeg', '.png', '.webp']
    image_files = []
    
    for ext in image_extensions:
        image_files.extend(Path('.').glob(f'*{ext}'))
        image_files.extend(Path('.').glob(f'*{ext.upper()}'))
    
    if not image_files:
        print("⚠️  当前目录下没有找到图片文件")
        print("请在当前目录下放置一些发票图片文件 (支持 .jpg, .png, .webp 格式)")
        return
    
    # 只处理前5张图片
    image_files = list(image_files)[:5]
    image_paths = [str(f) for f in image_files]
    
    print(f"📁 找到 {len(image_paths)} 张图片: {[f.name for f in image_files]}")
    
    try:
        result = await client.recognize_batch_invoices(image_paths, parallel_count=3)
        print_batch_results(result)
    except Exception as e:
        logger.error(f"批量识别失败: {e}")
        print(f"❌ 批量识别过程中出现错误: {e}")


async def demo_type_detection():
    """类型检测演示"""
    print("\n🚀 发票类型检测演示")
    print("-" * 30)
    
    client = InvoiceOCRClient()
    
    test_image_path = "test_invoice.jpg"
    
    if not os.path.exists(test_image_path):
        print(f"⚠️  测试图片不存在: {test_image_path}")
        return
    
    try:
        result = await client.detect_invoice_type(test_image_path)
        
        if result.get("success"):
            data = result["data"]
            print(f"\n🏷️  发票类型检测结果:")
            
            invoice_type = data.get("invoice_type", {})
            print(f"   类型: {invoice_type.get('name', 'Unknown')}")
            print(f"   代码: {invoice_type.get('code', 'N/A')}")
            print(f"   置信度: {invoice_type.get('confidence', 0):.2%}")
            
            candidates = data.get("candidates", [])
            if len(candidates) > 1:
                print(f"\n📊 候选类型:")
                for i, candidate in enumerate(candidates[:3], 1):
                    print(f"   {i}. {candidate.get('name')} - {candidate.get('confidence', 0):.2%}")
        else:
            error = result.get("error", {})
            print(f"❌ 类型检测失败: {error.get('message', '未知错误')}")
            
    except Exception as e:
        logger.error(f"类型检测失败: {e}")
        print(f"❌ 类型检测过程中出现错误: {e}")


async def main():
    """主函数"""
    print("🎯 Invoice OCR MCP 客户端演示")
    print("=" * 50)
    
    print("\n📝 使用说明:")
    print("1. 确保 Invoice OCR MCP 服务器可以正常启动")
    print("2. 在当前目录下放置发票图片文件进行测试")
    print("3. 支持的图片格式: JPG, PNG, WebP")
    
    try:
        # 演示各项功能
        await demo_single_recognition()
        await demo_batch_recognition()
        await demo_type_detection()
        
        print("\n✅ 演示完成!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断了程序")
    except Exception as e:
        logger.error(f"演示过程中出现错误: {e}", exc_info=True)
        print(f"\n❌ 演示过程中出现错误: {e}")


if __name__ == "__main__":
    # 设置异步事件循环（Windows兼容性）
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # 运行演示
    asyncio.run(main()) 
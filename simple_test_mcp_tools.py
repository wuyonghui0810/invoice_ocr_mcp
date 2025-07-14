#!/usr/bin/env python3
"""
简化的发票OCR MCP工具测试脚本

快速验证3个标准MCP工具的可用性
"""

import asyncio
import base64
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

print("🎯 发票OCR MCP工具简化测试")
print("="*50)

def create_test_image_data() -> str:
    """创建测试用的Base64图像数据"""
    png_data = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\xdac\xf8\x0f'
        b'\x00\x00\x01\x00\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    return base64.b64encode(png_data).decode('utf-8')

async def test_tools():
    """测试MCP工具"""
    try:
        # 动态导入避免配置问题
        from invoice_ocr_mcp.server import InvoiceOCRServer
        from invoice_ocr_mcp.config import Config
        
        print("✅ 1. 模块导入成功")
        
        # 创建配置
        config = Config()
        print("✅ 2. 配置创建成功")
        
        # 使用简化的日志设置
        import logging
        logging.basicConfig(level=logging.INFO)
        
        # Mock掉复杂的组件
        with patch('invoice_ocr_mcp.modules.utils.setup_logging') as mock_logging:
            mock_logging.return_value = logging.getLogger(__name__)
            
            # 创建服务器
            server = InvoiceOCRServer(config)
            print("✅ 3. 服务器创建成功")
            
            # 检查工具注册
            tools = server.get_tools()
            tool_names = [tool.name for tool in tools]
            
            print(f"\n📋 已注册的MCP工具数量: {len(tools)}")
            
            expected_tools = [
                "recognize_single_invoice",
                "recognize_batch_invoices", 
                "detect_invoice_type"
            ]
            
            results = {}
            
            for tool_name in expected_tools:
                if tool_name in tool_names:
                    tool = next(t for t in tools if t.name == tool_name)
                    print(f"✅ {tool_name}: 已注册")
                    print(f"   描述: {tool.description}")
                    
                    # 检查输入Schema
                    schema = tool.inputSchema
                    if schema and "properties" in schema:
                        properties = schema["properties"]
                        print(f"   输入参数: {list(properties.keys())}")
                    
                    results[tool_name] = {
                        "registered": True,
                        "description": tool.description,
                        "has_schema": bool(schema and "properties" in schema)
                    }
                else:
                    print(f"❌ {tool_name}: 未注册")
                    results[tool_name] = {"registered": False}
            
            # 统计结果
            registered_count = sum(1 for r in results.values() if r.get("registered", False))
            success_rate = (registered_count / len(expected_tools)) * 100
            
            print(f"\n📊 测试结果统计:")
            print(f"   期望工具数: {len(expected_tools)}")
            print(f"   已注册工具: {registered_count}")
            print(f"   注册成功率: {success_rate:.1f}%")
            
            if success_rate == 100:
                print("\n🎉 所有MCP工具均已正确注册！")
                return True
            else:
                print(f"\n⚠️ {len(expected_tools) - registered_count} 个工具未注册")
                return False
                
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_tool_execution():
    """测试工具执行逻辑（模拟）"""
    try:
        print("\n🔧 测试工具执行逻辑...")
        
        # Mock modelscope
        with patch('invoice_ocr_mcp.modules.ocr_engine.pipeline') as mock_pipeline:
            # 设置Mock返回值
            def mock_model(input_data):
                return {
                    "polygons": [{"polygon": [[10, 10], [100, 10], [100, 50], [10, 50]]}],
                    "text": "测试文本",
                    "scores": [0.95, 0.03, 0.02],
                    "labels": ["增值税专用发票", "增值税普通发票", "其他"]
                }
            
            mock_pipeline.return_value = mock_model
            
            # 测试OCR引擎基本功能
            from invoice_ocr_mcp.modules.ocr_engine import OCREngine
            from invoice_ocr_mcp.config import Config
            
            config = Config()
            engine = OCREngine(config)
            print("✅ OCR引擎创建成功")
            
            # 测试发票解析器
            from invoice_ocr_mcp.modules.invoice_parser import InvoiceParser
            parser = InvoiceParser(config)
            print("✅ 发票解析器创建成功")
            
            # 测试批量处理器
            from invoice_ocr_mcp.modules.batch_processor import BatchProcessor
            batch_processor = BatchProcessor(config)
            print("✅ 批量处理器创建成功")
            
            print("✅ 所有核心组件创建成功")
            return True
            
    except Exception as e:
        print(f"❌ 组件测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    print("开始执行MCP工具测试...\n")
    
    # 测试1: 工具注册
    print("📝 测试1: MCP工具注册检查")
    tool_registration_ok = await test_tools()
    
    # 测试2: 组件创建
    print("\n📝 测试2: 核心组件创建检查")  
    component_creation_ok = await test_tool_execution()
    
    # 总结
    print(f"\n{'='*50}")
    print("🎯 测试总结:")
    print(f"   工具注册测试: {'✅ 通过' if tool_registration_ok else '❌ 失败'}")
    print(f"   组件创建测试: {'✅ 通过' if component_creation_ok else '❌ 失败'}")
    
    overall_success = tool_registration_ok and component_creation_ok
    
    if overall_success:
        print("\n🎉 所有测试通过！MCP工具基础功能正常。")
        print("\n📝 测试结论:")
        print("   ✅ recognize_single_invoice: 工具已注册，基础组件可用")
        print("   ✅ recognize_batch_invoices: 工具已注册，基础组件可用") 
        print("   ✅ detect_invoice_type: 工具已注册，基础组件可用")
        print("\n💡 备注: 实际使用时需要配置ModelScope API Token和模型。")
        
        return 0
    else:
        print("\n❌ 存在问题，需要修复后再测试。")
        return 1

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 
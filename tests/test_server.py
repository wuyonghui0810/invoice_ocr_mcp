"""
MCP服务器测试
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from invoice_ocr_mcp.server import InvoiceOCRServer
from invoice_ocr_mcp.config import Config


class TestInvoiceOCRServer:
    """MCP服务器测试类"""
    
    @pytest.fixture
    def server(self, test_config):
        """创建测试服务器实例"""
        with patch('invoice_ocr_mcp.server.OCREngine'), \
             patch('invoice_ocr_mcp.server.InvoiceParser'), \
             patch('invoice_ocr_mcp.server.ImageProcessor'), \
             patch('invoice_ocr_mcp.server.BatchProcessor'):
            return InvoiceOCRServer(test_config)
    
    def test_server_initialization(self, server):
        """测试服务器初始化"""
        assert server is not None
        assert server.config is not None
        assert hasattr(server, 'server')
        assert hasattr(server, 'ocr_engine')
        assert hasattr(server, 'invoice_parser')
        assert hasattr(server, 'image_processor')
        assert hasattr(server, 'batch_processor')
    
    @pytest.mark.asyncio
    async def test_recognize_single_invoice_with_base64(self, server, sample_base64_image):
        """测试单张发票识别（Base64输入）"""
        # Mock依赖组件
        server.image_processor.decode_base64_image = AsyncMock()
        server.image_processor.preprocess_image = AsyncMock()
        server.ocr_engine.full_ocr_pipeline = AsyncMock(return_value={
            "processing_time": 1.0
        })
        server.invoice_parser.parse_invoice = AsyncMock(return_value={
            "invoice_type": {"name": "增值税专用发票"},
            "basic_info": {"invoice_number": "12345678"}
        })
        
        # 执行测试
        result = await server._recognize_single_invoice_impl(
            image_data=sample_base64_image,
            output_format="standard"
        )
        
        # 验证结果
        assert result is not None
        assert "invoice_type" in result
        assert "basic_info" in result
    
    @pytest.mark.asyncio
    async def test_recognize_single_invoice_with_url(self, server):
        """测试单张发票识别（URL输入）"""
        # Mock依赖组件
        server.image_processor.download_image = AsyncMock()
        server.image_processor.preprocess_image = AsyncMock()
        server.ocr_engine.full_ocr_pipeline = AsyncMock(return_value={
            "processing_time": 1.0
        })
        server.invoice_parser.parse_invoice = AsyncMock(return_value={
            "invoice_type": {"name": "增值税专用发票"},
            "basic_info": {"invoice_number": "12345678"}
        })
        
        # 执行测试
        result = await server._recognize_single_invoice_impl(
            image_url="https://example.com/invoice.jpg",
            output_format="standard"
        )
        
        # 验证结果
        assert result is not None
        assert "invoice_type" in result
        assert "basic_info" in result
    
    @pytest.mark.asyncio
    async def test_recognize_single_invoice_validation_error(self, server):
        """测试单张发票识别验证错误"""
        # 测试无输入参数
        with pytest.raises(ValueError, match="必须提供"):
            await server._recognize_single_invoice_impl()
    
    @pytest.mark.asyncio
    async def test_recognize_batch_invoices(self, server, sample_batch_input):
        """测试批量发票识别"""
        # Mock批量处理器
        server.batch_processor.process_batch = AsyncMock(return_value={
            "success": True,
            "batch_id": "test_batch_123",
            "results": [
                {"id": "invoice_001", "success": True},
                {"id": "invoice_002", "success": True},
                {"id": "invoice_003", "success": True}
            ],
            "statistics": {
                "total": 3,
                "successful": 3,
                "failed": 0,
                "success_rate": 1.0
            }
        })
        
        # 执行测试
        result = await server._recognize_batch_invoices_impl(
            images=sample_batch_input,
            parallel_count=3
        )
        
        # 验证结果
        assert result["success"] is True
        assert len(result["results"]) == 3
        assert result["statistics"]["successful"] == 3
    
    @pytest.mark.asyncio
    async def test_detect_invoice_type(self, server, sample_base64_image):
        """测试发票类型检测"""
        # Mock依赖组件
        server.image_processor.decode_base64_image = AsyncMock()
        server.image_processor.preprocess_image = AsyncMock()
        server.ocr_engine.classify_invoice_type = AsyncMock(return_value={
            "type": "增值税专用发票",
            "confidence": 0.95
        })
        
        # 执行测试
        result = await server._detect_invoice_type_impl(
            image_data=sample_base64_image
        )
        
        # 验证结果
        assert result["type"] == "增值税专用发票"
        assert result["confidence"] == 0.95
    
    @pytest.mark.asyncio
    async def test_error_handling(self, server, sample_base64_image):
        """测试错误处理"""
        # Mock异常
        server.image_processor.decode_base64_image = AsyncMock(
            side_effect=Exception("解码失败")
        )
        
        # 执行测试并验证异常处理
        with pytest.raises(Exception):
            await server._recognize_single_invoice_impl(
                image_data=sample_base64_image
            )
    
    def test_tool_registration(self, server):
        """测试工具注册"""
        # 验证工具是否正确注册
        # 这里需要根据实际的MCP服务器实现来测试
        assert hasattr(server, 'server')
        # 可以添加更多具体的工具注册验证


class TestServerIntegration:
    """服务器集成测试"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_recognition_pipeline(self, test_config, sample_base64_image):
        """测试完整识别流程"""
        # 这里需要模拟完整的识别流程
        # 由于涉及ModelScope模型，在CI环境中可能需要mock
        pass
    
    @pytest.mark.integration
    def test_server_startup_shutdown(self, test_config):
        """测试服务器启动和关闭"""
        with patch('invoice_ocr_mcp.server.OCREngine'), \
             patch('invoice_ocr_mcp.server.InvoiceParser'), \
             patch('invoice_ocr_mcp.server.ImageProcessor'), \
             patch('invoice_ocr_mcp.server.BatchProcessor'):
            
            server = InvoiceOCRServer(test_config)
            
            # 测试初始化
            assert server is not None
            
            # 测试清理（如果有的话）
            if hasattr(server, 'cleanup'):
                # server.cleanup() 
                pass 
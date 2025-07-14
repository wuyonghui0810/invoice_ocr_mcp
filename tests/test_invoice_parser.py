"""
发票解析器测试
"""

import pytest
from unittest.mock import Mock, AsyncMock
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from invoice_ocr_mcp.modules.invoice_parser import InvoiceParser


class TestInvoiceParser:
    """发票解析器测试类"""
    
    @pytest.fixture
    def invoice_parser(self, test_config):
        """创建发票解析器实例"""
        return InvoiceParser(test_config)
    
    def test_invoice_parser_initialization(self, invoice_parser):
        """测试发票解析器初始化"""
        assert invoice_parser is not None
        assert invoice_parser.config is not None
        assert hasattr(invoice_parser, 'invoice_types')
        assert len(invoice_parser.invoice_types) > 0
    
    @pytest.mark.asyncio
    async def test_parse_invoice_standard_format(self, invoice_parser, sample_ocr_result):
        """测试标准格式发票解析"""
        result = await invoice_parser.parse_invoice(sample_ocr_result, "standard")
        
        assert result is not None
        assert "invoice_type" in result
        assert "basic_info" in result
        assert "seller_info" in result
        assert "buyer_info" in result
        assert "items" in result
        assert "verification" in result
        assert "meta" in result
    
    @pytest.mark.asyncio
    async def test_parse_invoice_detailed_format(self, invoice_parser, sample_ocr_result):
        """测试详细格式发票解析"""
        result = await invoice_parser.parse_invoice(sample_ocr_result, "detailed")
        
        assert result is not None
        assert "raw_ocr_result" in result
        assert "parsing_details" in result
    
    @pytest.mark.asyncio
    async def test_parse_invoice_raw_format(self, invoice_parser, sample_ocr_result):
        """测试原始格式发票解析"""
        result = await invoice_parser.parse_invoice(sample_ocr_result, "raw")
        
        # 原始格式应该直接返回OCR结果
        assert result == sample_ocr_result
    
    def test_parse_invoice_type(self, invoice_parser):
        """测试发票类型解析"""
        classification = {
            "type": "增值税专用发票",
            "confidence": 0.95
        }
        
        result = invoice_parser._parse_invoice_type(classification)
        
        assert result["code"] == "01"
        assert result["name"] == "增值税专用发票"
        assert result["confidence"] == 0.95
    
    @pytest.mark.asyncio
    async def test_parse_basic_info(self, invoice_parser):
        """测试基本信息解析"""
        texts = [
            "发票号码: 12345678",
            "开票日期: 2024-01-15",
            "合计金额: ￥1000.00",
            "税额: ￥130.00"
        ]
        
        result = await invoice_parser._parse_basic_info(texts)
        
        assert "invoice_number" in result
        assert "invoice_date" in result
        assert "total_amount" in result
        assert "tax_amount" in result
    
    def test_extract_invoice_number(self, invoice_parser):
        """测试发票号码提取"""
        texts = [
            "增值税专用发票",
            "发票号码: 12345678",
            "开票日期: 2024-01-15"
        ]
        
        number = invoice_parser._extract_invoice_number(texts)
        assert number == "12345678"
    
    def test_extract_date(self, invoice_parser):
        """测试日期提取"""
        text = "开票日期: 2024年1月15日"
        date = invoice_parser._extract_date(text)
        assert date == "2024-01-15"
    
    def test_extract_amounts(self, invoice_parser):
        """测试金额提取"""
        texts = [
            "合计金额: ￥1000.00",
            "税额: ￥130.00",
            "不含税金额: ￥870.00"
        ]
        
        amounts = invoice_parser._extract_amounts(texts)
        
        assert amounts["total"] == "1000.00"
        assert amounts["tax"] == "130.00"
        assert amounts["without_tax"] == "870.00"
    
    def test_extract_tax_id(self, invoice_parser):
        """测试税号提取"""
        text = "纳税人识别号: 91110000123456789X"
        tax_id = invoice_parser._extract_tax_id(text)
        assert tax_id == "91110000123456789X"
    
    def test_extract_phone(self, invoice_parser):
        """测试电话号码提取"""
        text = "联系电话: 010-12345678"
        phone = invoice_parser._extract_phone(text)
        assert phone == "010-12345678"
    
    def test_calculate_confidence(self, invoice_parser, sample_ocr_result):
        """测试置信度计算"""
        confidence = invoice_parser._calculate_confidence(sample_ocr_result)
        assert 0 <= confidence <= 1
        assert isinstance(confidence, float)
    
    def test_find_seller_section(self, invoice_parser):
        """测试销售方信息区域查找"""
        texts = [
            "增值税专用发票",
            "销售方: 测试科技有限公司",
            "税号: 91110000123456789X",
            "地址: 北京市朝阳区",
            "购买方: 客户公司"
        ]
        
        seller_texts = invoice_parser._find_seller_section(texts)
        assert len(seller_texts) >= 2
        assert any("销售方" in text for text in seller_texts)
    
    def test_find_buyer_section(self, invoice_parser):
        """测试购买方信息区域查找"""
        texts = [
            "销售方: 测试科技有限公司",
            "购买方: 客户公司",
            "税号: 91110000987654321Y",
            "地址: 北京市海淀区",
            "商品名称: 测试商品"
        ]
        
        buyer_texts = invoice_parser._find_buyer_section(texts)
        assert len(buyer_texts) >= 2
        assert any("购买方" in text for text in buyer_texts)


class TestInvoiceParserEdgeCases:
    """发票解析器边界情况测试"""
    
    @pytest.fixture
    def invoice_parser(self, test_config):
        """创建发票解析器实例"""
        return InvoiceParser(test_config)
    
    @pytest.mark.asyncio
    async def test_parse_empty_ocr_result(self, invoice_parser):
        """测试空OCR结果解析"""
        empty_result = {
            "recognized_texts": [],
            "invoice_classification": {},
            "processing_time": 0
        }
        
        result = await invoice_parser.parse_invoice(empty_result)
        
        assert result is not None
        assert result["meta"]["confidence_score"] == 0.3  # 基于空文本的低置信度
    
    def test_extract_invalid_date(self, invoice_parser):
        """测试无效日期提取"""
        text = "开票日期: 无效日期"
        date = invoice_parser._extract_date(text)
        assert date is None
    
    def test_extract_invalid_amount(self, invoice_parser):
        """测试无效金额提取"""
        text = "金额: 无效金额"
        amount = invoice_parser._extract_single_amount(text)
        assert amount is None
    
    def test_extract_no_tax_id(self, invoice_parser):
        """测试无税号情况"""
        text = "公司名称但无税号"
        tax_id = invoice_parser._extract_tax_id(text)
        assert tax_id is None 
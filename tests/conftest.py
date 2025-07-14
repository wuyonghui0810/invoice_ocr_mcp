"""
Pytest配置文件

提供测试的fixtures和配置
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock
import sys
import os

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from invoice_ocr_mcp.config import Config
from invoice_ocr_mcp.modules.ocr_engine import OCREngine
from invoice_ocr_mcp.modules.invoice_parser import InvoiceParser
from invoice_ocr_mcp.modules.image_processor import ImageProcessor
from invoice_ocr_mcp.modules.batch_processor import BatchProcessor
from invoice_ocr_mcp.modules.model_manager import ModelManager


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """创建临时目录"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def test_config(temp_dir):
    """测试配置"""
    config = Config()
    config.models.cache_dir = str(temp_dir / "models")
    config.processing.max_batch_size = 10
    config.processing.max_workers = 2
    config.processing.max_image_size = 2048
    return config


@pytest.fixture
def mock_ocr_engine(test_config):
    """Mock OCR引擎"""
    engine = Mock(spec=OCREngine)
    engine.config = test_config
    
    # Mock异步方法
    engine.initialize_models = AsyncMock()
    engine.detect_text_regions = AsyncMock(return_value=[
        {"polygon": [[10, 10], [100, 10], [100, 50], [10, 50]]}
    ])
    engine.recognize_text = AsyncMock(return_value=["测试文本"])
    engine.classify_invoice_type = AsyncMock(return_value={
        "type": "增值税专用发票",
        "confidence": 0.95
    })
    engine.extract_key_information = AsyncMock(return_value={
        "entities": {"金额": "1000.00"}
    })
    engine.full_ocr_pipeline = AsyncMock(return_value={
        "text_regions": [{"polygon": [[10, 10], [100, 10], [100, 50], [10, 50]]}],
        "recognized_texts": ["测试文本"],
        "invoice_classification": {"type": "增值税专用发票", "confidence": 0.95},
        "key_information": {"entities": {"金额": "1000.00"}},
        "processing_time": 1.0
    })
    
    return engine


@pytest.fixture
def mock_invoice_parser(test_config):
    """Mock发票解析器"""
    parser = Mock(spec=InvoiceParser)
    parser.config = test_config
    
    parser.parse_invoice = AsyncMock(return_value={
        "invoice_type": {"code": "01", "name": "增值税专用发票", "confidence": 0.95},
        "basic_info": {
            "invoice_number": "12345678",
            "invoice_date": "2024-01-15",
            "total_amount": "1000.00"
        },
        "seller_info": {"name": "测试公司"},
        "buyer_info": {"name": "购买方公司"},
        "items": [],
        "verification": {"is_valid": True},
        "meta": {"processing_time": 0.5, "confidence_score": 0.9}
    })
    
    return parser


@pytest.fixture
def mock_image_processor(test_config):
    """Mock图像处理器"""
    processor = Mock(spec=ImageProcessor)
    processor.config = test_config
    
    # Mock图像数据
    import numpy as np
    mock_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    
    processor.decode_base64_image = AsyncMock(return_value=mock_image)
    processor.download_image = AsyncMock(return_value=mock_image)
    processor.preprocess_image = AsyncMock(return_value=mock_image)
    processor.validate_image = AsyncMock(return_value=(True, "验证通过"))
    
    return processor


@pytest.fixture
def sample_base64_image():
    """示例Base64图像数据"""
    # 创建一个简单的1x1像素PNG图像的Base64编码
    import base64
    
    # PNG文件头 + 最小PNG数据
    png_data = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\xdac\xf8\x0f'
        b'\x00\x00\x01\x00\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    
    return base64.b64encode(png_data).decode('utf-8')


@pytest.fixture
def sample_batch_input(sample_base64_image):
    """示例批量输入数据"""
    return [
        {
            "id": "invoice_001",
            "image_data": sample_base64_image
        },
        {
            "id": "invoice_002", 
            "image_url": "https://example.com/invoice2.jpg"
        },
        {
            "id": "invoice_003",
            "image_data": sample_base64_image
        }
    ]


@pytest.fixture
def sample_ocr_result():
    """示例OCR识别结果"""
    return {
        "text_regions": [
            {"polygon": [[10, 10], [100, 10], [100, 50], [10, 50]]},
            {"polygon": [[10, 60], [200, 60], [200, 100], [10, 100]]}
        ],
        "recognized_texts": [
            "增值税专用发票",
            "发票号码: 12345678",
            "开票日期: 2024-01-15",
            "销售方: 测试科技有限公司",
            "购买方: 客户公司",
            "合计金额: ￥1000.00",
            "税额: ￥130.00"
        ],
        "invoice_classification": {
            "type": "增值税专用发票",
            "confidence": 0.95,
            "all_scores": {"增值税专用发票": 0.95, "增值税普通发票": 0.03}
        },
        "key_information": {
            "entities": {
                "发票号码": "12345678",
                "开票日期": "2024-01-15",
                "销售方": "测试科技有限公司",
                "金额": "1000.00"
            }
        },
        "processing_time": 2.5
    }


@pytest.fixture
def sample_parsed_invoice():
    """示例解析后的发票数据"""
    return {
        "invoice_type": {
            "code": "01",
            "name": "增值税专用发票",
            "confidence": 0.95,
            "raw_type": "增值税专用发票"
        },
        "basic_info": {
            "invoice_number": "12345678",
            "invoice_date": "2024-01-15",
            "total_amount": "1000.00",
            "tax_amount": "130.00",
            "amount_without_tax": "870.00"
        },
        "seller_info": {
            "name": "测试科技有限公司",
            "tax_id": "91110000123456789X",
            "address": "北京市朝阳区测试街道123号",
            "phone": "010-12345678",
            "bank_account": "1234567890123456789"
        },
        "buyer_info": {
            "name": "客户公司",
            "tax_id": "91110000987654321Y",
            "address": "北京市海淀区客户路456号",
            "phone": "010-87654321",
            "bank_account": "9876543210987654321"
        },
        "items": [
            {
                "name": "测试商品",
                "specification": "标准版",
                "unit": "台",
                "quantity": "1",
                "unit_price": "870.00",
                "amount": "870.00",
                "tax_rate": "13%",
                "tax_amount": "113.10"
            }
        ],
        "verification": {
            "check_code": "12345678",
            "machine_number": "499098765432",
            "is_valid": True
        },
        "meta": {
            "processing_time": 2.5,
            "model_version": "v1.0.0",
            "confidence_score": 0.92
        }
    }


# 测试标记
def pytest_configure(config):
    """Pytest配置"""
    config.addinivalue_line(
        "markers", "unit: 单元测试"
    )
    config.addinivalue_line(
        "markers", "integration: 集成测试"
    )
    config.addinivalue_line(
        "markers", "slow: 慢速测试"
    )


def pytest_collection_modifyitems(config, items):
    """修改测试项配置"""
    # 为所有测试添加asyncio标记
    for item in items:
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)


# 测试环境设置
@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """设置测试环境"""
    # 设置测试模式环境变量
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    
    # Mock ModelScope相关环境变量
    monkeypatch.setenv("MODELSCOPE_API_TOKEN", "test_token")
    monkeypatch.setenv("MODELSCOPE_CACHE_DIR", "/tmp/test_models")


@pytest.fixture
def mock_modelscope_pipeline():
    """Mock ModelScope pipeline"""
    mock_pipeline = Mock()
    mock_pipeline.return_value = Mock()
    
    # Mock不同类型的模型返回值
    def side_effect(*args, **kwargs):
        mock_model = Mock()
        
        if "ocr-detection" in str(args):
            mock_model.return_value = {
                "polygons": [{"polygon": [[10, 10], [100, 10], [100, 50], [10, 50]]}]
            }
        elif "ocr-recognition" in str(args):
            mock_model.return_value = {"text": "测试文本"}
        elif "image-classification" in str(args):
            mock_model.return_value = {
                "scores": [0.95, 0.03, 0.02],
                "labels": ["增值税专用发票", "增值税普通发票", "其他"]
            }
        elif "text-classification" in str(args):
            mock_model.return_value = {"entities": {"金额": "1000.00"}}
        
        return mock_model
    
    mock_pipeline.side_effect = side_effect
    return mock_pipeline 
"""
OCR引擎测试
"""

import pytest
import numpy as np
from unittest.mock import Mock, AsyncMock, patch
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from invoice_ocr_mcp.modules.ocr_engine import OCREngine


class TestOCREngine:
    """OCR引擎测试类"""
    
    @pytest.fixture
    def mock_image(self):
        """Mock图像数据"""
        return np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
    
    @pytest.fixture
    def ocr_engine(self, test_config):
        """创建OCR引擎实例"""
        return OCREngine(test_config)
    
    def test_ocr_engine_initialization(self, ocr_engine):
        """测试OCR引擎初始化"""
        assert ocr_engine is not None
        assert ocr_engine.config is not None
        assert hasattr(ocr_engine, 'executor')
        assert hasattr(ocr_engine, '_models')
        assert ocr_engine._models_loaded is False
    
    @pytest.mark.asyncio
    async def test_initialize_models(self, ocr_engine, mock_modelscope_pipeline):
        """测试模型初始化"""
        with patch('invoice_ocr_mcp.modules.ocr_engine.pipeline', mock_modelscope_pipeline):
            await ocr_engine.initialize_models()
            assert ocr_engine._models_loaded is True
            assert len(ocr_engine._models) > 0
    
    @pytest.mark.asyncio
    async def test_detect_text_regions(self, ocr_engine, mock_image, mock_modelscope_pipeline):
        """测试文本区域检测"""
        with patch('invoice_ocr_mcp.modules.ocr_engine.pipeline', mock_modelscope_pipeline):
            # 初始化模型
            await ocr_engine.initialize_models()
            
            # 测试文本检测
            regions = await ocr_engine.detect_text_regions(mock_image)
            
            assert isinstance(regions, list)
            if regions:
                assert "polygon" in regions[0] or "bbox" in regions[0]
    
    @pytest.mark.asyncio
    async def test_recognize_text(self, ocr_engine, mock_image, mock_modelscope_pipeline):
        """测试文本识别"""
        with patch('invoice_ocr_mcp.modules.ocr_engine.pipeline', mock_modelscope_pipeline):
            # 初始化模型
            await ocr_engine.initialize_models()
            
            # 创建模拟图像区域
            image_regions = [mock_image, mock_image]
            
            # 测试文本识别
            texts = await ocr_engine.recognize_text(image_regions)
            
            assert isinstance(texts, list)
            assert len(texts) == len(image_regions)
    
    @pytest.mark.asyncio
    async def test_classify_invoice_type(self, ocr_engine, mock_image, mock_modelscope_pipeline):
        """测试发票类型分类"""
        with patch('invoice_ocr_mcp.modules.ocr_engine.pipeline', mock_modelscope_pipeline):
            # 初始化模型
            await ocr_engine.initialize_models()
            
            # 测试发票分类
            result = await ocr_engine.classify_invoice_type(mock_image)
            
            assert isinstance(result, dict)
            assert "type" in result
            assert "confidence" in result
    
    @pytest.mark.asyncio
    async def test_extract_key_information(self, ocr_engine, mock_modelscope_pipeline):
        """测试关键信息提取"""
        with patch('invoice_ocr_mcp.modules.ocr_engine.pipeline', mock_modelscope_pipeline):
            # 初始化模型
            await ocr_engine.initialize_models()
            
            # 测试信息提取
            texts = ["发票号码: 12345678", "金额: 1000.00", "日期: 2024-01-15"]
            result = await ocr_engine.extract_key_information(texts)
            
            assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_full_ocr_pipeline(self, ocr_engine, mock_image, mock_modelscope_pipeline):
        """测试完整OCR流程"""
        with patch('invoice_ocr_mcp.modules.ocr_engine.pipeline', mock_modelscope_pipeline):
            # 初始化模型
            await ocr_engine.initialize_models()
            
            # Mock _crop_text_regions方法
            ocr_engine._crop_text_regions = Mock(return_value=[mock_image])
            
            # 测试完整流程
            result = await ocr_engine.full_ocr_pipeline(mock_image)
            
            assert isinstance(result, dict)
            assert "text_regions" in result
            assert "recognized_texts" in result
            assert "invoice_classification" in result
            assert "key_information" in result
            assert "processing_time" in result
    
    def test_crop_text_regions(self, ocr_engine, mock_image):
        """测试文本区域裁剪"""
        text_regions = [
            {"polygon": [[10, 10], [100, 10], [100, 50], [10, 50]]},
            {"bbox": [20, 20, 120, 80]}
        ]
        
        cropped_regions = ocr_engine._crop_text_regions(mock_image, text_regions)
        
        assert isinstance(cropped_regions, list)
        assert len(cropped_regions) <= len(text_regions)
    
    def test_get_device(self, ocr_engine):
        """测试设备选择"""
        device = ocr_engine._get_device()
        assert device in ["cpu", "cuda:0"]
    
    @pytest.mark.asyncio
    async def test_error_handling(self, ocr_engine):
        """测试错误处理"""
        # 测试未初始化模型时的错误
        with pytest.raises(RuntimeError, match="模型未加载"):
            await ocr_engine.detect_text_regions(np.zeros((100, 100, 3)))
    
    @pytest.mark.asyncio
    async def test_cleanup(self, ocr_engine):
        """测试资源清理"""
        await ocr_engine.cleanup()
        assert not ocr_engine._models_loaded
        assert len(ocr_engine._models) == 0


class TestOCREnginePerformance:
    """OCR引擎性能测试"""
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, ocr_engine, mock_modelscope_pipeline):
        """测试并发处理性能"""
        with patch('invoice_ocr_mcp.modules.ocr_engine.pipeline', mock_modelscope_pipeline):
            await ocr_engine.initialize_models()
            
            # 创建多个图像
            images = [np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8) for _ in range(5)]
            
            # 并发处理
            import asyncio
            tasks = [ocr_engine.detect_text_regions(img) for img in images]
            results = await asyncio.gather(*tasks)
            
            assert len(results) == len(images)
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_memory_usage(self, ocr_engine, mock_modelscope_pipeline):
        """测试内存使用"""
        with patch('invoice_ocr_mcp.modules.ocr_engine.pipeline', mock_modelscope_pipeline):
            await ocr_engine.initialize_models()
            
            # 处理大图像
            large_image = np.random.randint(0, 255, (2048, 2048, 3), dtype=np.uint8)
            
            result = await ocr_engine.full_ocr_pipeline(large_image)
            assert result is not None
            
            # 清理
            await ocr_engine.cleanup() 
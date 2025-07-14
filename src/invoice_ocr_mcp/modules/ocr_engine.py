"""
OCR识别引擎模块

基于ModelScope实现的发票OCR识别核心引擎
"""

import asyncio
import concurrent.futures
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import cv2
from PIL import Image
import torch

try:
    from modelscope.pipelines import pipeline
    from modelscope.utils.constant import Tasks
    from modelscope.models import Model
    from modelscope.preprocessors import build_preprocessor
except ImportError:
    logging.warning("ModelScope未安装，部分功能可能不可用")
    pipeline = None
    Tasks = None

from ..config import Config


class OCREngine:
    """OCR识别引擎"""
    
    def __init__(self, config: Config):
        """初始化OCR引擎
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 初始化线程池
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=config.processing.max_workers
        )
        
        # 模型缓存
        self._models = {}
        self._models_loaded = False
        
        self.logger.info("OCR引擎初始化完成")
    
    async def initialize_models(self) -> None:
        """异步初始化所有模型"""
        if self._models_loaded:
            return
            
        self.logger.info("开始加载OCR模型...")
        start_time = time.time()
        
        try:
            # 并行加载所有模型
            tasks = [
                self._load_text_detection_model(),
                self._load_text_recognition_model(), 
                self._load_invoice_classification_model(),
                self._load_info_extraction_model()
            ]
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
            self._models_loaded = True
            load_time = time.time() - start_time
            self.logger.info(f"所有模型加载完成，耗时: {load_time:.2f}秒")
            
        except Exception as e:
            self.logger.error(f"模型加载失败: {str(e)}")
            raise
    
    async def _load_text_detection_model(self) -> None:
        """加载文本检测模型"""
        if pipeline is None:
            raise ImportError("ModelScope未安装")
            
        loop = asyncio.get_event_loop()
        
        def _load():
            return pipeline(
                Tasks.ocr_detection,
                model=self.config.models.text_detection_model,
                model_revision=self.config.models.text_detection_version,
                device=self._get_device()
            )
        
        self._models['text_detection'] = await loop.run_in_executor(
            self.executor, _load
        )
        self.logger.info("文本检测模型加载完成")
    
    async def _load_text_recognition_model(self) -> None:
        """加载文本识别模型"""
        if pipeline is None:
            raise ImportError("ModelScope未安装")
            
        loop = asyncio.get_event_loop()
        
        def _load():
            return pipeline(
                Tasks.ocr_recognition,
                model=self.config.models.text_recognition_model,
                model_revision=self.config.models.text_recognition_version,
                device=self._get_device()
            )
        
        self._models['text_recognition'] = await loop.run_in_executor(
            self.executor, _load
        )
        self.logger.info("文本识别模型加载完成")
    
    async def _load_invoice_classification_model(self) -> None:
        """加载发票分类模型"""
        if pipeline is None:
            raise ImportError("ModelScope未安装")
            
        loop = asyncio.get_event_loop()
        
        def _load():
            return pipeline(
                Tasks.image_classification,
                model=self.config.models.invoice_classification_model,
                model_revision=self.config.models.invoice_classification_version,
                device=self._get_device()
            )
        
        self._models['invoice_classification'] = await loop.run_in_executor(
            self.executor, _load
        )
        self.logger.info("发票分类模型加载完成")
    
    async def _load_info_extraction_model(self) -> None:
        """加载信息抽取模型"""
        if pipeline is None:
            raise ImportError("ModelScope未安装")
            
        loop = asyncio.get_event_loop()
        
        def _load():
            return pipeline(
                Tasks.text_classification,
                model=self.config.models.info_extraction_model,
                model_revision=self.config.models.info_extraction_version,
                device=self._get_device()
            )
        
        self._models['info_extraction'] = await loop.run_in_executor(
            self.executor, _load
        )
        self.logger.info("信息抽取模型加载完成")
    
    def _get_device(self) -> str:
        """获取推理设备"""
        if self.config.models.use_gpu and torch.cuda.is_available():
            return f"cuda:{self.config.models.gpu_device_id}"
        return "cpu"
    
    async def detect_text_regions(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """检测文本区域
        
        Args:
            image: 输入图像（numpy数组）
            
        Returns:
            文本区域检测结果列表
        """
        await self.initialize_models()
        
        if 'text_detection' not in self._models:
            raise RuntimeError("文本检测模型未加载")
        
        loop = asyncio.get_event_loop()
        
        def _detect():
            return self._models['text_detection'](image)
        
        try:
            result = await loop.run_in_executor(self.executor, _detect)
            self.logger.debug(f"检测到 {len(result.get('polygons', []))} 个文本区域")
            return result.get('polygons', [])
        except Exception as e:
            self.logger.error(f"文本区域检测失败: {str(e)}")
            raise
    
    async def recognize_text(self, image_regions: List[np.ndarray]) -> List[str]:
        """识别文本内容
        
        Args:
            image_regions: 文本区域图像列表
            
        Returns:
            识别出的文本列表
        """
        await self.initialize_models()
        
        if 'text_recognition' not in self._models:
            raise RuntimeError("文本识别模型未加载")
        
        if not image_regions:
            return []
        
        loop = asyncio.get_event_loop()
        
        def _recognize(region):
            return self._models['text_recognition'](region)
        
        try:
            # 批量并行识别
            tasks = [
                loop.run_in_executor(self.executor, _recognize, region)
                for region in image_regions
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 提取文本内容
            texts = []
            for result in results:
                if isinstance(result, Exception):
                    self.logger.warning(f"文本识别失败: {str(result)}")
                    texts.append("")
                else:
                    texts.append(result.get('text', ''))
            
            self.logger.debug(f"成功识别 {len([t for t in texts if t])} 个文本区域")
            return texts
            
        except Exception as e:
            self.logger.error(f"文本识别失败: {str(e)}")
            raise
    
    async def classify_invoice_type(self, image: np.ndarray) -> Dict[str, Any]:
        """分类发票类型
        
        Args:
            image: 发票图像
            
        Returns:
            发票类型分类结果
        """
        await self.initialize_models()
        
        if 'invoice_classification' not in self._models:
            raise RuntimeError("发票分类模型未加载")
        
        loop = asyncio.get_event_loop()
        
        def _classify():
            return self._models['invoice_classification'](image)
        
        try:
            result = await loop.run_in_executor(self.executor, _classify)
            
            # 解析分类结果
            if 'scores' in result and 'labels' in result:
                scores = result['scores']
                labels = result['labels']
                
                # 找到最高分的类别
                max_idx = np.argmax(scores)
                invoice_type = labels[max_idx]
                confidence = float(scores[max_idx])
                
                self.logger.debug(f"发票类型分类: {invoice_type}, 置信度: {confidence:.3f}")
                
                return {
                    'type': invoice_type,
                    'confidence': confidence,
                    'all_scores': {label: float(score) for label, score in zip(labels, scores)}
                }
            
            return {
                'type': 'unknown',
                'confidence': 0.0,
                'all_scores': {}
            }
            
        except Exception as e:
            self.logger.error(f"发票类型分类失败: {str(e)}")
            raise
    
    async def extract_key_information(self, text_list: List[str]) -> Dict[str, Any]:
        """提取关键信息
        
        Args:
            text_list: 识别出的文本列表
            
        Returns:
            关键信息抽取结果
        """
        await self.initialize_models()
        
        if 'info_extraction' not in self._models:
            raise RuntimeError("信息抽取模型未加载")
        
        if not text_list:
            return {}
        
        # 合并所有文本
        combined_text = ' '.join(text_list)
        
        loop = asyncio.get_event_loop()
        
        def _extract():
            return self._models['info_extraction'](combined_text)
        
        try:
            result = await loop.run_in_executor(self.executor, _extract)
            self.logger.debug("关键信息抽取完成")
            return result
            
        except Exception as e:
            self.logger.error(f"关键信息抽取失败: {str(e)}")
            raise
    
    async def full_ocr_pipeline(self, image: np.ndarray) -> Dict[str, Any]:
        """完整的OCR处理流程
        
        Args:
            image: 输入图像
            
        Returns:
            完整的OCR识别结果
        """
        start_time = time.time()
        
        try:
            # 1. 检测文本区域
            text_regions = await self.detect_text_regions(image)
            
            # 2. 从原图中裁剪文本区域
            region_images = self._crop_text_regions(image, text_regions)
            
            # 3. 识别文本内容
            texts = await self.recognize_text(region_images)
            
            # 4. 分类发票类型（并行执行）
            classification_task = self.classify_invoice_type(image)
            
            # 5. 提取关键信息（并行执行）
            extraction_task = self.extract_key_information(texts)
            
            # 等待并行任务完成
            classification_result, extraction_result = await asyncio.gather(
                classification_task, extraction_task
            )
            
            processing_time = time.time() - start_time
            
            return {
                'text_regions': text_regions,
                'recognized_texts': texts,
                'invoice_classification': classification_result,
                'key_information': extraction_result,
                'processing_time': processing_time
            }
            
        except Exception as e:
            self.logger.error(f"OCR处理流程失败: {str(e)}")
            raise
    
    def _crop_text_regions(self, image: np.ndarray, text_regions: List[Dict[str, Any]]) -> List[np.ndarray]:
        """从原图中裁剪文本区域
        
        Args:
            image: 原始图像
            text_regions: 文本区域坐标列表
            
        Returns:
            裁剪后的文本区域图像列表
        """
        region_images = []
        
        for region in text_regions:
            try:
                # 获取区域坐标
                if 'polygon' in region:
                    points = np.array(region['polygon'], dtype=np.int32)
                elif 'bbox' in region:
                    bbox = region['bbox']
                    x1, y1, x2, y2 = bbox
                    points = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.int32)
                else:
                    continue
                
                # 获取边界矩形
                x, y, w, h = cv2.boundingRect(points)
                
                # 确保坐标在图像范围内
                x = max(0, x)
                y = max(0, y)
                w = min(w, image.shape[1] - x)
                h = min(h, image.shape[0] - y)
                
                # 裁剪区域
                cropped = image[y:y+h, x:x+w]
                if cropped.size > 0:
                    region_images.append(cropped)
                    
            except Exception as e:
                self.logger.warning(f"裁剪文本区域失败: {str(e)}")
                continue
        
        return region_images
    
    async def cleanup(self) -> None:
        """清理资源"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
        
        # 清理模型缓存
        self._models.clear()
        self._models_loaded = False
        
        self.logger.info("OCR引擎资源清理完成") 
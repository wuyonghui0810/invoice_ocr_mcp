"""
RapidOCR引擎模块（v3.2.0适配）

基于RapidOCR v3.2.0实现的高性能OCR引擎
"""

import asyncio
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import cv2
import base64
from io import BytesIO
from PIL import Image

from rapidocr import RapidOCR  # 只保留v3.2.0

from ..config import Config
from .utils import setup_logging


class RapidOCREngine:
    """RapidOCR引擎类（v3.2.0）"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logging(config)
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._engine = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """初始化RapidOCR引擎"""
        if self._initialized:
            return
        self.logger.info("正在初始化RapidOCR v3.2.0引擎...")
        loop = asyncio.get_event_loop()
        self._engine = await loop.run_in_executor(self.executor, RapidOCR)
        self._initialized = True
        self.logger.info("RapidOCR v3.2.0引擎初始化完成")

    async def detect_text(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """检测图像中的文本区域"""
        await self.initialize()
        loop = asyncio.get_event_loop()
        def _detect():
            result = self._engine(image, return_word_box=True, return_single_char_box=True)
            # v3.2.0: result.boxes, result.txts, result.scores
            detected_regions = []
            boxes = getattr(result, 'boxes', [])
            txts = getattr(result, 'txts', [])
            scores = getattr(result, 'scores', [])
            for box, text, score in zip(boxes, txts, scores):
                detected_regions.append({
                    'bbox': box,
                    'text': text,
                    'confidence': float(score)
                })
            return detected_regions
        try:
            result = await loop.run_in_executor(self.executor, _detect)
            self.logger.debug(f"文本检测完成，发现 {len(result)} 个文本区域")
            return result
        except Exception as e:
            self.logger.error(f"文本检测失败: {e}")
            return []

    async def recognize_text(self, image: np.ndarray) -> List[str]:
        """识别图像中的文本内容"""
        detected_regions = await self.detect_text(image)
        return [region['text'] for region in detected_regions]

    async def classify_invoice_type(self, image: np.ndarray) -> Dict[str, Any]:
        """分类发票类型（基于文本内容分析）"""
        await self.initialize()
        text_regions = await self.detect_text(image)
        if not text_regions:
            return {
                "type": "unknown",
                "confidence": 0.0,
                "detected_keywords": []
            }
        all_text = " ".join([region['text'] for region in text_regions])
        invoice_type, confidence, keywords = self._classify_by_keywords(all_text)
        self.logger.info(f"发票类型分类完成: {invoice_type} (置信度: {confidence:.2f})")
        all_scores = {}
        for itype, config in {
            "general_invoice": {"keywords": ["增值税普通发票", "普通发票", "发票代码", "发票号码", "开票日期"], "weight": [3, 2, 2, 2, 1]},
            "vat_invoice": {"keywords": ["增值税专用发票", "专用发票", "纳税人识别号", "税额", "价税合计"], "weight": [5, 3, 2, 2, 2]},
            "electronic_invoice": {"keywords": ["电子发票", "电子普通发票", "二维码", "验证码"], "weight": [4, 3, 1, 1]},
            "receipt": {"keywords": ["收据", "收款收据", "往来款项收据", "收费收据"], "weight": [3, 2, 2, 2]},
            "train_ticket": {"keywords": ["车票", "火车票", "高铁票", "动车票", "席别", "车次"], "weight": [3, 3, 3, 3, 2, 2]},
            "taxi_ticket": {"keywords": ["出租车票", "的士票", "计程车", "里程", "等候时间"], "weight": [4, 3, 3, 2, 1]},
            "air_ticket": {"keywords": ["登机牌", "机票", "航班", "座位号", "登机口"], "weight": [4, 3, 2, 1, 1]},
            "hotel_invoice": {"keywords": ["住宿发票", "酒店发票", "宾馆", "房费", "住宿费"], "weight": [4, 3, 2, 2, 2]},
            "catering_invoice": {"keywords": ["餐饮发票", "餐费", "服务费", "酒水", "用餐"], "weight": [3, 2, 1, 1, 1]}
        }.items():
            score = 0
            for keyword, weight in zip(config["keywords"], config["weight"]):
                if keyword in all_text:
                    score += weight
            if score > 0:
                max_possible = sum(config["weight"])
                all_scores[itype] = min(score / max_possible * 2, 1.0)
        return {
            "type": invoice_type,
            "confidence": confidence,
            "detected_keywords": keywords,
            "ocr_text": all_text,
            "all_scores": all_scores
        }

    def _classify_by_keywords(self, text: str) -> Tuple[str, float, List[str]]:
        """根据关键词分类发票类型"""
        type_keywords = {
            "general_invoice": ["增值税普通发票", "普通发票", "发票代码", "发票号码", "开票日期"],
            "vat_invoice": ["增值税专用发票", "专用发票", "纳税人识别号", "税额", "价税合计"],
            "electronic_invoice": ["电子发票", "电子普通发票", "二维码", "验证码"],
            "receipt": ["收据", "收款收据", "往来款项收据", "收费收据"],
            "train_ticket": ["车票", "火车票", "高铁票", "动车票", "席别", "车次"],
            "taxi_ticket": ["出租车票", "的士票", "计程车", "里程", "等候时间"],
            "air_ticket": ["登机牌", "机票", "航班", "座位号", "登机口"],
            "hotel_invoice": ["住宿发票", "酒店发票", "宾馆", "房费", "住宿费"],
            "catering_invoice": ["餐饮发票", "餐费", "服务费", "酒水", "用餐"]
        }
        max_type = "unknown"
        max_score = 0
        detected_keywords = []
        for t, keywords in type_keywords.items():
            score = 0
            for kw in keywords:
                if kw in text:
                    score += 1
                    detected_keywords.append(kw)
            if score > max_score:
                max_score = score
                max_type = t
        confidence = min(max_score / 10.0, 1.0)
        return max_type, confidence, detected_keywords

    async def extract_key_information(self, text_list: List[str]) -> Dict[str, Any]:
        """基于规则提取关键信息"""
        import re
        text = " ".join(text_list)
        info = {}
        invoice_code_pattern = r'发票代码[：:\s]*(\d{10,12})'
        invoice_code_match = re.search(invoice_code_pattern, text)
        if invoice_code_match:
            info['invoice_code'] = invoice_code_match.group(1)
        invoice_number_pattern = r'发票号码[：:\s]*(\d{8,10})'
        invoice_number_match = re.search(invoice_number_pattern, text)
        if invoice_number_match:
            info['invoice_number'] = invoice_number_match.group(1)
        date_patterns = [
            r'(\d{4}[年-]\d{1,2}[月-]\d{1,2}[日]?)',
            r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
            r'开票日期[：:\s]*(\d{4}[年-]\d{1,2}[月-]\d{1,2}[日]?)'
        ]
        for pattern in date_patterns:
            date_match = re.search(pattern, text)
            if date_match:
                info['issue_date'] = date_match.group(1)
                break
        amount_patterns = [
            r'[￥¥]\s*(\d+\.?\d*)',
            r'金额[：:\s]*[￥¥]?\s*(\d+\.?\d*)',
            r'总额[：:\s]*[￥¥]?\s*(\d+\.?\d*)',
            r'价税合计[：:\s]*[￥¥]?\s*(\d+\.?\d*)'
        ]
        for pattern in amount_patterns:
            amount_match = re.search(pattern, text)
            if amount_match:
                info['total_amount'] = float(amount_match.group(1))
                break
        tax_id_pattern = r'纳税人识别号[：:\s]*([A-Z0-9]{15,20})'
        tax_id_match = re.search(tax_id_pattern, text)
        if tax_id_match:
            info['tax_id'] = tax_id_match.group(1)
        seller_patterns = [
            r'销售方名称[：:\s]*([^\n\r]+)',
            r'名称[：:\s]*([^\n\r]+)',
            r'单位名称[：:\s]*([^\n\r]+)'
        ]
        for pattern in seller_patterns:
            seller_match = re.search(pattern, text)
            if seller_match:
                info['seller_name'] = seller_match.group(1).strip()
                break
        return info

    async def full_ocr_pipeline(self, image: np.ndarray) -> Dict[str, Any]:
        """完整的OCR流水线处理"""
        await self.initialize()
        text_regions = await self.detect_text(image)
        text_list = [region['text'] for region in text_regions]
        classification_result = await self.classify_invoice_type(image)
        extracted_info = await self.extract_key_information(text_list)
        return {
            "text_regions": text_regions,
            "text_list": text_list,
            "classification": classification_result,
            "extracted_info": extracted_info,
            "total_text_count": len(text_regions),
            "processing_engine": "RapidOCR v3.2.0"
        }

    async def cleanup(self) -> None:
        if self.executor:
            self.executor.shutdown(wait=True)
        self.logger.info("RapidOCR v3.2.0引擎清理完成")

    @staticmethod
    def preprocess_image(image_data: Any) -> np.ndarray:
        """预处理图像数据"""
        if isinstance(image_data, str):
            if image_data.startswith('data:image') or len(image_data) > 100:
                if image_data.startswith('data:image'):
                    image_data = image_data.split(',')[1]
                image_bytes = base64.b64decode(image_data)
                image = Image.open(BytesIO(image_bytes))
                return np.array(image)
            else:
                return cv2.imread(image_data)
        elif isinstance(image_data, np.ndarray):
            return image_data
        elif hasattr(image_data, 'read'):
            image_bytes = image_data.read()
            image = Image.open(BytesIO(image_bytes))
            return np.array(image)
        else:
            raise ValueError(f"不支持的图像数据类型: {type(image_data)}") 
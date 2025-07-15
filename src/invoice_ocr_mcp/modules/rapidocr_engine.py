"""
RapidOCR引擎模块

基于RapidOCR实现的高性能OCR引擎
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

try:
    from rapidocr_onnxruntime import RapidOCR
    RAPIDOCR_AVAILABLE = True
except ImportError:
    RAPIDOCR_AVAILABLE = False
    RapidOCR = None

from ..config import Config
from .utils import setup_logging


class RapidOCREngine:
    """RapidOCR引擎类"""
    
    def __init__(self, config: Config):
        """初始化RapidOCR引擎
        
        Args:
            config: 系统配置
        """
        self.config = config
        self.logger = setup_logging(config)
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._engine = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """初始化RapidOCR引擎"""
        if self._initialized:
            return
            
        if not RAPIDOCR_AVAILABLE:
            raise ImportError(
                "RapidOCR未安装。请运行: pip install rapidocr-onnxruntime"
            )
        
        self.logger.info("正在初始化RapidOCR引擎...")
        
        try:
            # 在线程池中初始化RapidOCR，避免阻塞事件循环
            loop = asyncio.get_event_loop()
            self._engine = await loop.run_in_executor(
                self.executor, self._init_rapidocr
            )
            
            self._initialized = True
            self.logger.info("RapidOCR引擎初始化完成")
            
        except Exception as e:
            self.logger.error(f"RapidOCR引擎初始化失败: {e}")
            raise
    
    def _init_rapidocr(self) -> RapidOCR:
        """初始化RapidOCR实例"""
        # RapidOCR配置参数
        config_params = {
            'use_gpu': self.config.ocr_engine.rapidocr_use_gpu,
            'gpu_id': self.config.ocr_engine.rapidocr_device_id,
        }
        
        return RapidOCR(**config_params)
    
    async def detect_text(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """检测图像中的文本区域
        
        Args:
            image: 输入图像 (numpy array)
            
        Returns:
            检测到的文本区域列表
        """
        await self.initialize()
        
        loop = asyncio.get_event_loop()
        
        def _detect():
            # RapidOCR返回格式: (result_list, elapse_time)
            # result_list格式: [[[x1,y1], [x2,y2], [x3,y3], [x4,y4]], '识别文本', 置信度]
            result_tuple = self._engine(image)
            
            if not result_tuple or not result_tuple[0]:
                return []
            
            result_list = result_tuple[0]  # 获取实际的识别结果列表
            detected_regions = []
            
            for item in result_list:
                if len(item) >= 3:
                    box, text, confidence = item[0], item[1], item[2]
                    detected_regions.append({
                        'bbox': box,  # 边界框坐标
                        'text': text,  # 识别的文本
                        'confidence': float(confidence)  # 置信度
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
        """识别图像中的文本内容
        
        Args:
            image: 输入图像
            
        Returns:
            识别出的文本列表
        """
        detected_regions = await self.detect_text(image)
        return [region['text'] for region in detected_regions]
    
    async def classify_invoice_type(self, image: np.ndarray) -> Dict[str, Any]:
        """分类发票类型（基于文本内容分析）
        
        Args:
            image: 发票图像
            
        Returns:
            发票类型分类结果
        """
        await self.initialize()
        
        # 首先提取文本
        text_regions = await self.detect_text(image)
        if not text_regions:
            return {
                "invoice_type": "unknown",
                "confidence": 0.0,
                "detected_keywords": []
            }
        
        # 合并所有识别的文本
        all_text = " ".join([region['text'] for region in text_regions])
        
        # 基于关键词进行发票类型分类
        invoice_type, confidence, keywords = self._classify_by_keywords(all_text)
        
        self.logger.info(f"发票类型分类完成: {invoice_type} (置信度: {confidence:.2f})")
        
        # 计算所有类型得分用于候选列表
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
            "type": invoice_type,  # 修改字段名
            "confidence": confidence,
            "detected_keywords": keywords,
            "ocr_text": all_text,
            "all_scores": all_scores  # 添加所有类型得分
        }
    
    def _classify_by_keywords(self, text: str) -> Tuple[str, float, List[str]]:
        """基于关键词分类发票类型
        
        Args:
            text: 提取的文本内容
            
        Returns:
            (发票类型, 置信度, 检测到的关键词)
        """
        # 发票类型关键词映射 - 优化后的版本
        invoice_keywords = {
            "general_invoice": {
                "keywords": ["增值税普通发票", "普通发票", "发票代码", "发票号码", "开票日期", "发票", "代码", "号码", "增值税"],
                "weight": [5, 4, 3, 3, 2, 2, 1, 1, 1]
            },
            "vat_invoice": {
                "keywords": ["增值税专用发票", "专用发票", "纳税人识别号", "税额", "价税合计", "专用", "纳税人", "识别号"],
                "weight": [5, 4, 3, 2, 2, 2, 1, 1]
            },
            "electronic_invoice": {
                "keywords": ["电子发票", "电子普通发票", "二维码", "验证码", "电子", "查验"],
                "weight": [5, 4, 2, 2, 1, 1]
            },
            "receipt": {
                "keywords": ["收据", "收款收据", "往来款项收据", "收费收据", "收款"],
                "weight": [4, 3, 3, 3, 1]
            },
            "train_ticket": {
                "keywords": ["车票", "火车票", "高铁票", "动车票", "席别", "车次", "铁路"],
                "weight": [4, 4, 4, 4, 2, 2, 1]
            },
            "taxi_ticket": {
                "keywords": ["出租车票", "的士票", "计程车", "里程", "等候时间", "出租车"],
                "weight": [5, 4, 4, 2, 1, 2]
            },
            "air_ticket": {
                "keywords": ["登机牌", "机票", "航班", "座位号", "登机口", "航空"],
                "weight": [5, 4, 3, 2, 2, 1]
            },
            "hotel_invoice": {
                "keywords": ["住宿发票", "酒店发票", "宾馆", "房费", "住宿费", "住宿", "酒店"],
                "weight": [5, 4, 3, 2, 2, 1, 1]
            },
            "catering_invoice": {
                "keywords": ["餐饮发票", "餐费", "服务费", "酒水", "用餐", "餐饮"],
                "weight": [4, 3, 2, 1, 1, 1]
            }
        }
        
        text_lower = text.lower()
        type_scores = {}
        
        # 优化匹配逻辑：同时检查原文和小写文本
        for invoice_type, config in invoice_keywords.items():
            score = 0
            found_keywords = []
            
            for keyword, weight in zip(config["keywords"], config["weight"]):
                # 检查关键词是否在文本中（不区分大小写）
                if keyword.lower() in text_lower or keyword in text:
                    score += weight
                    found_keywords.append(keyword)
            
            if score > 0:
                type_scores[invoice_type] = {
                    "score": score,
                    "keywords": found_keywords
                }
        
        # 如果没有匹配的关键词，根据数字模式推断
        if not type_scores:
            # 检查是否包含发票特征模式
            import re
            
            # 发票代码模式 (通常10-12位数字)
            if re.search(r'\d{10,12}', text):
                type_scores["general_invoice"] = {
                    "score": 2,
                    "keywords": ["发票代码模式"]
                }
            
            # 如果仍然没有匹配，给一个默认的低置信度分类
            if not type_scores:
                return "general_invoice", 0.1, ["数字模式"]
        
        # 找到得分最高的类型
        best_type = max(type_scores.keys(), key=lambda k: type_scores[k]["score"])
        best_score = type_scores[best_type]["score"]
        best_keywords = type_scores[best_type]["keywords"]
        
        # 优化置信度计算：使用更合理的归一化方法
        max_possible_score = max([sum(config["weight"]) for config in invoice_keywords.values()])
        confidence = min(best_score / 10.0, 1.0)  # 调整置信度计算，使其更敏感
        
        return best_type, confidence, best_keywords
    
    async def extract_key_information(self, text_list: List[str]) -> Dict[str, Any]:
        """提取关键信息（基于规则的信息抽取）
        
        Args:
            text_list: 识别出的文本列表
            
        Returns:
            关键信息抽取结果
        """
        if not text_list:
            return {}
        
        # 合并所有文本
        combined_text = " ".join(text_list)
        
        # 基于正则表达式和规则提取关键信息
        extracted_info = self._extract_by_rules(combined_text)
        
        self.logger.debug("关键信息抽取完成")
        return extracted_info
    
    def _extract_by_rules(self, text: str) -> Dict[str, Any]:
        """基于规则提取关键信息
        
        Args:
            text: 输入文本
            
        Returns:
            提取的关键信息
        """
        import re
        
        info = {}
        
        # 发票代码提取
        invoice_code_pattern = r'发票代码[：:\s]*(\d{10,12})'
        invoice_code_match = re.search(invoice_code_pattern, text)
        if invoice_code_match:
            info['invoice_code'] = invoice_code_match.group(1)
        
        # 发票号码提取
        invoice_number_pattern = r'发票号码[：:\s]*(\d{8,10})'
        invoice_number_match = re.search(invoice_number_pattern, text)
        if invoice_number_match:
            info['invoice_number'] = invoice_number_match.group(1)
        
        # 日期提取
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
        
        # 金额提取
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
        
        # 纳税人识别号提取
        tax_id_pattern = r'纳税人识别号[：:\s]*([A-Z0-9]{15,20})'
        tax_id_match = re.search(tax_id_pattern, text)
        if tax_id_match:
            info['tax_id'] = tax_id_match.group(1)
        
        # 销售方提取
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
        """完整的OCR流水线处理
        
        Args:
            image: 输入图像
            
        Returns:
            完整的OCR处理结果
        """
        await self.initialize()
        
        # 执行文本检测和识别
        text_regions = await self.detect_text(image)
        
        # 提取所有文本
        text_list = [region['text'] for region in text_regions]
        
        # 执行发票类型分类
        classification_result = await self.classify_invoice_type(image)
        
        # 执行关键信息提取
        extracted_info = await self.extract_key_information(text_list)
        
        return {
            "text_regions": text_regions,
            "text_list": text_list,
            "classification": classification_result,
            "extracted_info": extracted_info,
            "total_text_count": len(text_regions),
            "processing_engine": "RapidOCR"
        }
    
    async def cleanup(self) -> None:
        """清理资源"""
        if self.executor:
            self.executor.shutdown(wait=True)
        self.logger.info("RapidOCR引擎清理完成")
    
    @staticmethod
    def preprocess_image(image_data: Any) -> np.ndarray:
        """预处理图像数据
        
        Args:
            image_data: 图像数据（可以是文件路径、base64字符串、numpy数组等）
            
        Returns:
            处理后的numpy数组
        """
        if isinstance(image_data, str):
            if image_data.startswith('data:image') or len(image_data) > 100:
                # Base64编码的图像
                if image_data.startswith('data:image'):
                    image_data = image_data.split(',')[1]
                
                image_bytes = base64.b64decode(image_data)
                image = Image.open(BytesIO(image_bytes))
                return np.array(image)
            else:
                # 文件路径
                return cv2.imread(image_data)
        
        elif isinstance(image_data, np.ndarray):
            return image_data
        
        elif hasattr(image_data, 'read'):
            # 文件对象
            image_bytes = image_data.read()
            image = Image.open(BytesIO(image_bytes))
            return np.array(image)
        
        else:
            raise ValueError(f"不支持的图像数据类型: {type(image_data)}") 
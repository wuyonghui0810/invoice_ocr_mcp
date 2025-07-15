"""
OCR引擎模块

只保留RapidOCR v3.2.0相关实现
"""

from ..config import Config

def create_ocr_engine(config: Config):
    """创建OCR引擎的工厂函数（仅支持RapidOCR）"""
    from .rapidocr_engine import RapidOCREngine
    return RapidOCREngine(config) 
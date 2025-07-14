"""
Invoice OCR MCP Server

企业发票OCR识别MCP服务器 - 基于ModelScope的专业发票识别解决方案
"""

__version__ = "1.0.0"
__author__ = "Invoice OCR Team"
__email__ = "team@example.com"
__description__ = "企业发票OCR识别MCP服务器"

from .server import InvoiceOCRServer
from .config import Config

__all__ = ["InvoiceOCRServer", "Config"] 
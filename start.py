#!/usr/bin/env python3
"""
发票OCR服务启动脚本
使用 uvicorn 启动 FastAPI 应用
"""

import uvicorn
from pathlib import Path
import sys

# 将src目录添加到Python路径
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from invoice_ocr_mcp.server import InvoiceOCRServer
from invoice_ocr_mcp.config import Config

def create_app():
    """创建FastAPI应用实例"""
    config = Config()
    server = InvoiceOCRServer(config)
    return server.app

if __name__ == "__main__":
    uvicorn.run(
        "start:create_app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        factory=True
    )
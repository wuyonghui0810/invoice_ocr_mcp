#!/usr/bin/env python3
"""
发票OCR MCP服务器启动脚本
"""

import sys
import os
import asyncio
from pathlib import Path

# 将src目录添加到Python路径
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# 现在可以导入模块了
from invoice_ocr_mcp.server import InvoiceOCRServer, main

if __name__ == "__main__":
    asyncio.run(main()) 
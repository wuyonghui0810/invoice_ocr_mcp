"""
Invoice OCR MCP Server

MCP服务器主文件，实现发票OCR识别的MCP协议接口
"""

import asyncio
import logging
import sys
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .config import Config
from .modules.ocr_engine import OCREngine
from .modules.invoice_parser import InvoiceParser
from .modules.image_processor import ImageProcessor
from .modules.batch_processor import BatchProcessor
from .modules.validators import validate_image_data, validate_batch_input
from .modules.utils import setup_logging, format_error_response


class InvoiceOCRServer:
    """发票OCR识别MCP服务器"""
    
    def __init__(self, config: Optional[Config] = None):
        """初始化服务器
        
        Args:
            config: 配置对象，如果为None则使用默认配置
        """
        self.config = config or Config()
        self.server = Server("invoice-ocr-mcp")
        self.logger = setup_logging(self.config)
        
        # 初始化核心组件
        from .modules.ocr_engine import create_ocr_engine
        self.ocr_engine = create_ocr_engine(self.config)
        self.invoice_parser = InvoiceParser(self.config)
        self.image_processor = ImageProcessor(self.config)
        self.batch_processor = BatchProcessor(self.config)
        
        # 注册MCP工具
        self._register_handlers()
        
        self.logger.info("Invoice OCR MCP Server initialized")
    
    def _register_handlers(self) -> None:
        """注册MCP处理器"""
        
        # 注册工具列表处理器
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """返回可用工具列表"""
            return [
                Tool(
                    name="recognize_single_invoice",
                    description="识别单张发票并提取结构化信息",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "image_data": {
                                "type": "string",
                                "description": "Base64编码的发票图像数据"
                            },
                            "image_url": {
                                "type": "string",
                                "description": "发票图像URL地址"
                            },
                            "output_format": {
                                "type": "string",
                                "enum": ["standard", "detailed", "raw"],
                                "default": "standard",
                                "description": "输出格式：标准/详细/原始"
                            }
                        },
                        "oneOf": [
                            {"required": ["image_data"]},
                            {"required": ["image_url"]}
                        ]
                    }
                ),
                Tool(
                    name="recognize_batch_invoices",
                    description="批量识别多张发票",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "images": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "image_data": {"type": "string"},
                                        "image_url": {"type": "string"}
                                    },
                                    "required": ["id"],
                                    "oneOf": [
                                        {"required": ["image_data"]},
                                        {"required": ["image_url"]}
                                    ]
                                },
                                "maxItems": 50
                            },
                            "parallel_count": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 10,
                                "default": 3,
                                "description": "并行处理数量"
                            }
                        },
                        "required": ["images"]
                    }
                ),
                Tool(
                    name="detect_invoice_type",
                    description="检测发票类型",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "image_data": {
                                "type": "string",
                                "description": "Base64编码的发票图像数据"
                            },
                            "image_url": {
                                "type": "string",
                                "description": "发票图像URL地址"
                            }
                        },
                        "oneOf": [
                            {"required": ["image_data"]},
                            {"required": ["image_url"]}
                        ]
                    }
                )
            ]
        
        # 注册工具调用处理器
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """处理工具调用"""
            try:
                if name == "recognize_single_invoice":
                    result = await self._recognize_single_invoice(arguments)
                elif name == "recognize_batch_invoices":
                    result = await self._recognize_batch_invoices(arguments)
                elif name == "detect_invoice_type":
                    result = await self._detect_invoice_type(arguments)
                else:
                    raise ValueError(f"未知的工具: {name}")
                
                return [TextContent(
                    type="text",
                    text=str(result)
                )]
                
            except Exception as e:
                self.logger.error(f"工具调用失败: {name}, 错误: {str(e)}", exc_info=True)
                return [TextContent(
                    type="text",
                    text=str(format_error_response("TOOL_CALL_ERROR", str(e)))
                )]
    
    async def _recognize_single_invoice(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """识别单张发票"""
        image_data = arguments.get("image_data")
        image_url = arguments.get("image_url")
        output_format = arguments.get("output_format", "standard")
        
        self.logger.info("收到单张发票识别请求")
        
        # 验证输入参数
        if not image_data and not image_url:
            return format_error_response(
                "INVALID_INPUT", 
                "必须提供 image_data 或 image_url 之一"
            )
        
        # 处理图像数据
        if image_data:
            # 验证Base64数据
            if not validate_image_data(image_data):
                return format_error_response(
                    "INVALID_IMAGE_FORMAT",
                    "无效的图像数据格式"
                )
            image = await self.image_processor.decode_base64_image(image_data)
        else:
            # 从URL下载图像
            image = await self.image_processor.download_image(image_url)
        
        # 预处理图像
        processed_image = await self.image_processor.preprocess_image(image)
        
        # 发票类型识别
        invoice_type_result = await self.ocr_engine.classify_invoice_type(processed_image)
        
        # OCR文本识别
        ocr_result = await self.ocr_engine.full_ocr_pipeline(processed_image)
        
        # 将发票类型信息合并到OCR结果中
        ocr_result['invoice_classification'] = invoice_type_result
        
        # 解析发票信息
        parsed_data = await self.invoice_parser.parse_invoice(
            ocr_result, 
            output_format
        )
        
        # 添加发票类型到返回结果
        if parsed_data and isinstance(parsed_data, dict):
            # 更新发票类型信息，使其包含更详细的分类结果
            parsed_data['invoice_type'] = {
                'code': None,
                'name': self._get_invoice_type_name(invoice_type_result.get('type', 'unknown')),
                'confidence': invoice_type_result.get('confidence', 0.0),
                'raw_type': invoice_type_result.get('type', 'unknown')
            }
            
            # 添加检测的关键词和识别文本区域
            parsed_data['detected_keywords'] = invoice_type_result.get('detected_keywords', [])
            parsed_data['text_regions'] = ocr_result.get('text_regions', [])
            parsed_data['extracted_info'] = parsed_data.get('basic_info', {})
            parsed_data['confidence'] = invoice_type_result.get('confidence', 0.0)
        
        self.logger.info(f"单张发票识别完成，类型: {invoice_type_result.get('type')}")
        
        return {
            "success": True,
            "data": parsed_data
        }
    
    def _get_invoice_type_name(self, type_code: str) -> str:
        """将发票类型代码转换为中文名称"""
        type_mapping = {
            "general_invoice": "增值税普通发票",
            "vat_invoice": "增值税专用发票", 
            "electronic_invoice": "电子发票",
            "receipt": "收据",
            "train_ticket": "火车票",
            "taxi_ticket": "出租车票",
            "air_ticket": "机票",
            "hotel_invoice": "住宿发票",
            "catering_invoice": "餐饮发票",
            "unknown": "未知类型"
        }
        return type_mapping.get(type_code, "未知类型")
    
    async def _recognize_batch_invoices(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """批量识别发票"""
        images = arguments.get("images", [])
        parallel_count = arguments.get("parallel_count", 3)
        
        self.logger.info(f"收到批量发票识别请求，共 {len(images)} 张图片")
        
        # 验证输入参数
        validation_result = validate_batch_input(images)
        if not validation_result["valid"]:
            return format_error_response(
                "INVALID_INPUT",
                validation_result["error"],
                validation_result.get("details")
            )
        
        # 批量处理
        batch_result = await self.batch_processor.process_batch(
            images,
            parallel_count,
            "standard"
        )
        
        # 检查批量处理结果
        if not batch_result.get("success"):
            return format_error_response(
                "BATCH_PROCESSING_ERROR",
                batch_result.get("error", "批量处理失败")
            )
        
        results = batch_result.get("results", [])
        statistics = batch_result.get("statistics", {})
        
        self.logger.info(f"批量识别完成，成功: {statistics.get('successful', 0)}/{statistics.get('total', 0)}")
        
        return {
            "success": True,
            "data": {
                "batch_id": batch_result.get("batch_id"),
                "total_count": len(images),
                "results": results,
                "statistics": statistics
            }
        }
    
    async def _detect_invoice_type(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """检测发票类型"""
        image_data = arguments.get("image_data")
        image_url = arguments.get("image_url")
        
        self.logger.info("收到发票类型检测请求")
        
        # 验证输入参数
        if not image_data and not image_url:
            return format_error_response(
                "INVALID_INPUT",
                "必须提供 image_data 或 image_url 之一"
            )
        
        # 处理图像数据
        if image_data:
            if not validate_image_data(image_data):
                return format_error_response(
                    "INVALID_IMAGE_FORMAT",
                    "无效的图像数据格式"
                )
            image = await self.image_processor.decode_base64_image(image_data)
        else:
            image = await self.image_processor.download_image(image_url)
        
        # 预处理图像
        processed_image = await self.image_processor.preprocess_image(image)
        
        # 发票类型分类
        classification_result = await self.ocr_engine.classify_invoice_type(
            processed_image
        )
        
        # 格式化类型检测结果
        result = {
            "invoice_type": {
                "code": None,
                "name": classification_result.get('type', 'unknown'),
                "confidence": classification_result.get('confidence', 0.0)
            },
            "candidates": [
                {
                    "name": label,
                    "confidence": score
                }
                for label, score in classification_result.get('all_scores', {}).items()
            ][:5],  # 返回前5个候选
            "detected_keywords": classification_result.get('detected_keywords', []),
            "ocr_text": classification_result.get('ocr_text', '')
        }
        
        return {
            "success": True,
            "data": result
        }
    
    async def _process_single_image(self, image_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理单张图像（用于批量处理）"""
        try:
            # 调用单张识别逻辑
            result = await self._recognize_single_invoice({
                "image_data": image_data.get("image_data"),
                "image_url": image_data.get("image_url"),
                "output_format": "standard"
            })
            
            return {
                "id": image_data.get("id"),
                "status": "success" if result.get("success") else "failed",
                "data": result.get("data") if result.get("success") else None,
                "error": result.get("error") if not result.get("success") else None
            }
            
        except Exception as e:
            self.logger.error(f"处理图像失败: {str(e)}", exc_info=True)
            return {
                "id": image_data.get("id"),
                "status": "failed",
                "data": None,
                "error": format_error_response("PROCESSING_ERROR", str(e))
            }

    async def run(self):
        """运行服务器"""
        async with stdio_server() as streams:
            await self.server.run(
                streams[0], 
                streams[1],
                initialization_options={}
            )


async def main():
    """主函数"""
    try:
        config = Config()
        server = InvoiceOCRServer(config)
        await server.run()
    except Exception as e:
        print(f"启动服务器时发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 
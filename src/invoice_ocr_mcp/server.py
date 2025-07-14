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
from mcp.types import Tool

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
        self.ocr_engine = OCREngine(self.config)
        self.invoice_parser = InvoiceParser(self.config)
        self.image_processor = ImageProcessor(self.config)
        self.batch_processor = BatchProcessor(self.config)
        
        # 注册MCP工具
        self._register_tools()
        
        self.logger.info("Invoice OCR MCP Server initialized")
    
    def _register_tools(self) -> None:
        """注册MCP工具"""
        
        # 1. 单张发票识别工具
        @self.server.tool()
        async def recognize_single_invoice(
            image_data: Optional[str] = None,
            image_url: Optional[str] = None,
            output_format: str = "standard"
        ) -> Dict[str, Any]:
            """识别单张发票并提取结构化信息
            
            Args:
                image_data: Base64编码的发票图像数据
                image_url: 发票图像URL地址
                output_format: 输出格式 (standard/detailed/raw)
            
            Returns:
                发票识别结果
            """
            try:
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
                invoice_type = await self.ocr_engine.classify_invoice_type(processed_image)
                
                # OCR文本识别
                ocr_result = await self.ocr_engine.extract_text(processed_image)
                
                # 解析发票信息
                parsed_data = await self.invoice_parser.parse_invoice(
                    ocr_result, 
                    invoice_type,
                    output_format
                )
                
                self.logger.info(f"单张发票识别完成，类型: {invoice_type.get('name')}")
                
                return {
                    "success": True,
                    "data": parsed_data
                }
                
            except Exception as e:
                self.logger.error(f"单张发票识别失败: {str(e)}", exc_info=True)
                return format_error_response("PROCESSING_ERROR", str(e))
        
        # 2. 批量发票识别工具
        @self.server.tool()
        async def recognize_batch_invoices(
            images: List[Dict[str, Any]],
            parallel_count: int = 3
        ) -> Dict[str, Any]:
            """批量识别多张发票
            
            Args:
                images: 发票图像数组，每个元素包含id和图像数据
                parallel_count: 并行处理数量，默认3，最大10
            
            Returns:
                批量识别结果
            """
            try:
                self.logger.info(f"收到批量发票识别请求，共 {len(images)} 张图片")
                
                # 验证输入参数
                validation_error = validate_batch_input(images, parallel_count)
                if validation_error:
                    return validation_error
                
                # 批量处理
                results = await self.batch_processor.process_batch(
                    images,
                    parallel_count,
                    self._process_single_image
                )
                
                # 统计结果
                success_count = len([r for r in results if r.get("status") == "success"])
                failed_count = len(results) - success_count
                
                self.logger.info(f"批量识别完成，成功: {success_count}, 失败: {failed_count}")
                
                return {
                    "success": True,
                    "data": {
                        "total_count": len(images),
                        "success_count": success_count,
                        "failed_count": failed_count,
                        "results": results,
                        "meta": {
                            "total_processing_time": sum(
                                r.get("processing_time", 0) for r in results
                            ),
                            "average_processing_time": sum(
                                r.get("processing_time", 0) for r in results
                            ) / len(results) if results else 0
                        }
                    }
                }
                
            except Exception as e:
                self.logger.error(f"批量发票识别失败: {str(e)}", exc_info=True)
                return format_error_response("BATCH_PROCESSING_ERROR", str(e))
        
        # 3. 发票类型检测工具
        @self.server.tool()
        async def detect_invoice_type(
            image_data: Optional[str] = None,
            image_url: Optional[str] = None
        ) -> Dict[str, Any]:
            """检测发票类型
            
            Args:
                image_data: Base64编码的发票图像数据
                image_url: 发票图像URL地址
            
            Returns:
                发票类型检测结果
            """
            try:
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
                classification_result = await self.ocr_engine.classify_invoice_type_detailed(
                    processed_image
                )
                
                self.logger.info(f"发票类型检测完成: {classification_result.get('invoice_type', {}).get('name')}")
                
                return {
                    "success": True,
                    "data": classification_result
                }
                
            except Exception as e:
                self.logger.error(f"发票类型检测失败: {str(e)}", exc_info=True)
                return format_error_response("TYPE_DETECTION_ERROR", str(e))
    
    async def _process_single_image(self, image_item: Dict[str, Any]) -> Dict[str, Any]:
        """处理单张图像（用于批量处理）
        
        Args:
            image_item: 包含图像数据的字典
        
        Returns:
            处理结果
        """
        import time
        start_time = time.time()
        
        try:
            # 获取图像数据
            image_id = image_item.get("id", "unknown")
            image_data = image_item.get("image_data")
            image_url = image_item.get("image_url")
            
            # 处理图像
            if image_data:
                image = await self.image_processor.decode_base64_image(image_data)
            else:
                image = await self.image_processor.download_image(image_url)
            
            # 预处理
            processed_image = await self.image_processor.preprocess_image(image)
            
            # 识别
            invoice_type = await self.ocr_engine.classify_invoice_type(processed_image)
            ocr_result = await self.ocr_engine.extract_text(processed_image)
            parsed_data = await self.invoice_parser.parse_invoice(
                ocr_result, 
                invoice_type,
                "standard"
            )
            
            processing_time = time.time() - start_time
            
            return {
                "id": image_id,
                "status": "success",
                "data": parsed_data,
                "processing_time": processing_time
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"处理图像 {image_item.get('id')} 失败: {str(e)}")
            
            return {
                "id": image_item.get("id", "unknown"),
                "status": "failed",
                "error": str(e),
                "processing_time": processing_time
            }
    
    async def start(self) -> None:
        """启动MCP服务器"""
        self.logger.info("启动 Invoice OCR MCP Server")
        
        try:
            # 初始化OCR引擎
            await self.ocr_engine.initialize()
            self.logger.info("OCR引擎初始化完成")
            
            # 启动MCP服务器
            async with stdio_server() as streams:
                await self.server.run(streams[0], streams[1])
                
        except KeyboardInterrupt:
            self.logger.info("收到中断信号，正在关闭服务器...")
        except Exception as e:
            self.logger.error(f"服务器启动失败: {str(e)}", exc_info=True)
            raise
        finally:
            await self.cleanup()
    
    async def cleanup(self) -> None:
        """清理资源"""
        try:
            await self.ocr_engine.cleanup()
            await self.batch_processor.cleanup()
            self.logger.info("资源清理完成")
        except Exception as e:
            self.logger.error(f"资源清理失败: {str(e)}")

    def get_tools(self) -> List[Tool]:
        """获取所有工具定义"""
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


async def main() -> None:
    """主函数"""
    try:
        # 创建并启动服务器
        config = Config()
        server = InvoiceOCRServer(config)
        await server.start()
    except Exception as e:
        logging.error(f"服务器启动失败: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # 设置事件循环策略（Windows兼容性）
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # 运行服务器
    asyncio.run(main()) 
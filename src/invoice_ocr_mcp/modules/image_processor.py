"""
图像处理模块

负责图像预处理、格式转换、质量优化等功能
"""

import asyncio
import base64
import io
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import cv2
from PIL import Image, ImageEnhance, ExifTags
import aiohttp
import aiofiles

from ..config import Config


class ImageProcessor:
    """图像处理器"""
    
    def __init__(self, config: Config):
        """初始化图像处理器
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 支持的图像格式
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
        
        # 图像质量增强参数
        self.enhancement_params = {
            'brightness': 1.1,      # 亮度增强
            'contrast': 1.2,        # 对比度增强
            'sharpness': 1.1,       # 锐化
            'color': 1.0            # 色彩饱和度
        }
        
        self.logger.info("图像处理器初始化完成")
    
    async def decode_base64_image(self, base64_data: str) -> np.ndarray:
        """解码Base64图像数据
        
        Args:
            base64_data: Base64编码的图像数据
            
        Returns:
            图像numpy数组
        """
        try:
            # 移除Base64前缀（如果存在）
            if ',' in base64_data:
                base64_data = base64_data.split(',')[1]
            
            # 解码Base64
            image_bytes = base64.b64decode(base64_data)
            
            # 转换为PIL图像
            pil_image = Image.open(io.BytesIO(image_bytes))
            
            # 处理EXIF方向信息
            pil_image = self._handle_exif_orientation(pil_image)
            
            # 转换为RGB格式
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # 转换为numpy数组
            image_array = np.array(pil_image)
            
            self.logger.debug(f"成功解码Base64图像，尺寸: {image_array.shape}")
            return image_array
            
        except Exception as e:
            self.logger.error(f"Base64图像解码失败: {str(e)}")
            raise ValueError(f"无效的Base64图像数据: {str(e)}")
    
    async def download_image(self, image_url: str) -> np.ndarray:
        """从URL下载图像
        
        Args:
            image_url: 图像URL地址
            
        Returns:
            图像numpy数组
        """
        try:
            timeout = aiohttp.ClientTimeout(total=self.config.processing.download_timeout)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        raise ValueError(f"HTTP错误: {response.status}")
                    
                    # 检查内容类型
                    content_type = response.headers.get('content-type', '')
                    if not content_type.startswith('image/'):
                        raise ValueError(f"不支持的内容类型: {content_type}")
                    
                    # 检查文件大小
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > self.config.processing.max_image_size:
                        raise ValueError(f"图像文件过大: {content_length} bytes")
                    
                    # 读取图像数据
                    image_bytes = await response.read()
            
            # 转换为PIL图像
            pil_image = Image.open(io.BytesIO(image_bytes))
            
            # 处理EXIF方向信息
            pil_image = self._handle_exif_orientation(pil_image)
            
            # 转换为RGB格式
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # 转换为numpy数组
            image_array = np.array(pil_image)
            
            self.logger.debug(f"成功下载图像，URL: {image_url}, 尺寸: {image_array.shape}")
            return image_array
            
        except Exception as e:
            self.logger.error(f"图像下载失败: {image_url}, 错误: {str(e)}")
            raise ValueError(f"无法下载图像: {str(e)}")
    
    async def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """图像预处理
        
        Args:
            image: 输入图像
            
        Returns:
            预处理后的图像
        """
        try:
            self.logger.debug("开始图像预处理")
            
            # 1. 尺寸检查和调整
            image = await self._resize_if_needed(image)
            
            # 2. 去噪处理
            image = await self._denoise_image(image)
            
            # 3. 图像增强
            image = await self._enhance_image(image)
            
            # 4. 文档图像特殊处理
            image = await self._document_specific_processing(image)
            
            self.logger.debug("图像预处理完成")
            return image
            
        except Exception as e:
            self.logger.error(f"图像预处理失败: {str(e)}")
            raise
    
    async def _resize_if_needed(self, image: np.ndarray) -> np.ndarray:
        """如果需要则调整图像尺寸"""
        height, width = image.shape[:2]
        max_size = self.config.processing.max_image_size
        
        # 检查是否需要缩放
        if max(height, width) > max_size:
            # 计算缩放比例
            scale = max_size / max(height, width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            # 使用高质量插值进行缩放
            image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
            self.logger.debug(f"图像尺寸调整: {width}x{height} -> {new_width}x{new_height}")
        
        # 确保图像尺寸是合理的
        if min(height, width) < 100:
            self.logger.warning("图像尺寸过小，可能影响识别效果")
        
        return image
    
    async def _denoise_image(self, image: np.ndarray) -> np.ndarray:
        """图像去噪处理"""
        # 使用非局部均值去噪
        denoised = cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
        return denoised
    
    async def _enhance_image(self, image: np.ndarray) -> np.ndarray:
        """图像增强处理"""
        # 转换为PIL图像进行增强
        pil_image = Image.fromarray(image)
        
        # 亮度增强
        if self.enhancement_params['brightness'] != 1.0:
            enhancer = ImageEnhance.Brightness(pil_image)
            pil_image = enhancer.enhance(self.enhancement_params['brightness'])
        
        # 对比度增强
        if self.enhancement_params['contrast'] != 1.0:
            enhancer = ImageEnhance.Contrast(pil_image)
            pil_image = enhancer.enhance(self.enhancement_params['contrast'])
        
        # 锐化处理
        if self.enhancement_params['sharpness'] != 1.0:
            enhancer = ImageEnhance.Sharpness(pil_image)
            pil_image = enhancer.enhance(self.enhancement_params['sharpness'])
        
        # 转换回numpy数组
        enhanced_image = np.array(pil_image)
        
        return enhanced_image
    
    async def _document_specific_processing(self, image: np.ndarray) -> np.ndarray:
        """文档图像特殊处理"""
        # 转换为灰度图进行处理
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        # 1. 自适应阈值处理（可选，根据图像质量决定）
        if self._needs_binarization(gray):
            # 使用自适应阈值
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            # 转换回彩色图像
            processed = cv2.cvtColor(binary, cv2.COLOR_GRAY2RGB)
        else:
            processed = image
        
        # 2. 形态学操作去除噪点
        kernel = np.ones((2, 2), np.uint8)
        processed = cv2.morphologyEx(processed, cv2.MORPH_CLOSE, kernel)
        
        # 3. 边缘保护的平滑处理
        processed = cv2.bilateralFilter(processed, 9, 75, 75)
        
        return processed
    
    def _needs_binarization(self, gray_image: np.ndarray) -> bool:
        """判断是否需要二值化处理"""
        # 计算图像的对比度
        std = np.std(gray_image)
        
        # 如果对比度较低，可能需要二值化
        return std < 50
    
    def _handle_exif_orientation(self, pil_image: Image.Image) -> Image.Image:
        """处理EXIF方向信息"""
        try:
            if hasattr(pil_image, '_getexif'):
                exif = pil_image._getexif()
                if exif is not None:
                    for tag, value in exif.items():
                        if tag in ExifTags.TAGS and ExifTags.TAGS[tag] == 'Orientation':
                            if value == 3:
                                pil_image = pil_image.rotate(180, expand=True)
                            elif value == 6:
                                pil_image = pil_image.rotate(270, expand=True)
                            elif value == 8:
                                pil_image = pil_image.rotate(90, expand=True)
                            break
        except Exception as e:
            self.logger.warning(f"处理EXIF方向信息失败: {str(e)}")
        
        return pil_image
    
    async def validate_image(self, image: Union[str, np.ndarray]) -> Tuple[bool, str]:
        """验证图像有效性
        
        Args:
            image: 图像数据（Base64字符串或numpy数组）
            
        Returns:
            (是否有效, 错误信息)
        """
        try:
            if isinstance(image, str):
                # Base64字符串验证
                if len(image) == 0:
                    return False, "图像数据为空"
                
                # 尝试解码
                try:
                    decoded_image = await self.decode_base64_image(image)
                except Exception as e:
                    return False, f"Base64解码失败: {str(e)}"
                
                image = decoded_image
            
            if isinstance(image, np.ndarray):
                # numpy数组验证
                if image.size == 0:
                    return False, "图像数组为空"
                
                if len(image.shape) not in [2, 3]:
                    return False, f"不支持的图像维度: {image.shape}"
                
                if len(image.shape) == 3 and image.shape[2] not in [1, 3, 4]:
                    return False, f"不支持的通道数: {image.shape[2]}"
                
                height, width = image.shape[:2]
                if height < 50 or width < 50:
                    return False, f"图像尺寸过小: {width}x{height}"
                
                if height > 10000 or width > 10000:
                    return False, f"图像尺寸过大: {width}x{height}"
                
                return True, "图像验证通过"
            
            return False, "不支持的图像格式"
            
        except Exception as e:
            return False, f"图像验证失败: {str(e)}"
    
    async def convert_to_base64(self, image: np.ndarray, format: str = 'JPEG', quality: int = 95) -> str:
        """将图像转换为Base64字符串
        
        Args:
            image: 图像numpy数组
            format: 输出格式 (JPEG/PNG)
            quality: JPEG质量 (1-100)
            
        Returns:
            Base64编码的图像字符串
        """
        try:
            # 转换为PIL图像
            pil_image = Image.fromarray(image)
            
            # 保存到内存缓冲区
            buffer = io.BytesIO()
            
            if format.upper() == 'JPEG':
                pil_image.save(buffer, format='JPEG', quality=quality, optimize=True)
                mime_type = 'image/jpeg'
            elif format.upper() == 'PNG':
                pil_image.save(buffer, format='PNG', optimize=True)
                mime_type = 'image/png'
            else:
                raise ValueError(f"不支持的图像格式: {format}")
            
            # 编码为Base64
            buffer.seek(0)
            image_bytes = buffer.getvalue()
            base64_string = base64.b64encode(image_bytes).decode('utf-8')
            
            # 添加数据URI前缀
            data_uri = f"data:{mime_type};base64,{base64_string}"
            
            return data_uri
            
        except Exception as e:
            self.logger.error(f"图像Base64转换失败: {str(e)}")
            raise
    
    async def save_image(self, image: np.ndarray, file_path: str) -> None:
        """保存图像到文件
        
        Args:
            image: 图像numpy数组
            file_path: 文件路径
        """
        try:
            # 转换为PIL图像
            pil_image = Image.fromarray(image)
            
            # 异步保存
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, pil_image.save, file_path)
            
            self.logger.debug(f"图像保存成功: {file_path}")
            
        except Exception as e:
            self.logger.error(f"图像保存失败: {file_path}, 错误: {str(e)}")
            raise
    
    async def load_image(self, file_path: str) -> np.ndarray:
        """从文件加载图像
        
        Args:
            file_path: 文件路径
            
        Returns:
            图像numpy数组
        """
        try:
            # 异步读取文件
            async with aiofiles.open(file_path, 'rb') as f:
                image_bytes = await f.read()
            
            # 转换为PIL图像
            pil_image = Image.open(io.BytesIO(image_bytes))
            
            # 处理EXIF方向信息
            pil_image = self._handle_exif_orientation(pil_image)
            
            # 转换为RGB格式
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # 转换为numpy数组
            image_array = np.array(pil_image)
            
            self.logger.debug(f"图像加载成功: {file_path}, 尺寸: {image_array.shape}")
            return image_array
            
        except Exception as e:
            self.logger.error(f"图像加载失败: {file_path}, 错误: {str(e)}")
            raise
    
    async def get_image_info(self, image: np.ndarray) -> Dict[str, Any]:
        """获取图像信息
        
        Args:
            image: 图像numpy数组
            
        Returns:
            图像信息字典
        """
        height, width = image.shape[:2]
        channels = image.shape[2] if len(image.shape) == 3 else 1
        
        # 计算图像统计信息
        mean_brightness = np.mean(image)
        std_brightness = np.std(image)
        
        # 估算文件大小（压缩后）
        estimated_size = height * width * channels * 0.1  # 假设10:1压缩比
        
        return {
            "width": int(width),
            "height": int(height), 
            "channels": int(channels),
            "dtype": str(image.dtype),
            "mean_brightness": float(mean_brightness),
            "std_brightness": float(std_brightness),
            "estimated_size_bytes": int(estimated_size),
            "aspect_ratio": round(width / height, 2)
        }
    
    async def create_thumbnail(self, image: np.ndarray, size: Tuple[int, int] = (200, 200)) -> np.ndarray:
        """创建缩略图
        
        Args:
            image: 原始图像
            size: 缩略图尺寸
            
        Returns:
            缩略图图像
        """
        try:
            # 转换为PIL图像
            pil_image = Image.fromarray(image)
            
            # 创建缩略图（保持纵横比）
            pil_image.thumbnail(size, Image.Resampling.LANCZOS)
            
            # 转换回numpy数组
            thumbnail = np.array(pil_image)
            
            return thumbnail
            
        except Exception as e:
            self.logger.error(f"缩略图创建失败: {str(e)}")
            raise 
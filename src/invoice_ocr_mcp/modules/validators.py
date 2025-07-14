"""
验证器模块

提供各种数据验证功能，包括图像数据、批量输入等验证
"""

import base64
import re
import logging
from typing import Any, Dict, List, Optional, Union
import mimetypes
from urllib.parse import urlparse


logger = logging.getLogger(__name__)


def validate_image_data(image_data: str) -> bool:
    """验证Base64图像数据格式
    
    Args:
        image_data: Base64编码的图像数据
        
    Returns:
        是否为有效的图像数据
    """
    if not image_data or not isinstance(image_data, str):
        return False
    
    try:
        # 移除可能的数据URI前缀
        if image_data.startswith('data:'):
            if ',' not in image_data:
                return False
            image_data = image_data.split(',')[1]
        
        # 验证Base64格式
        if not re.match(r'^[A-Za-z0-9+/]*={0,2}$', image_data):
            return False
        
        # 尝试解码
        decoded = base64.b64decode(image_data)
        
        # 检查最小大小（至少1KB）
        if len(decoded) < 1024:
            return False
        
        # 检查文件头是否为图像格式
        image_headers = [
            b'\xFF\xD8\xFF',  # JPEG
            b'\x89PNG\r\n\x1a\n',  # PNG
            b'GIF87a',  # GIF87a
            b'GIF89a',  # GIF89a
            b'BM',  # BMP
            b'II*\x00',  # TIFF (little endian)
            b'MM\x00*',  # TIFF (big endian)
            b'RIFF',  # WebP (需要进一步检查)
        ]
        
        for header in image_headers:
            if decoded.startswith(header):
                return True
        
        # 特殊处理WebP
        if decoded.startswith(b'RIFF') and b'WEBP' in decoded[:12]:
            return True
        
        return False
        
    except Exception as e:
        logger.debug(f"图像数据验证失败: {str(e)}")
        return False


def validate_image_url(image_url: str) -> bool:
    """验证图像URL格式
    
    Args:
        image_url: 图像URL地址
        
    Returns:
        是否为有效的图像URL
    """
    if not image_url or not isinstance(image_url, str):
        return False
    
    try:
        # URL格式验证
        parsed = urlparse(image_url)
        if not parsed.scheme or not parsed.netloc:
            return False
        
        # 协议验证
        if parsed.scheme not in ['http', 'https']:
            return False
        
        # 文件扩展名验证
        supported_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', 
            '.tiff', '.tif', '.webp', '.svg'
        }
        
        # 从URL路径中提取扩展名
        path = parsed.path.lower()
        for ext in supported_extensions:
            if path.endswith(ext):
                return True
        
        # 如果没有明确的扩展名，尝试从MIME类型推断
        mime_type, _ = mimetypes.guess_type(image_url)
        if mime_type and mime_type.startswith('image/'):
            return True
        
        # 允许无扩展名的URL（可能是动态生成的图片）
        if '.' not in path.split('/')[-1]:
            return True
        
        return False
        
    except Exception as e:
        logger.debug(f"图像URL验证失败: {str(e)}")
        return False


def validate_batch_input(images: List[Dict[str, Any]]) -> Dict[str, Any]:
    """验证批量输入数据
    
    Args:
        images: 图像列表
        
    Returns:
        验证结果 {"valid": bool, "error": str, "details": dict}
    """
    if not isinstance(images, list):
        return {
            "valid": False,
            "error": "输入必须是列表格式",
            "details": {"type": type(images).__name__}
        }
    
    if not images:
        return {
            "valid": False,
            "error": "图像列表不能为空",
            "details": {"count": 0}
        }
    
    # 检查列表长度
    if len(images) > 100:  # 假设最大批次为100
        return {
            "valid": False,
            "error": f"批次大小超限，最大支持100张图片，当前: {len(images)}",
            "details": {"count": len(images), "max_allowed": 100}
        }
    
    # 验证每个图像项
    validation_details = {
        "total_count": len(images),
        "valid_count": 0,
        "invalid_items": []
    }
    
    for i, image_item in enumerate(images):
        item_errors = []
        
        # 检查是否为字典
        if not isinstance(image_item, dict):
            item_errors.append(f"第{i+1}项不是字典格式")
            validation_details["invalid_items"].append({
                "index": i,
                "errors": item_errors
            })
            continue
        
        # 检查必需字段
        if "id" not in image_item:
            item_errors.append("缺少id字段")
        
        if "image_data" not in image_item and "image_url" not in image_item:
            item_errors.append("缺少image_data或image_url字段")
        
        # 验证ID格式
        if "id" in image_item:
            if not isinstance(image_item["id"], str) or not image_item["id"].strip():
                item_errors.append("id字段必须是非空字符串")
        
        # 验证图像数据
        if "image_data" in image_item:
            if not validate_image_data(image_item["image_data"]):
                item_errors.append("image_data格式无效")
        
        # 验证图像URL
        if "image_url" in image_item:
            if not validate_image_url(image_item["image_url"]):
                item_errors.append("image_url格式无效")
        
        # 记录验证结果
        if item_errors:
            validation_details["invalid_items"].append({
                "index": i,
                "id": image_item.get("id", f"item_{i}"),
                "errors": item_errors
            })
        else:
            validation_details["valid_count"] += 1
    
    # 最终验证结果
    is_valid = len(validation_details["invalid_items"]) == 0
    
    if is_valid:
        return {
            "valid": True,
            "error": None,
            "details": validation_details
        }
    else:
        error_summary = f"发现{len(validation_details['invalid_items'])}个无效项"
        return {
            "valid": False,
            "error": error_summary,
            "details": validation_details
        }


def validate_output_format(output_format: str) -> bool:
    """验证输出格式
    
    Args:
        output_format: 输出格式
        
    Returns:
        是否为有效格式
    """
    valid_formats = {"standard", "detailed", "raw"}
    return output_format in valid_formats


def validate_invoice_type_code(type_code: str) -> bool:
    """验证发票类型代码
    
    Args:
        type_code: 发票类型代码
        
    Returns:
        是否为有效的发票类型代码
    """
    valid_codes = {
        "01", "03", "04", "10", "11", "14", "15", "20",
        "99", "09", "61", "83", "100"
    }
    return type_code in valid_codes


def validate_amount(amount_str: str) -> bool:
    """验证金额格式
    
    Args:
        amount_str: 金额字符串
        
    Returns:
        是否为有效金额
    """
    if not amount_str or not isinstance(amount_str, str):
        return False
    
    try:
        # 移除货币符号和空格
        cleaned = amount_str.replace('￥', '').replace('¥', '').replace(',', '').strip()
        
        # 验证数字格式
        amount = float(cleaned)
        
        # 检查是否为非负数
        if amount < 0:
            return False
        
        # 检查小数位数（最多2位）
        if '.' in cleaned:
            decimal_places = len(cleaned.split('.')[1])
            if decimal_places > 2:
                return False
        
        return True
        
    except (ValueError, IndexError):
        return False


def validate_tax_id(tax_id: str) -> bool:
    """验证税号格式
    
    Args:
        tax_id: 税号
        
    Returns:
        是否为有效税号
    """
    if not tax_id or not isinstance(tax_id, str):
        return False
    
    # 统一社会信用代码（18位）
    if len(tax_id) == 18:
        return re.match(r'^[0-9A-HJ-NPQRTUWXY]{2}\d{6}[0-9A-HJ-NPQRTUWXY]{10}$', tax_id) is not None
    
    # 纳税人识别号（15位）
    elif len(tax_id) == 15:
        return re.match(r'^[0-9A-Z]{15}$', tax_id) is not None
    
    return False


def validate_phone_number(phone: str) -> bool:
    """验证电话号码格式
    
    Args:
        phone: 电话号码
        
    Returns:
        是否为有效电话号码
    """
    if not phone or not isinstance(phone, str):
        return False
    
    # 移除空格和特殊字符
    cleaned = re.sub(r'[\s\-()]', '', phone)
    
    # 手机号码格式
    mobile_pattern = r'^1[3-9]\d{9}$'
    
    # 固定电话格式
    landline_patterns = [
        r'^0\d{2,3}\d{7,8}$',  # 区号+号码
        r'^\d{3,4}\d{7,8}$',   # 简化格式
    ]
    
    # 检查手机号
    if re.match(mobile_pattern, cleaned):
        return True
    
    # 检查固定电话
    for pattern in landline_patterns:
        if re.match(pattern, cleaned):
            return True
    
    return False


def validate_date_string(date_str: str) -> bool:
    """验证日期字符串格式
    
    Args:
        date_str: 日期字符串
        
    Returns:
        是否为有效日期格式
    """
    if not date_str or not isinstance(date_str, str):
        return False
    
    # 支持的日期格式
    date_patterns = [
        r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
        r'^\d{4}/\d{2}/\d{2}$',  # YYYY/MM/DD
        r'^\d{4}年\d{1,2}月\d{1,2}日$',  # YYYY年MM月DD日
        r'^\d{4}\.\d{2}\.\d{2}$',  # YYYY.MM.DD
    ]
    
    for pattern in date_patterns:
        if re.match(pattern, date_str):
            return True
    
    return False


def sanitize_text(text: str, max_length: int = 1000) -> str:
    """清理和规范化文本
    
    Args:
        text: 原始文本
        max_length: 最大长度
        
    Returns:
        清理后的文本
    """
    if not text or not isinstance(text, str):
        return ""
    
    # 移除控制字符和特殊空白字符
    cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # 规范化空白字符
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # 去除首尾空白
    cleaned = cleaned.strip()
    
    # 限制长度
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    
    return cleaned


def validate_config_dict(config_dict: Dict[str, Any], required_keys: List[str]) -> Dict[str, Any]:
    """验证配置字典
    
    Args:
        config_dict: 配置字典
        required_keys: 必需的键列表
        
    Returns:
        验证结果
    """
    if not isinstance(config_dict, dict):
        return {
            "valid": False,
            "error": "配置必须是字典格式",
            "missing_keys": required_keys
        }
    
    missing_keys = [key for key in required_keys if key not in config_dict]
    
    if missing_keys:
        return {
            "valid": False,
            "error": f"缺少必需的配置项: {', '.join(missing_keys)}",
            "missing_keys": missing_keys
        }
    
    return {
        "valid": True,
        "error": None,
        "missing_keys": []
    } 
"""
工具函数模块

提供通用的工具函数，包括日志设置、错误处理、格式化等
"""

import logging
import logging.handlers
import sys
import time
import traceback
import json
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import uuid
import hashlib
import os


def setup_logging(config: Any) -> logging.Logger:
    """设置日志系统
    
    Args:
        config: 配置对象
        
    Returns:
        配置好的logger
    """
    # 创建日志目录
    log_dir = Path(getattr(config.logging, 'log_dir', './logs'))
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 获取配置参数
    log_level = getattr(config.logging, 'level', 'INFO').upper()
    log_format = getattr(config.logging, 'format', 'detailed')
    
    # 定义日志格式
    if log_format == 'simple':
        formatter = logging.Formatter(
            '%(levelname)s - %(message)s'
        )
    elif log_format == 'structured':
        formatter = StructuredFormatter()
    else:  # detailed
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # 获取根logger
    logger = logging.getLogger('invoice_ocr_mcp')
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # 清除现有处理器
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, log_level, logging.INFO))
    logger.addHandler(console_handler)
    
    # 文件处理器
    if getattr(config.logging, 'enable_file_logging', True):
        file_path = log_dir / getattr(config.logging, 'log_file', 'server.log')
        max_size = getattr(config.logging, 'log_max_size', 100 * 1024 * 1024)  # 字节
        backup_count = getattr(config.logging, 'log_backup_count', 10)
        
        file_handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=max_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(getattr(logging, log_level, logging.INFO))
        logger.addHandler(file_handler)
    
    # 错误日志处理器
    if getattr(config.logging, 'enable_error_logging', True):
        error_file = log_dir / getattr(config.logging, 'error_log_file', 'error.log')
        error_handler = logging.handlers.RotatingFileHandler(
            error_file,
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)
        logger.addHandler(error_handler)
    
    logger.info(f"日志系统初始化完成，级别: {log_level}")
    return logger


class StructuredFormatter(logging.Formatter):
    """结构化日志格式器"""
    
    def format(self, record):
        log_data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(record.created)),
            'level': record.levelname,
            'logger': record.name,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
            'module': record.module
        }
        
        # 添加异常信息
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # 添加额外字段
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        
        return json.dumps(log_data, ensure_ascii=False)


def format_error_response(error_code: str, 
                         error_message: str, 
                         details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """格式化错误响应
    
    Args:
        error_code: 错误代码
        error_message: 错误消息
        details: 额外的错误详情
        
    Returns:
        格式化的错误响应
    """
    response = {
        "success": False,
        "error": {
            "code": error_code,
            "message": error_message,
            "timestamp": time.time()
        }
    }
    
    if details:
        response["error"]["details"] = details
    
    return response


def format_success_response(data: Any, 
                          message: str = "操作成功",
                          meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """格式化成功响应
    
    Args:
        data: 响应数据
        message: 成功消息
        meta: 元数据
        
    Returns:
        格式化的成功响应
    """
    response = {
        "success": True,
        "message": message,
        "data": data,
        "timestamp": time.time()
    }
    
    if meta:
        response["meta"] = meta
    
    return response


def generate_request_id() -> str:
    """生成请求ID
    
    Returns:
        唯一的请求ID
    """
    return str(uuid.uuid4())


def calculate_file_hash(file_path: Union[str, Path], algorithm: str = 'md5') -> str:
    """计算文件哈希值
    
    Args:
        file_path: 文件路径
        algorithm: 哈希算法 (md5, sha1, sha256)
        
    Returns:
        文件哈希值
    """
    hash_algo = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_algo.update(chunk)
    
    return hash_algo.hexdigest()


def safe_json_dumps(obj: Any, **kwargs) -> str:
    """安全的JSON序列化
    
    Args:
        obj: 要序列化的对象
        **kwargs: 传递给json.dumps的参数
        
    Returns:
        JSON字符串
    """
    try:
        return json.dumps(obj, ensure_ascii=False, **kwargs)
    except TypeError:
        # 处理不可序列化的对象
        return json.dumps(str(obj), ensure_ascii=False, **kwargs)


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """安全的JSON反序列化
    
    Args:
        json_str: JSON字符串
        default: 解析失败时的默认值
        
    Returns:
        反序列化后的对象
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError, ValueError):
        return default


def timing_decorator(logger: Optional[logging.Logger] = None):
    """性能计时装饰器
    
    Args:
        logger: 日志记录器
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                if logger:
                    logger.debug(f"{func.__name__} 执行时间: {execution_time:.3f}秒")
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                if logger:
                    logger.error(f"{func.__name__} 执行失败，耗时: {execution_time:.3f}秒，错误: {str(e)}")
                raise
        
        return wrapper
    return decorator


def async_timing_decorator(logger: Optional[logging.Logger] = None):
    """异步性能计时装饰器
    
    Args:
        logger: 日志记录器
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                if logger:
                    logger.debug(f"{func.__name__} 执行时间: {execution_time:.3f}秒")
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                if logger:
                    logger.error(f"{func.__name__} 执行失败，耗时: {execution_time:.3f}秒，错误: {str(e)}")
                raise
        
        return wrapper
    return decorator


def get_error_traceback(exception: Exception) -> str:
    """获取异常的详细堆栈信息
    
    Args:
        exception: 异常对象
        
    Returns:
        堆栈信息字符串
    """
    return ''.join(traceback.format_exception(
        type(exception), exception, exception.__traceback__
    ))


def sanitize_filename(filename: str) -> str:
    """清理文件名，移除非法字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        清理后的文件名
    """
    # 定义非法字符
    illegal_chars = '<>:"/\\|?*'
    
    # 替换非法字符为下划线
    for char in illegal_chars:
        filename = filename.replace(char, '_')
    
    # 移除连续的下划线
    while '__' in filename:
        filename = filename.replace('__', '_')
    
    # 去除首尾下划线
    filename = filename.strip('_')
    
    # 确保文件名不为空
    if not filename:
        filename = 'unnamed'
    
    return filename


def format_bytes(bytes_size: int) -> str:
    """格式化字节大小为人类可读格式
    
    Args:
        bytes_size: 字节大小
        
    Returns:
        格式化后的大小字符串
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def create_directory_if_not_exists(directory: Union[str, Path]) -> None:
    """如果目录不存在则创建
    
    Args:
        directory: 目录路径
    """
    Path(directory).mkdir(parents=True, exist_ok=True)


def get_system_info() -> Dict[str, Any]:
    """获取系统信息
    
    Returns:
        系统信息字典
    """
    import platform
    import psutil
    
    try:
        cpu_count = os.cpu_count()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": cpu_count,
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "memory_percent": memory.percent,
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "disk_percent": round((disk.used / disk.total) * 100, 2)
        }
    except ImportError:
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": os.cpu_count()
        }


def retry_on_exception(max_retries: int = 3, 
                      delay: float = 1.0,
                      backoff_factor: float = 2.0,
                      exceptions: tuple = (Exception,)):
    """重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff_factor: 退避因子
        exceptions: 需要重试的异常类型
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        raise
                    
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
            
        return wrapper
    return decorator 
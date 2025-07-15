"""
配置管理模块

负责加载和管理所有配置参数
"""

import os
import logging
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv


@dataclass
class OCREngineConfig:
    """OCR引擎配置"""
    # 引擎类型：'rapidocr' 或 'modelscope'
    engine_type: str = "rapidocr"  # 默认使用RapidOCR
    
    # RapidOCR配置
    rapidocr_use_gpu: bool = False
    rapidocr_device_id: int = 0
    
    # ModelScope配置（仅当engine_type='modelscope'时生效）
    modelscope_use_gpu: bool = False
    modelscope_device_id: int = 0


@dataclass
class ModelConfig:
    """模型配置"""
    # 使用存在的文本检测模型
    text_detection_model: str = "damo/cv_resnet18_ocr-detection-line-level_damo"
    # 使用存在的文本识别模型  
    text_recognition_model: str = "damo/cv_convnextTiny_ocr-recognition-general_damo"
    # 发票分类模型 - 使用通用图像分类模型或设置为None启用mock模式
    invoice_classification_model: str = None  # 暂时设为None，启用mock模式
    # 信息抽取模型 - 使用通用文本分类模型或设置为None启用mock模式
    info_extraction_model: str = None  # 暂时设为None，启用mock模式
    cache_dir: str = "./cache/modelscope"
    use_gpu: bool = False
    gpu_device_id: int = 0
    # 启用mock模式 - 当某些模型不可用时使用模拟数据
    enable_mock_mode: bool = True


@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    log_level: str = "INFO"
    max_concurrent_requests: int = 10
    request_timeout: int = 300


@dataclass
class ProcessingConfig:
    """处理配置"""
    max_batch_size: int = 50
    max_image_size: int = 4096
    model_inference_timeout: int = 30
    parallel_workers: int = 4
    enable_cache: bool = True
    cache_expire_time: int = 86400


@dataclass
class SecurityConfig:
    """安全配置"""
    api_key: Optional[str] = None
    jwt_secret_key: Optional[str] = None
    cors_origins: str = "*"
    enable_https: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None


@dataclass
class LoggingConfig:
    """日志配置"""
    log_dir: str = "./logs"
    log_max_size: int = 100 * 1024 * 1024  # 100MB
    log_backup_count: int = 10
    enable_structured_logging: bool = True
    enable_access_log: bool = True


@dataclass
class CacheConfig:
    """缓存配置"""
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    cache_prefix: str = "invoice_ocr:"


@dataclass
class StorageConfig:
    """存储配置"""
    upload_dir: str = "./data/uploads"
    result_dir: str = "./data/results"
    temp_dir: str = "./data/temp"
    storage_type: str = "local"  # local/s3/oss
    max_upload_size: int = 50 * 1024 * 1024  # 50MB


class Config:
    """主配置类"""
    
    def __init__(self, config_file: Optional[str] = None, env_file: Optional[str] = None):
        """初始化配置
        
        Args:
            config_file: 配置文件路径
            env_file: 环境变量文件路径
        """
        # 加载环境变量
        if env_file:
            load_dotenv(env_file)
        else:
            # 尝试加载默认的.env文件
            for env_path in [".env", "env.example"]:
                if os.path.exists(env_path):
                    load_dotenv(env_path)
                    break
        
        # 初始化各模块配置
        self.ocr_engine = OCREngineConfig()
        self.models = ModelConfig()
        self.server = ServerConfig()
        self.processing = ProcessingConfig()
        self.security = SecurityConfig()
        self.logging = LoggingConfig()
        self.cache = CacheConfig()
        self.storage = StorageConfig()
        
        # 加载配置文件
        if config_file:
            self.load_from_file(config_file)
        else:
            # 尝试加载默认配置文件
            for config_path in ["configs/server.yaml", "server.yaml"]:
                if os.path.exists(config_path):
                    self.load_from_file(config_path)
                    break
        
        # 从环境变量覆盖配置
        self.load_from_env()
        
        # 验证配置
        self.validate()
        
        # 创建必要的目录
        self.create_directories()
    
    def load_from_file(self, config_file: str) -> None:
        """从文件加载配置"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            # 更新各模块配置
            if 'models' in config_data:
                self._update_dataclass(self.models, config_data['models'])
            
            if 'server' in config_data:
                self._update_dataclass(self.server, config_data['server'])
            
            if 'processing' in config_data:
                self._update_dataclass(self.processing, config_data['processing'])
            
            if 'security' in config_data:
                self._update_dataclass(self.security, config_data['security'])
            
            if 'logging' in config_data:
                self._update_dataclass(self.logging, config_data['logging'])
            
            if 'cache' in config_data:
                self._update_dataclass(self.cache, config_data['cache'])
            
            if 'storage' in config_data:
                self._update_dataclass(self.storage, config_data['storage'])
                
        except Exception as e:
            logging.warning(f"加载配置文件失败: {e}")
    
    def load_from_env(self) -> None:
        """从环境变量加载配置"""
        # ModelScope配置
        self.modelscope_api_token = os.getenv("MODELSCOPE_API_TOKEN")
        if not self.modelscope_api_token:
            logging.warning("未设置MODELSCOPE_API_TOKEN环境变量")
        
        # 模型配置
        if os.getenv("TEXT_DETECTION_MODEL"):
            self.models.text_detection_model = os.getenv("TEXT_DETECTION_MODEL")
        if os.getenv("TEXT_RECOGNITION_MODEL"):
            self.models.text_recognition_model = os.getenv("TEXT_RECOGNITION_MODEL")
        if os.getenv("INVOICE_CLASSIFICATION_MODEL"):
            self.models.invoice_classification_model = os.getenv("INVOICE_CLASSIFICATION_MODEL")
        if os.getenv("MODELSCOPE_CACHE_DIR"):
            self.models.cache_dir = os.getenv("MODELSCOPE_CACHE_DIR")
        if os.getenv("USE_GPU"):
            self.models.use_gpu = os.getenv("USE_GPU").lower() == "true"
        if os.getenv("CUDA_DEVICE_ID"):
            self.models.gpu_device_id = int(os.getenv("CUDA_DEVICE_ID"))
        
        # 服务器配置
        if os.getenv("HOST"):
            self.server.host = os.getenv("HOST")
        if os.getenv("PORT"):
            self.server.port = int(os.getenv("PORT"))
        if os.getenv("DEBUG"):
            self.server.debug = os.getenv("DEBUG").lower() == "true"
        if os.getenv("LOG_LEVEL"):
            self.server.log_level = os.getenv("LOG_LEVEL")
        if os.getenv("MAX_CONCURRENT_REQUESTS"):
            self.server.max_concurrent_requests = int(os.getenv("MAX_CONCURRENT_REQUESTS"))
        
        # 处理配置
        if os.getenv("MAX_BATCH_SIZE"):
            self.processing.max_batch_size = int(os.getenv("MAX_BATCH_SIZE"))
        if os.getenv("MAX_IMAGE_SIZE"):
            self.processing.max_image_size = int(os.getenv("MAX_IMAGE_SIZE"))
        if os.getenv("ENABLE_CACHE"):
            self.processing.enable_cache = os.getenv("ENABLE_CACHE").lower() == "true"
        if os.getenv("CACHE_EXPIRE_TIME"):
            self.processing.cache_expire_time = int(os.getenv("CACHE_EXPIRE_TIME"))
        
        # 安全配置
        if os.getenv("API_KEY"):
            self.security.api_key = os.getenv("API_KEY")
        if os.getenv("JWT_SECRET_KEY"):
            self.security.jwt_secret_key = os.getenv("JWT_SECRET_KEY")
        if os.getenv("CORS_ORIGINS"):
            self.security.cors_origins = os.getenv("CORS_ORIGINS")
        if os.getenv("ENABLE_HTTPS"):
            self.security.enable_https = os.getenv("ENABLE_HTTPS").lower() == "true"
        if os.getenv("SSL_CERT_PATH"):
            self.security.ssl_cert_path = os.getenv("SSL_CERT_PATH")
        if os.getenv("SSL_KEY_PATH"):
            self.security.ssl_key_path = os.getenv("SSL_KEY_PATH")
        
        # 日志配置
        if os.getenv("LOG_DIR"):
            self.logging.log_dir = os.getenv("LOG_DIR")
        if os.getenv("LOG_MAX_SIZE"):
            self.logging.log_max_size = int(os.getenv("LOG_MAX_SIZE")) * 1024 * 1024
        if os.getenv("ENABLE_STRUCTURED_LOGGING"):
            self.logging.enable_structured_logging = os.getenv("ENABLE_STRUCTURED_LOGGING").lower() == "true"
        
        # 缓存配置
        if os.getenv("REDIS_HOST"):
            self.cache.redis_host = os.getenv("REDIS_HOST")
        if os.getenv("REDIS_PORT"):
            self.cache.redis_port = int(os.getenv("REDIS_PORT"))
        if os.getenv("REDIS_PASSWORD"):
            self.cache.redis_password = os.getenv("REDIS_PASSWORD")
        
        # 存储配置
        if os.getenv("UPLOAD_DIR"):
            self.storage.upload_dir = os.getenv("UPLOAD_DIR")
        if os.getenv("RESULT_DIR"):
            self.storage.result_dir = os.getenv("RESULT_DIR")
        if os.getenv("TEMP_DIR"):
            self.storage.temp_dir = os.getenv("TEMP_DIR")
        if os.getenv("MAX_UPLOAD_SIZE"):
            self.storage.max_upload_size = int(os.getenv("MAX_UPLOAD_SIZE")) * 1024 * 1024
    
    def _update_dataclass(self, instance: Any, data: Dict[str, Any]) -> None:
        """更新dataclass实例"""
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
    
    def validate(self) -> None:
        """验证配置"""
        errors = []
        
        # 验证必需的配置
        if not self.modelscope_api_token:
            errors.append("缺少ModelScope API Token")
        
        # 验证端口范围
        if not (1 <= self.server.port <= 65535):
            errors.append(f"无效的端口号: {self.server.port}")
        
        # 验证批次大小
        if self.processing.max_batch_size <= 0:
            errors.append(f"无效的批次大小: {self.processing.max_batch_size}")
        
        # 验证GPU设置
        if self.models.use_gpu and self.models.gpu_device_id < 0:
            errors.append(f"无效的GPU设备ID: {self.models.gpu_device_id}")
        
        # 验证SSL配置
        if self.security.enable_https:
            if not self.security.ssl_cert_path or not self.security.ssl_key_path:
                errors.append("启用HTTPS时必须提供SSL证书路径")
        
        if errors:
            raise ValueError(f"配置验证失败: {'; '.join(errors)}")
    
    def create_directories(self) -> None:
        """创建必要的目录"""
        directories = [
            self.models.cache_dir,
            self.logging.log_dir,
            self.storage.upload_dir,
            self.storage.result_dir,
            self.storage.temp_dir,
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "models": {
                "text_detection_model": self.models.text_detection_model,
                "text_recognition_model": self.models.text_recognition_model,
                "invoice_classification_model": self.models.invoice_classification_model,
                "info_extraction_model": self.models.info_extraction_model,
                "cache_dir": self.models.cache_dir,
                "use_gpu": self.models.use_gpu,
                "gpu_device_id": self.models.gpu_device_id,
            },
            "server": {
                "host": self.server.host,
                "port": self.server.port,
                "debug": self.server.debug,
                "log_level": self.server.log_level,
                "max_concurrent_requests": self.server.max_concurrent_requests,
                "request_timeout": self.server.request_timeout,
            },
            "processing": {
                "max_batch_size": self.processing.max_batch_size,
                "max_image_size": self.processing.max_image_size,
                "model_inference_timeout": self.processing.model_inference_timeout,
                "parallel_workers": self.processing.parallel_workers,
                "enable_cache": self.processing.enable_cache,
                "cache_expire_time": self.processing.cache_expire_time,
            },
            "security": {
                "cors_origins": self.security.cors_origins,
                "enable_https": self.security.enable_https,
            },
            "logging": {
                "log_dir": self.logging.log_dir,
                "log_max_size": self.logging.log_max_size,
                "log_backup_count": self.logging.log_backup_count,
                "enable_structured_logging": self.logging.enable_structured_logging,
                "enable_access_log": self.logging.enable_access_log,
            },
            "cache": {
                "redis_host": self.cache.redis_host,
                "redis_port": self.cache.redis_port,
                "redis_db": self.cache.redis_db,
                "cache_prefix": self.cache.cache_prefix,
            },
            "storage": {
                "upload_dir": self.storage.upload_dir,
                "result_dir": self.storage.result_dir,
                "temp_dir": self.storage.temp_dir,
                "storage_type": self.storage.storage_type,
                "max_upload_size": self.storage.max_upload_size,
            }
        }
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"Config(server={self.server.host}:{self.server.port}, debug={self.server.debug})"


# 全局配置实例
config = Config()


def get_config() -> Config:
    """获取全局配置实例"""
    return config


def reload_config(config_file: Optional[str] = None, env_file: Optional[str] = None) -> Config:
    """重新加载配置"""
    global config
    config = Config(config_file, env_file)
    return config 
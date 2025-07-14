"""
模型管理器模块

负责ModelScope模型的下载、缓存、版本管理和性能监控
"""

import asyncio
import logging
import os
import time
import json
from typing import Any, Dict, List, Optional
from pathlib import Path
import shutil
import hashlib

try:
    from modelscope.hub.api import HubApi
    from modelscope import snapshot_download
    from modelscope.utils.constant import ModelFile
except ImportError:
    logging.warning("ModelScope未安装，模型管理功能不可用")
    HubApi = None
    snapshot_download = None

from ..config import Config


class ModelManager:
    """模型管理器"""
    
    def __init__(self, config: Config):
        """初始化模型管理器
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 模型缓存目录
        self.cache_dir = Path(config.models.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 模型注册表文件
        self.registry_file = self.cache_dir / "model_registry.json"
        
        # 模型状态
        self.model_registry = self._load_registry()
        
        self.logger.info(f"模型管理器初始化完成，缓存目录: {self.cache_dir}")
    
    def _load_registry(self) -> Dict[str, Any]:
        """加载模型注册表"""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"加载模型注册表失败: {str(e)}")
        
        return {
            "models": {},
            "last_updated": None,
            "version": "1.0"
        }
    
    def _save_registry(self) -> None:
        """保存模型注册表"""
        try:
            self.model_registry["last_updated"] = time.time()
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(self.model_registry, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"保存模型注册表失败: {str(e)}")
    
    async def download_all_models(self) -> Dict[str, Any]:
        """下载所有需要的模型
        
        Returns:
            下载结果统计
        """
        start_time = time.time()
        
        models_to_download = [
            {
                "name": "text_detection",
                "model_id": self.config.models.text_detection_model,
                "revision": getattr(self.config.models, 'text_detection_version', 'v1.0.2')
            },
            {
                "name": "text_recognition", 
                "model_id": self.config.models.text_recognition_model,
                "revision": getattr(self.config.models, 'text_recognition_version', 'v1.0.1')
            },
            {
                "name": "invoice_classification",
                "model_id": self.config.models.invoice_classification_model,
                "revision": getattr(self.config.models, 'invoice_classification_version', 'v1.0.0')
            },
            {
                "name": "info_extraction",
                "model_id": self.config.models.info_extraction_model,
                "revision": getattr(self.config.models, 'info_extraction_version', 'v1.0.0')
            }
        ]
        
        successful = 0
        failed = 0
        results = []
        
        self.logger.info(f"开始下载 {len(models_to_download)} 个模型")
        
        for model_info in models_to_download:
            try:
                result = await self.download_model(
                    model_info["name"],
                    model_info["model_id"], 
                    model_info["revision"]
                )
                
                if result["success"]:
                    successful += 1
                else:
                    failed += 1
                
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"下载模型失败 {model_info['name']}: {str(e)}")
                failed += 1
                results.append({
                    "model_name": model_info["name"],
                    "success": False,
                    "error": str(e)
                })
        
        total_time = time.time() - start_time
        
        self.logger.info(f"模型下载完成，成功: {successful}/{len(models_to_download)}, 耗时: {total_time:.2f}秒")
        
        return {
            "total": len(models_to_download),
            "successful": successful,
            "failed": failed,
            "results": results,
            "total_time": total_time
        }
    
    async def download_model(self, 
                           model_name: str, 
                           model_id: str, 
                           revision: str = None) -> Dict[str, Any]:
        """下载单个模型
        
        Args:
            model_name: 模型名称
            model_id: ModelScope模型ID
            revision: 模型版本
            
        Returns:
            下载结果
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"开始下载模型: {model_name} ({model_id})")
            
            # 检查模型是否已存在
            if self.is_model_cached(model_name, model_id, revision):
                self.logger.info(f"模型已缓存: {model_name}")
                return {
                    "model_name": model_name,
                    "model_id": model_id,
                    "revision": revision,
                    "success": True,
                    "cached": True,
                    "download_time": 0
                }
            
            # 下载模型
            loop = asyncio.get_event_loop()
            
            def _download():
                return snapshot_download(
                    model_id,
                    revision=revision,
                    cache_dir=str(self.cache_dir),
                    ignore_file_pattern=[r"\.git", r"\.gitignore", r"\.gitattributes"]
                )
            
            if snapshot_download is None:
                raise ImportError("ModelScope未安装")
            
            model_path = await loop.run_in_executor(None, _download)
            
            # 验证下载结果
            model_path = Path(model_path)
            if not model_path.exists():
                raise ValueError(f"模型下载失败，路径不存在: {model_path}")
            
            # 计算模型大小
            model_size = self._calculate_directory_size(model_path)
            
            # 更新注册表
            self.model_registry["models"][model_name] = {
                "model_id": model_id,
                "revision": revision,
                "local_path": str(model_path),
                "download_time": time.time(),
                "size_bytes": model_size,
                "status": "ready"
            }
            self._save_registry()
            
            download_time = time.time() - start_time
            
            self.logger.info(f"模型下载完成: {model_name}, 大小: {model_size / 1024 / 1024:.2f}MB, 耗时: {download_time:.2f}秒")
            
            return {
                "model_name": model_name,
                "model_id": model_id,
                "revision": revision,
                "success": True,
                "cached": False,
                "local_path": str(model_path),
                "size_bytes": model_size,
                "download_time": download_time
            }
            
        except Exception as e:
            error_msg = f"模型下载失败: {model_name}, 错误: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                "model_name": model_name,
                "model_id": model_id,
                "revision": revision,
                "success": False,
                "error": str(e),
                "download_time": time.time() - start_time
            }
    
    def is_model_cached(self, model_name: str, model_id: str, revision: str = None) -> bool:
        """检查模型是否已缓存
        
        Args:
            model_name: 模型名称
            model_id: 模型ID
            revision: 模型版本
            
        Returns:
            是否已缓存
        """
        if model_name not in self.model_registry["models"]:
            return False
        
        model_info = self.model_registry["models"][model_name]
        
        # 检查模型ID和版本是否匹配
        if model_info["model_id"] != model_id:
            return False
        
        if revision and model_info.get("revision") != revision:
            return False
        
        # 检查本地文件是否存在
        local_path = model_info.get("local_path")
        if not local_path or not Path(local_path).exists():
            return False
        
        return True
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """获取模型信息
        
        Args:
            model_name: 模型名称
            
        Returns:
            模型信息
        """
        return self.model_registry["models"].get(model_name)
    
    def get_all_models_info(self) -> Dict[str, Any]:
        """获取所有模型信息
        
        Returns:
            所有模型信息
        """
        return self.model_registry
    
    async def check_model_updates(self) -> Dict[str, Any]:
        """检查模型更新
        
        Returns:
            更新检查结果
        """
        if HubApi is None:
            return {"error": "ModelScope未安装"}
        
        update_info = []
        
        for model_name, model_info in self.model_registry["models"].items():
            try:
                model_id = model_info["model_id"]
                current_revision = model_info.get("revision")
                
                # 获取最新版本信息（这里简化实现）
                # 实际应用中需要调用ModelScope API获取最新版本
                update_info.append({
                    "model_name": model_name,
                    "model_id": model_id,
                    "current_revision": current_revision,
                    "has_update": False,  # 简化实现
                    "latest_revision": current_revision
                })
                
            except Exception as e:
                self.logger.warning(f"检查模型更新失败: {model_name}, 错误: {str(e)}")
        
        return {
            "models": update_info,
            "check_time": time.time()
        }
    
    async def delete_model(self, model_name: str) -> bool:
        """删除模型
        
        Args:
            model_name: 模型名称
            
        Returns:
            是否删除成功
        """
        if model_name not in self.model_registry["models"]:
            return False
        
        try:
            model_info = self.model_registry["models"][model_name]
            local_path = model_info.get("local_path")
            
            if local_path and Path(local_path).exists():
                shutil.rmtree(local_path)
                self.logger.info(f"删除模型文件: {local_path}")
            
            # 从注册表中移除
            del self.model_registry["models"][model_name]
            self._save_registry()
            
            self.logger.info(f"删除模型成功: {model_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"删除模型失败: {model_name}, 错误: {str(e)}")
            return False
    
    def _calculate_directory_size(self, directory: Path) -> int:
        """计算目录大小
        
        Args:
            directory: 目录路径
            
        Returns:
            目录大小（字节）
        """
        total_size = 0
        
        try:
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            self.logger.warning(f"计算目录大小失败: {directory}, 错误: {str(e)}")
        
        return total_size
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息
        
        Returns:
            缓存统计信息
        """
        total_models = len(self.model_registry["models"])
        total_size = 0
        ready_models = 0
        
        for model_info in self.model_registry["models"].values():
            if model_info.get("status") == "ready":
                ready_models += 1
            total_size += model_info.get("size_bytes", 0)
        
        # 获取缓存目录可用空间
        cache_stat = shutil.disk_usage(self.cache_dir)
        
        return {
            "total_models": total_models,
            "ready_models": ready_models,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "cache_directory": str(self.cache_dir),
            "disk_total_bytes": cache_stat.total,
            "disk_used_bytes": cache_stat.used,
            "disk_free_bytes": cache_stat.free,
            "disk_usage_percent": round((cache_stat.used / cache_stat.total) * 100, 2)
        }
    
    async def cleanup_cache(self, keep_recent: int = 30) -> Dict[str, Any]:
        """清理缓存
        
        Args:
            keep_recent: 保留最近N天的模型
            
        Returns:
            清理结果
        """
        current_time = time.time()
        keep_threshold = current_time - (keep_recent * 24 * 3600)
        
        cleaned_models = []
        cleaned_size = 0
        
        for model_name, model_info in list(self.model_registry["models"].items()):
            download_time = model_info.get("download_time", current_time)
            
            if download_time < keep_threshold:
                model_size = model_info.get("size_bytes", 0)
                
                if await self.delete_model(model_name):
                    cleaned_models.append(model_name)
                    cleaned_size += model_size
        
        self.logger.info(f"缓存清理完成，删除 {len(cleaned_models)} 个模型，释放空间 {cleaned_size / 1024 / 1024:.2f}MB")
        
        return {
            "cleaned_models": cleaned_models,
            "cleaned_count": len(cleaned_models),
            "cleaned_size_bytes": cleaned_size,
            "cleaned_size_mb": round(cleaned_size / 1024 / 1024, 2)
        } 
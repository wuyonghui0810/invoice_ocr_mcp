"""
批量处理器模块

负责批量发票识别的任务调度、并发管理和结果汇总
"""

import asyncio
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import traceback

from ..config import Config
from .ocr_engine import OCREngine
from .invoice_parser import InvoiceParser
from .image_processor import ImageProcessor
from .validators import validate_image_data


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BatchTask:
    """批处理任务"""
    id: str
    image_data: Optional[str] = None
    image_url: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    @property
    def processing_time(self) -> Optional[float]:
        """处理时间"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


class BatchProcessor:
    """批量处理器"""
    
    def __init__(self, config: Config):
        """初始化批量处理器
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 初始化依赖组件
        self.ocr_engine = OCREngine(config)
        self.invoice_parser = InvoiceParser(config)
        self.image_processor = ImageProcessor(config)
        
        # 并发控制
        self.semaphore = asyncio.Semaphore(config.processing.parallel_workers)
        
        # 活跃任务追踪
        self.active_batches: Dict[str, List[BatchTask]] = {}
        
        self.logger.info("批量处理器初始化完成")
    
    async def process_batch(self, 
                          images: List[Dict[str, Any]], 
                          parallel_count: int = None,
                          output_format: str = "standard") -> Dict[str, Any]:
        """处理批量发票识别
        
        Args:
            images: 图像列表，每个包含id和image_data或image_url
            parallel_count: 并行处理数量
            output_format: 输出格式
            
        Returns:
            批处理结果
        """
        batch_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            self.logger.info(f"开始批量处理，批次ID: {batch_id}, 图像数量: {len(images)}")
            
            # 验证输入
            validation_result = await self._validate_batch_input(images)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "batch_id": batch_id,
                    "error": validation_result["error"],
                    "results": []
                }
            
            # 创建批处理任务
            tasks = await self._create_batch_tasks(images, batch_id)
            
            # 设置并行数量
            if parallel_count is None:
                parallel_count = min(self.config.processing.parallel_workers, len(tasks))
            else:
                parallel_count = min(parallel_count, self.config.processing.parallel_workers)
            
            # 执行批量处理
            results = await self._execute_batch_tasks(tasks, parallel_count, output_format)
            
            # 计算统计信息
            stats = self._calculate_batch_stats(tasks, start_time)
            
            # 清理批次记录
            if batch_id in self.active_batches:
                del self.active_batches[batch_id]
            
            self.logger.info(f"批量处理完成，批次ID: {batch_id}, 成功: {stats['successful']}/{stats['total']}")
            
            return {
                "success": True,
                "batch_id": batch_id,
                "results": results,
                "statistics": stats
            }
            
        except Exception as e:
            self.logger.error(f"批量处理失败，批次ID: {batch_id}, 错误: {str(e)}")
            error_trace = traceback.format_exc()
            self.logger.debug(f"错误堆栈: {error_trace}")
            
            return {
                "success": False,
                "batch_id": batch_id,
                "error": f"批量处理失败: {str(e)}",
                "results": []
            }
    
    async def _validate_batch_input(self, images: List[Dict[str, Any]]) -> Dict[str, Any]:
        """验证批量输入
        
        Args:
            images: 图像列表
            
        Returns:
            验证结果
        """
        if not images:
            return {"valid": False, "error": "图像列表为空"}
        
        if len(images) > self.config.processing.max_batch_size:
            return {
                "valid": False, 
                "error": f"批次大小超限，最大支持 {self.config.processing.max_batch_size} 张图片"
            }
        
        # 检查每个图像项
        for i, image_item in enumerate(images):
            if not isinstance(image_item, dict):
                return {"valid": False, "error": f"第 {i+1} 项不是有效的字典格式"}
            
            if "id" not in image_item:
                return {"valid": False, "error": f"第 {i+1} 项缺少id字段"}
            
            if "image_data" not in image_item and "image_url" not in image_item:
                return {"valid": False, "error": f"第 {i+1} 项缺少image_data或image_url字段"}
            
            # 验证image_data格式（如果存在）
            if "image_data" in image_item:
                if not validate_image_data(image_item["image_data"]):
                    return {"valid": False, "error": f"第 {i+1} 项的image_data格式无效"}
        
        return {"valid": True, "error": None}
    
    async def _create_batch_tasks(self, images: List[Dict[str, Any]], batch_id: str) -> List[BatchTask]:
        """创建批处理任务
        
        Args:
            images: 图像列表
            batch_id: 批次ID
            
        Returns:
            任务列表
        """
        tasks = []
        
        for image_item in images:
            task = BatchTask(
                id=image_item["id"],
                image_data=image_item.get("image_data"),
                image_url=image_item.get("image_url")
            )
            tasks.append(task)
        
        # 记录批次任务
        self.active_batches[batch_id] = tasks
        
        return tasks
    
    async def _execute_batch_tasks(self, 
                                 tasks: List[BatchTask], 
                                 parallel_count: int,
                                 output_format: str) -> List[Dict[str, Any]]:
        """执行批处理任务
        
        Args:
            tasks: 任务列表
            parallel_count: 并行数量
            output_format: 输出格式
            
        Returns:
            处理结果列表
        """
        # 创建信号量控制并发
        semaphore = asyncio.Semaphore(parallel_count)
        
        # 创建任务协程
        async def process_single_task(task: BatchTask) -> Dict[str, Any]:
            async with semaphore:
                return await self._process_single_task(task, output_format)
        
        # 并发执行所有任务
        task_coroutines = [process_single_task(task) for task in tasks]
        results = await asyncio.gather(*task_coroutines, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = {
                    "id": tasks[i].id,
                    "success": False,
                    "error": {
                        "code": "PROCESSING_ERROR",
                        "message": str(result)
                    },
                    "processing_time": None
                }
                processed_results.append(error_result)
                tasks[i].status = TaskStatus.FAILED
                tasks[i].error = str(result)
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _process_single_task(self, task: BatchTask, output_format: str) -> Dict[str, Any]:
        """处理单个任务
        
        Args:
            task: 批处理任务
            output_format: 输出格式
            
        Returns:
            处理结果
        """
        task.start_time = time.time()
        task.status = TaskStatus.PROCESSING
        
        try:
            # 获取图像数据
            if task.image_data:
                image = await self.image_processor.decode_base64_image(task.image_data)
            elif task.image_url:
                image = await self.image_processor.download_image(task.image_url)
            else:
                raise ValueError("缺少图像数据")
            
            # 图像预处理
            processed_image = await self.image_processor.preprocess_image(image)
            
            # OCR识别
            ocr_result = await self.ocr_engine.full_ocr_pipeline(processed_image)
            
            # 发票解析
            parsed_result = await self.invoice_parser.parse_invoice(ocr_result, output_format)
            
            task.end_time = time.time()
            task.status = TaskStatus.COMPLETED
            task.result = parsed_result
            
            return {
                "id": task.id,
                "success": True,
                "data": parsed_result,
                "processing_time": task.processing_time
            }
            
        except Exception as e:
            task.end_time = time.time()
            task.status = TaskStatus.FAILED
            task.error = str(e)
            
            self.logger.error(f"任务处理失败，任务ID: {task.id}, 错误: {str(e)}")
            
            return {
                "id": task.id,
                "success": False,
                "error": {
                    "code": "PROCESSING_ERROR",
                    "message": str(e)
                },
                "processing_time": task.processing_time
            }
    
    def _calculate_batch_stats(self, tasks: List[BatchTask], start_time: float) -> Dict[str, Any]:
        """计算批处理统计信息
        
        Args:
            tasks: 任务列表
            start_time: 开始时间
            
        Returns:
            统计信息
        """
        total = len(tasks)
        successful = len([t for t in tasks if t.status == TaskStatus.COMPLETED])
        failed = len([t for t in tasks if t.status == TaskStatus.FAILED])
        
        # 计算处理时间统计
        processing_times = [t.processing_time for t in tasks if t.processing_time is not None]
        
        total_time = time.time() - start_time
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        max_processing_time = max(processing_times) if processing_times else 0
        min_processing_time = min(processing_times) if processing_times else 0
        
        return {
            "total": total,
            "successful": successful,
            "failed": failed,
            "success_rate": round(successful / total, 3) if total > 0 else 0,
            "total_time": round(total_time, 2),
            "avg_processing_time": round(avg_processing_time, 2),
            "max_processing_time": round(max_processing_time, 2),
            "min_processing_time": round(min_processing_time, 2),
            "throughput": round(total / total_time, 2) if total_time > 0 else 0
        }
    
    async def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """获取批处理状态
        
        Args:
            batch_id: 批次ID
            
        Returns:
            批处理状态信息
        """
        if batch_id not in self.active_batches:
            return None
        
        tasks = self.active_batches[batch_id]
        
        status_counts = {
            TaskStatus.PENDING: 0,
            TaskStatus.PROCESSING: 0,
            TaskStatus.COMPLETED: 0,
            TaskStatus.FAILED: 0
        }
        
        for task in tasks:
            status_counts[task.status] += 1
        
        progress = (status_counts[TaskStatus.COMPLETED] + status_counts[TaskStatus.FAILED]) / len(tasks)
        
        return {
            "batch_id": batch_id,
            "total_tasks": len(tasks),
            "status_counts": {status.value: count for status, count in status_counts.items()},
            "progress": round(progress, 3),
            "is_complete": progress == 1.0
        }
    
    async def cancel_batch(self, batch_id: str) -> bool:
        """取消批处理
        
        Args:
            batch_id: 批次ID
            
        Returns:
            是否成功取消
        """
        if batch_id not in self.active_batches:
            return False
        
        tasks = self.active_batches[batch_id]
        
        # 标记未开始的任务为失败
        cancelled_count = 0
        for task in tasks:
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.FAILED
                task.error = "批处理被取消"
                cancelled_count += 1
        
        self.logger.info(f"批处理取消，批次ID: {batch_id}, 取消任务数: {cancelled_count}")
        
        return True
    
    async def cleanup_completed_batches(self, max_age_hours: int = 24) -> int:
        """清理已完成的批处理记录
        
        Args:
            max_age_hours: 最大保留时间（小时）
            
        Returns:
            清理的批次数量
        """
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        batch_ids_to_remove = []
        
        for batch_id, tasks in self.active_batches.items():
            # 检查是否所有任务都已完成
            all_completed = all(t.status in [TaskStatus.COMPLETED, TaskStatus.FAILED] for t in tasks)
            
            if all_completed:
                # 检查最后完成时间
                last_end_time = max(t.end_time for t in tasks if t.end_time)
                if last_end_time and (current_time - last_end_time) > max_age_seconds:
                    batch_ids_to_remove.append(batch_id)
        
        # 删除过期批次
        for batch_id in batch_ids_to_remove:
            del self.active_batches[batch_id]
        
        if batch_ids_to_remove:
            self.logger.info(f"清理过期批处理记录，数量: {len(batch_ids_to_remove)}")
        
        return len(batch_ids_to_remove)
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """获取处理统计信息
        
        Returns:
            处理统计信息
        """
        total_batches = len(self.active_batches)
        active_batches = 0
        total_tasks = 0
        completed_tasks = 0
        failed_tasks = 0
        
        for tasks in self.active_batches.values():
            has_active = any(t.status in [TaskStatus.PENDING, TaskStatus.PROCESSING] for t in tasks)
            if has_active:
                active_batches += 1
            
            total_tasks += len(tasks)
            completed_tasks += len([t for t in tasks if t.status == TaskStatus.COMPLETED])
            failed_tasks += len([t for t in tasks if t.status == TaskStatus.FAILED])
        
        return {
            "total_batches": total_batches,
            "active_batches": active_batches,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "success_rate": round(completed_tasks / total_tasks, 3) if total_tasks > 0 else 0,
            "max_concurrent": self.config.processing.parallel_workers
        }
    
    async def cleanup(self) -> None:
        """清理资源"""
        # 清理OCR引擎
        if hasattr(self.ocr_engine, 'cleanup'):
            await self.ocr_engine.cleanup()
        
        # 清理批次记录
        self.active_batches.clear()
        
        self.logger.info("批量处理器资源清理完成") 
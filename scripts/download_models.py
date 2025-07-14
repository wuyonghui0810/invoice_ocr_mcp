#!/usr/bin/env python3
"""
ModelScope 模型下载脚本

用于下载和缓存Invoice OCR所需的所有模型
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
from typing import Dict, List

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    from modelscope import snapshot_download
    from modelscope.hub.api import HubApi
except ImportError:
    print("❌ ModelScope库未安装，请先安装:")
    print("pip install modelscope")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModelDownloader:
    """ModelScope模型下载器"""
    
    def __init__(self, cache_dir: str = "./cache/modelscope"):
        """初始化下载器
        
        Args:
            cache_dir: 模型缓存目录
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置ModelScope缓存目录
        os.environ['MODELSCOPE_CACHE'] = str(self.cache_dir)
        
        # 检查API Token
        self.api_token = os.getenv('MODELSCOPE_API_TOKEN')
        if not self.api_token:
            logger.warning("未设置MODELSCOPE_API_TOKEN环境变量，可能影响模型下载")
        
        # 定义需要下载的模型
        self.models = {
            "text_detection": {
                "model_id": "damo/cv_resnet18_ocr-detection-line-level_damo",
                "revision": "v1.0.2",
                "description": "文本检测模型 - ResNet18"
            },
            "text_recognition": {
                "model_id": "damo/cv_convnextTiny_ocr-recognition-general_damo", 
                "revision": "v1.0.1",
                "description": "文本识别模型 - ConvNext"
            },
            "invoice_classification": {
                "model_id": "damo/cv_resnest50_ocr-invoice-classification",
                "revision": "v1.0.0", 
                "description": "发票分类模型 - ResNeSt50"
            },
            "info_extraction": {
                "model_id": "damo/nlp_structbert_document-classification_chinese-base",
                "revision": "v1.0.0",
                "description": "信息抽取模型 - StructBERT"
            }
        }
        
        logger.info(f"模型缓存目录: {self.cache_dir}")
        logger.info(f"需要下载 {len(self.models)} 个模型")
    
    def check_model_exists(self, model_name: str, model_id: str) -> bool:
        """检查模型是否已存在
        
        Args:
            model_name: 模型名称
            model_id: 模型ID
            
        Returns:
            模型是否存在
        """
        # 检查缓存目录下是否有对应的模型文件
        model_cache_path = self.cache_dir / "hub" / model_id.replace("/", "--")
        
        if model_cache_path.exists():
            # 检查是否有模型文件
            model_files = list(model_cache_path.rglob("*.bin")) + \
                         list(model_cache_path.rglob("*.pth")) + \
                         list(model_cache_path.rglob("*.onnx")) + \
                         list(model_cache_path.rglob("config.json"))
            
            if model_files:
                logger.info(f"✅ 模型 {model_name} 已存在，跳过下载")
                return True
        
        return False
    
    async def download_model(self, model_name: str, model_info: Dict[str, str]) -> bool:
        """下载单个模型
        
        Args:
            model_name: 模型名称
            model_info: 模型信息
            
        Returns:
            下载是否成功
        """
        model_id = model_info["model_id"]
        revision = model_info.get("revision", "master")
        description = model_info.get("description", "")
        
        logger.info(f"📥 开始下载模型: {model_name}")
        logger.info(f"   模型ID: {model_id}")
        logger.info(f"   版本: {revision}")
        logger.info(f"   描述: {description}")
        
        # 检查模型是否已存在
        if self.check_model_exists(model_name, model_id):
            return True
        
        try:
            # 下载模型
            model_path = snapshot_download(
                model_id=model_id,
                revision=revision,
                cache_dir=self.cache_dir
            )
            
            logger.info(f"✅ 模型 {model_name} 下载成功")
            logger.info(f"   本地路径: {model_path}")
            
            # 验证下载的模型
            if self.verify_model(model_path):
                logger.info(f"✅ 模型 {model_name} 验证通过")
                return True
            else:
                logger.error(f"❌ 模型 {model_name} 验证失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ 模型 {model_name} 下载失败: {str(e)}")
            return False
    
    def verify_model(self, model_path: str) -> bool:
        """验证模型文件
        
        Args:
            model_path: 模型路径
            
        Returns:
            验证是否通过
        """
        try:
            model_dir = Path(model_path)
            
            # 检查必要文件是否存在
            required_files = ["config.json"]
            model_files = [".bin", ".pth", ".onnx"]
            
            # 检查配置文件
            config_exists = any((model_dir / f).exists() for f in required_files)
            
            # 检查模型文件
            model_file_exists = any(
                list(model_dir.rglob(f"*{ext}")) for ext in model_files
            )
            
            if config_exists and model_file_exists:
                return True
            else:
                logger.warning(f"模型文件不完整: {model_path}")
                return False
                
        except Exception as e:
            logger.error(f"验证模型时出错: {e}")
            return False
    
    async def download_all_models(self, force_redownload: bool = False) -> Dict[str, bool]:
        """下载所有模型
        
        Args:
            force_redownload: 是否强制重新下载
            
        Returns:
            各模型下载结果
        """
        logger.info("🚀 开始下载所有模型...")
        
        if force_redownload:
            logger.info("⚠️  强制重新下载模式，将忽略已存在的模型")
        
        results = {}
        
        # 顺序下载每个模型
        for model_name, model_info in self.models.items():
            if force_redownload:
                # 删除已存在的模型
                model_id = model_info["model_id"]
                model_cache_path = self.cache_dir / "hub" / model_id.replace("/", "--")
                if model_cache_path.exists():
                    import shutil
                    shutil.rmtree(model_cache_path)
                    logger.info(f"🗑️  删除已存在的模型: {model_name}")
            
            success = await self.download_model(model_name, model_info)
            results[model_name] = success
            
            if success:
                print(f"✅ {model_name}: 下载成功")
            else:
                print(f"❌ {model_name}: 下载失败")
        
        return results
    
    def get_cache_info(self) -> Dict[str, any]:
        """获取缓存信息
        
        Returns:
            缓存统计信息
        """
        cache_size = 0
        model_count = 0
        
        try:
            for root, dirs, files in os.walk(self.cache_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    cache_size += os.path.getsize(file_path)
                    if file.endswith(('.bin', '.pth', '.onnx')):
                        model_count += 1
        except Exception as e:
            logger.error(f"获取缓存信息失败: {e}")
        
        return {
            "cache_dir": str(self.cache_dir),
            "cache_size_mb": cache_size / (1024 * 1024),
            "model_files": model_count,
            "total_models": len(self.models)
        }
    
    def print_cache_info(self):
        """打印缓存信息"""
        info = self.get_cache_info()
        
        print("\n📊 缓存信息:")
        print(f"   缓存目录: {info['cache_dir']}")
        print(f"   缓存大小: {info['cache_size_mb']:.1f} MB")
        print(f"   模型文件: {info['model_files']} 个")
        print(f"   预期模型: {info['total_models']} 个")
    
    def cleanup_cache(self):
        """清理缓存"""
        try:
            import shutil
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                logger.info(f"🗑️  缓存目录已清理: {self.cache_dir}")
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"清理缓存失败: {e}")


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ModelScope模型下载脚本")
    parser.add_argument("--cache-dir", default="./cache/modelscope", 
                       help="模型缓存目录")
    parser.add_argument("--force", action="store_true",
                       help="强制重新下载所有模型")
    parser.add_argument("--cleanup", action="store_true",
                       help="清理缓存后退出")
    parser.add_argument("--info", action="store_true",
                       help="仅显示缓存信息")
    
    args = parser.parse_args()
    
    # 创建下载器
    downloader = ModelDownloader(args.cache_dir)
    
    print("🎯 ModelScope 模型下载器")
    print("=" * 50)
    
    # 处理不同命令
    if args.cleanup:
        print("🗑️  清理模型缓存...")
        downloader.cleanup_cache()
        print("✅ 缓存清理完成")
        return
    
    if args.info:
        downloader.print_cache_info()
        return
    
    # 检查环境
    if not downloader.api_token:
        print("⚠️  警告: 未设置 MODELSCOPE_API_TOKEN")
        print("   某些模型可能需要登录才能下载")
        print("   请访问 https://www.modelscope.cn/my/myaccesstoken 获取Token")
    
    try:
        # 下载模型
        results = await downloader.download_all_models(force_redownload=args.force)
        
        # 显示结果
        print("\n📋 下载结果:")
        success_count = sum(results.values())
        total_count = len(results)
        
        for model_name, success in results.items():
            status = "✅" if success else "❌"
            print(f"   {status} {model_name}")
        
        print(f"\n📊 总结:")
        print(f"   成功: {success_count}/{total_count}")
        print(f"   失败: {total_count - success_count}/{total_count}")
        
        if success_count == total_count:
            print("\n🎉 所有模型下载完成！")
        else:
            print(f"\n⚠️  有 {total_count - success_count} 个模型下载失败")
            print("请检查网络连接和API Token设置")
        
        # 显示缓存信息
        downloader.print_cache_info()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断了下载")
    except Exception as e:
        logger.error(f"下载过程中出现错误: {e}", exc_info=True)
        print(f"\n❌ 下载失败: {e}")


if __name__ == "__main__":
    # Windows异步事件循环兼容性
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main()) 
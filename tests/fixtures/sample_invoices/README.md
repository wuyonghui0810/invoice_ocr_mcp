# 示例发票图片

这个目录用于存放测试用的发票图片样本。

## 文件结构

- `vat_special_invoice.jpg` - 增值税专用发票样本
- `vat_common_invoice.jpg` - 增值税普通发票样本
- `electronic_invoice.jpg` - 电子发票样本
- `digital_invoice.jpg` - 数电发票样本

## 注意事项

1. 测试图片应该是匿名化的，不包含真实的企业信息
2. 图片分辨率建议在300DPI以上，确保OCR识别质量
3. 支持的格式：JPG、PNG、BMP、TIFF
4. 单个文件大小不超过10MB

## 使用说明

这些图片主要用于：
- 集成测试
- 性能基准测试
- 模型准确率验证
- 边界情况测试 
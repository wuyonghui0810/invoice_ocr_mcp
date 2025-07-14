# 期望结果

这个目录存放对应测试图片的期望识别结果，用于验证OCR识别的准确性。

## 文件结构

每个测试图片都对应一个JSON文件，包含期望的识别结果：

- `vat_special_invoice.json` - 增值税专用发票期望结果
- `vat_common_invoice.json` - 增值税普通发票期望结果
- `electronic_invoice.json` - 电子发票期望结果
- `digital_invoice.json` - 数电发票期望结果

## JSON格式说明

```json
{
  "invoice_type": {
    "code": "01",
    "name": "增值税专用发票",
    "confidence": 0.95
  },
  "basic_info": {
    "invoice_number": "12345678",
    "invoice_date": "2024-01-15",
    "total_amount": "1000.00",
    "tax_amount": "130.00",
    "amount_without_tax": "870.00"
  },
  "seller_info": {
    "name": "示例科技有限公司",
    "tax_id": "91110000123456789X",
    "address": "北京市朝阳区示例街道123号",
    "phone": "010-12345678",
    "bank_account": "1234567890123456789"
  },
  "buyer_info": {
    "name": "客户公司",
    "tax_id": "91110000987654321Y",
    "address": "北京市海淀区客户路456号",
    "phone": "010-87654321",
    "bank_account": "9876543210987654321"
  },
  "items": [
    {
      "name": "测试商品",
      "specification": "标准版",
      "unit": "台",
      "quantity": "1",
      "unit_price": "870.00",
      "amount": "870.00",
      "tax_rate": "13%",
      "tax_amount": "113.10"
    }
  ],
  "verification": {
    "check_code": "12345678",
    "machine_number": "499098765432",
    "is_valid": true
  }
}
```

## 使用说明

1. 期望结果用于自动化测试的结果验证
2. 可以设置容差范围，允许识别结果在合理范围内波动
3. 关键字段（如发票号码、金额）应该完全匹配
4. 置信度字段可以有适当的误差范围 
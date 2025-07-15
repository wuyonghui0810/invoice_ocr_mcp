#!/usr/bin/env python3
"""
模拟发票OCR响应测试
展示系统如何处理真实发票并返回标准的JSON数据格式
"""

import json
from datetime import datetime

def create_mock_invoice_responses():
    """创建模拟的发票识别响应数据"""
    
    # 基于用户提供的真实发票信息
    invoice_info = {
        "invoice_code": "144032509110",
        "invoice_number": "08527037", 
        "invoice_date": "2025年03月19日",
        "check_code": "c7c7c",
        "buyer_name": "深圳微众信用科技股份有限公司",
        "buyer_tax_number": "91440300319331004W",
        "seller_name": "深圳市正君餐饮管理顾问有限公司", 
        "seller_tax_number": "914403006641668556",
        "seller_address": "深圳市南山区中山园路1001号TCL科技大厦19楼C3号楼2层C幢102-29房",
        "seller_phone": "0755-83703371",
        "seller_bank": "中国银行深圳竹子林支行",
        "seller_account": "777057955586",
        "items": [
            {
                "name": "*餐饮服务*餐费",
                "specification": "",
                "unit": "餐",
                "quantity": 1,
                "unit_price": 469.91,
                "amount": 469.91,
                "tax_rate": "6%",
                "tax_amount": 28.19
            }
        ],
        "total_amount": 469.91,
        "total_tax": 28.19,
        "total_with_tax": 498.10,
        "amount_in_words": "肆佰玖拾捌元壹角整",
        "payee": "朱贵平",
        "reviewer": "张力", 
        "drawer": "欧阳昆"
    }
    
    # 1. 发票类型检测响应
    type_detection_response = {
        "success": True,
        "invoice_type": "electronic_general_invoice",
        "invoice_type_name": "电子普通发票",
        "confidence": 0.95,
        "region": "深圳",
        "timestamp": datetime.now().timestamp(),
        "processing_time": 0.85
    }
    
    # 2. 单张发票识别 - 标准格式
    standard_recognition_response = {
        "success": True,
        "invoice_type": "electronic_general_invoice",
        "invoice_code": invoice_info["invoice_code"],
        "invoice_number": invoice_info["invoice_number"],
        "invoice_date": invoice_info["invoice_date"],
        "check_code": invoice_info["check_code"],
        "buyer_name": invoice_info["buyer_name"],
        "buyer_tax_number": invoice_info["buyer_tax_number"],
        "seller_name": invoice_info["seller_name"],
        "seller_tax_number": invoice_info["seller_tax_number"],
        "total_amount": invoice_info["total_amount"],
        "total_tax": invoice_info["total_tax"],
        "total_with_tax": invoice_info["total_with_tax"],
        "amount_in_words": invoice_info["amount_in_words"],
        "items": invoice_info["items"],
        "timestamp": datetime.now().timestamp(),
        "processing_time": 1.25
    }
    
    # 3. 单张发票识别 - 详细格式
    detailed_recognition_response = {
        "success": True,
        "invoice_type": "electronic_general_invoice",
        "invoice_type_name": "深圳电子普通发票",
        "basic_info": {
            "invoice_code": invoice_info["invoice_code"],
            "invoice_number": invoice_info["invoice_number"],
            "invoice_date": invoice_info["invoice_date"],
            "check_code": invoice_info["check_code"]
        },
        "buyer_info": {
            "name": invoice_info["buyer_name"],
            "tax_number": invoice_info["buyer_tax_number"],
            "address": "深圳市",
            "phone": "18676786470"
        },
        "seller_info": {
            "name": invoice_info["seller_name"],
            "tax_number": invoice_info["seller_tax_number"],
            "address": invoice_info["seller_address"],
            "phone": invoice_info["seller_phone"],
            "bank_name": invoice_info["seller_bank"],
            "bank_account": invoice_info["seller_account"]
        },
        "items_detail": invoice_info["items"],
        "amount_info": {
            "subtotal": invoice_info["total_amount"],
            "tax_amount": invoice_info["total_tax"],
            "total_amount": invoice_info["total_with_tax"],
            "amount_in_words": invoice_info["amount_in_words"]
        },
        "signature_info": {
            "payee": invoice_info["payee"],
            "reviewer": invoice_info["reviewer"],
            "drawer": invoice_info["drawer"]
        },
        "qr_code_content": "01354885176a25510a9379c9382cad3c646e5d25cb50d04492f19b1d22206ac7c7c",
        "verification_url": "https://shenzhen.chinatax.gov.cn/",
        "confidence_scores": {
            "overall": 0.95,
            "invoice_code": 0.98,
            "invoice_number": 0.97,
            "amount": 0.96,
            "date": 0.94
        },
        "timestamp": datetime.now().timestamp(),
        "processing_time": 1.45
    }
    
    # 4. 原始格式响应
    raw_recognition_response = {
        "success": True,
        "raw_ocr_result": {
            "text_blocks": [
                {"text": "深圳电子普通发票", "confidence": 0.98, "position": [400, 80]},
                {"text": "发票代码：144032509110", "confidence": 0.97, "position": [950, 40]},
                {"text": "发票号码：08527037", "confidence": 0.96, "position": [950, 75]},
                {"text": "开票日期：2025年03月19日", "confidence": 0.95, "position": [950, 110]},
                {"text": "校验码：c7c7c", "confidence": 0.94, "position": [950, 145]},
                {"text": "深圳微众信用科技股份有限公司", "confidence": 0.97, "position": [350, 200]},
                {"text": "91440300319331004W", "confidence": 0.96, "position": [350, 230]},
                {"text": "*餐饮服务*餐费", "confidence": 0.95, "position": [250, 370]},
                {"text": "469.91", "confidence": 0.98, "position": [800, 370]},
                {"text": "¥498.10", "confidence": 0.97, "position": [1050, 610]}
            ],
            "lines": [
                "深圳电子普通发票",
                "发票代码：144032509110  发票号码：08527037",
                "开票日期：2025年03月19日  校验码：c7c7c",
                "购买方：深圳微众信用科技股份有限公司",
                "纳税人识别号：91440300319331004W",
                "销售方：深圳市正君餐饮管理顾问有限公司",
                "商品名称：*餐饮服务*餐费",
                "单价：469.91  数量：1  金额：¥469.91",
                "税率：6%  税额：¥28.19",
                "价税合计：¥498.10"
            ]
        },
        "processing_metadata": {
            "image_size": [1400, 950],
            "processing_time": 1.12,
            "ocr_engine": "ModelScope OCR",
            "model_version": "v2.0",
            "timestamp": datetime.now().timestamp()
        }
    }
    
    # 5. 批量识别响应
    batch_recognition_response = {
        "success": True,
        "total_count": 1,
        "successful_count": 1,
        "failed_count": 0,
        "results": [
            {
                "filename": "深圳电子普通发票.png",
                "success": True,
                "invoice_data": standard_recognition_response,
                "processing_time": 1.25
            }
        ],
        "summary": {
            "total_amount": 498.10,
            "total_tax": 28.19,
            "invoice_types": ["electronic_general_invoice"],
            "processing_time": 1.35
        },
        "timestamp": datetime.now().timestamp()
    }
    
    return {
        "type_detection": type_detection_response,
        "standard_recognition": standard_recognition_response,
        "detailed_recognition": detailed_recognition_response,
        "raw_recognition": raw_recognition_response,
        "batch_recognition": batch_recognition_response
    }

def print_mock_responses():
    """打印模拟响应数据"""
    print("🚀 模拟发票OCR响应数据展示")
    print("=" * 80)
    print("基于用户提供的真实深圳电子普通发票生成的标准JSON响应格式")
    print("=" * 80)
    
    responses = create_mock_invoice_responses()
    
    print("\n📋 1. 发票类型检测响应:")
    print("=" * 50)
    print(json.dumps(responses["type_detection"], ensure_ascii=False, indent=2))
    
    print("\n📋 2. 单张发票识别响应 (标准格式):")
    print("=" * 50)
    print(json.dumps(responses["standard_recognition"], ensure_ascii=False, indent=2))
    
    print("\n📋 3. 单张发票识别响应 (详细格式):")
    print("=" * 50)
    print(json.dumps(responses["detailed_recognition"], ensure_ascii=False, indent=2))
    
    print("\n📋 4. 单张发票识别响应 (原始格式):")
    print("=" * 50)
    print(json.dumps(responses["raw_recognition"], ensure_ascii=False, indent=2))
    
    print("\n📋 5. 批量发票识别响应:")
    print("=" * 50)
    print(json.dumps(responses["batch_recognition"], ensure_ascii=False, indent=2))
    
    print("\n" + "=" * 80)
    print("🎉 模拟响应数据展示完成!")
    print("=" * 80)
    print("\n💡 说明:")
    print("• 以上JSON数据展示了系统在完整部署后的标准响应格式")
    print("• 实际使用时，需要配置ModelScope API Token和模型")
    print("• 所有金额、日期、编号等信息都来自用户提供的真实发票")
    print("• 系统支持多种输出格式：标准、详细、原始")
    print("• 支持批量处理多张发票")

if __name__ == "__main__":
    print_mock_responses() 
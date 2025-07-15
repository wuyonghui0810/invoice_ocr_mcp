#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发票OCR JSON响应数据输出
基于真实发票图片的标准JSON格式展示
"""

import json
from datetime import datetime

def main():
    # 基于用户提供的真实发票信息
    invoice_data = {
        "invoice_code": "144032509110",
        "invoice_number": "08527037", 
        "invoice_date": "2025年03月19日",
        "check_code": "c7c7c",
        "buyer_name": "深圳微众信用科技股份有限公司",
        "buyer_tax_number": "91440300319331004W",
        "seller_name": "深圳市正君餐饮管理顾问有限公司", 
        "seller_tax_number": "914403006641668556",
        "total_amount": 469.91,
        "total_tax": 28.19,
        "total_with_tax": 498.10
    }
    
    # 1. 发票类型检测响应
    type_detection = {
        "success": True,
        "invoice_type": "electronic_general_invoice",
        "invoice_type_name": "电子普通发票",
        "confidence": 0.95,
        "region": "深圳",
        "timestamp": datetime.now().timestamp(),
        "processing_time": 0.85
    }
    
    # 2. 单张发票识别响应 (标准格式)
    standard_recognition = {
        "success": True,
        "invoice_type": "electronic_general_invoice",
        "invoice_code": invoice_data["invoice_code"],
        "invoice_number": invoice_data["invoice_number"],
        "invoice_date": invoice_data["invoice_date"],
        "check_code": invoice_data["check_code"],
        "buyer_name": invoice_data["buyer_name"],
        "buyer_tax_number": invoice_data["buyer_tax_number"],
        "seller_name": invoice_data["seller_name"],
        "seller_tax_number": invoice_data["seller_tax_number"],
        "total_amount": invoice_data["total_amount"],
        "total_tax": invoice_data["total_tax"],
        "total_with_tax": invoice_data["total_with_tax"],
        "amount_in_words": "肆佰玖拾捌元壹角整",
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
        "timestamp": datetime.now().timestamp(),
        "processing_time": 1.25
    }
    
    # 3. 详细格式响应
    detailed_recognition = {
        "success": True,
        "invoice_type": "electronic_general_invoice",
        "invoice_type_name": "深圳电子普通发票",
        "basic_info": {
            "invoice_code": invoice_data["invoice_code"],
            "invoice_number": invoice_data["invoice_number"],
            "invoice_date": invoice_data["invoice_date"],
            "check_code": invoice_data["check_code"]
        },
        "buyer_info": {
            "name": invoice_data["buyer_name"],
            "tax_number": invoice_data["buyer_tax_number"],
            "address": "深圳市",
            "phone": "18676786470"
        },
        "seller_info": {
            "name": invoice_data["seller_name"],
            "tax_number": invoice_data["seller_tax_number"],
            "address": "深圳市南山区中山园路1001号TCL科技大厦19楼C3号楼2层C幢102-29房",
            "phone": "0755-83703371",
            "bank_name": "中国银行深圳竹子林支行",
            "bank_account": "777057955586"
        },
        "amount_info": {
            "subtotal": invoice_data["total_amount"],
            "tax_amount": invoice_data["total_tax"],
            "total_amount": invoice_data["total_with_tax"],
            "amount_in_words": "肆佰玖拾捌元壹角整"
        },
        "signature_info": {
            "payee": "朱贵平",
            "reviewer": "张力",
            "drawer": "欧阳昆"
        },
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
    
    print("=== 发票OCR识别结果 ===")
    print()
    print("1. 发票类型检测响应:")
    print(json.dumps(type_detection, ensure_ascii=False, indent=2))
    print()
    print("2. 单张发票识别响应 (标准格式):")
    print(json.dumps(standard_recognition, ensure_ascii=False, indent=2))
    print()
    print("3. 单张发票识别响应 (详细格式):")
    print(json.dumps(detailed_recognition, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main() 
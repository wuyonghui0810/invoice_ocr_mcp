"""
发票解析器模块

将OCR识别结果解析为结构化的发票信息
"""

import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import json

from ..config import Config


class InvoiceParser:
    """发票信息解析器"""
    
    def __init__(self, config: Config):
        """初始化发票解析器
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 发票类型映射
        self.invoice_types = {
            "01": "增值税专用发票",
            "03": "机动车增值税专用发票", 
            "04": "增值税普通发票",
            "10": "增值税电子普通发票",
            "11": "增值税普通发票（卷式）",
            "14": "增值税普通发票（通行费）",
            "15": "二手车发票",
            "20": "增值税电子专用发票",
            "99": "数电发票（增值税专用发票）",
            "09": "数电发票（普通发票）",
            "61": "数电发票（航空运输电子客票行程单）",
            "83": "数电发票（铁路电子客票）",
            "100": "区块链发票（支持深圳、北京和云南地区）"
        }
        
        # 正则表达式模式
        self._compile_patterns()
        
        self.logger.info("发票解析器初始化完成")
    
    def _compile_patterns(self) -> None:
        """编译正则表达式模式"""
        # 发票号码模式
        self.invoice_number_pattern = re.compile(r'[0-9]{8,12}')
        
        # 日期模式
        self.date_patterns = [
            re.compile(r'(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})[日]?'),
            re.compile(r'(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})'),
            re.compile(r'(\d{4})\-(\d{2})\-(\d{2})'),
            re.compile(r'(\d{4})/(\d{2})/(\d{2})'),
        ]
        
        # 金额模式
        self.amount_patterns = [
            re.compile(r'[￥¥]?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*元?'),
            re.compile(r'(\d+(?:,\d{3})*(?:\.\d{2})?)'),
        ]
        
        # 税号模式（18位统一社会信用代码或15位纳税人识别号）
        self.tax_id_patterns = [
            re.compile(r'[0-9A-Z]{18}'),  # 统一社会信用代码
            re.compile(r'[0-9A-Z]{15}'),  # 纳税人识别号
        ]
        
        # 电话模式
        self.phone_pattern = re.compile(r'1[3-9]\d{9}|0\d{2,3}-?\d{7,8}|\d{3,4}-\d{7,8}')
        
        # 银行账号模式
        self.bank_account_pattern = re.compile(r'\d{16,21}')
    
    async def parse_invoice(self, ocr_result: Dict[str, Any], output_format: str = "standard") -> Dict[str, Any]:
        """解析发票信息
        
        Args:
            ocr_result: OCR识别结果
            output_format: 输出格式 (standard/detailed/raw)
            
        Returns:
            解析后的发票信息
        """
        try:
            self.logger.info("开始解析发票信息")
            
            # 提取文本列表
            texts = ocr_result.get('recognized_texts', [])
            classification = ocr_result.get('invoice_classification', {})
            
            # 解析各个部分
            invoice_type = self._parse_invoice_type(classification)
            basic_info = await self._parse_basic_info(texts)
            seller_info = await self._parse_seller_info(texts)
            buyer_info = await self._parse_buyer_info(texts)
            items = await self._parse_items(texts)
            verification = await self._parse_verification_info(texts)
            
            # 构建结果
            result = {
                "invoice_type": invoice_type,
                "basic_info": basic_info,
                "seller_info": seller_info,
                "buyer_info": buyer_info,
                "items": items,
                "verification": verification,
                "meta": {
                    "processing_time": ocr_result.get('processing_time', 0),
                    "model_version": "v1.0.0",
                    "confidence_score": self._calculate_confidence(ocr_result)
                }
            }
            
            # 根据输出格式返回
            if output_format == "detailed":
                result["raw_ocr_result"] = ocr_result
                result["parsing_details"] = self._get_parsing_details(texts)
            elif output_format == "raw":
                return ocr_result
            
            self.logger.info("发票信息解析完成")
            return result
            
        except Exception as e:
            self.logger.error(f"发票解析失败: {str(e)}")
            raise
    
    def _parse_invoice_type(self, classification: Dict[str, Any]) -> Dict[str, Any]:
        """解析发票类型
        
        Args:
            classification: 分类结果
            
        Returns:
            发票类型信息
        """
        invoice_type = classification.get('type', 'unknown')
        confidence = classification.get('confidence', 0.0)
        
        # 尝试映射到标准类型
        type_code = None
        type_name = "未知类型"
        
        for code, name in self.invoice_types.items():
            if invoice_type in name or name in invoice_type:
                type_code = code
                type_name = name
                break
        
        return {
            "code": type_code,
            "name": type_name,
            "confidence": confidence,
            "raw_type": invoice_type
        }
    
    async def _parse_basic_info(self, texts: List[str]) -> Dict[str, Any]:
        """解析基本信息
        
        Args:
            texts: 文本列表
            
        Returns:
            基本信息字典
        """
        basic_info = {
            "invoice_number": None,
            "invoice_date": None,
            "total_amount": None,
            "tax_amount": None,
            "amount_without_tax": None
        }
        
        combined_text = ' '.join(texts)
        
        # 解析发票号码
        basic_info["invoice_number"] = self._extract_invoice_number(texts)
        
        # 解析日期
        basic_info["invoice_date"] = self._extract_date(combined_text)
        
        # 解析金额
        amounts = self._extract_amounts(texts)
        if amounts:
            basic_info["total_amount"] = amounts.get("total")
            basic_info["tax_amount"] = amounts.get("tax")
            basic_info["amount_without_tax"] = amounts.get("without_tax")
        
        return basic_info
    
    async def _parse_seller_info(self, texts: List[str]) -> Dict[str, Any]:
        """解析销售方信息
        
        Args:
            texts: 文本列表
            
        Returns:
            销售方信息字典
        """
        seller_info = {
            "name": None,
            "tax_id": None,
            "address": None,
            "phone": None,
            "bank_account": None
        }
        
        # 查找销售方相关文本
        seller_texts = self._find_seller_section(texts)
        
        if seller_texts:
            combined_text = ' '.join(seller_texts)
            
            # 提取各项信息
            seller_info["name"] = self._extract_company_name(seller_texts, "seller")
            seller_info["tax_id"] = self._extract_tax_id(combined_text)
            seller_info["address"] = self._extract_address(combined_text)
            seller_info["phone"] = self._extract_phone(combined_text)
            seller_info["bank_account"] = self._extract_bank_account(combined_text)
        
        return seller_info
    
    async def _parse_buyer_info(self, texts: List[str]) -> Dict[str, Any]:
        """解析购买方信息
        
        Args:
            texts: 文本列表
            
        Returns:
            购买方信息字典
        """
        buyer_info = {
            "name": None,
            "tax_id": None,
            "address": None,
            "phone": None,
            "bank_account": None
        }
        
        # 查找购买方相关文本
        buyer_texts = self._find_buyer_section(texts)
        
        if buyer_texts:
            combined_text = ' '.join(buyer_texts)
            
            # 提取各项信息
            buyer_info["name"] = self._extract_company_name(buyer_texts, "buyer")
            buyer_info["tax_id"] = self._extract_tax_id(combined_text)
            buyer_info["address"] = self._extract_address(combined_text)
            buyer_info["phone"] = self._extract_phone(combined_text)
            buyer_info["bank_account"] = self._extract_bank_account(combined_text)
        
        return buyer_info
    
    async def _parse_items(self, texts: List[str]) -> List[Dict[str, Any]]:
        """解析商品明细
        
        Args:
            texts: 文本列表
            
        Returns:
            商品明细列表
        """
        items = []
        
        # 查找商品明细表格区域
        item_texts = self._find_items_section(texts)
        
        if item_texts:
            # 解析表格行
            for item_text in item_texts:
                item = self._parse_single_item(item_text)
                if item:
                    items.append(item)
        
        return items
    
    async def _parse_verification_info(self, texts: List[str]) -> Dict[str, Any]:
        """解析验证信息
        
        Args:
            texts: 文本列表
            
        Returns:
            验证信息字典
        """
        verification = {
            "check_code": None,
            "machine_number": None,
            "is_valid": True
        }
        
        combined_text = ' '.join(texts)
        
        # 提取校验码
        verification["check_code"] = self._extract_check_code(combined_text)
        
        # 提取机器编号
        verification["machine_number"] = self._extract_machine_number(combined_text)
        
        return verification
    
    def _extract_invoice_number(self, texts: List[str]) -> Optional[str]:
        """提取发票号码"""
        for text in texts:
            if '发票号码' in text or '号码' in text:
                matches = self.invoice_number_pattern.findall(text)
                if matches:
                    return matches[0]
        
        # 如果没找到，尝试在所有文本中查找最长的数字串
        all_numbers = []
        for text in texts:
            numbers = self.invoice_number_pattern.findall(text)
            all_numbers.extend(numbers)
        
        if all_numbers:
            # 返回最长的数字串
            return max(all_numbers, key=len)
        
        return None
    
    def _extract_date(self, text: str) -> Optional[str]:
        """提取日期"""
        for pattern in self.date_patterns:
            match = pattern.search(text)
            if match:
                try:
                    year, month, day = match.groups()
                    # 格式化为标准日期格式
                    date = datetime(int(year), int(month), int(day))
                    return date.strftime('%Y-%m-%d')
                except ValueError:
                    continue
        
        return None
    
    def _extract_amounts(self, texts: List[str]) -> Dict[str, Optional[str]]:
        """提取金额信息"""
        amounts = {
            "total": None,
            "tax": None,
            "without_tax": None
        }
        
        for text in texts:
            text_lower = text.lower()
            
            # 提取总额
            if '合计' in text or '总计' in text or '价税合计' in text:
                amount = self._extract_single_amount(text)
                if amount:
                    amounts["total"] = amount
            
            # 提取税额
            elif '税额' in text:
                amount = self._extract_single_amount(text)
                if amount:
                    amounts["tax"] = amount
            
            # 提取不含税金额
            elif '不含税' in text or '金额' in text:
                amount = self._extract_single_amount(text)
                if amount:
                    amounts["without_tax"] = amount
        
        return amounts
    
    def _extract_single_amount(self, text: str) -> Optional[str]:
        """从文本中提取单个金额"""
        for pattern in self.amount_patterns:
            match = pattern.search(text)
            if match:
                amount = match.group(1).replace(',', '')
                try:
                    # 验证是否为有效数字
                    float(amount)
                    return amount
                except ValueError:
                    continue
        
        return None
    
    def _extract_tax_id(self, text: str) -> Optional[str]:
        """提取税号"""
        for pattern in self.tax_id_patterns:
            match = pattern.search(text)
            if match:
                return match.group(0)
        
        return None
    
    def _extract_phone(self, text: str) -> Optional[str]:
        """提取电话号码"""
        match = self.phone_pattern.search(text)
        if match:
            return match.group(0)
        
        return None
    
    def _extract_bank_account(self, text: str) -> Optional[str]:
        """提取银行账号"""
        match = self.bank_account_pattern.search(text)
        if match:
            return match.group(0)
        
        return None
    
    def _extract_address(self, text: str) -> Optional[str]:
        """提取地址信息"""
        # 查找包含地址关键词的部分
        address_keywords = ['市', '区', '县', '路', '街', '号', '室', '楼']
        
        for keyword in address_keywords:
            if keyword in text:
                # 提取包含关键词的连续文本段
                parts = text.split()
                for part in parts:
                    if keyword in part and len(part) > 5:
                        return part
        
        return None
    
    def _extract_company_name(self, texts: List[str], entity_type: str) -> Optional[str]:
        """提取公司名称"""
        keywords = {
            "seller": ["销售方", "开票方", "出售方"],
            "buyer": ["购买方", "收票方", "购方"]
        }
        
        target_keywords = keywords.get(entity_type, [])
        
        for text in texts:
            for keyword in target_keywords:
                if keyword in text:
                    # 提取关键词后的公司名称
                    parts = text.split(keyword)
                    if len(parts) > 1:
                        name_part = parts[1].strip()
                        # 清理和验证公司名称
                        if len(name_part) > 2 and ('公司' in name_part or '企业' in name_part):
                            return name_part.split()[0]
        
        return None
    
    def _extract_check_code(self, text: str) -> Optional[str]:
        """提取校验码"""
        # 校验码通常是8-12位数字
        check_code_pattern = re.compile(r'校验码[：:]?\s*([0-9]{8,12})')
        match = check_code_pattern.search(text)
        if match:
            return match.group(1)
        
        return None
    
    def _extract_machine_number(self, text: str) -> Optional[str]:
        """提取机器编号"""
        # 机器编号通常是12位数字
        machine_pattern = re.compile(r'机器编号[：:]?\s*([0-9]{12})')
        match = machine_pattern.search(text)
        if match:
            return match.group(1)
        
        return None
    
    def _find_seller_section(self, texts: List[str]) -> List[str]:
        """查找销售方信息区域"""
        seller_texts = []
        seller_keywords = ["销售方", "开票方", "出售方"]
        
        found_seller = False
        for text in texts:
            if any(keyword in text for keyword in seller_keywords):
                found_seller = True
                seller_texts.append(text)
            elif found_seller and any(keyword in text for keyword in ["购买方", "收票方", "商品"]):
                break
            elif found_seller:
                seller_texts.append(text)
        
        return seller_texts
    
    def _find_buyer_section(self, texts: List[str]) -> List[str]:
        """查找购买方信息区域"""
        buyer_texts = []
        buyer_keywords = ["购买方", "收票方", "购方"]
        
        found_buyer = False
        for text in texts:
            if any(keyword in text for keyword in buyer_keywords):
                found_buyer = True
                buyer_texts.append(text)
            elif found_buyer and any(keyword in text for keyword in ["商品", "合计", "税额"]):
                break
            elif found_buyer:
                buyer_texts.append(text)
        
        return buyer_texts
    
    def _find_items_section(self, texts: List[str]) -> List[str]:
        """查找商品明细区域"""
        item_texts = []
        item_keywords = ["商品名称", "货物", "商品", "明细"]
        
        found_items = False
        for text in texts:
            if any(keyword in text for keyword in item_keywords):
                found_items = True
            elif found_items and ("合计" in text or "总计" in text):
                break
            elif found_items:
                item_texts.append(text)
        
        return item_texts
    
    def _parse_single_item(self, text: str) -> Optional[Dict[str, Any]]:
        """解析单个商品项"""
        # 这里应该根据实际的发票格式进行解析
        # 简化版本，实际应用中需要更复杂的解析逻辑
        
        if len(text.strip()) < 3:
            return None
        
        item = {
            "name": text.strip(),
            "specification": None,
            "unit": None,
            "quantity": None,
            "unit_price": None,
            "amount": None,
            "tax_rate": None,
            "tax_amount": None
        }
        
        # 尝试提取金额
        amount = self._extract_single_amount(text)
        if amount:
            item["amount"] = amount
        
        return item
    
    def _calculate_confidence(self, ocr_result: Dict[str, Any]) -> float:
        """计算整体置信度"""
        classification = ocr_result.get('invoice_classification', {})
        classification_confidence = classification.get('confidence', 0.0)
        
        # 根据识别到的文本数量调整置信度
        texts = ocr_result.get('recognized_texts', [])
        text_count = len([t for t in texts if t.strip()])
        
        if text_count > 20:
            text_confidence = 0.9
        elif text_count > 10:
            text_confidence = 0.7
        elif text_count > 5:
            text_confidence = 0.5
        else:
            text_confidence = 0.3
        
        # 综合置信度
        overall_confidence = (classification_confidence * 0.6 + text_confidence * 0.4)
        return round(overall_confidence, 3)
    
    def _get_parsing_details(self, texts: List[str]) -> Dict[str, Any]:
        """获取解析详情（用于详细输出格式）"""
        return {
            "total_text_regions": len(texts),
            "non_empty_regions": len([t for t in texts if t.strip()]),
            "detected_patterns": {
                "has_invoice_number": any('发票号码' in t for t in texts),
                "has_seller_info": any('销售方' in t for t in texts),
                "has_buyer_info": any('购买方' in t for t in texts),
                "has_amount_info": any('合计' in t or '金额' in t for t in texts)
            }
        } 
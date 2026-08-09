from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
from PIL import Image
import torch
import pytesseract
import re
import logging
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class LayoutLMService:
    """LayoutLMv3-based invoice extraction service"""
    
    def __init__(self):
        self.processor = None
        self.model = None
        self.loaded = False
    
    def load_model(self):
        """Load LayoutLMv3 model (lazy loading)"""
        if self.loaded:
            return
        
        try:
            logger.info("Loading LayoutLMv3 model...")
            self.processor = LayoutLMv3Processor.from_pretrained(
                "microsoft/layoutlmv3-base",
                apply_ocr=True
            )
            self.model = LayoutLMv3ForTokenClassification.from_pretrained(
                "microsoft/layoutlmv3-base"
            )
            self.loaded = True
            logger.info("✅ LayoutLMv3 model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load LayoutLMv3 model: {e}")
            raise
    
    def extract_invoice(self, image_path: str) -> Tuple[Dict[str, Any], float]:
        """
        Extract invoice data using LayoutLMv3 + OCR
        
        Returns:
            (extracted_data, confidence)
        """
        # Load model if not loaded
        self.load_model()
        
        logger.info(f"Processing invoice with LayoutLMv3: {image_path}")
        
        try:
            # Load image
            image = Image.open(image_path).convert("RGB")
            
            # Get OCR text first (Tesseract)
            logger.info("Running Tesseract OCR...")
            ocr_text = pytesseract.image_to_string(image)
            
            # Get OCR data with positions
            ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            
            logger.info(f"OCR extracted {len(ocr_text)} characters")
            
            # Parse the OCR text with smart extraction
            extracted_data, confidence = self._parse_ocr_text(ocr_text, ocr_data)
            
            logger.info(f"LayoutLM extraction complete: {len(extracted_data)} fields, {confidence}% confidence")
        
            return extracted_data, confidence
            
        except Exception as e:
            logger.error(f"LayoutLM extraction failed: {e}")
            raise

    def extract_from_image(self, image_path: str) -> Dict[str, Any]:
        """
        Wrapper to match TripleHybrid expectations.
        Returns dict with extracted_data and overall_confidence.
        """
        try:
            data, conf = self.extract_invoice(image_path)
            return {
                "extracted_data": data,
                "overall_confidence": conf,
            }
        except Exception as e:
            logger.error(f"LayoutLM extract_from_image failed: {e}")
            return {
                "extracted_data": {},
                "overall_confidence": 0.0,
                "error": str(e),
            }
    
    def _parse_ocr_text(self, text: str, ocr_data: dict) -> Tuple[Dict[str, Any], float]:
        """
        Parse OCR text into structured invoice data
        Uses position-aware extraction
        """
        extracted_data = {}
        field_confidences = {}
        
        # Extract vendor (first lines with high confidence)
        vendor, vendor_conf = self._extract_vendor_smart(text, ocr_data)
        if vendor:
            extracted_data['vendor_name'] = vendor
            field_confidences['vendor_name'] = vendor_conf
        
        # Extract invoice number
        invoice_num, inv_conf = self._extract_invoice_number(text, ocr_data)
        if invoice_num:
            extracted_data['invoice_number'] = invoice_num
            field_confidences['invoice_number'] = inv_conf
        
        # Extract date
        inv_date, date_conf = self._extract_date(text, ocr_data)
        if inv_date:
            extracted_data['invoice_date'] = inv_date
            field_confidences['invoice_date'] = date_conf
        
        # Extract total amount
        amount, amount_conf = self._extract_total_amount(text, ocr_data)
        if amount is not None:
            extracted_data['total_amount'] = amount
            field_confidences['total_amount'] = amount_conf
        
        # Extract currency
        currency = self._extract_currency(text)
        if currency:
            extracted_data['currency'] = currency
            field_confidences['currency'] = 95.0
        
        # Extract PO number (if exists)
        po_number, po_conf = self._extract_po_number(text, ocr_data)
        if po_number:
            extracted_data['po_number'] = po_number
            field_confidences['po_number'] = po_conf
        
        # Calculate overall confidence
        overall_conf = self._calculate_confidence(field_confidences, ocr_data)
        
        return extracted_data, overall_conf
    
    def _extract_vendor_smart(self, text: str, ocr_data: dict) -> Tuple[Optional[str], float]:
        """Extract vendor using position-aware logic"""
        lines = text.split('\n')
        
        # Look for company name in first 5 lines
        for line in lines[:5]:
            line = line.strip()
            # Company name pattern
            if len(line) > 5 and sum(1 for c in line if c.isupper()) > len(line) * 0.5:
                # Exclude lines with numbers (likely not company name)
                if not re.search(r'\d{3,}', line):
                    # Exclude common non-company words
                    if not any(word in line.upper() for word in ['CUSTOMER', 'BILL TO', 'SHIP TO', 'DATE']):
                        logger.info(f"Vendor found: {line}")
                        return line, 90.0
        
        return None, 0.0
    
    def _extract_invoice_number(self, text: str, ocr_data: dict) -> Tuple[Optional[str], float]:
        """Extract invoice number with multiple patterns"""
        patterns = [
            (r'(?:invoice|order)\s*#?\s*:?\s*([A-Z0-9-]{5,})', 95),
            (r'inv\.?\s*#?\s*:?\s*([A-Z0-9-]{5,})', 90),
            (r'#\s*([A-Z0-9]{5,})', 85),
        ]
        
        for pattern, base_conf in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                inv_num = match.group(1).strip()
                # Validate: should have digits
                if re.search(r'\d', inv_num):
                    # Not a date
                    if not re.match(r'\d{2}[-/]\d{2}[-/]\d{2,4}', inv_num):
                        logger.info(f"Invoice number found: {inv_num}")
                        return inv_num, base_conf
        
        return None, 0.0
    
    def _extract_date(self, text: str, ocr_data: dict) -> Tuple[Optional[str], float]:
        """Extract invoice date"""
        # Look for date with context
        date_pattern = r'(?:date|invoice date|dated)[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})'
        match = re.search(date_pattern, text, re.IGNORECASE)
        
        if match:
            date_str = match.group(1)
            parsed_date = self._parse_date(date_str)
            if parsed_date:
                return parsed_date, 90.0
        
        # Fallback: find any date pattern
        all_dates = re.findall(r'\d{2}[-/]\d{2}[-/]\d{4}', text)
        if all_dates:
            parsed_date = self._parse_date(all_dates[0])
            if parsed_date:
                return parsed_date, 75.0
        
        return None, 0.0
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date to YYYY-MM-DD"""
        formats = ['%m-%d-%Y', '%m/%d/%Y', '%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d']
        
        for fmt in formats:
            try:
                parsed = datetime.strptime(date_str, fmt)
                if 2000 <= parsed.year <= 2030:
                    return parsed.strftime('%Y-%m-%d')
            except:
                continue
        
        return None
    
    def _extract_total_amount(self, text: str, ocr_data: dict) -> Tuple[Optional[float], float]:
        """Extract total amount"""
        # Priority patterns
        patterns = [
            (r'(?:invoice total|balance due|amount due|total due)[:\s]*\$?\s*([\d,]+\.?\d*)', 95),
            (r'total\s*\(usd\)[:\s]*\$?\s*([\d,]+\.?\d*)', 90),
            (r'\btotal[:\s]*\$?\s*([\d,]+\.\d{2})', 85),
        ]
        
        for pattern, base_conf in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                    logger.info(f"Total amount found: ${amount}")
                    return amount, base_conf
                except:
                    pass
        
        return None, 0.0
    
    def _extract_currency(self, text: str) -> str:
        """Extract currency"""
        if '$' in text or re.search(r'\bUSD\b', text, re.IGNORECASE):
            return 'USD'
        elif '€' in text or re.search(r'\bEUR\b', text, re.IGNORECASE):
            return 'EUR'
        elif '£' in text or re.search(r'\bGBP\b', text, re.IGNORECASE):
            return 'GBP'
        return 'USD'
    
    def _extract_po_number(self, text: str, ocr_data: dict) -> Tuple[Optional[str], float]:
        """Extract PO number"""
        pattern = r'(?:po|p\.o\.|purchase order)\s*#?[:\s]*([A-Z0-9-]{4,})'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            po = match.group(1).strip()
            if len(po) >= 4:
                return po, 85.0
        
        return None, 0.0
    
    def _calculate_confidence(self, field_confidences: Dict[str, float], ocr_data: dict) -> float:
        """Calculate overall confidence"""
        if not field_confidences:
            return 0.0
        
        # Weight important fields
        weights = {
            'vendor_name': 1.5,
            'invoice_number': 2.0,
            'total_amount': 2.0,
            'invoice_date': 1.5,
            'currency': 0.5,
            'po_number': 0.5,
        }
        
        weighted_sum = 0
        weight_total = 0
        
        for field, confidence in field_confidences.items():
            weight = weights.get(field, 1.0)
            weighted_sum += confidence * weight
            weight_total += weight
        
        if weight_total == 0:
            return 0.0
        
        return round(weighted_sum / weight_total, 2)


# Create singleton
layoutlm_service = LayoutLMService()

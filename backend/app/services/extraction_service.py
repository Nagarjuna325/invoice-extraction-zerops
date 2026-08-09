# import re
# from datetime import datetime
# from typing import Dict, Any, Optional, Tuple, List
# import logging

# logger = logging.getLogger(__name__)


# class ExtractionService:
#     """Extract structured invoice fields from OCR text with improved patterns"""
    
#     def __init__(self):
#         # Enhanced keyword patterns
#         self.vendor_keywords = [
#             r'(?:from|vendor|supplier|company|seller)[:\s]+(.+)',
#             r'^([A-Z][A-Z\s&\.]+(?:INC|LLC|LTD|CORP|CO)?)',  # Company name pattern
#         ]
        
#         self.invoice_keywords = [
#             r'(?:invoice|order)\s*(?:#|no|number)[:\s]*([A-Z0-9-]+)',
#             r'(?:inv|invoice)\s*[:\s]*([A-Z0-9-]{5,})',
#             r'order\s*#[:\s]*(\d{5,})',
#         ]
        
#         self.date_keywords = [
#             r'(?:date|invoice date|dated)[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
#             r'date[:\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
#         ]
        
#         self.total_keywords = [
#             r'(?:invoice total|balance due|amount due|total due)[:\s]*\$?\s*([\d,]+\.?\d*)',
#             r'(?:grand total|total)[:\s]*\$\s*([\d,]+\.\d{2})',
#         ]
    
#     def extract_all_fields(self, text: str, ocr_confidence: float) -> Tuple[Dict[str, Any], Dict[str, float]]:
#         """Extract all invoice fields from text with improved logic"""
#         logger.info("Starting improved field extraction")
        
#         extracted_data = {}
#         field_confidences = {}
        
#         # Extract vendor (try multiple approaches)
#         vendor, vendor_conf = self._extract_vendor_improved(text, ocr_confidence)
#         if vendor:
#             extracted_data['vendor_name'] = vendor
#             field_confidences['vendor_name'] = vendor_conf
        
#         # Extract invoice/order number
#         invoice_num, inv_conf = self._extract_invoice_number_improved(text, ocr_confidence)
#         if invoice_num:
#             extracted_data['invoice_number'] = invoice_num
#             field_confidences['invoice_number'] = inv_conf
        
#         # Extract date
#         inv_date, date_conf = self._extract_date_improved(text, ocr_confidence)
#         if inv_date:
#             extracted_data['invoice_date'] = inv_date
#             field_confidences['invoice_date'] = date_conf
        
#         # Extract total amount
#         amount, amount_conf = self._extract_total_amount_improved(text, ocr_confidence)
#         if amount is not None:
#             extracted_data['total_amount'] = amount
#             field_confidences['total_amount'] = amount_conf
        
#         # Extract currency
#         currency = self._extract_currency(text)
#         if currency:
#             extracted_data['currency'] = currency
#             field_confidences['currency'] = 95.0
        
#         # Extract PO number
#         po_number, po_conf = self._extract_po_number(text, ocr_confidence)
#         if po_number:
#             extracted_data['po_number'] = po_number
#             field_confidences['po_number'] = po_conf
        
#         logger.info(f"Extraction complete: {len(extracted_data)} fields extracted")
#         logger.info(f"Extracted fields: {list(extracted_data.keys())}")
        
#         return extracted_data, field_confidences
    
#     def _extract_vendor_improved(self, text: str, base_confidence: float) -> Tuple[Optional[str], float]:
#         """Improved vendor extraction with multiple strategies"""
#         lines = [line.strip() for line in text.split('\n') if line.strip()]
        
#         # Strategy 1: Look for company patterns in first 5 lines
#         company_pattern = r'^([A-Z][A-Z\s&\.\,]+(?:RECEIPT|INC|LLC|LTD|CORP|CO\.?)?)'
#         for i, line in enumerate(lines[:5]):
#             match = re.match(company_pattern, line)
#             if match:
#                 vendor = match.group(1).strip()
#                 # Filter out common non-company words
#                 if len(vendor) > 3 and vendor not in ['CUSTOMER', 'VEHICLE', 'ORDER', 'DATE']:
#                     logger.info(f"Vendor found (pattern match): {vendor}")
#                     return vendor, min(base_confidence + 10, 100)
        
#         # Strategy 2: First substantive line (length > 5, mostly uppercase)
#         for line in lines[:3]:
#             if len(line) > 5 and sum(1 for c in line if c.isupper()) > len(line) * 0.6:
#                 # Exclude lines with numbers/dates
#                 if not re.search(r'\d{2,}', line):
#                     logger.info(f"Vendor found (first line): {line}")
#                     return line, base_confidence
        
#         return None, 0.0
    
#     def _extract_invoice_number_improved(self, text: str, base_confidence: float) -> Tuple[Optional[str], float]:
#         """Improved invoice/order number extraction"""
        
#         # Priority patterns (most specific first)
#         patterns = [
#             (r'order\s*#[:\s]*(\d{6,})', 100),  # "Order #: 45752969"
#             (r'invoice\s*#[:\s]*([A-Z0-9-]{5,})', 95),  # "Invoice #: INV-123"
#             (r'invoice\s*(?:no|number)[:\s]*([A-Z0-9-]{5,})', 95),
#             (r'order[:\s]+(\d{5,})', 90),
#             (r'#[:\s]*([A-Z0-9]{5,})', 80),
#         ]
        
#         for pattern, bonus in patterns:
#             match = re.search(pattern, text, re.IGNORECASE)
#             if match:
#                 inv_num = match.group(1).strip()
#                 # Validate: should have digits and reasonable length
#                 if len(inv_num) >= 4 and re.search(r'\d', inv_num):
#                     # Extra validation: not a date or phone number
#                     if not re.match(r'\d{2}[-/]\d{2}[-/]\d{2,4}', inv_num):
#                         logger.info(f"Invoice number found: {inv_num}")
#                         return inv_num, min(base_confidence + bonus - 95, 100)
        
#         return None, 0.0
    
#     def _extract_date_improved(self, text: str, base_confidence: float) -> Tuple[Optional[str], float]:
#         """Improved date extraction with better parsing"""
        
#         # Look for date near keywords
#         date_context_pattern = r'(?:date|invoice date|dated)[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})'
#         match = re.search(date_context_pattern, text, re.IGNORECASE)
        
#         if match:
#             date_str = match.group(1)
#             parsed_date = self._parse_date(date_str)
#             if parsed_date:
#                 logger.info(f"Date found (with context): {parsed_date}")
#                 return parsed_date, min(base_confidence + 10, 100)
        
#         # Fallback: Find all date-like patterns
#         date_patterns = [
#             r'\b(\d{2}[-/]\d{2}[-/]\d{4})\b',  # 05-12-2025
#             r'\b(\d{4}[-/]\d{2}[-/]\d{2})\b',  # 2025-12-05
#             r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b',
#         ]
        
#         for pattern in date_patterns:
#             matches = re.findall(pattern, text, re.IGNORECASE)
#             if matches:
#                 # Take the first valid date
#                 for date_str in matches:
#                     parsed_date = self._parse_date(date_str)
#                     if parsed_date:
#                         logger.info(f"Date found (pattern match): {parsed_date}")
#                         return parsed_date, base_confidence
        
#         return None, 0.0
    
#     def _parse_date(self, date_str: str) -> Optional[str]:
#         """Parse date string to YYYY-MM-DD format"""
#         date_formats = [
#             '%m-%d-%Y',  # 05-12-2025
#             '%m/%d/%Y',  # 05/12/2025
#             '%d-%m-%Y',  # 12-05-2025
#             '%d/%m/%Y',  # 12/05/2025
#             '%Y-%m-%d',  # 2025-05-12
#             '%Y/%m/%d',  # 2025/05/12
#             '%d %b %Y',  # 12 May 2025
#             '%d %B %Y',  # 12 May 2025
#         ]
        
#         for fmt in date_formats:
#             try:
#                 parsed = datetime.strptime(date_str, fmt)
#                 # Sanity check: date should be reasonable (not too far in future/past)
#                 year = parsed.year
#                 if 2000 <= year <= 2030:
#                     return parsed.strftime('%Y-%m-%d')
#             except ValueError:
#                 continue
        
#         return None
    
#     def _extract_total_amount_improved(self, text: str, base_confidence: float) -> Tuple[Optional[float], float]:
#         """Improved total amount extraction"""
        
#         # Priority 1: Look for "Invoice Total" or "Balance Due" with dollar sign
#         priority_patterns = [
#             r'(?:invoice total|balance due|amount due|total due)[:\s]*\$\s*([\d,]+\.?\d*)',
#             r'(?:invoice total|balance due)[:\s]*([\d,]+\.\d{2})',
#         ]
        
#         for pattern in priority_patterns:
#             match = re.search(pattern, text, re.IGNORECASE)
#             if match:
#                 amount_str = match.group(1).replace(',', '')
#                 try:
#                     amount = float(amount_str)
#                     logger.info(f"Total amount found (priority): ${amount}")
#                     return amount, min(base_confidence + 15, 100)
#                 except ValueError:
#                     pass
        
#         # Priority 2: Look for "Total" with dollar sign (but not "Total Labor" or "Total Parts")
#         pattern = r'(?<!Labor|Parts|Tax)\s+Total[:\s]*\$\s*([\d,]+\.\d{2})'
#         match = re.search(pattern, text, re.IGNORECASE)
#         if match:
#             amount_str = match.group(1).replace(',', '')
#             try:
#                 amount = float(amount_str)
#                 logger.info(f"Total amount found: ${amount}")
#                 return amount, min(base_confidence + 10, 100)
#             except ValueError:
#                 pass
        
#         # Priority 3: Find all amounts, take the one after "Total" keyword
#         lines = text.split('\n')
#         for i, line in enumerate(lines):
#             if re.search(r'(?:invoice total|balance due|amount due)', line, re.IGNORECASE):
#                 # Look in this line and next 2 lines for amount
#                 search_text = '\n'.join(lines[i:i+3])
#                 amounts = re.findall(r'\$\s*([\d,]+\.\d{2})', search_text)
#                 if amounts:
#                     amount_str = amounts[0].replace(',', '')
#                     try:
#                         amount = float(amount_str)
#                         logger.info(f"Total amount found (nearby): ${amount}")
#                         return amount, base_confidence
#                     except ValueError:
#                         pass
        
#         return None, 0.0
    
#     def _extract_currency(self, text: str) -> Optional[str]:
#         """Extract currency"""
#         if '$' in text or re.search(r'\bUSD\b', text, re.IGNORECASE):
#             return 'USD'
#         elif '€' in text or re.search(r'\bEUR\b', text, re.IGNORECASE):
#             return 'EUR'
#         elif '£' in text or re.search(r'\bGBP\b', text, re.IGNORECASE):
#             return 'GBP'
#         return 'USD'  # Default
    
#     def _extract_po_number(self, text: str, base_confidence: float) -> Tuple[Optional[str], float]:
#         """Extract purchase order number"""
#         patterns = [
#             r'(?:po|p\.o\.|purchase order)\s*#?[:\s]*([A-Z0-9-]{4,})',
#         ]
        
#         for pattern in patterns:
#             match = re.search(pattern, text, re.IGNORECASE)
#             if match:
#                 po = match.group(1).strip()
#                 if len(po) >= 4:
#                     return po, min(base_confidence, 100)
        
#         return None, 0.0
    
#     def calculate_overall_confidence(self, field_confidences: Dict[str, float]) -> float:
#         """Calculate overall extraction confidence"""
#         if not field_confidences:
#             return 0.0
        
#         # Weight important fields more
#         weights = {
#             'vendor_name': 1.5,
#             'invoice_number': 1.8,
#             'total_amount': 2.0,
#             'invoice_date': 1.5,
#             'currency': 0.5,
#             'po_number': 0.5,
#         }
        
#         weighted_sum = 0
#         weight_total = 0
        
#         for field, confidence in field_confidences.items():
#             weight = weights.get(field, 1.0)
#             weighted_sum += confidence * weight
#             weight_total += weight
        
#         if weight_total == 0:
#             return 0.0
        
#         overall = round(weighted_sum / weight_total, 2)
#         logger.info(f"Overall confidence calculated: {overall}%")
#         return overall


# # Create singleton instance
# extraction_service = ExtractionService()







import re
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)


class ExtractionService:
    """Extract structured invoice fields from OCR text with improved patterns"""
    
    def __init__(self):
        # Enhanced keyword patterns
        self.vendor_keywords = [
            r'(?:from|vendor|supplier|company|seller)[:\s]+(.+)',
            r'^([A-Z][A-Z\s&\.]+(?:INC|LLC|LTD|CORP|CO)?)',
        ]
        
        self.invoice_keywords = [
            r'(?:invoice|order)\s*(?:#|no|number)[:\s]*([A-Z0-9-]+)',
            r'(?:inv|invoice)\s*[:\s]*([A-Z0-9-]{5,})',
            r'order\s*#[:\s]*(\d{5,})',
        ]
        
        self.date_keywords = [
            r'(?:date|invoice date|dated)[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'date[:\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        ]
        
        self.total_keywords = [
            r'(?:invoice total|balance due|amount due|total due)[:\s]*\$?\s*([\d,]+\.?\d*)',
            r'(?:grand total|total)[:\s]*\$\s*([\d,]+\.\d{2})',
        ]
    
    def extract_all_fields(self, text: str, ocr_confidence: float) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """Extract all invoice fields from text with improved logic"""
        logger.info("Starting improved field extraction")
        
        extracted_data = {}
        field_confidences = {}
        
        # Extract vendor
        vendor, vendor_conf = self._extract_vendor_improved(text, ocr_confidence)
        if vendor:
            extracted_data['vendor_name'] = vendor
            field_confidences['vendor_name'] = vendor_conf
        
        # Extract invoice/order number
        invoice_num, inv_conf = self._extract_invoice_number_improved(text, ocr_confidence)
        if invoice_num:
            extracted_data['invoice_number'] = invoice_num
            field_confidences['invoice_number'] = inv_conf
        
        # Extract date
        inv_date, date_conf = self._extract_date_improved(text, ocr_confidence)
        if inv_date:
            extracted_data['invoice_date'] = inv_date
            field_confidences['invoice_date'] = date_conf
        
        # Extract total amount
        amount, amount_conf = self._extract_total_amount_improved(text, ocr_confidence)
        if amount is not None:
            extracted_data['total_amount'] = amount
            field_confidences['total_amount'] = amount_conf
        
        # Extract currency
        currency = self._extract_currency(text)
        if currency:
            extracted_data['currency'] = currency
            field_confidences['currency'] = 95.0
        
        # Extract PO number
        po_number, po_conf = self._extract_po_number(text, ocr_confidence)
        if po_number:
            extracted_data['po_number'] = po_number
            field_confidences['po_number'] = po_conf
        
        logger.info(f"Extraction complete: {len(extracted_data)} fields extracted")
        logger.info(f"Extracted fields: {list(extracted_data.keys())}")
        
        return extracted_data, field_confidences
    
    def _extract_vendor_improved(self, text: str, base_confidence: float) -> Tuple[Optional[str], float]:
        """Improved vendor extraction"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Look for company patterns in first 5 lines
        company_pattern = r'^([A-Z][A-Z\s&\.\,]+(?:RECEIPT|INC|LLC|LTD|CORP|CO\.?)?)'
        for i, line in enumerate(lines[:5]):
            match = re.match(company_pattern, line)
            if match:
                vendor = match.group(1).strip()
                if len(vendor) > 3 and vendor not in ['CUSTOMER', 'VEHICLE', 'ORDER', 'DATE', 'BILL TO']:
                    logger.info(f"Vendor found: {vendor}")
                    return vendor, min(base_confidence + 10, 100)
        
        # Fallback: First substantive line
        for line in lines[:3]:
            if len(line) > 5 and sum(1 for c in line if c.isupper()) > len(line) * 0.6:
                if not re.search(r'\d{2,}', line):
                    logger.info(f"Vendor found (first line): {line}")
                    return line, base_confidence
        
        return None, 0.0
    
    def _extract_invoice_number_improved(self, text: str, base_confidence: float) -> Tuple[Optional[str], float]:
        """Improved invoice/order number extraction"""
        
        patterns = [
            (r'invoice\s*#[:\s]*([A-Z0-9-]{5,})', 100),
            (r'invoice\s*(?:no|number)[:\s]*([A-Z0-9-]{5,})', 95),
            (r'order\s*#[:\s]*(\d{5,})', 90),
            (r'#[:\s]*([A-Z0-9]{5,})', 80),
        ]
        
        for pattern, bonus in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                inv_num = match.group(1).strip()
                if len(inv_num) >= 4 and re.search(r'\d', inv_num):
                    if not re.match(r'\d{2}[-/]\d{2}[-/]\d{2,4}', inv_num):
                        logger.info(f"Invoice number found: {inv_num}")
                        return inv_num, min(base_confidence + bonus - 95, 100)
        
        return None, 0.0
    
    def _extract_date_improved(self, text: str, base_confidence: float) -> Tuple[Optional[str], float]:
        """Improved date extraction"""
        
        # Look for date near keywords
        date_context_pattern = r'(?:date|invoice date|dated)[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})'
        match = re.search(date_context_pattern, text, re.IGNORECASE)
        
        if match:
            date_str = match.group(1)
            parsed_date = self._parse_date(date_str)
            if parsed_date:
                logger.info(f"Date found: {parsed_date}")
                return parsed_date, min(base_confidence + 10, 100)
        
        # Fallback patterns
        date_patterns = [
            r'\b(\d{2}[-/]\d{2}[-/]\d{4})\b',
            r'\b(\d{4}[-/]\d{2}[-/]\d{2})\b',
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                for date_str in matches:
                    parsed_date = self._parse_date(date_str)
                    if parsed_date:
                        logger.info(f"Date found: {parsed_date}")
                        return parsed_date, base_confidence
        
        return None, 0.0
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date to YYYY-MM-DD"""
        date_formats = [
            '%m-%d-%Y',
            '%m/%d/%Y',
            '%d-%m-%Y',
            '%d/%m/%Y',
            '%Y-%m-%d',
            '%Y/%m/%d',
        ]
        
        for fmt in date_formats:
            try:
                parsed = datetime.strptime(date_str, fmt)
                year = parsed.year
                if 2000 <= year <= 2030:
                    return parsed.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        return None
    
    def _extract_total_amount_improved(self, text: str, base_confidence: float) -> Tuple[Optional[float], float]:
        """Improved total amount extraction - FIXED REGEX"""
        
        # Priority 1: Invoice Total / Balance Due
        priority_patterns = [
            r'(?:invoice total|balance due|amount due|total due)[:\s]*\$?\s*([\d,]+\.?\d*)',
            r'total\s*\(usd\)[:\s]*\$?\s*([\d,]+\.?\d*)',
        ]
        
        for pattern in priority_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                    logger.info(f"Total amount found (priority): ${amount}")
                    return amount, min(base_confidence + 15, 100)
                except ValueError:
                    pass
        
        # Priority 2: Look for "Total" with dollar - FIXED PATTERN
        # Changed from negative lookbehind to simpler pattern
        lines = text.split('\n')
        for i, line in enumerate(lines):
            # Skip lines that have "Labor", "Parts", or "Tax" before "Total"
            if re.search(r'(labor|parts|tax)\s+total', line, re.IGNORECASE):
                continue
            
            # Look for Total with amount
            match = re.search(r'\btotal[:\s]*\$?\s*([\d,]+\.\d{2})', line, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                    logger.info(f"Total amount found: ${amount}")
                    return amount, min(base_confidence + 10, 100)
                except ValueError:
                    pass
        
        return None, 0.0
    
    def _extract_currency(self, text: str) -> Optional[str]:
        """Extract currency"""
        if '$' in text or re.search(r'\bUSD\b', text, re.IGNORECASE):
            return 'USD'
        elif '€' in text or re.search(r'\bEUR\b', text, re.IGNORECASE):
            return 'EUR'
        elif '£' in text or re.search(r'\bGBP\b', text, re.IGNORECASE):
            return 'GBP'
        return 'USD'
    
    def _extract_po_number(self, text: str, base_confidence: float) -> Tuple[Optional[str], float]:
        """Extract PO number"""
        patterns = [
            r'(?:po|p\.o\.|purchase order)\s*#?[:\s]*([A-Z0-9-]{4,})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                po = match.group(1).strip()
                if len(po) >= 4:
                    return po, min(base_confidence, 100)
        
        return None, 0.0
    
    def calculate_overall_confidence(self, field_confidences: Dict[str, float]) -> float:
        """Calculate overall confidence"""
        if not field_confidences:
            return 0.0
        
        weights = {
            'vendor_name': 1.5,
            'invoice_number': 1.8,
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
        
        overall = round(weighted_sum / weight_total, 2)
        logger.info(f"Overall confidence: {overall}%")
        return overall


# Create singleton
extraction_service = ExtractionService()

"""
Docling Service - IBM Document Understanding
Provides structure-aware document extraction with tables and layout understanding

PHASE 1 FIXES:
- Fixed initialization error (removed pipeline_options)
- Added confidence calibration
- Enhanced error handling
- Improved field extraction

Key Features:
- Multi-page PDF processing
- Table extraction (line items)
- Layout-aware field detection
- Deterministic results (no randomness)
- Header/Footer separation
"""

import logging
from typing import Dict, Any, Tuple, List, Optional
from pathlib import Path
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class DoclingService:
    """
    IBM Docling-based document understanding service
    Extracts structured data from PDFs including tables and layout
    """
    
    def __init__(self):
        self.converter = None
        self._load_converter()
    
    def _load_converter(self):
        """
        Lazy load Docling converter
        FIXED: Removed pipeline_options parameter that caused error
        """
        try:
            from docling.document_converter import DocumentConverter
            
            # FIXED: Use simple initialization without pipeline_options
            # The DocumentConverter class doesn't accept pipeline_options in __init__
            self.converter = DocumentConverter()
            
            logger.info("✅ Docling converter initialized successfully")
            
        except ImportError as e:
            logger.warning(f"⚠️  Docling not available: {e}")
            logger.warning("Install with: pip install docling docling-ibm-models --break-system-packages")
            self.converter = None
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Docling: {e}")
            logger.info("Continuing without Docling - will use 3-model system")
            self.converter = None
    
    def extract_from_pdf(
        self, 
        pdf_path: str
    ) -> Tuple[Dict[str, Any], float, Dict[str, Any]]:
        """
        Extract structured data from PDF using Docling
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            (extracted_data, confidence, metadata)
            
        Extracted Fields:
            - invoice_number
            - invoice_date
            - due_date
            - total_amount
            - subtotal
            - tax_amount
            - vendor_name
            - vendor_address
            - customer_name
            - customer_address
            - line_items (array)
            - currency
        """
        
        if not self.converter:
            logger.warning("Docling converter not available, returning empty")
            return {}, 0.0, {'error': 'Converter not initialized'}
        
        try:
            logger.info(f"🔍 Docling processing: {pdf_path}")
            
            # Convert document
            result = self.converter.convert(pdf_path)
            doc = result.document
        
            # 🔍 DEBUG: Log Docling's raw text
            logger.info("=" * 80)
            logger.info("DOCLING RAW TEXT OUTPUT:")
            logger.info("=" * 80)
            raw_text_md = doc.export_to_markdown()
            logger.info(raw_text_md)
            logger.info("=" * 80)
            
            if not result or not hasattr(result, 'document'):
                logger.warning("Docling returned empty result")
                return {}, 0.0, {'warning': 'Empty result'}
            
            # Extract all data
            extracted_data = {}
            metadata = {
                'page_count': 0,
                'tables_found': 0,
                'processing_method': 'docling',
                'layout_detected': True,
                'raw_text': raw_text_md
            }
            
            # Get document content
            doc_content = result.document
            
            # Count pages
            if hasattr(doc_content, 'pages'):
                metadata['page_count'] = len(doc_content.pages)
            
            # Extract header information
            header_data = self._extract_header_fields(doc_content)
            extracted_data.update(header_data)
            
            # Extract tables (line items)
            tables_data = self._extract_tables(doc_content)
            if tables_data:
                extracted_data['line_items'] = tables_data.get('line_items', [])
                metadata['tables_found'] = len(tables_data.get('line_items', []))
            
            # Extract totals from document
            totals_data = self._extract_totals(doc_content)
            extracted_data.update(totals_data)
            
            # Extract addresses
            addresses_data = self._extract_addresses(doc_content)
            extracted_data.update(addresses_data)
            
            # PHASE 1: Calculate CALIBRATED confidence
            confidence = self._calculate_docling_confidence(extracted_data, metadata)
            
            logger.info(f"✅ Docling extracted {len(extracted_data)} fields")
            logger.info(f"   Found {metadata['tables_found']} line items")
            logger.info(f"   Confidence: {confidence:.1f}%")
            
            return extracted_data, confidence, metadata
            
        except Exception as e:
            logger.error(f"❌ Docling extraction failed: {e}", exc_info=True)
            return {}, 0.0, {'error': str(e)}
    
    def _extract_header_fields(self, doc_content) -> Dict[str, Any]:
        """
        Extract header fields (invoice number, dates, vendor)
        
        Strategy:
        1. Look for common keywords
        2. Extract values near keywords
        3. Validate format
        """
        fields = {}
        
        try:
            # Get full text
            full_text = self._get_document_text(doc_content)
            
            # Invoice Number
            inv_patterns = [
                r'invoice\s*#?\s*:?\s*([A-Z0-9\-/]+)',
                r'invoice\s+number\s*:?\s*([A-Z0-9\-/]+)',
                r'document\s+number\s*:?\s*([A-Z0-9\-/]+)',
                r'#\s*([A-Z]{2,5}[-/]?\d{4,}[-/]?\d+)'
            ]
            
            for pattern in inv_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    fields['invoice_number'] = match.group(1).strip()
                    break
            
            # Invoice Date
            date_patterns = [
                r'invoice\s+date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'issued\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    fields['invoice_date'] = match.group(1).strip()
                    break
            
            # Due Date
            due_patterns = [
                r'due\s+date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'payment\s+due\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
            ]
            
            for pattern in due_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    fields['due_date'] = match.group(1).strip()
                    break
            
            # Vendor Name (usually at top of document)
            # Get first few lines
            lines = full_text.split('\n')[:10]
            for line in lines:
                line = line.strip()
                # Look for company-like names (capitalized, >3 chars, not "INVOICE")
                if (len(line) > 3 and 
                    line[0].isupper() and 
                    'invoice' not in line.lower() and
                    'receipt' not in line.lower()):
                    # Likely vendor name
                    if 'vendor_name' not in fields:
                        fields['vendor_name'] = line
                        break
            
            # Currency
            currency_match = re.search(r'\b([A-Z]{3})\b', full_text)
            if currency_match:
                fields['currency'] = currency_match.group(1)
            elif '$' in full_text:
                fields['currency'] = 'USD'
            elif '€' in full_text:
                fields['currency'] = 'EUR'
            elif '£' in full_text:
                fields['currency'] = 'GBP'
            
        except Exception as e:
            logger.warning(f"Header extraction error: {e}")
        
        return fields
    
    def _extract_tables(self, doc_content) -> Dict[str, Any]:
        """
        Extract tables (line items) from document
        
        Returns line items in format:
        [
            {
                'description': 'Widget A',
                'quantity': 100,
                'unit_price': 2.50,
                'total': 250.00
            },
            ...
        ]
        """
        tables_data = {
            'line_items': []
        }
        
        try:
            # Check if document has tables
            if not hasattr(doc_content, 'tables'):
                logger.debug("No tables attribute in document")
                return tables_data
            
            tables = getattr(doc_content, 'tables', [])
            
            for table in tables:
                # Parse table into line items
                items = self._parse_table_to_line_items(table)
                tables_data['line_items'].extend(items)
            
            logger.debug(f"Extracted {len(tables_data['line_items'])} line items")
            
        except Exception as e:
            logger.warning(f"Table extraction error: {e}")
        
        return tables_data
    
    def _parse_table_to_line_items(self, table) -> List[Dict[str, Any]]:
        """
        Parse a table structure into line items
        
        Detects columns: Description, Quantity, Unit Price, Total
        """
        items = []
        
        try:
            # Get table data - try multiple methods
            rows = None
            
            if hasattr(table, 'data'):
                rows = table.data
            elif hasattr(table, 'to_dataframe'):
                df = table.to_dataframe()
                rows = df.values.tolist()
            elif hasattr(table, 'rows'):
                rows = table.rows
            
            if not rows or len(rows) < 2:
                return items
            
            # First row is usually header
            header = rows[0]
            
            # Detect column indices
            desc_col = self._find_column_index(header, ['description', 'item', 'product', 'service'])
            qty_col = self._find_column_index(header, ['quantity', 'qty', 'amount'])
            price_col = self._find_column_index(header, ['unit price', 'price', 'rate'])
            total_col = self._find_column_index(header, ['total', 'amount', 'line total'])
            
            # Extract items
            for row in rows[1:]:
                if len(row) < 2:
                    continue
                
                # Skip total/subtotal rows
                first_cell = str(row[0]).lower() if len(row) > 0 else ""
                if any(word in first_cell for word in ['total', 'subtotal', 'tax', 'grand']):
                    continue
                
                item = {}
                
                if desc_col is not None and desc_col < len(row):
                    item['description'] = str(row[desc_col]).strip()
                
                if qty_col is not None and qty_col < len(row):
                    item['quantity'] = self._parse_number(row[qty_col])
                
                if price_col is not None and price_col < len(row):
                    item['unit_price'] = self._parse_number(row[price_col])
                
                if total_col is not None and total_col < len(row):
                    item['total'] = self._parse_number(row[total_col])
                
                # Only add if we got at least description and one number
                if item.get('description') and (item.get('quantity') or item.get('total')):
                    items.append(item)
            
        except Exception as e:
            logger.warning(f"Table parsing error: {e}")
        
        return items
    
    def _extract_totals(self, doc_content) -> Dict[str, Any]:
        """
        Extract total amounts from document
        
        Strategy:
        1. Look for "Total:", "Grand Total:", "Amount Due:"
        2. Extract number after label
        3. Handle multiple totals (subtotal, tax, grand total)
        """
        totals = {}
        
        try:
            full_text = self._get_document_text(doc_content)
            
            # Total Amount (most important)
            total_patterns = [
                r'(?:grand\s+)?total\s*:?\s*\$?\s*([\d,]+\.?\d*)',
                r'amount\s+due\s*:?\s*\$?\s*([\d,]+\.?\d*)',
                r'balance\s+due\s*:?\s*\$?\s*([\d,]+\.?\d*)'
            ]
            
            for pattern in total_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    try:
                        totals['total_amount'] = float(amount_str)
                        break
                    except:
                        pass
            
            # Subtotal
            subtotal_pattern = r'subtotal\s*:?\s*\$?\s*([\d,]+\.?\d*)'
            match = re.search(subtotal_pattern, full_text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    totals['subtotal'] = float(amount_str)
                except:
                    pass
            
            # Tax
            tax_pattern = r'tax\s*:?\s*\$?\s*([\d,]+\.?\d*)'
            match = re.search(tax_pattern, full_text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    totals['tax_amount'] = float(amount_str)
                except:
                    pass
            
        except Exception as e:
            logger.warning(f"Totals extraction error: {e}")
        
        return totals
    
    def _extract_addresses(self, doc_content) -> Dict[str, Any]:
        """Extract vendor and customer addresses"""
        addresses = {}
        
        try:
            full_text = self._get_document_text(doc_content)
            
            # Look for address patterns (street, city, zip)
            address_pattern = r'\d+\s+[\w\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)[,\s]+[\w\s]+,\s*[A-Z]{2}\s+\d{5}'
            
            matches = re.findall(address_pattern, full_text, re.IGNORECASE)
            
            if len(matches) >= 1:
                addresses['vendor_address'] = matches[0].strip()
            
            if len(matches) >= 2:
                addresses['customer_address'] = matches[1].strip()
            
        except Exception as e:
            logger.warning(f"Address extraction error: {e}")
        
        return addresses
    
    def _get_document_text(self, doc_content) -> str:
        """Extract full text from document"""
        try:
            if hasattr(doc_content, 'export_to_markdown'):
                return doc_content.export_to_markdown()
            elif hasattr(doc_content, 'export_to_text'):
                return doc_content.export_to_text()
            elif hasattr(doc_content, 'text'):
                return doc_content.text
            else:
                # Fallback: concatenate all text
                return str(doc_content)
        except Exception as e:
            logger.warning(f"Text extraction failed: {e}")
            return str(doc_content)
    
    def _find_column_index(self, header: List, keywords: List[str]) -> Optional[int]:
        """Find column index by matching keywords"""
        for i, col_name in enumerate(header):
            col_name_lower = str(col_name).lower()
            for keyword in keywords:
                if keyword in col_name_lower:
                    return i
        return None
    
    def _parse_number(self, value: Any) -> Optional[float]:
        """Parse a value as number"""
        try:
            # Remove currency symbols and commas
            cleaned = re.sub(r'[$€£,\s]', '', str(value))
            # Extract number
            match = re.search(r'[\d.]+', cleaned)
            if match:
                return float(match.group())
        except:
            pass
        return None
    
    def _calculate_docling_confidence(
        self, 
        extracted_data: Dict, 
        metadata: Dict
    ) -> float:
        """
        PHASE 1: Calculate CALIBRATED confidence score for Docling extraction
        
        Improvements:
        - More realistic confidence (not overconfident)
        - Penalize if key fields missing
        - Boost for high-quality extraction
        
        Higher confidence if:
        - More fields extracted
        - Tables found
        - Multi-page processed
        - Layout detected
        """
        confidence = 40.0  # Base confidence (lowered from 50)
        
        # Field coverage bonus (more conservative)
        field_count = len([v for v in extracted_data.values() if v])
        confidence += min(field_count * 4, 25)  # Up to +25 (was +30)
        
        # Key fields bonus
        key_fields = ['invoice_number', 'invoice_date', 'total_amount', 'vendor_name']
        key_fields_found = sum(1 for f in key_fields if f in extracted_data and extracted_data[f])
        confidence += key_fields_found * 5  # +5 per key field
        
        # Table bonus
        if metadata.get('tables_found', 0) > 0:
            confidence += 12  # Reduced from 15
        
        # Multi-page bonus
        if metadata.get('page_count', 0) > 1:
            confidence += 3  # Reduced from 5
        
        # Layout detection bonus
        if metadata.get('layout_detected'):
            confidence += 8  # Reduced from 10
        
        # PHASE 1: Penalize if missing critical fields
        if 'total_amount' not in extracted_data:
            confidence -= 15
        
        if 'invoice_number' not in extracted_data:
            confidence -= 10
        
        # Cap at 95% (never claim 100%)
        confidence = max(10.0, min(confidence, 95.0))
        
        logger.debug(f"Docling confidence calculation: {confidence:.1f}% ({field_count} fields, {key_fields_found}/4 key fields)")
        
        return confidence


# Singleton instance
docling_service = DoclingService()

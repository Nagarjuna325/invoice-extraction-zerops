# """
# Universal document processor
# Handles: Images, PDFs, Excel, CSV
# """
# import os
# import fitz  # PyMuPDF
# import pandas as pd
# from PIL import Image
# from typing import Dict, Any, Tuple, Optional, List
# import logging
# import re
# from datetime import datetime

# logger = logging.getLogger(__name__)


# class DocumentProcessor:
#     """
#     Process different document types:
#     - Images (PNG, JPG)
#     - PDFs (convert to images)
#     - Excel (parse structured data)
#     - CSV (parse structured data)
#     """
    
#     def __init__(self):
#         self.supported_image_formats = ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']
#         self.supported_pdf_formats = ['.pdf']
#         self.supported_excel_formats = ['.xlsx', '.xls', '.xlsm']
#         self.supported_csv_formats = ['.csv']
    
#     def detect_document_type(self, file_path: str) -> str:
#         """
#         Detect document type from file extension
        
#         Returns:
#             'image', 'pdf', 'excel', 'csv', or 'unknown'
#         """
#         ext = os.path.splitext(file_path)[1].lower()
        
#         if ext in self.supported_image_formats:
#             return 'image'
#         elif ext in self.supported_pdf_formats:
#             return 'pdf'
#         elif ext in self.supported_excel_formats:
#             return 'excel'
#         elif ext in self.supported_csv_formats:
#             return 'csv'
#         else:
#             return 'unknown'
    
#     def process_document(self, file_path: str) -> Tuple[str, Any]:
#         """
#         Process any document type
        
#         Returns:
#             (document_type, processed_data)
            
#             For images/PDFs: returns image path(s)
#             For Excel/CSV: returns structured data dict
#         """
#         doc_type = self.detect_document_type(file_path)
        
#         logger.info(f"Processing {doc_type} document: {file_path}")
        
#         if doc_type == 'image':
#             return 'image', file_path
        
#         elif doc_type == 'pdf':
#             return self.process_pdf(file_path)
        
#         elif doc_type == 'excel':
#             return self.process_excel(file_path)
        
#         elif doc_type == 'csv':
#             return self.process_csv(file_path)
        
#         else:
#             raise ValueError(f"Unsupported document type: {doc_type}")
    
#     def process_pdf(self, pdf_path: str, max_pages: int = 10) -> Tuple[str, List[str]]:
#         """
#         Convert PDF to images
        
#         Args:
#             pdf_path: Path to PDF file
#             max_pages: Maximum pages to process (prevent 50-page timeout)
            
#         Returns:
#             ('pdf', list of image paths)
#         """
#         logger.info(f"Converting PDF to images: {pdf_path}")
        
#         try:
#             # Open PDF
#             doc = fitz.open(pdf_path)
#             total_pages = len(doc)
            
#             logger.info(f"PDF has {total_pages} pages")
            
#             if total_pages > max_pages:
#                 logger.warning(f"PDF has {total_pages} pages, limiting to first {max_pages}")
#                 pages_to_process = max_pages
#             else:
#                 pages_to_process = total_pages
            
#             # Convert pages to images
#             image_paths = []
            
#             for page_num in range(pages_to_process):
#                 page = doc[page_num]
                
#                 # Render page to image (high quality)
#                 pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for quality
                
#                 # Save as PNG
#                 output_path = f"{pdf_path}_page_{page_num + 1}.png"
#                 pix.save(output_path)
                
#                 image_paths.append(output_path)
#                 logger.info(f"Converted page {page_num + 1}/{pages_to_process}")
            
#             doc.close()
            
#             logger.info(f"✅ PDF converted: {len(image_paths)} pages")
#             return 'pdf', image_paths
            
#         except Exception as e:
#             logger.error(f"PDF processing failed: {e}")
#             raise
    
#     def process_excel(self, excel_path: str) -> Tuple[str, Dict[str, Any]]:
#         """
#         Parse Excel invoice (structured data)
        
#         Returns:
#             ('excel', extracted_invoice_data)
#         """
#         logger.info(f"Parsing Excel file: {excel_path}")
        
#         try:
#             # Read Excel file
#             df = pd.read_excel(excel_path, sheet_name=0)
            
#             logger.info(f"Excel has {len(df)} rows, {len(df.columns)} columns")
            
#             # Extract invoice data from Excel structure
#             invoice_data = self._extract_from_excel_dataframe(df)
            
#             logger.info(f"✅ Excel parsed: {len(invoice_data)} fields extracted")
#             return 'excel', invoice_data
            
#         except Exception as e:
#             logger.error(f"Excel processing failed: {e}")
#             raise
    
#     def process_csv(self, csv_path: str) -> Tuple[str, Dict[str, Any]]:
#         """
#         Parse CSV invoice (structured data)
        
#         Returns:
#             ('csv', extracted_invoice_data)
#         """
#         logger.info(f"Parsing CSV file: {csv_path}")
        
#         try:
#             # Read CSV file
#             df = pd.read_csv(csv_path)
            
#             logger.info(f"CSV has {len(df)} rows, {len(df.columns)} columns")
            
#             # Extract invoice data
#             invoice_data = self._extract_from_excel_dataframe(df)
            
#             logger.info(f"✅ CSV parsed: {len(invoice_data)} fields extracted")
#             return 'csv', invoice_data
            
#         except Exception as e:
#             logger.error(f"CSV processing failed: {e}")
#             raise
    
#     def _extract_from_excel_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
#         """
#         Extract invoice fields from Excel/CSV dataframe
        
#         Strategy:
#         1. Search for keywords in cells
#         2. Extract values next to keywords
#         3. Find totals in rightmost columns
#         """
#         invoice_data = {}
#         confidence = {}
        
#         # Convert dataframe to string for searching
#         df_str = df.astype(str)
        
#         # Search patterns
#         patterns = {
#             'invoice_number': [
#                 r'INVOICE\s*#?\s*:?\s*([A-Z0-9-]+)',
#                 r'INV[-\s](\d+)',
#                 r'Invoice\s*No\.?\s*:?\s*([A-Z0-9-]+)'
#             ],
#             'invoice_date': [
#                 r'INVOICE\s*DATE\s*:?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
#                 r'Date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
#                 r'(\d{4}-\d{2}-\d{2})'
#             ],
#             'total_amount': [
#                 r'TOTAL\s*:?\s*\$?([\d,]+\.?\d{0,2})',
#                 r'Grand\s*Total\s*:?\s*\$?([\d,]+\.?\d{2})',
#                 r'Amount\s*Due\s*:?\s*\$?([\d,]+\.?\d{2})'
#             ],
#             'vendor_name': [
#                 r'From\s*:?\s*([A-Za-z\s]+)',
#                 r'Vendor\s*:?\s*([A-Za-z\s]+)',
#                 r'Supplier\s*:?\s*([A-Za-z\s]+)'
#             ]
#         }
        
#         # Search each cell for patterns
#         for field, pattern_list in patterns.items():
#             for pattern in pattern_list:
#                 found = False
                
#                 # Search all cells
#                 for col in df_str.columns:
#                     for idx, value in df_str[col].items():
#                         match = re.search(pattern, str(value), re.IGNORECASE)
                        
#                         if match:
#                             extracted_value = match.group(1).strip()
                            
#                             # Clean value
#                             if field == 'total_amount':
#                                 extracted_value = float(extracted_value.replace(',', ''))
#                             elif field == 'invoice_date':
#                                 extracted_value = self._parse_date_flexible(extracted_value)
                            
#                             invoice_data[field] = extracted_value
#                             confidence[field] = 95.0
#                             found = True
#                             logger.info(f"Found {field}: {extracted_value}")
#                             break
                    
#                     if found:
#                         break
                
#                 if found:
#                     break
        
#         # Add confidence scores
#         invoice_data['_confidences'] = confidence
        
#         return invoice_data
    
#     def _parse_date_flexible(self, date_str: str) -> Optional[str]:
#         """Parse various date formats to YYYY-MM-DD"""
#         formats = [
#             '%B %d, %Y',      # October 15, 2023
#             '%b %d, %Y',      # Oct 15, 2023
#             '%Y-%m-%d',       # 2023-10-15
#             '%m/%d/%Y',       # 10/15/2023
#             '%d/%m/%Y',       # 15/10/2023
#             '%m-%d-%Y',       # 10-15-2023
#         ]
        
#         for fmt in formats:
#             try:
#                 parsed = datetime.strptime(date_str, fmt)
#                 return parsed.strftime('%Y-%m-%d')
#             except:
#                 continue
        
#         return date_str  # Return as-is if can't parse
    
#     def cleanup_temp_files(self, file_paths: List[str]):
#         """Clean up temporary PDF-to-image files"""
#         for file_path in file_paths:
#             try:
#                 if os.path.exists(file_path) and '_page_' in file_path:
#                     os.remove(file_path)
#                     logger.debug(f"Cleaned up: {file_path}")
#             except Exception as e:
#                 logger.warning(f"Failed to cleanup {file_path}: {e}")


# # Create singleton
# document_processor = DocumentProcessor()



"""
Universal document processor - IMPROVED
Handles: Images, PDFs, Excel, CSV
"""
import os
import fitz  # PyMuPDF
import pandas as pd
from PIL import Image
from typing import Dict, Any, Tuple, Optional, List
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Process different document types:
    - Images (PNG, JPG)
    - PDFs (convert to images)
    - Excel (parse structured data)
    - CSV (parse structured data)
    """
    
    def __init__(self):
        self.supported_image_formats = ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']
        self.supported_pdf_formats = ['.pdf']
        self.supported_excel_formats = ['.xlsx', '.xls', '.xlsm']
        self.supported_csv_formats = ['.csv']
    
    def detect_document_type(self, file_path: str) -> str:
        """Detect document type from file extension"""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in self.supported_image_formats:
            return 'image'
        elif ext in self.supported_pdf_formats:
            return 'pdf'
        elif ext in self.supported_excel_formats:
            return 'excel'
        elif ext in self.supported_csv_formats:
            return 'csv'
        else:
            return 'unknown'
    
    def process_document(self, file_path: str) -> Tuple[str, Any]:
        """
        Process any document type
        
        Returns:
            (document_type, processed_data)
        """
        doc_type = self.detect_document_type(file_path)
        
        logger.info(f"Processing {doc_type} document: {file_path}")
        
        if doc_type == 'image':
            return 'image', file_path
        
        elif doc_type == 'pdf':
            return self.process_pdf(file_path)
        
        elif doc_type == 'excel':
            return self.process_excel(file_path)
        
        elif doc_type == 'csv':
            return self.process_csv(file_path)
        
        else:
            raise ValueError(f"Unsupported document type: {doc_type}")
    
    def process_pdf(self, pdf_path: str, max_pages: int = 10) -> Tuple[str, List[str]]:
        """
        Convert PDF to images - PHASE 4: Multi-page support
        
        Args:
            pdf_path: Path to PDF file
            max_pages: Maximum pages to process (prevent timeout)
            
        Returns:
            ('pdf', list of image paths)
        """
        logger.info(f"Converting PDF to images: {pdf_path}")
        
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            logger.info(f"PDF has {total_pages} pages")
            
            # PHASE 4: Process ALL pages (up to max_pages limit)
            if total_pages > max_pages:
                logger.warning(f"PDF has {total_pages} pages, limiting to first {max_pages}")
                pages_to_process = max_pages
            else:
                pages_to_process = total_pages
            
            image_paths = []
            
            for page_num in range(pages_to_process):
                page = doc[page_num]
                
                # Render page to image (high quality - 300 DPI equivalent)
                # Matrix(2, 2) = 2x zoom = ~200 DPI
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                
                # Save as PNG
                output_path = f"{pdf_path}_page_{page_num + 1}.png"
                pix.save(output_path)
                
                image_paths.append(output_path)
                logger.info(f"Converted page {page_num + 1}/{pages_to_process}")
            
            doc.close()
            
            logger.info(f"✅ PDF converted: {len(image_paths)} pages")
            return 'pdf', image_paths
            
        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            raise
    
    def process_excel(self, excel_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        Parse Excel invoice (structured data)
        IMPROVED: Better data extraction
        """
        logger.info(f"Parsing Excel file: {excel_path}")
        
        try:
            # Read Excel file
            df = pd.read_excel(excel_path, sheet_name=0, header=None)
            
            logger.info(f"Excel has {len(df)} rows, {len(df.columns)} columns")
            
            # Extract invoice data
            invoice_data = self._extract_from_dataframe(df, 'excel')
            
            logger.info(f"✅ Excel parsed: {len(invoice_data)} fields extracted")
            return 'excel', invoice_data
            
        except Exception as e:
            logger.error(f"Excel processing failed: {e}")
            raise
    
    def process_csv(self, csv_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        Parse CSV invoice (structured data)
        IMPROVED: Better data extraction
        """
        logger.info(f"Parsing CSV file: {csv_path}")
        
        try:
            # Read CSV file
            df = pd.read_csv(csv_path, header=None)
            
            logger.info(f"CSV has {len(df)} rows, {len(df.columns)} columns")
            
            # Extract invoice data
            invoice_data = self._extract_from_dataframe(df, 'csv')
            
            logger.info(f"✅ CSV parsed: {len(invoice_data)} fields extracted")
            return 'csv', invoice_data
            
        except Exception as e:
            logger.error(f"CSV processing failed: {e}")
            raise
    
    def _extract_from_dataframe(self, df: pd.DataFrame, source: str) -> Dict[str, Any]:
        """
        IMPROVED: Extract invoice fields from Excel/CSV dataframe
        
        Strategy:
        1. Convert all cells to strings
        2. Search for invoice-specific keywords
        3. Extract values from adjacent cells
        4. Skip header/template text
        """
        invoice_data = {}
        confidence = {}
        
        # Convert dataframe to string
        df_str = df.astype(str)
        
        # Patterns with context-aware extraction
        extraction_rules = [
            {
                'field': 'invoice_number',
                'patterns': [
                    (r'INVOICE\s*#?\s*:?\s*([A-Z0-9-]+)', 1),
                    (r'INV[-\s#:]([A-Z0-9-]+)', 1),
                    (r'Invoice\s*No\.?\s*:?\s*([A-Z0-9-]+)', 1),
                ],
                'skip_values': ['TEMPLATE', 'EXAMPLE', 'SAMPLE', 'YOUR', 'COMPANY']
            },
            {
                'field': 'invoice_date',
                'patterns': [
                    (r'INVOICE\s*DATE\s*:?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})', 1),
                    (r'Date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', 1),
                    (r'(\d{4}-\d{2}-\d{2})', 1),
                    (r'(October|November|December|January|February|March|April|May|June|July|August|September)\s+\d{1,2},?\s+\d{4}', 0),
                ],
                'skip_values': []
            },
            {
                'field': 'total_amount',
                'patterns': [
                    (r'TOTAL\s*:?\s*\$?([\d,]+\.?\d{0,2})', 1),
                    (r'Grand\s*Total\s*:?\s*\$?([\d,]+\.?\d{2})', 1),
                    (r'Amount\s*Due\s*:?\s*\$?([\d,]+\.?\d{2})', 1),
                    (r'\$\s*([\d,]+\.\d{2})', 1),
                ],
                'skip_values': ['TOTAL', '0.00', '00.00']
            },
            {
                'field': 'vendor_name',
                'patterns': [
                    (r'From\s*:?\s*([A-Za-z][A-Za-z\s&]+)', 1),
                    (r'Vendor\s*:?\s*([A-Za-z][A-Za-z\s&]+)', 1),
                    (r'Supplier\s*:?\s*([A-Za-z][A-Za-z\s&]+)', 1),
                ],
                'skip_values': ['TEMPLATE', 'INVOICE', 'EXAMPLE', 'SAMPLE', 'YOUR', 'COMPANY', 'VENDOR']
            }
        ]
        
        # Search all cells
        for rule in extraction_rules:
            field = rule['field']
            patterns = rule['patterns']
            skip_values = rule['skip_values']
            
            found = False
            
            for pattern, group_num in patterns:
                if found:
                    break
                
                # Search all cells
                for col in range(len(df_str.columns)):
                    if found:
                        break
                    
                    for row in range(len(df_str)):
                        cell_value = str(df_str.iloc[row, col])
                        
                        match = re.search(pattern, cell_value, re.IGNORECASE)
                        
                        if match:
                            extracted_value = match.group(group_num).strip()
                            
                            # Skip template/placeholder values
                            if any(skip in extracted_value.upper() for skip in skip_values):
                                continue
                            
                            # Clean value based on field type
                            if field == 'total_amount':
                                try:
                                    extracted_value = float(extracted_value.replace(',', ''))
                                    if extracted_value == 0:
                                        continue  # Skip $0.00
                                except:
                                    continue
                            
                            elif field == 'invoice_date':
                                parsed_date = self._parse_date_flexible(extracted_value)
                                if not parsed_date:
                                    continue
                                extracted_value = parsed_date
                            
                            elif field == 'vendor_name':
                                # Clean vendor name
                                extracted_value = re.sub(r'[^A-Za-z\s&]', '', extracted_value).strip()
                                if len(extracted_value) < 3:
                                    continue
                            
                            elif field == 'invoice_number':
                                # Must have some digits
                                if not re.search(r'\d', extracted_value):
                                    continue
                            
                            invoice_data[field] = extracted_value
                            confidence[field] = 95.0
                            found = True
                            logger.info(f"Found {field}: {extracted_value}")
                            break
        
        # Add confidence scores
        invoice_data['_confidences'] = confidence
        
        return invoice_data
    
    def _parse_date_flexible(self, date_str: str) -> Optional[str]:
        """Parse various date formats to YYYY-MM-DD"""
        formats = [
            '%B %d, %Y',      # October 15, 2023
            '%b %d, %Y',      # Oct 15, 2023
            '%B %d %Y',       # October 15 2023
            '%Y-%m-%d',       # 2023-10-15
            '%m/%d/%Y',       # 10/15/2023
            '%d/%m/%Y',       # 15/10/2023
            '%m-%d-%Y',       # 10-15-2023
        ]
        
        for fmt in formats:
            try:
                parsed = datetime.strptime(date_str, fmt)
                return parsed.strftime('%Y-%m-%d')
            except:
                continue
        
        return None
    
    def cleanup_temp_files(self, file_paths: List[str]):
        """Clean up temporary PDF-to-image files"""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path) and '_page_' in file_path:
                    os.remove(file_path)
                    logger.debug(f"Cleaned up: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {file_path}: {e}")


# Create singleton
document_processor = DocumentProcessor()
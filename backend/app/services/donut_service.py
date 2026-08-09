from transformers import DonutProcessor, VisionEncoderDecoderModel
from PIL import Image
import re
import logging
from typing import Dict, Any, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DonutService:
    """Donut-based invoice extraction service"""
    
    def __init__(self):
        self.processor = None
        self.model = None
        self.loaded = False
    
    def load_model(self):
        """Load Donut model (lazy loading)"""
        if self.loaded:
            return
        
        try:
            logger.info("Loading Donut model...")
            self.processor = DonutProcessor.from_pretrained(
                "naver-clova-ix/donut-base-finetuned-cord-v2"
            )
            self.model = VisionEncoderDecoderModel.from_pretrained(
                "naver-clova-ix/donut-base-finetuned-cord-v2"
            )
            self.loaded = True
            logger.info("✅ Donut model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Donut model: {e}")
            raise
    
    def extract_invoice(self, image_path: str) -> Tuple[Dict[str, Any], float]:
        """
        Extract invoice data using Donut
        
        Returns:
            (extracted_data, confidence)
        """
        # Load model if not loaded
        self.load_model()
        
        logger.info(f"Processing invoice with Donut: {image_path}")
        
        try:
            # Load and prepare image
            image = Image.open(image_path).convert("RGB")
            pixel_values = self.processor(image, return_tensors="pt").pixel_values
            
            # Generate predictions
            task_prompt = "<s_cord-v2>"
            decoder_input_ids = self.processor.tokenizer(
                task_prompt, 
                add_special_tokens=False, 
                return_tensors="pt"
            ).input_ids
            
            outputs = self.model.generate(
                pixel_values,
                decoder_input_ids=decoder_input_ids,
                max_length=self.model.decoder.config.max_position_embeddings,
                early_stopping=True,
                pad_token_id=self.processor.tokenizer.pad_token_id,
                eos_token_id=self.processor.tokenizer.eos_token_id,
                use_cache=True,
                num_beams=1,
                bad_words_ids=[[self.processor.tokenizer.unk_token_id]],
                return_dict_in_generate=True,
            )
            
            # Decode output
            sequence = self.processor.batch_decode(outputs.sequences)[0]
            sequence = sequence.replace(self.processor.tokenizer.eos_token, "")
            sequence = sequence.replace(self.processor.tokenizer.pad_token, "")
            sequence = sequence.replace(task_prompt, "")
            
            logger.info("Donut extraction complete, parsing output...")
            
            # Parse the output
            extracted_data, confidence = self._parse_donut_output(sequence)
            
            logger.info(f"Parsed {len(extracted_data)} fields with {confidence}% confidence")
            
            return extracted_data, confidence
            
        except Exception as e:
            logger.error(f"Donut extraction failed: {e}")
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
            logger.error(f"Donut extract_from_image failed: {e}")
            return {
                "extracted_data": {},
                "overall_confidence": 0.0,
                "error": str(e),
            }
    
    def _parse_donut_output(self, sequence: str) -> Tuple[Dict[str, Any], float]:
        """
        Parse Donut XML output into structured data
        
        Args:
            sequence: Raw Donut output with XML tags
            
        Returns:
            (extracted_data, confidence)
        """
        extracted_data = {}
        
        # Extract vendor/company name (usually first <s_nm>)
        vendor_match = re.search(r'<s_nm>\s*([A-Z][A-Z\s&\.]+(?:RECEIPT|INC|LLC)?)', sequence)
        if vendor_match:
            vendor = vendor_match.group(1).strip()
            # Clean up vendor name
            vendor = re.sub(r'\s+', ' ', vendor)
            extracted_data['vendor_name'] = vendor
        
        # Extract invoice/order number
        # Look for patterns like "Order # 45752969" or numbers after "Order"
        invoice_patterns = [
            r'Order\s*#\s*(\d{5,})',
            r'Invoice\s*#?\s*([A-Z0-9-]{5,})',
            r'<s_price>\s*(\d{6,})\s*</s_price>',  # Sometimes in price tag
        ]
        
        for pattern in invoice_patterns:
            match = re.search(pattern, sequence, re.IGNORECASE)
            if match:
                extracted_data['invoice_number'] = match.group(1).strip()
                break
        
        # Extract date
        # Look for date patterns
        date_pattern = r'(\d{2}-\d{2}-\d{4})'
        date_matches = re.findall(date_pattern, sequence)
        if date_matches:
            # Take first valid date
            for date_str in date_matches:
                parsed_date = self._parse_date(date_str)
                if parsed_date:
                    extracted_data['invoice_date'] = parsed_date
                    break
        
        # Extract total amount
        # Look for price tags with amounts
        amount_patterns = [
            r'Invoice Total[:\s]*\$?\s*([\d,]+\.\d{2})',
            r'Balance Due[:\s]*\$?\s*([\d,]+\.\d{2})',
            r'Total[:\s]*\$?\s*([\d,]+\.\d{2})',
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, sequence, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                    extracted_data['total_amount'] = amount
                    break
                except:
                    pass
        
        # If no total found, look for last price tag with 0.00
        if 'total_amount' not in extracted_data:
            price_tags = re.findall(r'<s_price>\s*([\d,]+\.\d{2})', sequence)
            if price_tags:
                try:
                    # Take last price (usually the total)
                    amount = float(price_tags[-1].replace(',', ''))
                    extracted_data['total_amount'] = amount
                except:
                    pass
        
        # Extract currency (default USD)
        extracted_data['currency'] = 'USD'
        
        # Calculate confidence based on how many fields we extracted
        expected_fields = 4  # vendor, invoice_number, date, amount
        extracted_count = len([k for k in extracted_data.keys() if k != 'currency'])
        confidence = (extracted_count / expected_fields) * 100
        
        # Boost confidence if we got the important fields
        if 'vendor_name' in extracted_data:
            confidence += 5
        if 'invoice_number' in extracted_data:
            confidence += 5
        if 'total_amount' in extracted_data:
            confidence += 10
        
        confidence = min(confidence, 100)
        
        return extracted_data, round(confidence, 2)
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date to YYYY-MM-DD format"""
        formats = [
            '%m-%d-%Y',
            '%d-%m-%Y',
            '%Y-%m-%d',
        ]
        
        for fmt in formats:
            try:
                parsed = datetime.strptime(date_str, fmt)
                if 2000 <= parsed.year <= 2030:
                    return parsed.strftime('%Y-%m-%d')
            except:
                continue
        
        return None


# Create singleton
donut_service = DonutService()

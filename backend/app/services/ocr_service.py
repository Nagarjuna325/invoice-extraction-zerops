from pathlib import Path
from app.services.tesseract_service import tesseract_service
import logging
import time

logger = logging.getLogger(__name__)


class OCRService:
    """Main OCR service that handles different OCR engines"""
    
    def process_file(self, file_path: str, ocr_engine: str = "tesseract") -> dict:
        """
        Process file with specified OCR engine
        
        Args:
            file_path: Path to file
            ocr_engine: OCR engine to use
            
        Returns:
            dict with extracted_text, confidence, and processing_time
        """
        start_time = time.time()
        
        logger.info(f"Starting OCR processing: {file_path} with {ocr_engine}")
        
        try:
            if ocr_engine == "tesseract":
                text, ocr_data = tesseract_service.extract_text(file_path)
                confidence = tesseract_service.calculate_confidence(ocr_data)
            else:
                raise ValueError(f"Unsupported OCR engine: {ocr_engine}")
            
            processing_time = int((time.time() - start_time) * 1000)  # milliseconds
            
            result = {
                "extracted_text": text.strip(),
                "ocr_confidence": round(confidence, 2),
                "processing_time_ms": processing_time,
                "ocr_engine": ocr_engine
            }
            
            logger.info(f"OCR complete: {processing_time}ms, confidence: {confidence:.2f}%")
            
            return result
            
        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            raise


# Create singleton instance
ocr_service = OCRService()
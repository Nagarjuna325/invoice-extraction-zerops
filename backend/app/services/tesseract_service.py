import pytesseract
from PIL import Image
from pathlib import Path
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Configure Tesseract path
if settings.TESSERACT_PATH:
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH


class TesseractService:
    """Tesseract OCR service"""
    
    def __init__(self):
        self.lang = settings.TESSERACT_LANG
    
    def extract_text(
        self,
        image_path: str,
        config: str | None = None,
        psm: int | None = None,
        whitelist: str | None = None,
    ) -> tuple[str, dict]:
        """
        Extract text from image using Tesseract
        
        Args:
            image_path: Path to image file
            config: Optional raw Tesseract config string
            psm: Optional page segmentation mode override
            whitelist: Optional character whitelist
            
        Returns:
            (extracted_text, ocr_data_dict)
        """
        try:
            logger.info(f"Processing with Tesseract: {image_path}")
            
            # Open image
            img = Image.open(image_path)

            config_parts = []
            if psm is not None:
                config_parts.append(f"--psm {psm}")
            if whitelist:
                config_parts.append(f"-c tessedit_char_whitelist={whitelist}")
            if config:
                config_parts.append(config)
            config_str = " ".join(config_parts) if config_parts else ""
            
            # Get OCR data with confidence scores
            ocr_data = pytesseract.image_to_data(
                img, 
                lang=self.lang,
                output_type=pytesseract.Output.DICT,
                config=config_str,
            )
            
            # Extract text
            text = pytesseract.image_to_string(
                img,
                lang=self.lang,
                config=config_str,
            )
            
            logger.info(f"Tesseract extraction complete: {len(text)} characters")
            
            return text, ocr_data
            
        except Exception as e:
            logger.error(f"Tesseract extraction failed: {e}")
            raise
    
    def calculate_confidence(self, ocr_data: dict) -> float:
        """
        Calculate average confidence from OCR data
        
        Args:
            ocr_data: OCR data dictionary from Tesseract
            
        Returns:
            Average confidence score (0-100)
        """
        confidences = [
            conf for conf in ocr_data.get('conf', []) 
            if conf != -1  # Filter out invalid confidence scores
        ]
        
        if not confidences:
            return 0.0
        
        return sum(confidences) / len(confidences)


# Create singleton instance
tesseract_service = TesseractService()

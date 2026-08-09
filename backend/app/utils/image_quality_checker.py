"""
Image Quality Checker - PHASE 4
Detects and handles poor quality images before OCR

Features:
- Resolution check (min 300 DPI recommended)
- Blur detection (Laplacian variance)
- Contrast check
- Brightness check
- Auto-enhancement option
"""

import cv2
import numpy as np
from PIL import Image
import logging
from typing import Tuple, Dict, Any, Optional
import os

logger = logging.getLogger(__name__)


class ImageQualityChecker:
    """Check and enhance image quality for better OCR results"""
    
    # Quality thresholds
    MIN_WIDTH = 800          # Minimum width in pixels
    MIN_HEIGHT = 600         # Minimum height in pixels
    MIN_DPI = 150            # Minimum DPI (300 recommended)
    MIN_BLUR_SCORE = 100     # Laplacian variance threshold
    MIN_CONTRAST = 30        # Minimum contrast (0-255 scale)
    MIN_BRIGHTNESS = 50      # Minimum average brightness
    MAX_BRIGHTNESS = 230     # Maximum average brightness
    
    def check_quality(
        self,
        image_path: str,
        auto_enhance: bool = True
    ) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        """
        Check image quality and optionally enhance
        
        Args:
            image_path: Path to image file
            auto_enhance: Whether to auto-enhance poor quality images
            
        Returns:
            (is_acceptable, quality_metrics, enhanced_image_path)
        """
        
        logger.info(f"📸 Checking image quality: {image_path}")
        
        try:
            # Load image with PIL for DPI check
            pil_image = Image.open(image_path)
            
            # Load with OpenCV for quality checks
            cv_image = cv2.imread(image_path)
            
            if cv_image is None:
                logger.error(f"Failed to load image: {image_path}")
                return False, {'error': 'Cannot load image'}, None
            
            # Initialize metrics
            metrics = {}
            issues = []
            
            # 1. Resolution Check
            height, width = cv_image.shape[:2]
            metrics['width'] = width
            metrics['height'] = height
            
            if width < self.MIN_WIDTH or height < self.MIN_HEIGHT:
                issues.append(f"Low resolution: {width}x{height} (min: {self.MIN_WIDTH}x{self.MIN_HEIGHT})")
                logger.warning(f"⚠️  Low resolution: {width}x{height}")
            else:
                logger.info(f"✅ Resolution OK: {width}x{height}")
            
            # 2. DPI Check (if available)
            try:
                dpi = pil_image.info.get('dpi', (72, 72))
                metrics['dpi'] = dpi[0] if isinstance(dpi, tuple) else dpi
                
                if metrics['dpi'] < self.MIN_DPI:
                    issues.append(f"Low DPI: {metrics['dpi']} (min: {self.MIN_DPI})")
                    logger.warning(f"⚠️  Low DPI: {metrics['dpi']}")
                else:
                    logger.info(f"✅ DPI OK: {metrics['dpi']}")
            except:
                metrics['dpi'] = None
                logger.debug("DPI info not available")
            
            # 3. Blur Detection (Laplacian variance)
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            metrics['blur_score'] = round(laplacian_var, 2)
            
            if laplacian_var < self.MIN_BLUR_SCORE:
                issues.append(f"Image is blurry (score: {laplacian_var:.2f}, min: {self.MIN_BLUR_SCORE})")
                logger.warning(f"⚠️  Blurry image: {laplacian_var:.2f}")
            else:
                logger.info(f"✅ Sharpness OK: {laplacian_var:.2f}")
            
            # 4. Contrast Check
            contrast = gray.std()
            metrics['contrast'] = round(contrast, 2)
            
            if contrast < self.MIN_CONTRAST:
                issues.append(f"Low contrast: {contrast:.2f} (min: {self.MIN_CONTRAST})")
                logger.warning(f"⚠️  Low contrast: {contrast:.2f}")
            else:
                logger.info(f"✅ Contrast OK: {contrast:.2f}")
            
            # 5. Brightness Check
            brightness = gray.mean()
            metrics['brightness'] = round(brightness, 2)
            
            if brightness < self.MIN_BRIGHTNESS:
                issues.append(f"Too dark: {brightness:.2f} (min: {self.MIN_BRIGHTNESS})")
                logger.warning(f"⚠️  Too dark: {brightness:.2f}")
            elif brightness > self.MAX_BRIGHTNESS:
                issues.append(f"Too bright: {brightness:.2f} (max: {self.MAX_BRIGHTNESS})")
                logger.warning(f"⚠️  Too bright: {brightness:.2f}")
            else:
                logger.info(f"✅ Brightness OK: {brightness:.2f}")
            
            # Store issues in metrics
            metrics['issues'] = issues
            metrics['issue_count'] = len(issues)
            
            # Determine if acceptable
            is_acceptable = len(issues) == 0
            
            # Auto-enhance if needed
            enhanced_path = None
            if not is_acceptable and auto_enhance:
                logger.info("🔧 Auto-enhancing image...")
                enhanced_path = self._enhance_image(cv_image, image_path, metrics)
                
                if enhanced_path:
                    logger.info(f"✅ Image enhanced: {enhanced_path}")
                    metrics['enhanced'] = True
                else:
                    logger.warning("⚠️  Enhancement failed")
                    metrics['enhanced'] = False
            
            return is_acceptable, metrics, enhanced_path
            
        except Exception as e:
            logger.error(f"Error checking image quality: {e}")
            return False, {'error': str(e)}, None
    
    def _enhance_image(
        self,
        cv_image: np.ndarray,
        original_path: str,
        metrics: Dict[str, Any]
    ) -> Optional[str]:
        """
        Enhance image quality
        
        Applies:
        - Denoising
        - Contrast enhancement (CLAHE)
        - Sharpening
        - Brightness adjustment
        """
        
        try:
            enhanced = cv_image.copy()
            
            # 1. Denoise (if blurry)
            if metrics.get('blur_score', 1000) < self.MIN_BLUR_SCORE:
                enhanced = cv2.fastNlMeansDenoisingColored(enhanced, None, 10, 10, 7, 21)
                logger.debug("Applied denoising")
            
            # 2. Contrast Enhancement (CLAHE)
            if metrics.get('contrast', 100) < self.MIN_CONTRAST:
                lab = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                l = clahe.apply(l)
                
                enhanced = cv2.merge([l, a, b])
                enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
                logger.debug("Applied CLAHE contrast enhancement")
            
            # 3. Brightness Adjustment
            brightness = metrics.get('brightness', 128)
            if brightness < self.MIN_BRIGHTNESS:
                # Too dark - increase brightness
                hsv = cv2.cvtColor(enhanced, cv2.COLOR_BGR2HSV)
                h, s, v = cv2.split(hsv)
                v = cv2.add(v, 30)  # Increase brightness
                enhanced = cv2.merge([h, s, v])
                enhanced = cv2.cvtColor(enhanced, cv2.COLOR_HSV2BGR)
                logger.debug("Increased brightness")
            elif brightness > self.MAX_BRIGHTNESS:
                # Too bright - decrease brightness
                hsv = cv2.cvtColor(enhanced, cv2.COLOR_BGR2HSV)
                h, s, v = cv2.split(hsv)
                v = cv2.subtract(v, 30)  # Decrease brightness
                enhanced = cv2.merge([h, s, v])
                enhanced = cv2.cvtColor(enhanced, cv2.COLOR_HSV2BGR)
                logger.debug("Decreased brightness")
            
            # 4. Sharpening
            kernel = np.array([[-1, -1, -1],
                             [-1,  9, -1],
                             [-1, -1, -1]])
            enhanced = cv2.filter2D(enhanced, -1, kernel)
            logger.debug("Applied sharpening")
            
            # Save enhanced image
            base_path = os.path.dirname(original_path)
            base_name = os.path.basename(original_path)
            name, ext = os.path.splitext(base_name)
            enhanced_path = os.path.join(base_path, f"{name}_enhanced{ext}")
            
            cv2.imwrite(enhanced_path, enhanced)
            
            return enhanced_path
            
        except Exception as e:
            logger.error(f"Error enhancing image: {e}")
            return None


# Singleton
image_quality_checker = ImageQualityChecker()
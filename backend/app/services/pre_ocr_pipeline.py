import logging
import os
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from app.config import settings
from app.utils.image_quality_checker import image_quality_checker
from app.services.ocr_variant_generator import ocr_variant_generator

logger = logging.getLogger(__name__)


@dataclass
class PreOcrResult:
    image_path: str
    temp_files: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PreOcrPipeline:
    SMALL_FONT_MEDIAN_PX = 26
    SMALL_FONT_MIN_COMPONENTS = 25
    DESKEW_MIN_ANGLE = 0.5

    def __init__(self) -> None:
        self.enabled = settings.ENABLE_ADVANCED_OCR_PIPELINE

    def preprocess_image(
        self,
        image_path: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> PreOcrResult:
        if not self.enabled:
            return PreOcrResult(image_path=image_path)

        metadata: Dict[str, Any] = {"pre_ocr_enabled": True, "context": context or {}}

        cv_image = cv2.imread(image_path)
        if cv_image is None:
            logger.warning("Pre-OCR: failed to load image: %s", image_path)
            metadata["error"] = "load_failed"
            return PreOcrResult(image_path=image_path, metadata=metadata)

        height, width = cv_image.shape[:2]
        metadata["source_size"] = {"width": width, "height": height}

        dpi_metadata = self._read_dpi(image_path)
        metadata["dpi_metadata"] = dpi_metadata

        page_info = self._detect_page_size(width, height)
        metadata.update(page_info)

        estimated_dpi, estimate_method = self._estimate_dpi(
            width, height, dpi_metadata, page_info
        )
        metadata["estimated_dpi"] = round(estimated_dpi, 2) if estimated_dpi else None
        metadata["dpi_estimate_method"] = estimate_method

        target_dpi = settings.PRE_OCR_TARGET_DPI
        if estimated_dpi and estimated_dpi >= target_dpi:
            small_font, median_height = self._detect_small_font(cv_image)
            metadata["small_font_detected"] = small_font
            metadata["small_font_median_px"] = median_height
            if small_font:
                target_dpi = settings.PRE_OCR_SMALL_FONT_DPI

        metadata["target_dpi"] = target_dpi

        scale_factor = 1.0
        if estimated_dpi and estimated_dpi > 0:
            scale_factor = target_dpi / float(estimated_dpi)

        if scale_factor < 1.0:
            scale_factor = 1.0
        if abs(scale_factor - 1.0) < 0.05:
            scale_factor = 1.0

        metadata["scale_factor"] = round(scale_factor, 4)
        effective_dpi = None
        if estimated_dpi:
            effective_dpi = estimated_dpi * scale_factor
        metadata["effective_dpi"] = round(effective_dpi, 2) if effective_dpi else None
        logger.info(
            "Pre-OCR: size=%sx%s dpi_meta=%s dpi_est=%s (%s) page=%s target=%s scale=%s",
            width,
            height,
            metadata.get("dpi_metadata"),
            metadata.get("estimated_dpi"),
            metadata.get("dpi_estimate_method"),
            metadata.get("page_size_guess"),
            metadata.get("target_dpi"),
            metadata.get("scale_factor"),
        )
        if metadata.get("estimated_dpi") or metadata.get("effective_dpi"):
            logger.info(
                "Pre-OCR: pre_dpi=%s post_dpi=%s",
                metadata.get("estimated_dpi"),
                metadata.get("effective_dpi"),
            )

        processed = cv_image
        if scale_factor != 1.0:
            processed = self._rescale_image(processed, scale_factor)
            metadata["scaled_size"] = {
                "width": processed.shape[1],
                "height": processed.shape[0],
            }
            logger.info(
                "Pre-OCR: scaled to %sx%s",
                processed.shape[1],
                processed.shape[0],
            )

        deskew_angle = 0.0
        if settings.PRE_OCR_ENABLE_DESKEW:
            processed, deskew_angle = self._deskew_image(processed)

        metadata["deskew_angle"] = round(deskew_angle, 3)
        metadata["deskew_applied"] = abs(deskew_angle) >= self.DESKEW_MIN_ANGLE
        if metadata["deskew_applied"]:
            logger.info("Pre-OCR: deskew applied (angle=%.3f)", deskew_angle)

        changed = scale_factor != 1.0 or metadata["deskew_applied"]
        temp_files: List[str] = []
        output_path = image_path
        if changed:
            output_path = self._save_temp_image(processed)
            metadata["output_path"] = output_path
            temp_files.append(output_path)
            logger.info("Pre-OCR: output image %s", output_path)
        else:
            logger.info("Pre-OCR: no scaling/deskew applied")

        quality_metrics = {}
        enhanced_path = None
        try:
            _, quality_metrics, enhanced_path = image_quality_checker.check_quality(
                output_path,
                auto_enhance=True,
            )
        except Exception as exc:
            logger.warning("Pre-OCR: quality check failed: %s", exc)

        if quality_metrics:
            quality_metrics["pre_dpi_metadata"] = metadata.get("dpi_metadata")
            quality_metrics["pre_dpi_estimated"] = metadata.get("estimated_dpi")
            quality_metrics["post_dpi_effective"] = metadata.get("effective_dpi")
            quality_metrics["pre_ocr_scale_factor"] = metadata.get("scale_factor")
            logger.info(
                "Pre-OCR: post-quality res=%sx%s blur=%s contrast=%s brightness=%s post_dpi=%s",
                quality_metrics.get("width"),
                quality_metrics.get("height"),
                quality_metrics.get("blur_score"),
                quality_metrics.get("contrast"),
                quality_metrics.get("brightness"),
                quality_metrics.get("post_dpi_effective"),
            )

        if enhanced_path:
            output_path = enhanced_path
            if self._is_temp_path(output_path):
                temp_files.append(output_path)
            metadata["enhanced_path"] = output_path
            logger.info("Pre-OCR: enhanced image %s", output_path)

        metadata["quality_metrics"] = quality_metrics
        if settings.PRE_OCR_GENERATE_VARIANTS:
            variant_ctx = {
                "estimated_dpi": metadata.get("estimated_dpi"),
                "target_dpi": metadata.get("target_dpi"),
                "small_font_detected": metadata.get("small_font_detected"),
            }
            variants = ocr_variant_generator.generate(output_path, context=variant_ctx)
            metadata["variants"] = variants.variants
            metadata["variant_metadata"] = variants.metadata
            temp_files.extend(variants.temp_files)
        return PreOcrResult(
            image_path=output_path,
            temp_files=temp_files,
            metadata=metadata,
        )

    def _is_temp_path(self, path: str) -> bool:
        try:
            temp_root = os.path.abspath(tempfile.gettempdir())
            check_path = os.path.abspath(path)
            return check_path.startswith(temp_root)
        except Exception:
            return False

    def _read_dpi(self, image_path: str) -> Optional[float]:
        try:
            with Image.open(image_path) as img:
                dpi = img.info.get("dpi")
                if isinstance(dpi, tuple) and dpi and dpi[0]:
                    return float(dpi[0])
                if isinstance(dpi, (int, float)) and dpi:
                    return float(dpi)
        except Exception:
            return None
        return None

    def _detect_page_size(self, width: int, height: int) -> Dict[str, Any]:
        ratio = max(width, height) / max(1, min(width, height))
        candidates = {
            "letter": (8.5, 11.0),
            "a4": (8.27, 11.69),
        }

        chosen = settings.PRE_OCR_PAGE_SIZE_FALLBACK.lower()
        if settings.PRE_OCR_AUTO_DETECT_PAGE_SIZE:
            best_name = None
            best_diff = None
            for name, dims in candidates.items():
                long_in = max(dims)
                short_in = min(dims)
                page_ratio = long_in / short_in
                diff = abs(ratio - page_ratio)
                if best_diff is None or diff < best_diff:
                    best_diff = diff
                    best_name = name
            if best_name:
                chosen = best_name

        if chosen not in candidates:
            chosen = "letter"

        long_in = max(candidates[chosen])
        short_in = min(candidates[chosen])

        return {
            "page_size_guess": chosen,
            "page_ratio": round(ratio, 4),
            "page_size_ratio": round(long_in / short_in, 4),
            "page_size_inches": {"long": long_in, "short": short_in},
        }

    def _estimate_dpi(
        self,
        width: int,
        height: int,
        dpi_metadata: Optional[float],
        page_info: Dict[str, Any],
    ) -> Tuple[Optional[float], str]:
        if dpi_metadata and dpi_metadata > 0:
            return dpi_metadata, "metadata"

        page_inches = page_info.get("page_size_inches") or {}
        long_in = page_inches.get("long")
        short_in = page_inches.get("short")
        if not long_in or not short_in:
            return None, "unknown"

        long_px = max(width, height)
        short_px = min(width, height)
        dpi_long = long_px / long_in
        dpi_short = short_px / short_in
        return min(dpi_long, dpi_short), "page_size"

    def _detect_small_font(self, cv_image: np.ndarray) -> Tuple[bool, Optional[float]]:
        try:
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (3, 3), 0)
            _, thresh = cv2.threshold(
                blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
            )
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)

            contours, _ = cv2.findContours(
                cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            heights = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if h < 6 or h > 80:
                    continue
                if w < 2 or w > 200:
                    continue
                if w * h < 15:
                    continue
                heights.append(h)

            if len(heights) < self.SMALL_FONT_MIN_COMPONENTS:
                return False, None

            median_height = float(np.median(heights))
            if median_height < self.SMALL_FONT_MEDIAN_PX:
                logger.info("Pre-OCR: small font detected (median_px=%.1f)", median_height)
            return median_height < self.SMALL_FONT_MEDIAN_PX, median_height
        except Exception:
            return False, None

    def _rescale_image(self, cv_image: np.ndarray, scale_factor: float) -> np.ndarray:
        height, width = cv_image.shape[:2]
        new_width = max(1, int(round(width * scale_factor)))
        new_height = max(1, int(round(height * scale_factor)))
        return cv2.resize(
            cv_image,
            (new_width, new_height),
            interpolation=cv2.INTER_CUBIC,
        )

    def _deskew_image(self, cv_image: np.ndarray) -> Tuple[np.ndarray, float]:
        try:
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (3, 3), 0)
            _, thresh = cv2.threshold(
                blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
            )
            coords = cv2.findNonZero(thresh)
            if coords is None:
                return cv_image, 0.0

            angle = cv2.minAreaRect(coords)[-1]
            if angle > 45:
                angle = 90 - angle
            elif angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle

            if abs(angle) > 80:
                return cv_image, 0.0

            if abs(angle) < self.DESKEW_MIN_ANGLE:
                return cv_image, 0.0

            height, width = cv_image.shape[:2]
            center = (width // 2, height // 2)
            matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(
                cv_image,
                matrix,
                (width, height),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE,
            )
            return rotated, float(angle)
        except Exception:
            return cv_image, 0.0

    def _save_temp_image(self, cv_image: np.ndarray) -> str:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        temp_path = temp_file.name
        temp_file.close()
        cv2.imwrite(temp_path, cv_image)
        return temp_path


pre_ocr_pipeline = PreOcrPipeline()

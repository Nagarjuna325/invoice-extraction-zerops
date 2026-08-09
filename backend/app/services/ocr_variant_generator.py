import logging
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class VariantResult:
    base_path: str
    variants: Dict[str, str] = field(default_factory=dict)
    temp_files: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class OcrVariantGenerator:
    def generate(self, image_path: str, context: Optional[Dict[str, Any]] = None) -> VariantResult:
        cv_image = cv2.imread(image_path)
        if cv_image is None:
            logger.warning("Variant generation skipped (load failed): %s", image_path)
            return VariantResult(base_path=image_path)

        ctx = context or {}
        variants: Dict[str, str] = {}
        temp_files: List[str] = []

        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        variants["v1_gray"] = self._write_image(gray)
        temp_files.append(variants["v1_gray"])

        v2 = self._apply_clahe(cv_image)
        variants["v2_clahe"] = self._write_image(v2)
        temp_files.append(variants["v2_clahe"])

        v3 = self._apply_binarize(gray)
        variants["v3_binarized"] = self._write_image(v3)
        temp_files.append(variants["v3_binarized"])

        v4_path = self._build_superres_variant(cv_image, ctx)
        if v4_path:
            variants["v4_superres_clahe"] = v4_path
            temp_files.append(v4_path)

        metadata = {
            "variant_count": len(variants),
            "variant_names": list(variants.keys()),
        }
        logger.info("Pre-OCR: variants generated %s", list(variants.keys()))
        return VariantResult(
            base_path=image_path,
            variants=variants,
            temp_files=temp_files,
            metadata=metadata,
        )

    def _apply_clahe(self, cv_image: np.ndarray) -> np.ndarray:
        lab = cv2.cvtColor(cv_image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        merged = cv2.merge([l, a, b])
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    def _apply_binarize(self, gray: np.ndarray) -> np.ndarray:
        blur = cv2.GaussianBlur(gray, (3, 3), 0)
        binary = cv2.adaptiveThreshold(
            blur,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            11,
        )
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
        return cleaned

    def _build_superres_variant(self, cv_image: np.ndarray, ctx: Dict[str, Any]) -> Optional[str]:
        estimated_dpi = ctx.get("estimated_dpi")
        target_dpi = ctx.get("target_dpi")
        small_font = ctx.get("small_font_detected")

        use_superres = False
        if estimated_dpi and target_dpi:
            use_superres = estimated_dpi < target_dpi
        if small_font:
            use_superres = True

        if not use_superres:
            return None

        height, width = cv_image.shape[:2]
        scale = settings.PRE_OCR_VARIANT_SUPERRES_SCALE
        max_dim = settings.PRE_OCR_VARIANT_MAX_DIM
        if max(width, height) * scale > max_dim:
            scale = max_dim / max(width, height)

        if scale <= 1.0:
            return None

        resized = cv2.resize(
            cv_image,
            (int(round(width * scale)), int(round(height * scale))),
            interpolation=cv2.INTER_CUBIC,
        )
        enhanced = self._apply_clahe(resized)
        return self._write_image(enhanced)

    def _write_image(self, cv_image: np.ndarray) -> str:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        temp_path = temp_file.name
        temp_file.close()
        cv2.imwrite(temp_path, cv_image)
        return temp_path


ocr_variant_generator = OcrVariantGenerator()

import logging
import os
import re
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from app.config import settings
from app.services.tesseract_service import tesseract_service

logger = logging.getLogger(__name__)


@dataclass
class FooterTotalResult:
    value: Optional[float]
    confidence: float
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    debug: Dict[str, Any] = field(default_factory=dict)


class FooterTotalExtractor:
    def extract(self, image_path: str) -> FooterTotalResult:
        if not settings.ENABLE_FOOTER_TOTAL_EXTRACT:
            return FooterTotalResult(None, 0.0, debug={"enabled": False})

        cv_image = cv2.imread(image_path)
        if cv_image is None:
            logger.warning("Footer total: failed to load image: %s", image_path)
            return FooterTotalResult(None, 0.0, debug={"error": "load_failed"})

        crop, crop_meta = self._crop_footer(cv_image)
        if crop is None:
            return FooterTotalResult(None, 0.0, debug={"error": "crop_failed"})

        processed = self._preprocess_crop(crop)
        temp_path = None
        try:
            temp_path = self._write_temp_image(processed)
            text, data = tesseract_service.extract_text(
                temp_path,
                psm=6,
                whitelist=settings.FOOTER_TOTAL_WHITELIST,
            )
        except Exception as exc:
            logger.warning("Footer total OCR failed: %s", exc)
            return FooterTotalResult(None, 0.0, debug={"error": str(exc), **crop_meta})
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    logger.debug("Footer total temp cleanup failed: %s", temp_path)

        candidates = self._extract_candidates(
            data,
            offset_x=crop_meta["x0"],
            offset_y=crop_meta["y0"],
            require_decimal=settings.FOOTER_TOTAL_REQUIRE_DECIMAL,
        )
        best = self._select_best(candidates, cv_image.shape[1], cv_image.shape[0])
        if best:
            logger.info(
                "Footer total extracted: %s (conf %.1f)",
                best["value"],
                best["confidence"],
            )
            return FooterTotalResult(
                value=best["value"],
                confidence=best["confidence"],
                candidates=candidates,
                debug={
                    "crop": crop_meta,
                    "raw_text": text.strip(),
                    "selected": best,
                },
            )

        logger.info("Footer total: no candidate found")
        return FooterTotalResult(
            value=None,
            confidence=0.0,
            candidates=candidates,
            debug={
                "crop": crop_meta,
                "raw_text": text.strip(),
            },
        )

    def _crop_footer(self, cv_image: np.ndarray) -> Tuple[Optional[np.ndarray], Dict[str, Any]]:
        height, width = cv_image.shape[:2]
        y0 = int(height * settings.FOOTER_REGION_Y_MIN)
        x0 = int(width * settings.FOOTER_REGION_X_MIN)
        y0 = max(0, min(height - 1, y0))
        x0 = max(0, min(width - 1, x0))
        crop = cv_image[y0:height, x0:width]
        if crop.size == 0:
            return None, {}
        return crop, {"x0": x0, "y0": y0, "width": width, "height": height}

    def _preprocess_crop(self, crop: np.ndarray) -> np.ndarray:
        scale = settings.FOOTER_TOTAL_SUPERRES_SCALE
        if scale and scale != 1.0:
            crop = cv2.resize(
                crop,
                (int(crop.shape[1] * scale), int(crop.shape[0] * scale)),
                interpolation=cv2.INTER_CUBIC,
            )
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        blur = cv2.GaussianBlur(enhanced, (3, 3), 0)
        _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh

    def _write_temp_image(self, cv_image: np.ndarray) -> str:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        temp_path = temp_file.name
        temp_file.close()
        cv2.imwrite(temp_path, cv_image)
        return temp_path

    def _extract_candidates(
        self,
        ocr_data: Dict[str, Any],
        offset_x: int,
        offset_y: int,
        require_decimal: bool,
    ) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        texts = ocr_data.get("text", []) or []
        confs = ocr_data.get("conf", []) or []
        lefts = ocr_data.get("left", []) or []
        tops = ocr_data.get("top", []) or []
        widths = ocr_data.get("width", []) or []
        heights = ocr_data.get("height", []) or []

        for idx, raw in enumerate(texts):
            if not raw or str(raw).strip() == "":
                continue
            cleaned = re.sub(r"[^\d.,]", "", str(raw))
            if not cleaned:
                continue
            normalized = cleaned.replace(",", "")
            if require_decimal and not re.fullmatch(r"\d+\.\d{2}", normalized):
                continue
            if not require_decimal and not re.fullmatch(r"\d+(?:\.\d{2})?", normalized):
                continue

            try:
                value = float(normalized)
            except Exception:
                continue

            conf = 0.0
            if idx < len(confs):
                try:
                    conf = float(confs[idx])
                except Exception:
                    conf = 0.0

            x = int(lefts[idx]) if idx < len(lefts) else 0
            y = int(tops[idx]) if idx < len(tops) else 0
            w = int(widths[idx]) if idx < len(widths) else 0
            h = int(heights[idx]) if idx < len(heights) else 0

            candidates.append(
                {
                    "value": value,
                    "raw": str(raw),
                    "confidence": max(0.0, min(conf, 100.0)),
                    "bbox": [x + offset_x, y + offset_y, x + w + offset_x, y + h + offset_y],
                }
            )

        return candidates

    def _select_best(
        self,
        candidates: List[Dict[str, Any]],
        image_width: int,
        image_height: int,
    ) -> Optional[Dict[str, Any]]:
        if not candidates:
            return None

        def score(candidate: Dict[str, Any]) -> float:
            x1, y1, x2, y2 = candidate["bbox"]
            x_center = (x1 + x2) / 2.0
            y_center = (y1 + y2) / 2.0
            x_score = x_center / max(1.0, image_width)
            y_score = y_center / max(1.0, image_height)
            return y_score * 0.7 + x_score * 0.3

        candidates_sorted = sorted(candidates, key=score, reverse=True)
        return candidates_sorted[0]


footer_total_extractor = FooterTotalExtractor()

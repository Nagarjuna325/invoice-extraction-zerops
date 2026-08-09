import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class OcrToken:
    text: str
    conf: Optional[float]
    bbox: Optional[List[float]]
    bbox_px: Optional[List[int]]
    source: str
    page: int = 1


@dataclass
class OcrOutput:
    text: str
    tokens: List[OcrToken] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OcrMatrixResult:
    outputs: Dict[str, OcrOutput] = field(default_factory=dict)
    raw_texts: Dict[str, str] = field(default_factory=dict)
    tokens: Dict[str, List[OcrToken]] = field(default_factory=dict)


class OcrMatrixRunner:
    def __init__(self) -> None:
        self._paddle = None
        self._trocr_processor = None
        self._trocr_model = None

    def run(self, variants: Dict[str, str]) -> OcrMatrixResult:
        outputs: Dict[str, OcrOutput] = {}

        if settings.OCR_MATRIX_ENABLE_PADDLE:
            for key in ("v1_gray", "v2_clahe", "v4_superres_clahe"):
                image_path = variants.get(key)
                if image_path:
                    outputs[f"paddle_{key}"] = self._run_paddle(image_path)

        if settings.OCR_MATRIX_ENABLE_TESSERACT:
            image_path = variants.get("v3_binarized")
            if image_path:
                outputs["tesseract_v3_binarized"] = self._run_tesseract(image_path)

        if settings.OCR_MATRIX_ENABLE_TROCR:
            image_path = variants.get("v1_gray")
            if image_path:
                outputs["trocr_v1_gray"] = self._run_trocr(image_path)

        raw_texts = {key: output.text for key, output in outputs.items()}
        tokens = {key: output.tokens for key, output in outputs.items()}
        return OcrMatrixResult(outputs=outputs, raw_texts=raw_texts, tokens=tokens)

    def _run_paddle(self, image_path: str) -> OcrOutput:
        try:
            if self._paddle is None:
                from paddleocr import PaddleOCR  # type: ignore

                try:
                    self._paddle = PaddleOCR(
                        use_angle_cls=True,
                        lang=settings.OCR_MATRIX_PADDLE_LANG,
                        show_log=False,
                    )
                except Exception:
                    self._paddle = PaddleOCR(
                        use_angle_cls=True,
                        lang=settings.OCR_MATRIX_PADDLE_LANG,
                    )

            result = self._paddle.ocr(image_path, cls=True)
            tokens: List[OcrToken] = []
            lines: List[str] = []
            for page in result or []:
                for entry in page:
                    bbox, (text, conf) = entry
                    lines.append(text)
                    bbox_px = [int(bbox[0][0]), int(bbox[0][1]), int(bbox[2][0]), int(bbox[2][1])]
                    tokens.append(
                        OcrToken(
                            text=text,
                            conf=float(conf) if conf is not None else None,
                            bbox=None,
                            bbox_px=bbox_px,
                            source="paddle",
                        )
                    )
            return OcrOutput(text="\n".join(lines), tokens=tokens, meta={"engine": "paddle"})
        except Exception as exc:
            logger.warning("PaddleOCR failed for %s: %s", image_path, exc)
            return OcrOutput(text="", tokens=[], meta={"engine": "paddle", "error": str(exc)})

    def _run_tesseract(self, image_path: str) -> OcrOutput:
        try:
            from app.services.tesseract_service import tesseract_service

            text, ocr_data = tesseract_service.extract_text(image_path)
            tokens: List[OcrToken] = []
            texts = ocr_data.get("text", []) or []
            confs = ocr_data.get("conf", []) or []
            lefts = ocr_data.get("left", []) or []
            tops = ocr_data.get("top", []) or []
            widths = ocr_data.get("width", []) or []
            heights = ocr_data.get("height", []) or []
            for idx, raw in enumerate(texts):
                if not raw or str(raw).strip() == "":
                    continue
                try:
                    x = int(lefts[idx])
                    y = int(tops[idx])
                    w = int(widths[idx])
                    h = int(heights[idx])
                    conf_val = None
                    if idx < len(confs):
                        try:
                            conf_val = float(confs[idx])
                        except Exception:
                            conf_val = None
                    tokens.append(
                        OcrToken(
                            text=str(raw).strip(),
                            conf=conf_val,
                            bbox=None,
                            bbox_px=[x, y, x + w, y + h],
                            source="tesseract",
                        )
                    )
                except Exception:
                    continue
            return OcrOutput(text=text, tokens=tokens, meta={"engine": "tesseract"})
        except Exception as exc:
            logger.warning("Tesseract (matrix) failed for %s: %s", image_path, exc)
            return OcrOutput(text="", tokens=[], meta={"engine": "tesseract", "error": str(exc)})

    def _run_trocr(self, image_path: str) -> OcrOutput:
        try:
            if self._trocr_model is None or self._trocr_processor is None:
                from transformers import TrOCRProcessor, VisionEncoderDecoderModel

                self._trocr_processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-printed")
                self._trocr_model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-printed")

            from PIL import Image

            image = Image.open(image_path).convert("RGB")
            pixel_values = self._trocr_processor(images=image, return_tensors="pt").pixel_values
            generated_ids = self._trocr_model.generate(pixel_values)
            text = self._trocr_processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            return OcrOutput(text=text or "", tokens=[], meta={"engine": "trocr"})
        except Exception as exc:
            logger.warning("TrOCR failed for %s: %s", image_path, exc)
            return OcrOutput(text="", tokens=[], meta={"engine": "trocr", "error": str(exc)})


ocr_matrix_runner = OcrMatrixRunner()

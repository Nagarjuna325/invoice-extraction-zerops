import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.services.ocr_matrix import OcrToken
from app.utils.field_validators import validator

logger = logging.getLogger(__name__)


@dataclass
class ColumnDef:
    name: str
    center_x: float


@dataclass
class ParsedRow:
    description: str
    quantity: Optional[float]
    unit_price: Optional[float]
    amount: Optional[float]
    amount_text: str
    amount_conf: float
    confidence: float
    y_center: float
    y_min: float
    y_max: float
    merge_only: bool = False


class LineItemParser:
    HEADER_KEYWORDS = {
        "qty": ["qty", "quantity", "qnty", "q'ty", "quant"],
        "description": ["description", "desc", "item", "product", "part", "name", "details"],
        "unit_price": ["unit", "price", "rate", "cost", "unitprice"],
        "amount": ["amount", "amt", "total", "ext", "extended", "line"],
    }

    SUMMARY_KEYWORDS = ["subtotal", "total", "tax", "balance", "amount due"]

    def parse(self, tokens: List[OcrToken], image_path: Optional[str] = None) -> Dict[str, Any]:
        if not tokens:
            return {"line_items": [], "confidence": 0.0, "metadata": {}}

        lines = self._group_tokens_by_line(tokens)
        if not lines:
            return {"line_items": [], "confidence": 0.0, "metadata": {}}

        page_width = max(token.bbox_px[2] for line in lines for token in line if token.bbox_px)
        header_idx = self._find_header_line(lines)
        metadata = {
            "header_detected": header_idx is not None,
            "columns": [],
        }
        if settings.LINEITEM_REQUIRE_HEADER and header_idx is None:
            metadata["skipped_reason"] = "header_required"
            return {"line_items": [], "confidence": 0.0, "metadata": metadata}

        columns = self._build_columns(lines, header_idx, page_width)
        column_bounds = self._column_bounds(columns)
        amount_bounds = self._amount_column_bounds(column_bounds, page_width)

        start_idx = header_idx + 1 if header_idx is not None else 0
        parsed_rows: List[ParsedRow] = []

        for line in lines[start_idx:]:
            line_text = self._line_text(line)
            if self._is_summary_line(line_text):
                continue
            row = self._parse_line(line, columns, column_bounds)
            if not row:
                continue
            if row.merge_only:
                if not settings.LINEITEM_MERGE_MULTILINE or not parsed_rows:
                    continue
                prev = parsed_rows[-1]
                if settings.LINEITEM_MERGE_REQUIRE_AMOUNT and prev.amount is None:
                    continue
                if abs(row.y_center - prev.y_center) <= settings.LINEITEM_MERGE_MAX_GAP_PX:
                    if row.description:
                        prev.description = f"{prev.description} {row.description}".strip()
                    continue
                continue
            parsed_rows.append(row)

        if settings.ENABLE_AMOUNT_COLUMN_REOCR and amount_bounds and parsed_rows and image_path:
            self._reocr_amount_column(parsed_rows, amount_bounds, image_path)

        valid_rows = [
            row
            for row in parsed_rows
            if row.amount is not None and self._amount_format_ok(row.amount_text)
        ]
        if settings.LINEITEM_MIN_VALID_ROWS and len(valid_rows) < settings.LINEITEM_MIN_VALID_ROWS:
            metadata["skipped_reason"] = "insufficient_valid_rows"
            metadata["valid_row_count"] = len(valid_rows)
            metadata["min_valid_rows"] = settings.LINEITEM_MIN_VALID_ROWS
            return {"line_items": [], "confidence": 0.0, "metadata": metadata}

        line_items = []
        for row in parsed_rows:
            if settings.LINEITEM_SKIP_NONE_AMOUNT and row.amount is None:
                continue
            if row.amount is None and not row.description:
                continue
            line_items.append(
                {
                    "description": row.description,
                    "quantity": row.quantity,
                    "unit_price": row.unit_price,
                    "amount": row.amount,
                    "confidence": round(row.confidence, 3),
                }
            )

        confidence = 0.0
        if parsed_rows:
            confidence = sum(row.confidence for row in parsed_rows) / len(parsed_rows)

        metadata["columns"] = [col.name for col in columns]
        metadata["valid_row_count"] = len(valid_rows)
        metadata["min_valid_rows"] = settings.LINEITEM_MIN_VALID_ROWS

        return {"line_items": line_items, "confidence": confidence, "metadata": metadata}

    def _find_header_line(self, lines: List[List[OcrToken]]) -> Optional[int]:
        best_idx = None
        best_score = 0
        for idx, line in enumerate(lines[:8]):
            matches = self._header_matches(line)
            score = len(matches)
            if score > best_score and score >= 2:
                best_score = score
                best_idx = idx
        return best_idx

    def _header_matches(self, line: List[OcrToken]) -> List[str]:
        matched = []
        for token in line:
            normalized = self._normalize_token_text(token.text)
            if not normalized:
                continue
            for col, keywords in self.HEADER_KEYWORDS.items():
                if normalized in keywords or any(normalized.startswith(word) for word in keywords):
                    matched.append(col)
                    break
        return list(set(matched))

    def _build_columns(
        self, lines: List[List[OcrToken]], header_idx: Optional[int], page_width: float
    ) -> List[ColumnDef]:
        columns: List[ColumnDef] = []
        if header_idx is not None:
            header_line = lines[header_idx]
            for token in header_line:
                normalized = self._normalize_token_text(token.text)
                if not normalized or not token.bbox_px:
                    continue
                for col, keywords in self.HEADER_KEYWORDS.items():
                    if normalized in keywords or any(normalized.startswith(word) for word in keywords):
                        columns.append(ColumnDef(name=col, center_x=self._x_center(token)))
                        break

        if not columns:
            numeric_clusters = self._numeric_clusters(lines, page_width)
            if numeric_clusters:
                columns = self._columns_from_clusters(numeric_clusters)

        if not any(col.name == "amount" for col in columns):
            numeric_clusters = self._numeric_clusters(lines, page_width)
            if numeric_clusters:
                amount_center = numeric_clusters[-1]["center"]
                columns.append(ColumnDef(name="amount", center_x=amount_center))

        columns = sorted(columns, key=lambda col: col.center_x)
        return columns

    def _columns_from_clusters(self, clusters: List[Dict[str, Any]]) -> List[ColumnDef]:
        columns: List[ColumnDef] = []
        if not clusters:
            return columns
        clusters_sorted = sorted(clusters, key=lambda item: item["center"])
        if len(clusters_sorted) >= 1:
            columns.append(ColumnDef(name="qty", center_x=clusters_sorted[0]["center"]))
        if len(clusters_sorted) >= 2:
            columns.append(ColumnDef(name="unit_price", center_x=clusters_sorted[-2]["center"]))
        columns.append(ColumnDef(name="amount", center_x=clusters_sorted[-1]["center"]))
        return columns

    def _numeric_clusters(self, lines: List[List[OcrToken]], page_width: float) -> List[Dict[str, Any]]:
        numeric_tokens = [
            token
            for line in lines
            for token in line
            if token.bbox_px and re.search(r"\d", token.text)
        ]
        if not numeric_tokens:
            return []
        centers = sorted(self._x_center(token) for token in numeric_tokens)
        if not centers:
            return []
        threshold = max(24.0, page_width * 0.04)
        clusters: List[List[float]] = []
        current: List[float] = [centers[0]]
        for center in centers[1:]:
            if abs(center - current[-1]) <= threshold:
                current.append(center)
            else:
                clusters.append(current)
                current = [center]
        clusters.append(current)
        return [{"center": sum(cluster) / len(cluster)} for cluster in clusters]

    def _column_bounds(self, columns: List[ColumnDef]) -> List[Tuple[float, float, ColumnDef]]:
        if not columns:
            return []
        bounds: List[Tuple[float, float, ColumnDef]] = []
        centers = [col.center_x for col in columns]
        for idx, col in enumerate(columns):
            left = (centers[idx - 1] + centers[idx]) / 2 if idx > 0 else -float("inf")
            right = (centers[idx] + centers[idx + 1]) / 2 if idx + 1 < len(centers) else float("inf")
            bounds.append((left, right, col))
        return bounds

    def _parse_line(
        self,
        line: List[OcrToken],
        columns: List[ColumnDef],
        column_bounds: List[Tuple[float, float, ColumnDef]],
    ) -> Optional[ParsedRow]:
        if not line:
            return None
        line_text = self._line_text(line)
        y_center = self._line_y_center(line)
        y_min = min(token.bbox_px[1] for token in line if token.bbox_px)
        y_max = max(token.bbox_px[3] for token in line if token.bbox_px)
        numeric_tokens = [token for token in line if re.search(r"\d", token.text)]
        if not numeric_tokens and line_text.strip():
            return ParsedRow(
                description=line_text.strip(),
                quantity=None,
                unit_price=None,
                amount=None,
                amount_text="",
                amount_conf=0.0,
                confidence=0.4,
                y_center=y_center,
                y_min=y_min,
                y_max=y_max,
                merge_only=True,
            )
        if not numeric_tokens:
            return None

        desc_tokens = []
        amounts: Dict[str, str] = {}
        confidences: List[float] = []
        amount_confidences: List[float] = []

        amount_bound = self._amount_left_bound(columns)
        for token in line:
            if not token.bbox_px:
                continue
            if re.search(r"\d", token.text):
                col_name = self._column_for_token(token, column_bounds)
                amounts.setdefault(col_name, "")
                amounts[col_name] = f"{amounts[col_name]} {token.text}".strip()
                confidences.append(self._norm_conf(token.conf))
                if col_name == "amount":
                    amount_confidences.append(self._norm_conf(token.conf))
            else:
                if amount_bound is None or token.bbox_px[2] < amount_bound:
                    desc_tokens.append(token.text)

        description = " ".join(desc_tokens).strip()
        qty = self._parse_quantity(amounts.get("qty"))
        unit_price = self._parse_amount(amounts.get("unit_price"))
        amount_text = amounts.get("amount", "")
        amount = self._parse_amount(amount_text)
        confidence = sum(confidences) / len(confidences) if confidences else 0.6
        amount_conf = (
            sum(amount_confidences) / len(amount_confidences) if amount_confidences else confidence
        )

        return ParsedRow(
            description=description,
            quantity=qty,
            unit_price=unit_price,
            amount=amount,
            amount_text=amount_text,
            amount_conf=amount_conf,
            confidence=confidence,
            y_center=y_center,
            y_min=y_min,
            y_max=y_max,
        )

    def _column_for_token(self, token: OcrToken, bounds: List[Tuple[float, float, ColumnDef]]) -> str:
        center = self._x_center(token)
        for left, right, col in bounds:
            if left <= center <= right:
                return col.name
        return "amount"

    def _amount_left_bound(self, columns: List[ColumnDef]) -> Optional[float]:
        for idx, col in enumerate(columns):
            if col.name == "amount":
                if idx == 0:
                    return None
                return (columns[idx - 1].center_x + col.center_x) / 2
        return None

    def _amount_column_bounds(
        self, column_bounds: List[Tuple[float, float, ColumnDef]], page_width: float
    ) -> Optional[Tuple[float, float]]:
        for left, right, col in column_bounds:
            if col.name == "amount":
                left_bound = 0 if left == -float("inf") else max(0.0, left)
                right_bound = page_width if right == float("inf") else min(page_width, right)
                return left_bound, right_bound
        return None

    def _parse_amount(self, value: Optional[str]) -> Optional[float]:
        if not value:
            return None
        if not self._amount_format_ok(value):
            return None
        try:
            return float(validator.normalize_decimal_format(value))
        except Exception:
            return None

    def _parse_quantity(self, value: Optional[str]) -> Optional[float]:
        if not value:
            return None
        match = re.search(r"\d+(?:[.,]\d+)?", value)
        if not match:
            return None
        try:
            return float(match.group(0))
        except Exception:
            return None

    def _is_summary_line(self, text: str) -> bool:
        lower = text.lower()
        return any(keyword in lower for keyword in self.SUMMARY_KEYWORDS)

    def _group_tokens_by_line(self, tokens: List[OcrToken]) -> List[List[OcrToken]]:
        tokens_with_boxes = [t for t in tokens if t.bbox_px]
        tokens_sorted = sorted(tokens_with_boxes, key=lambda t: (self._y_center(t), self._x_center(t)))
        lines: List[List[OcrToken]] = []
        line_centers: List[float] = []
        for token in tokens_sorted:
            y_center = self._y_center(token)
            height = self._height(token)
            assigned = False
            for idx, center in enumerate(line_centers):
                if abs(y_center - center) <= max(height * 0.6, 8):
                    lines[idx].append(token)
                    line_centers[idx] = (line_centers[idx] + y_center) / 2.0
                    assigned = True
                    break
            if not assigned:
                lines.append([token])
                line_centers.append(y_center)
        for line in lines:
            line.sort(key=lambda t: self._x_center(t))
        return lines

    def _line_text(self, line: List[OcrToken]) -> str:
        return " ".join(token.text for token in line if token.text)

    def _reocr_amount_column(
        self, rows: List[ParsedRow], amount_bounds: Tuple[float, float], image_path: str
    ) -> None:
        try:
            from PIL import Image
            import pytesseract
        except Exception as exc:
            logger.warning("Amount re-OCR disabled (missing libs): %s", exc)
            return

        if settings.TESSERACT_PATH:
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH

        config = "--psm 7 -c tessedit_char_whitelist=0123456789.,"

        try:
            image = Image.open(image_path)
        except Exception as exc:
            logger.warning("Amount re-OCR skipped (image open failed): %s", exc)
            return

        img_width, img_height = image.size

        for row in rows:
            if row.amount_conf >= settings.LINEITEM_REOCR_MIN_CONF and self._has_decimal(row.amount_text):
                continue
            if row.y_max <= row.y_min:
                continue
            crop_box = (
                max(0, int(amount_bounds[0] - 2)),
                max(0, int(row.y_min - 2)),
                min(img_width, int(amount_bounds[1] + 2)),
                min(img_height, int(row.y_max + 2)),
            )
            crop = image.crop(crop_box)
            if settings.ENABLE_SUPERRES_CROPS and (
                row.amount is None or row.amount_conf < settings.LINEITEM_SUPERRES_MIN_CONF
            ):
                crop = self._superres_crop(crop)
            ocr_data = pytesseract.image_to_data(
                crop,
                lang=settings.TESSERACT_LANG,
                output_type=pytesseract.Output.DICT,
                config=config,
            )
            text = pytesseract.image_to_string(
                crop,
                lang=settings.TESSERACT_LANG,
                config=config,
            )

            candidate = self._best_amount_from_text(text)
            if not candidate:
                continue
            if not self._amount_format_ok(candidate):
                continue

            try:
                value = float(validator.normalize_decimal_format(candidate))
            except Exception:
                continue

            reocr_conf = self._avg_conf_from_data(ocr_data)
            if value and (row.amount is None or reocr_conf > row.amount_conf + 0.05):
                row.amount = value
                row.amount_text = candidate
                row.amount_conf = reocr_conf
                row.confidence = max(row.confidence, reocr_conf)

    def _best_amount_from_text(self, text: str) -> str:
        candidates = re.findall(r"\d+[.,]\d{2}", text)
        return candidates[-1] if candidates else ""

    def _avg_conf_from_data(self, ocr_data: Dict[str, Any]) -> float:
        confs = []
        for conf in ocr_data.get("conf", []) or []:
            try:
                conf_val = float(conf)
            except Exception:
                continue
            if conf_val < 0:
                continue
            confs.append(conf_val / 100.0 if conf_val > 1.0 else conf_val)
        if not confs:
            return 0.5
        return sum(confs) / len(confs)

    def _has_decimal(self, text: str) -> bool:
        return bool(re.search(r"[.,]\d{2}\b", text))

    def _amount_format_ok(self, text: str) -> bool:
        if not settings.LINEITEM_REQUIRE_DECIMAL:
            return True
        if self._has_decimal(text):
            return True
        if settings.LINEITEM_ALLOW_NO_DECIMAL_WITH_CURRENCY:
            return bool(re.search(r"[$€£₹]", text))
        return False

    def _superres_crop(self, crop: Any) -> Any:
        if settings.LINEITEM_SUPERRES_METHOD.lower() != "opencv":
            logger.info("Super-res method '%s' not available, using OpenCV.", settings.LINEITEM_SUPERRES_METHOD)
        try:
            import cv2
            import numpy as np
        except Exception as exc:
            logger.warning("Super-res skipped (OpenCV missing): %s", exc)
            return crop

        scale = max(1.0, settings.LINEITEM_SUPERRES_SCALE)
        if scale == 1.0:
            return crop

        img = np.array(crop)
        height, width = img.shape[:2]
        resized = cv2.resize(
            img,
            (int(width * scale), int(height * scale)),
            interpolation=cv2.INTER_CUBIC,
        )
        try:
            from PIL import Image

            return Image.fromarray(resized)
        except Exception:
            return resized

    def _normalize_token_text(self, text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", text.lower())

    def _norm_conf(self, conf: Optional[float]) -> float:
        if conf is None:
            return 0.6
        conf_val = float(conf)
        if conf_val > 1.0:
            conf_val = conf_val / 100.0
        return max(0.0, min(conf_val, 1.0))

    def _x_center(self, token: OcrToken) -> float:
        return (token.bbox_px[0] + token.bbox_px[2]) / 2.0

    def _y_center(self, token: OcrToken) -> float:
        return (token.bbox_px[1] + token.bbox_px[3]) / 2.0

    def _height(self, token: OcrToken) -> float:
        return abs(token.bbox_px[3] - token.bbox_px[1])

    def _line_y_center(self, line: List[OcrToken]) -> float:
        centers = [self._y_center(token) for token in line if token.bbox_px]
        if not centers:
            return 0.0
        return sum(centers) / len(centers)


line_item_parser = LineItemParser()

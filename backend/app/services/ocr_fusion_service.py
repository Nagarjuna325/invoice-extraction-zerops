import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.config import settings
from app.services.ocr_matrix import OcrMatrixResult, OcrOutput, OcrToken
from app.utils.label_matcher import label_matcher

logger = logging.getLogger(__name__)


@dataclass
class FieldSpec:
    name: str
    label_patterns: List[re.Pattern]
    label_phrases: List[List[str]]
    value_type: str
    label_keywords: List[str]
    allow_next_line: bool = True
    blacklist_terms: Optional[List[str]] = None


@dataclass
class FieldCandidate:
    value: str
    score: float
    source: str
    raw: str


class OcrFusionService:
    def __init__(self) -> None:
        self.specs = self._build_specs()
        self.label_matcher = label_matcher

    def fuse(self, matrix_result: OcrMatrixResult) -> Tuple[Dict[str, Any], float, Dict[str, Any]]:
        candidates: Dict[str, List[FieldCandidate]] = {}
        label_debug: Optional[List[Dict[str, Any]]] = [] if settings.LABEL_MATCH_DEBUG else None

        for source_name, output in matrix_result.outputs.items():
            engine = self._engine_from_source(source_name)
            weight = self._engine_weight(engine)
            extracted = self._extract_from_output(output, source_name, weight, label_debug)
            for field, cand in extracted.items():
                candidates.setdefault(field, []).append(cand)

        fused_fields: Dict[str, Any] = {}
        per_field_scores: List[float] = []
        debug: Dict[str, Any] = {}

        for field, items in candidates.items():
            if not items:
                continue
            best = self._pick_best_candidate(field, items)
            fused_fields[field] = best.value
            per_field_scores.append(best.score)
            debug[field] = [
                {"value": cand.value, "score": round(cand.score, 3), "source": cand.source}
                for cand in items
            ]

        overall_confidence = 0.0
        if per_field_scores:
            overall_confidence = min(95.0, max(50.0, (sum(per_field_scores) / len(per_field_scores)) * 100.0))

        if label_debug is not None:
            debug["label_matches"] = label_debug
            if settings.LABEL_MATCH_DEBUG:
                self._log_label_matches(label_debug)

        return fused_fields, overall_confidence, debug

    def _build_specs(self) -> List[FieldSpec]:
        return [
            FieldSpec(
                name="invoice_number",
                label_patterns=[
                    re.compile(r"\binvoice\s*(number|no|#|id)\b", re.IGNORECASE),
                    re.compile(r"\binv\s*(number|no|#)\b", re.IGNORECASE),
                ],
                label_phrases=[
                    ["invoice", "number"],
                    ["invoice", "no"],
                    ["invoice", "id"],
                    ["inv", "number"],
                    ["inv", "no"],
                ],
                value_type="id",
                label_keywords=["invoice", "inv", "number", "no", "#", "id"],
            ),
            FieldSpec(
                name="po_number",
                label_patterns=[
                    re.compile(r"\b(purchase\s*order|po\s*(number|#)|p\.?o\.?)\b", re.IGNORECASE),
                    re.compile(r"\byour\s*purchase\s*order\b", re.IGNORECASE),
                ],
                label_phrases=[
                    ["your", "purchase", "order"],
                    ["purchase", "order"],
                    ["po"],
                    ["p", "o"],
                ],
                value_type="id",
                label_keywords=["purchase", "order", "po", "p.o.", "your"],
            ),
            FieldSpec(
                name="invoice_date",
                label_patterns=[
                    re.compile(r"\binvoice\s*date\b", re.IGNORECASE),
                    re.compile(r"\binv\s*date\b", re.IGNORECASE),
                    re.compile(r"\bdate\b", re.IGNORECASE),
                ],
                label_phrases=[
                    ["invoice", "date"],
                    ["inv", "date"],
                ],
                value_type="date",
                label_keywords=["invoice", "inv", "date"],
                blacklist_terms=["printed"],
            ),
            FieldSpec(
                name="due_date",
                label_patterns=[
                    re.compile(r"\bdue\s*date\b", re.IGNORECASE),
                    re.compile(r"\bpayment\s*due\b", re.IGNORECASE),
                    re.compile(r"\bpay\s*by\b", re.IGNORECASE),
                ],
                label_phrases=[
                    ["due", "date"],
                    ["payment", "due"],
                    ["pay", "by"],
                ],
                value_type="date",
                label_keywords=["due", "payment", "pay"],
            ),
            FieldSpec(
                name="total_amount",
                label_patterns=[
                    re.compile(r"\b(total\s*amount|total\s*due|grand\s*total|amount\s*due|balance\s*due|total)\b", re.IGNORECASE),
                ],
                label_phrases=[
                    ["total", "amount"],
                    ["total", "due"],
                    ["grand", "total"],
                    ["amount", "due"],
                    ["balance", "due"],
                    ["total"],
                ],
                value_type="amount",
                label_keywords=["total", "amount", "balance", "grand", "due"],
            ),
        ]

    def _extract_from_output(
        self,
        output: OcrOutput,
        source_name: str,
        weight: float,
        label_debug: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, FieldCandidate]:
        candidates: Dict[str, FieldCandidate] = {}
        tokens = output.tokens or []
        if tokens:
            lines = self._group_tokens_by_line(tokens)
            anchored_dates: Dict[str, FieldCandidate] = {}
            if settings.ENABLE_LABEL_ANCHORED_DATES:
                anchored_dates = self._extract_label_anchored_dates(
                    lines,
                    source_name,
                    weight,
                    label_debug,
                )
            if settings.ENABLE_LABEL_ANCHORED_DATES_TEXT and output.text:
                anchored_dates_text = self._extract_label_anchored_dates_text(
                    output.text, source_name, weight
                )
                for field, cand in anchored_dates_text.items():
                    existing = anchored_dates.get(field)
                    if existing is None or cand.score > existing.score:
                        anchored_dates[field] = cand
            fallback_candidates = self._extract_from_due_line(lines, source_name, weight)
            for spec in self.specs:
                cand = self._extract_from_lines(lines, spec, source_name, weight, label_debug)
                if cand:
                    candidates[spec.name] = cand
            for field, cand in fallback_candidates.items():
                if field not in candidates:
                    candidates[field] = cand
            if anchored_dates:
                for field, cand in anchored_dates.items():
                    if settings.LABEL_DATE_PREFER_ANCHORED or field not in candidates:
                        candidates[field] = cand
                    elif cand.score > candidates[field].score:
                        candidates[field] = cand
            if settings.OCR_FUSION_TOTAL_FALLBACK and "total_amount" not in candidates:
                total_cand = self._extract_total_fallback(lines, source_name, weight)
                if total_cand:
                    candidates["total_amount"] = total_cand
        else:
            text = output.text or ""
            anchored_fields = set()
            if settings.ENABLE_LABEL_ANCHORED_DATES_TEXT and text:
                anchored_dates_text = self._extract_label_anchored_dates_text(
                    text, source_name, weight
                )
                for field, cand in anchored_dates_text.items():
                    candidates[field] = cand
                anchored_fields = set(anchored_dates_text.keys())
            for spec in self.specs:
                cand = self._extract_from_text(text, spec, source_name, weight)
                if cand:
                    if (
                        spec.value_type == "date"
                        and settings.LABEL_DATE_PREFER_ANCHORED
                        and spec.name in anchored_fields
                    ):
                        continue
                    existing = candidates.get(spec.name)
                    if existing is None or cand.score > existing.score:
                        candidates[spec.name] = cand
        return candidates

    def _extract_label_anchored_dates(
        self,
        lines: List[List[OcrToken]],
        source_name: str,
        weight: float,
        label_debug: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, FieldCandidate]:
        date_specs = {spec.name: spec for spec in self.specs if spec.value_type == "date"}
        if not date_specs:
            return {}

        best: Dict[str, FieldCandidate] = {}
        max_x = settings.LABEL_DATE_MAX_X_DIST_PX
        max_y = settings.LABEL_DATE_MAX_Y_GAP_PX
        min_conf = settings.LABEL_DATE_MIN_CONF

        for idx, line in enumerate(lines):
            line_text = self._line_text(line)
            line_lower = line_text.lower()
            for field_name, spec in date_specs.items():
                if spec.blacklist_terms and any(term in line_lower for term in spec.blacklist_terms):
                    continue
                match_result = self._label_match(
                    line_text,
                    spec,
                    source_name=source_name,
                    line_index=idx,
                    label_debug=label_debug,
                )
                if not match_result.matched:
                    continue
                label_tokens = self._find_label_tokens(line, spec)
                if not label_tokens:
                    continue

                label_right = max(t.bbox_px[2] for t in label_tokens if t.bbox_px)
                label_y = self._line_y_center(label_tokens)
                candidate_tokens = [
                    t
                    for t in self._tokens_right_of_label(line, label_tokens)
                    if t.bbox_px and self._x_center(t) <= label_right + max_x
                ]
                candidate_tokens = [t for t in candidate_tokens if self._looks_like_date_token(t.text)]
                raw = self._tokens_text(candidate_tokens)
                date_candidate = self._extract_date_candidate(raw) if raw else ""
                used_tokens = candidate_tokens

                if not date_candidate and spec.allow_next_line:
                    for next_idx in range(idx + 1, len(lines)):
                        next_line = lines[next_idx]
                        next_y = self._line_y_center(next_line)
                        if next_y - label_y > max_y:
                            break
                        next_text = self._line_text(next_line)
                        if self._line_has_date_label(next_text, date_specs.values()):
                            continue
                        next_candidates = [
                            t
                            for t in next_line
                            if t.bbox_px
                            and self._x_center(t) >= label_right - 8
                            and self._x_center(t) <= label_right + max_x
                        ]
                        next_candidates = [t for t in next_candidates if self._looks_like_date_token(t.text)]
                        raw = self._tokens_text(next_candidates)
                        date_candidate = self._extract_date_candidate(raw) if raw else ""
                        used_tokens = next_candidates
                        if date_candidate:
                            break

                if not date_candidate:
                    continue

                normalized = self._normalize_value(date_candidate, "date")
                if not normalized:
                    continue

                conf = self._tokens_confidence(used_tokens)
                if conf < min_conf:
                    continue
                score = conf * weight

                existing = best.get(field_name)
                if existing is None or score > existing.score:
                    best[field_name] = FieldCandidate(
                        value=normalized,
                        score=score,
                        source=source_name,
                        raw=date_candidate,
                    )

        return best

    def _extract_label_anchored_dates_text(
        self,
        text: str,
        source_name: str,
        weight: float,
    ) -> Dict[str, FieldCandidate]:
        if not text:
            return {}
        date_specs = {spec.name: spec for spec in self.specs if spec.value_type == "date"}
        if not date_specs:
            return {}

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return {}

        lookahead = max(0, settings.LABEL_DATE_TEXT_LOOKAHEAD_LINES)
        base_score = settings.LABEL_DATE_TEXT_SCORE
        best: Dict[str, FieldCandidate] = {}

        for idx, line in enumerate(lines):
            line_lower = line.lower()
            for field_name, spec in date_specs.items():
                if spec.blacklist_terms and any(term in line_lower for term in spec.blacklist_terms):
                    continue
                match = None
                for pattern in spec.label_patterns:
                    match = pattern.search(line)
                    if match:
                        break
                if not match:
                    continue

                tail = line[match.end():].strip()
                date_candidate = self._extract_date_candidate(tail) if tail else ""
                used_same_line = bool(date_candidate)

                if not date_candidate and spec.allow_next_line and lookahead > 0:
                    for next_idx in range(idx + 1, min(len(lines), idx + 1 + lookahead)):
                        next_line = lines[next_idx].strip()
                        if not next_line:
                            continue
                        if self._line_has_date_label(next_line, date_specs.values()):
                            continue
                        next_lower = next_line.lower()
                        if spec.blacklist_terms and any(term in next_lower for term in spec.blacklist_terms):
                            continue
                        date_candidate = self._extract_date_candidate(next_line)
                        if date_candidate:
                            break

                if not date_candidate:
                    continue

                normalized = self._normalize_value(date_candidate, "date")
                if not normalized:
                    continue

                score = base_score * weight
                if used_same_line:
                    score += 0.1 * weight

                existing = best.get(field_name)
                if existing is None or score > existing.score:
                    best[field_name] = FieldCandidate(
                        value=normalized,
                        score=score,
                        source=source_name,
                        raw=date_candidate,
                    )

        return best

    def _group_tokens_by_line(self, tokens: List[OcrToken]) -> List[List[OcrToken]]:
        tokens_with_boxes = [t for t in tokens if t.bbox_px]
        if not tokens_with_boxes:
            return []
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

    def _extract_from_lines(
        self,
        lines: List[List[OcrToken]],
        spec: FieldSpec,
        source_name: str,
        weight: float,
        label_debug: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[FieldCandidate]:
        for idx, line in enumerate(lines):
            line_text = self._line_text(line)
            if spec.blacklist_terms and any(term in line_text.lower() for term in spec.blacklist_terms):
                continue
            match_result = self._label_match(
                line_text,
                spec,
                source_name=source_name,
                line_index=idx,
                label_debug=label_debug,
            )
            if not match_result.matched:
                continue

            label_tokens = self._find_label_tokens(line, spec)
            if not label_tokens:
                continue

            bounds = self._column_bounds_for_label(line, label_tokens)
            candidate_tokens = self._tokens_right_of_label(line, label_tokens, bounds)
            if not candidate_tokens and spec.allow_next_line and idx + 1 < len(lines):
                candidate_tokens = self._tokens_below_label(lines[idx + 1], label_tokens, bounds)

            if not candidate_tokens:
                continue

            raw = self._tokens_text(candidate_tokens)
            value = self._normalize_value(raw, spec.value_type)
            if not value:
                continue

            conf = self._tokens_confidence(candidate_tokens)
            score = conf * weight
            return FieldCandidate(value=value, score=score, source=source_name, raw=raw)

        return None

    def _extract_from_text(
        self,
        text: str,
        spec: FieldSpec,
        source_name: str,
        weight: float,
    ) -> Optional[FieldCandidate]:
        if not text:
            return None
        for pattern in spec.label_patterns:
            match = pattern.search(text)
            if not match:
                continue
            tail = text[match.end(): match.end() + 80]
            value = self._normalize_value(tail, spec.value_type)
            if value:
                return FieldCandidate(value=value, score=0.4 * weight, source=source_name, raw=tail.strip())
        return None

    def _find_label_tokens(self, line: List[OcrToken], spec: FieldSpec) -> List[OcrToken]:
        phrase_tokens = self._find_label_phrase_tokens(line, spec.label_phrases)
        if phrase_tokens:
            return phrase_tokens
        return self._find_label_keyword_tokens(line, spec.label_keywords)

    def _find_label_phrase_tokens(self, line: List[OcrToken], phrases: List[List[str]]) -> List[OcrToken]:
        if not phrases:
            return []
        indexed_words: List[Tuple[int, str]] = []
        for idx, token in enumerate(line):
            normalized = self._normalize_token_text(token.text)
            if normalized:
                indexed_words.append((idx, normalized))
        for phrase in phrases:
            normalized_phrase = [self._normalize_token_text(word) for word in phrase if word]
            if not normalized_phrase:
                continue
            for start in range(0, len(indexed_words) - len(normalized_phrase) + 1):
                matched = True
                for offset, expected in enumerate(normalized_phrase):
                    if indexed_words[start + offset][1] != expected:
                        matched = False
                        break
                if matched:
                    indices = [indexed_words[start + offset][0] for offset in range(len(normalized_phrase))]
                    return [line[i] for i in indices]
        return []

    def _find_label_keyword_tokens(self, line: List[OcrToken], keywords: List[str]) -> List[OcrToken]:
        label_tokens = []
        keyword_set = {kw.replace(".", "").lower() for kw in keywords}
        for token in line:
            normalized = self._normalize_token_text(token.text)
            if not normalized:
                continue
            if normalized in keyword_set:
                label_tokens.append(token)
        return label_tokens

    def _tokens_right_of_label(
        self,
        line: List[OcrToken],
        label_tokens: List[OcrToken],
        bounds: Optional[Tuple[float, float]] = None,
    ) -> List[OcrToken]:
        label_right = max(t.bbox_px[2] for t in label_tokens if t.bbox_px)
        candidates = [t for t in line if t.bbox_px and t.bbox_px[0] >= label_right - 4]
        if bounds:
            left_bound, right_bound = bounds
            candidates = [
                t
                for t in candidates
                if self._x_center(t) >= left_bound - 6 and self._x_center(t) <= right_bound + 6
            ]
        return candidates

    def _tokens_below_label(
        self,
        line: List[OcrToken],
        label_tokens: List[OcrToken],
        bounds: Optional[Tuple[float, float]] = None,
    ) -> List[OcrToken]:
        if bounds:
            left_bound, right_bound = bounds
            return [
                t
                for t in line
                if t.bbox_px and left_bound - 8 <= self._x_center(t) <= right_bound + 8
            ]
        label_left = min(t.bbox_px[0] for t in label_tokens if t.bbox_px)
        label_right = max(t.bbox_px[2] for t in label_tokens if t.bbox_px)
        extended_right = label_right + 120
        return [t for t in line if t.bbox_px and label_left - 10 <= t.bbox_px[0] <= extended_right]

    def _line_text(self, line: List[OcrToken]) -> str:
        return " ".join(t.text for t in line)

    def _tokens_text(self, tokens: List[OcrToken]) -> str:
        return " ".join(t.text for t in tokens)

    def _tokens_confidence(self, tokens: List[OcrToken]) -> float:
        confs = []
        for token in tokens:
            if token.conf is None:
                continue
            conf_val = float(token.conf)
            if conf_val > 1.0:
                conf_val = conf_val / 100.0
            confs.append(conf_val)
        if not confs:
            return 0.4
        return sum(confs) / len(confs)

    def _looks_like_date_token(self, text: str) -> bool:
        if not text:
            return False
        lower = text.lower()
        if any(ch.isdigit() for ch in lower):
            return True
        return any(month in lower for month in ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"))

    def _line_has_date_label(self, text: str, specs: Iterable[FieldSpec]) -> bool:
        if not text:
            return False
        for spec in specs:
            if spec.blacklist_terms and any(term in text.lower() for term in spec.blacklist_terms):
                continue
            match_result = self._label_match(text, spec)
            if match_result.matched:
                return True
        return False

    def _label_match(
        self,
        line_text: str,
        spec: FieldSpec,
        source_name: Optional[str] = None,
        line_index: Optional[int] = None,
        label_debug: Optional[List[Dict[str, Any]]] = None,
    ) -> "LabelMatchResult":
        match_result = self.label_matcher.match_line(line_text, spec.name, spec.label_patterns)
        if label_debug is not None and match_result.matched:
            label_debug.append(
                {
                    "source": source_name or "",
                    "line_index": line_index,
                    "field": spec.name,
                    "method": match_result.method,
                    "score": round(match_result.score, 4),
                    "rule_score": match_result.rule_score,
                    "semantic_score": match_result.semantic_score,
                    "line_text": self._truncate_text(line_text, 160),
                }
            )
        return match_result

    def _truncate_text(self, text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return f"{text[:limit]}..."

    def _log_label_matches(self, matches: List[Dict[str, Any]]) -> None:
        if not matches:
            logger.info("[label-matcher] No label matches detected")
            return
        logger.info("[label-matcher] %s label matches detected", len(matches))
        for match in matches:
            logger.info(
                "[label-matcher] field=%s method=%s score=%.4f rule=%s semantic=%s source=%s line=%s text=%s",
                match.get("field"),
                match.get("method"),
                match.get("score", 0.0),
                match.get("rule_score"),
                match.get("semantic_score"),
                match.get("source"),
                match.get("line_index"),
                match.get("line_text"),
            )

    def _extract_total_fallback(
        self,
        lines: List[List[OcrToken]],
        source_name: str,
        weight: float,
    ) -> Optional[FieldCandidate]:
        page_width, page_height = self._page_dimensions(lines)
        if not page_width or not page_height:
            return None

        bottom_y = page_height * (1.0 - settings.OCR_FUSION_TOTAL_REGION_Y)
        right_x = page_width * settings.OCR_FUSION_TOTAL_REGION_X

        best: Optional[FieldCandidate] = None
        best_score = 0.0

        for idx, line in enumerate(lines):
            line_y = self._line_y_center(line)
            if line_y < bottom_y:
                continue

            line_text = self._line_text(line)
            line_lower = line_text.lower()

            amount_text = self._amount_text_in_region(line, right_x)
            if not amount_text and ("total" in line_lower or "amount" in line_lower):
                next_line = lines[idx + 1] if idx + 1 < len(lines) else None
                if next_line:
                    amount_text = self._amount_text_in_region(next_line, right_x)

            if not amount_text:
                continue

            for candidate in self._amount_candidates(amount_text):
                if not self._looks_like_total(candidate):
                    continue
                normalized = self._normalize_amount(candidate)
                if not normalized:
                    continue
                try:
                    value = float(normalized)
                except Exception:
                    continue
                if value <= 0:
                    continue

                score = self._tokens_confidence(line) * weight
                if "total" in line_lower or "amount" in line_lower:
                    score += 0.4
                if self._has_two_decimals(candidate):
                    score += 0.3
                if self._has_currency_symbol(candidate, line_text):
                    score += 0.2
                if self._line_right_bias(line, right_x):
                    score += 0.2

                if score > best_score:
                    best_score = score
                    best = FieldCandidate(
                        value=str(value),
                        score=score,
                        source=source_name,
                        raw=candidate,
                    )

        return best

    def _amount_text_in_region(self, line: List[OcrToken], right_x: float) -> str:
        tokens = [
            t for t in line if t.bbox_px and self._x_center(t) >= right_x and re.search(r"\d", t.text)
        ]
        if not tokens:
            return ""
        return self._tokens_text(tokens)

    def _amount_candidates(self, text: str) -> List[str]:
        return [m.group(0) for m in re.finditer(r"[-+]?\d+(?:[.,]\d{2,3})+", text)]

    def _looks_like_total(self, candidate: str) -> bool:
        if self._has_two_decimals(candidate):
            return True
        if "$" in candidate:
            return True
        return False

    def _has_two_decimals(self, text: str) -> bool:
        return bool(re.search(r"[.,]\d{2}\b", text))

    def _has_currency_symbol(self, candidate: str, line_text: str) -> bool:
        return "$" in candidate or "$" in line_text

    def _line_right_bias(self, line: List[OcrToken], right_x: float) -> bool:
        centers = [self._x_center(token) for token in line if token.bbox_px]
        if not centers:
            return False
        return max(centers) >= right_x

    def _page_dimensions(self, lines: List[List[OcrToken]]) -> Tuple[float, float]:
        max_x = 0.0
        max_y = 0.0
        for line in lines:
            for token in line:
                if not token.bbox_px:
                    continue
                max_x = max(max_x, token.bbox_px[2])
                max_y = max(max_y, token.bbox_px[3])
        return max_x, max_y

    def _line_y_center(self, line: List[OcrToken]) -> float:
        centers = [self._y_center(token) for token in line if token.bbox_px]
        if not centers:
            return 0.0
        return sum(centers) / len(centers)

    def _extract_from_due_line(
        self,
        lines: List[List[OcrToken]],
        source_name: str,
        weight: float,
    ) -> Dict[str, FieldCandidate]:
        """
        Fallback parsing for lines that contain due terms and date/id columns.
        """
        for idx, line in enumerate(lines):
            line_text = self._line_text(line)
            upper = line_text.upper()
            if not re.search(r"D\s*U\s*E", upper):
                continue

            date_candidate = self._extract_date_candidate(line_text)
            if not date_candidate:
                neighbor_indices = [idx - 1, idx + 1]
                for neighbor_idx in neighbor_indices:
                    if neighbor_idx < 0 or neighbor_idx >= len(lines):
                        continue
                    neighbor_text = self._line_text(lines[neighbor_idx])
                    if "printed" in neighbor_text.lower():
                        continue
                    date_candidate = self._extract_date_candidate(neighbor_text)
                    if date_candidate:
                        break
            inv_candidate = self._extract_invoice_candidate_from_line(line_text)
            po_candidate = self._extract_po_candidate_from_line(line_text, upper)

            conf = self._tokens_confidence(line)
            result: Dict[str, FieldCandidate] = {}

            if date_candidate:
                normalized = self._normalize_value(date_candidate, "date")
                if normalized:
                    result["invoice_date"] = FieldCandidate(
                        value=normalized,
                        score=conf * weight,
                        source=source_name,
                        raw=date_candidate,
                    )

            if inv_candidate:
                normalized = self._normalize_value(inv_candidate, "id")
                if normalized:
                    result["invoice_number"] = FieldCandidate(
                        value=normalized,
                        score=conf * weight,
                        source=source_name,
                        raw=inv_candidate,
                    )

            if po_candidate:
                normalized = self._normalize_value(po_candidate, "id")
                if normalized:
                    result["po_number"] = FieldCandidate(
                        value=normalized,
                        score=conf * weight,
                        source=source_name,
                        raw=po_candidate,
                    )

            if result:
                return result

        return {}

    def _extract_date_candidate(self, line_text: str) -> str:
        month_date = self._parse_month_date(line_text)
        if month_date:
            return month_date
        match = re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", line_text)
        if match:
            return match.group(0)
        match = re.search(r"\b\d{1,2}\s+\d{1,2}[/-]\d{2,4}\b", line_text)
        if match:
            return match.group(0).replace(" ", "/")
        match = re.search(r"\b\d{1,2}\s+\d{1,2}\s+\d{2,4}\b", line_text)
        if match:
            parts = match.group(0).split()
            if len(parts) == 3:
                return "/".join(parts)
        collapsed = re.sub(r"[^0-9]+", "/", line_text).strip("/")
        if collapsed:
            for match in re.finditer(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", collapsed):
                month = int(match.group(1))
                day = int(match.group(2))
                if 1 <= month <= 12 and 1 <= day <= 31:
                    return f"{match.group(1)}/{match.group(2)}/{match.group(3)}"
            for match in re.finditer(r"(\d{4})/(\d{1,2})/(\d{1,2})", collapsed):
                month = int(match.group(2))
                day = int(match.group(3))
                if 1 <= month <= 12 and 1 <= day <= 31:
                    return f"{match.group(2)}/{match.group(3)}/{match.group(1)}"
        return ""

    def _parse_month_date(self, text: str) -> str:
        if not text:
            return ""
        lower = text.lower()
        month_map = {
            "jan": 1,
            "feb": 2,
            "mar": 3,
            "apr": 4,
            "may": 5,
            "jun": 6,
            "jul": 7,
            "aug": 8,
            "sep": 9,
            "oct": 10,
            "nov": 11,
            "dec": 12,
        }
        month_pattern = (
            r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|"
            r"jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|"
            r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
        )

        pattern = re.compile(
            rf"\b(?P<month>{month_pattern})\s+(?P<day>\d{{1,2}})"
            r"(?:st|nd|rd|th)?[,\s]+(?P<year>\d{2,4})\b",
            re.IGNORECASE,
        )
        match = pattern.search(lower)
        if match:
            month = month_map.get(match.group("month")[:3])
            if month:
                day = int(match.group("day"))
                year = self._normalize_year(match.group("year"))
                return f"{month:02d}/{day:02d}/{year}"

        pattern = re.compile(
            rf"\b(?P<day>\d{{1,2}})(?:st|nd|rd|th)?\s+(?P<month>{month_pattern})"
            r"[,\s]+(?P<year>\d{2,4})\b",
            re.IGNORECASE,
        )
        match = pattern.search(lower)
        if match:
            month = month_map.get(match.group("month")[:3])
            if month:
                day = int(match.group("day"))
                year = self._normalize_year(match.group("year"))
                return f"{month:02d}/{day:02d}/{year}"
        return ""

    def _normalize_year(self, year_text: str) -> str:
        try:
            year = int(year_text)
        except Exception:
            return year_text
        if year < 100:
            year += 2000 if year < 50 else 1900
        return f"{year:04d}"

    def _extract_invoice_candidate_from_line(self, line_text: str) -> str:
        if "|" in line_text:
            tail = line_text.split("|")[-1]
            match = re.search(r"\b[A-Za-z0-9]{5,}\b", tail)
            if match:
                return match.group(0)
        match = re.search(r"\b\d{5,}\b", line_text)
        return match.group(0) if match else ""

    def _extract_po_candidate_from_line(self, line_text: str, upper: str) -> str:
        due_idx = upper.find("DUE")
        head = line_text[:due_idx] if due_idx > 0 else line_text
        match = re.search(r"\b[A-Za-z0-9]{3,}-[A-Za-z0-9]{1,}\b", head)
        if match:
            return match.group(0)
        match = re.search(r"\b[A-Za-z]\d{5,}\b", head)
        if match:
            return match.group(0)
        match = re.search(r"\b\d{5,}\b", head)
        return match.group(0) if match else ""

    def _normalize_value(self, raw: str, value_type: str) -> str:
        if not raw:
            return ""
        if value_type == "amount":
            return self._normalize_amount(raw)
        if value_type == "date":
            return self._normalize_date(raw)
        if value_type == "id":
            return self._normalize_id(raw)
        return raw.strip()

    def _normalize_amount(self, raw: str) -> str:
        cleaned = raw.replace(",", ".")
        cleaned = self._normalize_numeric_text(cleaned)
        match = re.search(r"[-+]?[0-9]+(?:\\.[0-9]{1,2})?", cleaned)
        return match.group(0) if match else ""

    def _normalize_date(self, raw: str) -> str:
        month_date = self._parse_month_date(raw)
        if month_date:
            return month_date
        cleaned = self._normalize_numeric_text(raw)
        match = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", cleaned)
        if match:
            return match.group(0)
        collapsed = re.sub(r"[^0-9]+", "/", cleaned).strip("/")
        if collapsed:
            match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", collapsed)
            if match:
                return f"{match.group(1)}/{match.group(2)}/{match.group(3)}"
            match = re.search(r"(\d{4})/(\d{1,2})/(\d{1,2})", collapsed)
            if match:
                return f"{match.group(2)}/{match.group(3)}/{match.group(1)}"
        return ""

    def _normalize_id(self, raw: str) -> str:
        cleaned = self._normalize_numeric_text(raw)
        cleaned = re.sub(r"[^A-Za-z0-9\\-_/]", "", cleaned)
        if any(ch.isdigit() for ch in cleaned):
            return cleaned
        return ""

    def _normalize_numeric_text(self, text: str) -> str:
        replacements = {
            "O": "0",
            "o": "0",
            "I": "1",
            "l": "1",
            "S": "5",
            "B": "8",
        }
        for src, dst in replacements.items():
            text = text.replace(src, dst)
        return text

    def _engine_from_source(self, source_name: str) -> str:
        if source_name.startswith("paddle"):
            return "paddle"
        if source_name.startswith("tesseract"):
            return "tesseract"
        if source_name.startswith("trocr"):
            return "trocr"
        return "unknown"

    def _engine_weight(self, engine: str) -> float:
        if engine == "paddle":
            return settings.OCR_FUSION_WEIGHT_PADDLE
        if engine == "tesseract":
            return settings.OCR_FUSION_WEIGHT_TESSERACT
        if engine == "trocr":
            return settings.OCR_FUSION_WEIGHT_TROCR
        return 0.7

    def _column_bounds_for_label(
        self,
        line: List[OcrToken],
        label_tokens: List[OcrToken],
    ) -> Optional[Tuple[float, float]]:
        if not label_tokens:
            return None
        label_center = self._tokens_center(label_tokens)
        label_left = min(t.bbox_px[0] for t in label_tokens if t.bbox_px)
        label_right = max(t.bbox_px[2] for t in label_tokens if t.bbox_px)

        spans: List[Dict[str, float]] = []
        for spec in self.specs:
            tokens = self._find_label_tokens(line, spec)
            if not tokens:
                continue
            center = self._tokens_center(tokens)
            left = min(t.bbox_px[0] for t in tokens if t.bbox_px)
            right = max(t.bbox_px[2] for t in tokens if t.bbox_px)
            if abs(center - label_center) <= 4:
                continue
            spans.append({"center": center, "left": left, "right": right})

        spans.append({"center": label_center, "left": label_left, "right": label_right, "current": True})
        spans_sorted = sorted(spans, key=lambda item: item["center"])

        current_index = None
        for idx, span in enumerate(spans_sorted):
            if span.get("current"):
                current_index = idx
                break
        if current_index is None:
            return None

        prev_center = spans_sorted[current_index - 1]["center"] if current_index > 0 else None
        next_center = (
            spans_sorted[current_index + 1]["center"] if current_index + 1 < len(spans_sorted) else None
        )

        left_bound = (prev_center + label_center) / 2 if prev_center is not None else label_left - 20
        right_bound = (label_center + next_center) / 2 if next_center is not None else label_right + 160
        return left_bound, right_bound

    def _x_center(self, token: OcrToken) -> float:
        return (token.bbox_px[0] + token.bbox_px[2]) / 2.0

    def _y_center(self, token: OcrToken) -> float:
        return (token.bbox_px[1] + token.bbox_px[3]) / 2.0

    def _height(self, token: OcrToken) -> float:
        return abs(token.bbox_px[3] - token.bbox_px[1])

    def _tokens_center(self, tokens: List[OcrToken]) -> float:
        centers = [self._x_center(token) for token in tokens if token.bbox_px]
        if not centers:
            return 0.0
        return sum(centers) / len(centers)

    def _normalize_token_text(self, text: str) -> str:
        return re.sub(r"[^a-z0-9#]+", "", text.lower())

    def _pick_best_candidate(self, field: str, candidates: List[FieldCandidate]) -> FieldCandidate:
        if not candidates:
            return FieldCandidate(value="", score=0.0, source="none", raw="")
        return max(candidates, key=lambda c: c.score)


ocr_fusion_service = OcrFusionService()

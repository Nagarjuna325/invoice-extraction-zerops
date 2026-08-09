
"""
Template learning service - SMART CORRUPTION DETECTION
Detects ML extraction errors without hardcoded ranges
"""
import re
import hashlib
import statistics
from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy.orm import Session
from datetime import datetime
import json
import logging

import pytesseract
from pytesseract import Output
from PIL import Image, ImageOps

from app.config import settings
from app.services.correction_service import correction_service
from app.models.vendor import Vendor
from app.models.correction import Correction

logger = logging.getLogger(__name__)


class TemplateService:
    """
    Template learning service - SMART validation
    Detects corruption patterns, doesn't enforce hardcoded rules
    """

    def build_template_voter_fields(
        self,
        template_data: Dict[str, Any],
        image_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build a lightweight voter payload from template_data.

        Uses the first available example for each field in field_patterns.
        If bbox anchors are present and an image_path is provided, re-OCR those
        regions with strict parsing (dates/amounts/ids) to override bad full-page OCR.
        """
        template = self._normalize_template_data(template_data)
        if not template or "field_patterns" not in template:
            return {}

        voter_fields: Dict[str, Any] = {}
        for field, pattern in template.get("field_patterns", {}).items():
            if field.startswith("_"):
                continue

            candidate = None
            bbox = pattern.get("bbox")

            # Prefer anchored re-OCR when bbox + image_path is available
            if bbox and image_path:
                candidate = self._extract_field_from_bbox(
                    field_name=field,
                    pattern=pattern,
                    image_path=image_path,
                )

            # Fallback to stored examples
            if candidate is None:
                examples = pattern.get("examples") or []
                candidate = examples[0] if examples else pattern.get("example")

            if candidate is not None:
                voter_fields[field] = candidate
        return voter_fields

    def update_template_from_corrections(
        self,
        db: Session,
        vendor_id: int,
        min_samples: int = 1,
        max_examples: int = 5,
    ) -> Optional[Dict[str, Any]]:
        """
        Rebuild template_data from recorded corrections.
        Returns the updated template_data if written, otherwise None.
        """
        corrections: List[Correction] = correction_service.get_corrections_for_vendor(db, vendor_id)
        if len(corrections) < min_samples:
            logger.info(f"[template-refresh] Not enough corrections for vendor {vendor_id} (have {len(corrections)})")
            return None

        field_patterns: Dict[str, Any] = {}
        for row in corrections:
            field = row.field_name
            value = row.corrected_value
            if field.startswith("_"):
                continue

            pattern = field_patterns.setdefault(
                field,
                {
                    "examples": [],
                    "occurrences": 0,
                    "bboxes": [],
                    "page_numbers": [],
                },
            )
            examples = pattern.get("examples", [])
            if value not in examples:
                examples.append(value)
                if len(examples) > max_examples:
                    examples = examples[-max_examples:]
                pattern["examples"] = examples
            pattern["occurrences"] = pattern.get("occurrences", 0) + 1
            if row.bbox:
                try:
                    bbox = row.bbox if isinstance(row.bbox, list) else json.loads(row.bbox)
                    if isinstance(bbox, list) and len(bbox) == 4:
                        pattern["bboxes"].append(bbox)
                except Exception:
                    pass
            if row.page_number is not None:
                pattern["page_numbers"].append(row.page_number)

        vendor: Vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
        if not vendor:
            logger.warning(f"[template-refresh] Vendor {vendor_id} not found")
            return None

        template_version = (vendor.template_version or 0) + 1
        template_data = {
            "version": str(template_version),
            "learned_from_corrections": len(corrections),
            "last_updated": datetime.utcnow().isoformat(),
            "field_patterns": field_patterns,
        }

        # Stabilize anchors: median bbox and dominant page number
        for field, pat in template_data["field_patterns"].items():
            bboxes = pat.get("bboxes", [])
            if bboxes:
                coords = list(zip(*bboxes))
                median_bbox = [float(statistics.median(c)) for c in coords]
                pat["bbox"] = median_bbox
            pat.pop("bboxes", None)
            pages = pat.get("page_numbers", [])
            if pages:
                try:
                    pat["page_number"] = int(statistics.mode(pages))
                except statistics.StatisticsError:
                    pat["page_number"] = int(statistics.median(pages))
            pat.pop("page_numbers", None)

        vendor.template_data = template_data
        vendor.template_version = template_version
        vendor.has_template = True
        vendor.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(vendor)

        logger.info(
            f"[template-refresh] Updated template for vendor {vendor_id}: "
            f"{len(field_patterns)} fields, version {template_version}"
        )
        return template_data
    
    def _normalize_template_data(self, template_data: Any) -> Dict[str, Any]:
        if template_data is None:
            return {}
        if isinstance(template_data, str):
            try:
                return json.loads(template_data)
            except Exception:
                logger.warning("[template-voter] Failed to parse template_data string")
                return {}
        return template_data

    def _extract_field_from_bbox(
        self,
        field_name: str,
        pattern: Dict[str, Any],
        image_path: str,
    ) -> Optional[Any]:
        """
        Crop the anchored bbox and re-OCR with strict parsing for the field type.
        BBox is expected as normalized [x0, y0, x1, y1].
        """
        try:
            img = Image.open(image_path)
            w, h = img.size
            bbox = pattern.get("bbox") or []
            if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
                return None

            x0, y0, x1, y1 = bbox
            # Clamp and add a tiny padding to mitigate box errors
            pad = 0.01
            x0 = max(0.0, x0 - pad)
            y0 = max(0.0, y0 - pad)
            x1 = min(1.0, x1 + pad)
            y1 = min(1.0, y1 + pad)

            crop_box = (
                int(x0 * w),
                int(y0 * h),
                int(x1 * w),
                int(y1 * h),
            )
            cropped = img.crop(crop_box)
            # Upscale for better OCR
            upscale = pattern.get("upscale", 2)
            if upscale and upscale > 1:
                new_size = (int(cropped.size[0] * upscale), int(cropped.size[1] * upscale))
                cropped = cropped.resize(new_size, Image.LANCZOS)

            # Optional binarization for clarity
            cropped = ImageOps.autocontrast(cropped)

            psm = pattern.get("psm", "7")
            tess_conf = f"--psm {psm}"
            lang = settings.TESSERACT_LANG or "eng"
            raw_text = pytesseract.image_to_string(cropped, lang=lang, config=tess_conf)
            if not raw_text:
                return None

            cleaned = raw_text.strip().replace("\n", " ").replace("\r", " ")
            return self._post_process_field(field_name, cleaned, pattern)
        except Exception as e:
            logger.warning(f"[template-voter] BBox OCR failed for {field_name}: {e}")
            return None

    def _post_process_field(self, field_name: str, text: str, pattern: Dict[str, Any]) -> Optional[Any]:
        field_type = pattern.get("type", "")
        lname = field_name.lower()
        text = text.strip()
        if not text:
            return None

        # Date fields
        if field_type == "date" or "date" in lname:
            return self._extract_date(text)

        # Amount fields
        if field_type == "monetary" or "amount" in lname or "total" in lname:
            return self._extract_amount(text)

        # Invoice number or identifiers
        if field_type == "identifier" or "number" in lname or "invoice" in lname:
            cleaned = text.strip()
            if any(ch.isdigit() for ch in cleaned):
                return cleaned
            return None

        # Fallback: raw cleaned text
        return text

    def _extract_date(self, text: str) -> Optional[str]:
        """
        Extract a plausible date with a 4-digit year using strict patterns.
        Returns ISO date (YYYY-MM-DD) or None.
        """
        month_map = {
            "january": 1, "jan": 1,
            "february": 2, "feb": 2,
            "march": 3, "mar": 3,
            "april": 4, "apr": 4,
            "may": 5,
            "june": 6, "jun": 6,
            "july": 7, "jul": 7,
            "august": 8, "aug": 8,
            "september": 9, "sep": 9, "sept": 9,
            "october": 10, "oct": 10,
            "november": 11, "nov": 11,
            "december": 12, "dec": 12,
        }
        patterns = [
            r"(?i)\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d{1,2},\s*\d{4}\b",
            r"\b\d{4}[-/]\d{2}[-/]\d{2}\b",
            r"\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b",
        ]
        candidates: List[str] = []
        for pat in patterns:
            candidates.extend(re.findall(pat, text))
        if not candidates:
            return None

        def parse_candidate(s: str) -> Optional[datetime]:
            s = s.strip()
            try:
                if re.match(r"\b\d{4}[-/]\d{2}[-/]\d{2}\b", s):
                    return datetime.strptime(s.replace("/", "-"), "%Y-%m-%d")
                if re.match(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b", s):
                    parts = re.split(r"[-/]", s)
                    m, d, y = int(parts[0]), int(parts[1]), int(parts[2])
                    return datetime(year=y, month=m, day=d)
                # Month name case
                m = re.match(r"(?i)\b([a-z]{3,})[a-z]*\s+(\d{1,2}),\s*(\d{4})\b", s)
                if m:
                    month = month_map.get(m.group(1).lower())
                    if month:
                        return datetime(year=int(m.group(3)), month=month, day=int(m.group(2)))
            except Exception:
                return None
            return None

        now_year = datetime.utcnow().year
        for cand in candidates:
            dt = parse_candidate(cand)
            if not dt:
                continue
            # Basic plausibility window: invoices usually within +/- 5 years
            if dt.year < now_year - 5 or dt.year > now_year + 2:
                continue
            return dt.date().isoformat()
        return None

    def _extract_amount(self, text: str) -> Optional[str]:
        """
        Extract monetary amount; require decimal separator to avoid stray tokens like 10.
        Returns normalized string (e.g., '80.00') or None.
        """
        # Replace commas used as decimal with dot after stripping thousand separators
        cand = re.findall(r"[-+]?[0-9]{1,3}(?:[.,][0-9]{3})*[.,][0-9]{2}", text)
        if not cand:
            return None
        raw = cand[0]
        # Normalize thousand separators
        if raw.count(",") > 1 and "." not in raw:
            raw = raw.replace(",", "")
        raw = raw.replace(",", ".")
        try:
            value = float(raw)
            return f"{value:.2f}"
        except Exception:
            return None

    def find_bbox_for_value(self, image_path: str, target_value: str) -> Optional[List[float]]:
        """
        Locate a value on the page image using Tesseract word boxes.
        Returns normalized bbox [x0,y0,x1,y1] or None.
        """
        try:
            if not target_value:
                return None
            img = Image.open(image_path)
            W, H = img.size
            data = pytesseract.image_to_data(img, lang=settings.TESSERACT_LANG or "eng", output_type=Output.DICT)
            tokens = []
            for i, txt in enumerate(data["text"]):
                if not txt or txt.strip() == "":
                    continue
                tokens.append(
                    (
                        txt.strip(),
                        data["left"][i],
                        data["top"][i],
                        data["width"][i],
                        data["height"][i],
                    )
                )
            if not tokens:
                return None

            norm_target = re.sub(r"\s+", " ", target_value.strip().lower())
            best_bbox = None
            for txt, x, y, w, h in tokens:
                lt = txt.lower()
                if lt == norm_target or norm_target in lt or lt in norm_target:
                    x0, y0, x1, y1 = x / W, y / H, (x + w) / W, (y + h) / H
                    best_bbox = [x0, y0, x1, y1]
                    break
            return best_bbox
        except Exception as e:
            logger.warning(f"[template-voter] Failed to locate bbox for value '{target_value}': {e}")
            return None
    
    def create_template_from_invoice(
        self,
        db: Session,
        vendor_id: int,
        extracted_data: Dict[str, Any],
        field_confidences: Dict[str, float],
        corrected_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create or update template - stores PATTERNS not VALUES"""
        from app.models.vendor import Vendor
        
        vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
        
        if not vendor:
            logger.error(f"Vendor {vendor_id} not found")
            return {}
        
        # Use corrected data if available
        final_data = corrected_data if corrected_data else extracted_data
        
        # Get existing template or create new
        if vendor.has_template and vendor.template_data:
            template = json.loads(vendor.template_data) if isinstance(vendor.template_data, str) else vendor.template_data
            logger.info(f"Updating existing template for vendor {vendor_id}")
        else:
            template = {
                "version": "2.0",  # New smart version
                "learned_from_invoices": 0,
                "created_at": datetime.now().isoformat(),
                "field_patterns": {}
            }
            logger.info(f"Creating new smart template for vendor {vendor_id}")
        
        template["learned_from_invoices"] = template.get("learned_from_invoices", 0) + 1
        template["last_updated"] = datetime.now().isoformat()
        
        # Learn PATTERNS, not exact values
        for field, value in final_data.items():
            if field.startswith('_'):
                continue
            
            confidence = field_confidences.get(field, 0.0)
            pattern_info = self._analyze_value_pattern(field, value)
            
            if field not in template["field_patterns"]:
                template["field_patterns"][field] = {
                    "examples": [value],  # Store multiple examples
                    "confidence": confidence,
                    "occurrences": 1,
                    **pattern_info
                }
            else:
                pattern = template["field_patterns"][field]
                
                # Keep multiple examples
                examples = pattern.get("examples", [])
                if value not in examples:
                    examples.append(value)
                    if len(examples) > 5:  # Keep max 5 examples
                        examples.pop(0)
                    pattern["examples"] = examples
                
                if confidence > pattern.get("confidence", 0):
                    pattern["confidence"] = confidence
                
                pattern["occurrences"] = pattern.get("occurrences", 0) + 1
                
                # Update pattern info
                pattern.update(pattern_info)
        
        # Save template
        vendor.template_data = template
        vendor.has_template = True
        vendor.updated_at = datetime.now()
        
        db.commit()
        db.refresh(vendor)
        
        logger.info(f"✅ Smart template updated for vendor {vendor_id}")
        
        return template
    
    def apply_template(
        self,
        template_data: Dict[str, Any],
        extracted_data: Dict[str, Any],
        field_confidences: Dict[str, float],
        image_path: Optional[str] = None,
    ) -> tuple[Dict[str, Any], Dict[str, float]]:
        """
        Apply SMART validation - detect corruption, don't enforce ranges.
        Optionally re-OCR anchored bboxes from the template when an image_path is provided.
        """
        if not template_data or "field_patterns" not in template_data:
            logger.warning("No valid template data")
            return extracted_data, field_confidences
        
        corrected_data = extracted_data.copy()
        corrected_confidences = field_confidences.copy()
        
        patterns = template_data.get("field_patterns", {})
        
        logger.info(f"🧠 Applying SMART corruption detection with {len(patterns)} patterns")
        
        issues_found = 0
        
        # For each field, check for CORRUPTION not exact match
        for field, pattern in patterns.items():
            extracted_value = extracted_data.get(field)
            extracted_conf = field_confidences.get(field, 0.0)

            # If we have a bbox anchor and an image, re-OCR that region to override bad full-page OCR
            anchored_value = None
            bbox_to_use = pattern.get("bbox")
            bbox_source = "template"
            if not bbox_to_use and image_path:
                # Try to auto-attach a bbox using a known example if none was stored
                examples = pattern.get("examples") or []
                example_value = examples[0] if examples else pattern.get("example")
                if example_value:
                    try:
                        auto_bbox = self.find_bbox_for_value(str(image_path), str(example_value))
                        if auto_bbox:
                            bbox_to_use = auto_bbox
                            bbox_source = "auto"
                    except Exception:
                        pass

            if image_path and bbox_to_use:
                try:
                    pattern_with_bbox = dict(pattern)
                    pattern_with_bbox["bbox"] = bbox_to_use
                    anchored_value = self._extract_field_from_bbox(
                        field_name=field,
                        pattern=pattern_with_bbox,
                        image_path=image_path,
                    )
                    if anchored_value is not None:
                        corrected_data[field] = anchored_value
                        corrected_confidences[field] = max(
                            extracted_conf, settings.TEMPLATE_VOTER_CONFIDENCE
                        )
                        logger.info(
                            f"[template-ocr] Overrode '{field}' using bbox ({bbox_source}) -> {anchored_value}"
                        )
                        continue
                except Exception as e:
                    logger.warning(f"[template-ocr] Failed bbox re-OCR for '{field}': {e}")

            # Run smart corruption detection
            is_corrupted, issues = self._detect_corruption(field, extracted_value, pattern)
            
            if is_corrupted:
                logger.warning(f"⚠️  Field '{field}' appears CORRUPTED:")
                for issue in issues:
                    logger.warning(f"   - {issue}")
                
                # Flag for review, don't reject
                corrected_confidences[field] = 50.0  # Medium-low confidence
                issues_found += 1
                
                # Add review flag
                if '_needs_review' not in corrected_data:
                    corrected_data['_needs_review'] = []
                
                corrected_data['_needs_review'].append({
                    'field': field,
                    'extracted': extracted_value,
                    'issues': issues,
                    'confidence': 50.0
                })
            
            elif extracted_value:
                # No corruption detected - boost confidence
                boosted_conf = min(extracted_conf + 5.0, 100.0)
                corrected_confidences[field] = boosted_conf
                logger.info(f"✅ '{field}' looks clean: {extracted_conf:.1f}% → {boosted_conf:.1f}%")
        
        if issues_found > 0:
            logger.warning(f"⚠️  {issues_found} field(s) flagged as potentially corrupted")
        
        return corrected_data, corrected_confidences
    
    def _analyze_value_pattern(self, field: str, value: Any) -> Dict[str, Any]:
        """Analyze value to extract PATTERN information"""
        info = {
            "value_type": type(value).__name__,
            "field_type": self._classify_field(field),
        }
        
        if isinstance(value, str):
            info.update({
                "length": len(value),
                "has_letters": bool(re.search(r'[a-zA-Z]', value)),
                "has_digits": bool(re.search(r'\d', value)),
                "format_pattern": self._extract_string_pattern(value),
            })
        
        elif isinstance(value, (int, float)):
            info.update({
                "digit_count": len(str(int(abs(value)))),
                "is_decimal": isinstance(value, float),
                "magnitude": self._get_magnitude(value),
            })
        
        return info
    
    def _classify_field(self, field_name: str) -> str:
        """Classify field type from name"""
        field_lower = field_name.lower()
        
        if 'amount' in field_lower or 'total' in field_lower or 'price' in field_lower:
            return 'monetary'
        elif 'date' in field_lower:
            return 'date'
        elif 'number' in field_lower or 'num' in field_lower or 'id' in field_lower:
            return 'identifier'
        elif 'name' in field_lower or 'vendor' in field_lower:
            return 'name'
        elif 'currency' in field_lower:
            return 'currency'
        else:
            return 'generic'
    
    def _extract_string_pattern(self, value: str) -> str:
        """Extract pattern from string"""
        # Date patterns
        if re.match(r'^\d{4}-\d{2}-\d{2}$', value):
            return 'date_iso'
        
        # Invoice number patterns
        if re.match(r'^[A-Z]{2,5}-\d{4,}-\d{2,}$', value):
            return 'invoice_standard'
        if re.match(r'^-\d+', value):
            return 'invoice_broken_prefix'
        if re.match(r'^\d+$', value):
            return 'numeric_only'
        
        # Currency
        if re.match(r'^[A-Z]{3}$', value):
            return 'currency_code'
        
        # Mixed
        if re.search(r'[a-zA-Z]', value) and re.search(r'\d', value):
            return 'alphanumeric'
        
        return 'text'
    
    def _get_magnitude(self, value: float) -> str:
        """Get order of magnitude"""
        if value == 0:
            return 'zero'
        
        abs_val = abs(value)
        
        if abs_val < 1:
            return 'fractional'
        elif abs_val < 100:
            return 'tens'
        elif abs_val < 1000:
            return 'hundreds'
        elif abs_val < 10000:
            return 'thousands'
        elif abs_val < 100000:
            return 'ten_thousands'
        elif abs_val < 1000000:
            return 'hundred_thousands'
        else:
            return 'millions_plus'
    
    def _detect_corruption(
        self, 
        field: str, 
        value: Any, 
        pattern: Dict[str, Any]
    ) -> Tuple[bool, list]:
        """
        SMART corruption detection - no hardcoded values!
        Returns: (is_corrupted, [list of issues])
        """
        issues = []
        
        if value is None:
            return False, []
        
        field_type = pattern.get("field_type", "generic")
        expected_format = pattern.get("format_pattern")
        expected_magnitude = pattern.get("magnitude")
        expected_digit_count = pattern.get("digit_count")
        
        # MONETARY FIELD CHECKS
        if field_type == 'monetary' and isinstance(value, (int, float)):
            # Check 1: Negative amounts are suspicious
            if value < 0:
                issues.append(f"Negative amount: {value}")
            
            # Check 2: Too many digits (likely corruption)
            actual_digits = len(str(int(abs(value))))
            if expected_digit_count and actual_digits > expected_digit_count + 2:
                issues.append(f"Too many digits: {actual_digits} (expected ~{expected_digit_count})")
            
            # Check 3: Magnitude jump (likely corruption, not just different amount)
            actual_magnitude = self._get_magnitude(value)
            if expected_magnitude and actual_magnitude != expected_magnitude:
                # Allow one level difference (hundreds vs thousands OK)
                # But hundreds vs hundred_thousands is corruption
                mag_order = ['tens', 'hundreds', 'thousands', 'ten_thousands', 'hundred_thousands', 'millions_plus']
                if expected_magnitude in mag_order and actual_magnitude in mag_order:
                    expected_idx = mag_order.index(expected_magnitude)
                    actual_idx = mag_order.index(actual_magnitude)
                    if abs(actual_idx - expected_idx) > 2:
                        issues.append(f"Magnitude jump: {expected_magnitude} → {actual_magnitude} (likely corruption)")
            
            # Check 4: Suspicious patterns (looks like concatenated date)
            str_value = str(value)
            if '2023' in str_value or '2024' in str_value or '2025' in str_value:
                if value > 10000:  # Year in amount is suspicious
                    issues.append(f"Amount contains year digits: {value}")
        
        # IDENTIFIER FIELD CHECKS (invoice numbers, IDs)
        elif field_type == 'identifier' and isinstance(value, str):
            # Check 1: Missing prefix
            if expected_format == 'invoice_standard' and value.startswith('-'):
                issues.append(f"Missing prefix (starts with '-')")
            
            # Check 2: Format completely different
            actual_format = self._extract_string_pattern(value)
            if expected_format and actual_format != expected_format:
                # Only flag if drastically different
                if expected_format == 'invoice_standard' and actual_format == 'numeric_only':
                    issues.append(f"Format changed: {expected_format} → {actual_format}")
            
            # Check 3: Length drastically different
            expected_length = pattern.get("length")
            if expected_length and abs(len(value) - expected_length) > 5:
                issues.append(f"Length mismatch: {len(value)} vs expected ~{expected_length}")
        
        # DATE FIELD CHECKS
        elif field_type == 'date' and isinstance(value, str):
            # Check: Not a valid date format
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', value):
                issues.append(f"Invalid date format: {value}")
        
        # CURRENCY FIELD CHECKS
        elif field_type == 'currency' and isinstance(value, str):
            # Check: Not 3-letter code
            if not re.match(r'^[A-Z]{3}$', value):
                issues.append(f"Invalid currency code: {value}")
        
        return len(issues) > 0, issues
    
    def get_template_stats(self, db: Session, vendor_id: int) -> Dict[str, Any]:
        """Get template statistics"""
        from app.models.vendor import Vendor
        
        vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
        
        if not vendor or not vendor.has_template:
            return {
                "has_template": False,
                "vendor_id": vendor_id
            }
        
        template = vendor.template_data
        if isinstance(template, str):
            template = json.loads(template)
        
        return {
            "has_template": True,
            "vendor_id": vendor_id,
            "vendor_name": vendor.vendor_name,
            "learned_from_invoices": template.get("learned_from_invoices", 0),
            "field_count": len(template.get("field_patterns", {})),
            "fields": list(template.get("field_patterns", {}).keys()),
            "version": template.get("version", "1.0"),
            "last_updated": template.get("last_updated"),
            "created_at": template.get("created_at")
        }


# Create singleton
template_service = TemplateService()


"""
Intelligent 4-Way Merger
Merges results from 4 ML models using sophisticated consensus voting

PHASE 1 COMPLETE:
- Confidence calibration integrated
- Better error handling
- Improved logging

Enhancement:
- Optional OCR text voters (RapidOCR/Docling/Tesseract) to improve consensus

Features:
- Weighted consensus voting
- Confidence calibration
- Conflict resolution
- Validation integration
- Detailed voting logs
"""

import logging
import re
from typing import Dict, Any, List, Tuple, Optional
from app.utils.consensus_algorithm import consensus_voting
from app.utils.field_validators import validator
from app.config import settings

logger = logging.getLogger(__name__)


class IntelligentMerger:
    """
    Intelligent merger for quadruple hybrid ML system
    
    Merges results from:
    1. Docling (structure-aware)
    2. Impira (Q&A)
    3. LayoutLMv3 (layout analysis)
    4. Donut (end-to-end)
    
    Using:
    - Consensus voting with calibration (PHASE 1)
    - Weighted confidence
    - Field type validation
    - Conflict resolution
    """
    
    # Standard invoice fields to extract
    STANDARD_FIELDS = [
        'invoice_number',
        'invoice_date',
        'due_date',
        'total_amount',
        'subtotal',
        'tax_amount',
        'vendor_name',
        'customer_name',
        'currency',
        'payment_terms'
    ]
    
    def __init__(self):
        self.consensus_algo = consensus_voting
    
    def merge_4way(
        self,
        docling_result: Dict[str, Any],
        impira_result: Dict[str, Any],
        layoutlm_result: Dict[str, Any],
        donut_result: Dict[str, Any],
        raw_ocr_text: str = "",
        extra_ocr_texts: Optional[Dict[str, str]] = None,
        extra_ocr_fields: Optional[Dict[str, Any]] = None,
        extra_ocr_confidence: float = 82.0,
        extra_template_fields: Optional[Dict[str, Any]] = None,
        template_confidence: float = 85.0,
    ) -> Dict[str, Any]:
        """
        Merge results from all 4 models with PHASE 1 calibration
        
        Args:
            docling_result: {extracted_data, confidence, metadata}
            impira_result: {extracted_data, confidence}
            layoutlm_result: {extracted_data, confidence}
            donut_result: {extracted_data, confidence}
            raw_ocr_text: Raw OCR text for validation context
            extra_ocr_texts: Optional OCR voter texts (e.g., {'ocr_rapid': str, 'ocr_docling': str, 'ocr_tesseract': str})
            
        Returns:
            {
                'extracted_data': Merged and validated data,
                'field_confidences': Calibrated confidence per field,
                'voting_details': Detailed voting information,
                'model_outputs': All individual model outputs,
                'overall_confidence': Average calibrated confidence,
                'needs_review': List of fields flagged for review
            }
        """
        
        logger.info("="*80)
        logger.info("INTELLIGENT 4-WAY MERGER - STARTING")
        logger.info("="*80)
        
        # Prepare model results
        model_results = {
            'docling': docling_result,
            'impira': impira_result,
            'layoutlm': layoutlm_result,
            'donut': donut_result
        }

        # Add OCR-text voters if provided
        if extra_ocr_texts:
            self._add_ocr_voters(model_results, extra_ocr_texts)
        if extra_ocr_fields:
            self._add_ocr_field_voter(
                model_results,
                extra_ocr_fields,
                confidence=extra_ocr_confidence,
            )
        # Add template voter if provided
        if extra_template_fields:
            self._add_template_voter(
                model_results,
                extra_template_fields,
                confidence=template_confidence,
            )
        
        # Log model availability
        for model_name, result in model_results.items():
            data = result.get('extracted_data', {})
            conf = result.get('confidence', 0)
            logger.info(f"  {model_name.upper()}: {len(data)} fields, {conf:.1f}% confidence")
        
        # Collect all fields that any model extracted
        all_fields = set()
        for result in model_results.values():
            all_fields.update(result.get('extracted_data', {}).keys())
        
        logger.info(f"\nTotal unique fields across all models: {len(all_fields)}")
        
        # Perform voting on each field (WITH PHASE 1 CALIBRATION)
        merged_data = {}
        field_confidences = {}
        voting_details = {}
        needs_review = []
        
        for field in all_fields:
            logger.info(f"\n--- Voting on: {field} ---")

            # If bbox override is enabled and template OCR has a value for this field, force it
            template_value = None
            if extra_template_fields:
                template_value = extra_template_fields.get(field)
            if settings.USE_BBOX_OVERRIDE and template_value not in (None, "", []):
                merged_data[field] = template_value
                field_confidences[field] = template_confidence
                voting_details[field] = {
                    "consensus_value": template_value,
                    "confidence": template_confidence,
                    "agreement_level": "forced_template_bbox",
                    "vote_counts": {"ocr_template": 1},
                    "selected_from": ["ocr_template"],
                    "all_values": [template_value],
                }
                logger.info(f"[bbox-override] Using template OCR for '{field}': {template_value}")
                continue

            # Prefer label-anchored OCR fusion when other models are clearly wrong
            ocr_fused_override = self._prefer_ocr_fused(field, model_results, raw_ocr_text)
            if ocr_fused_override is not None:
                merged_data[field] = ocr_fused_override
                field_confidences[field] = extra_ocr_confidence
                voting_details[field] = {
                    "consensus_value": ocr_fused_override,
                    "confidence": extra_ocr_confidence,
                    "agreement_level": "ocr_fused_override",
                    "vote_counts": {"ocr_fused": 1},
                    "selected_from": ["ocr_fused"],
                    "all_values": [ocr_fused_override],
                }
                logger.info(f"[ocr-fused-override] Using OCR fusion for '{field}': {ocr_fused_override}")
                continue
             
            # Vote on this field (returns calibrated confidence)
            vote_result = self.consensus_algo.vote_on_field(field, model_results)
            
            consensus_value = vote_result['consensus_value']
            confidence = vote_result['confidence']  # Already calibrated in Phase 1!
            agreement_level = vote_result['agreement_level']
            
            # Log voting details
            logger.info(f"  Vote counts: {vote_result['vote_counts']}")
            logger.info(f"  Agreement: {agreement_level}")
            logger.info(f"  Selected: {consensus_value} (from {vote_result['selected_from']})")
            logger.info(f"  Confidence: {confidence:.1f}% (calibrated)")
            
            # Store voting details
            voting_details[field] = vote_result
            
            # Check if needs review
            if agreement_level in ['weak', 'conflict']:
                needs_review.append({
                    'field': field,
                    'reason': f'Low agreement ({agreement_level})',
                    'all_values': vote_result['all_values'],
                    'selected': consensus_value
                })
                logger.warning(f"  ⚠️  Flagged for review: {agreement_level} agreement")
            
            # Store result
            if consensus_value is not None:
                merged_data[field] = consensus_value
                field_confidences[field] = confidence
        
        # Calculate overall confidence (average of calibrated confidences)
        if field_confidences:
            overall_confidence = sum(field_confidences.values()) / len(field_confidences)
        else:
            overall_confidence = 0.0
        
        # Special handling for line items (only Docling extracts these)
        if 'line_items' in docling_result.get('extracted_data', {}):
            merged_data['line_items'] = docling_result['extracted_data']['line_items']
            logger.info(f"\n✅ Line items: {len(merged_data['line_items'])} from Docling")
        
        logger.info("\n" + "="*80)
        logger.info("MERGER COMPLETE")
        logger.info("="*80)
        logger.info(f"  Merged fields: {len(merged_data)}")
        logger.info(f"  Overall confidence: {overall_confidence:.1f}% (calibrated)")
        logger.info(f"  Fields needing review: {len(needs_review)}")
        
        return {
            'extracted_data': merged_data,
            'field_confidences': field_confidences,
            'voting_details': voting_details,
            'model_outputs': {
                'docling': docling_result.get('extracted_data', {}),
                'impira': impira_result.get('extracted_data', {}),
                'layoutlm': layoutlm_result.get('extracted_data', {}),
                'donut': donut_result.get('extracted_data', {}),
                # OCR voters are logged only in voting_details; we keep core model outputs unchanged
            },
            'overall_confidence': round(overall_confidence, 2),
            'needs_review': needs_review,
            'raw_ocr_text': raw_ocr_text
        }
    
    def detect_conflicts(
        self,
        voting_details: Dict[str, Dict]
    ) -> List[Dict[str, Any]]:
        """
        Detect fields with significant conflicts
        
        Returns list of conflicts with details
        """
        conflicts = []
        
        for field, vote_info in voting_details.items():
            if vote_info['agreement_level'] in ['weak', 'conflict']:
                conflicts.append({
                    'field': field,
                    'agreement_level': vote_info['agreement_level'],
                    'all_values': vote_info['all_values'],
                    'selected': vote_info['consensus_value'],
                    'vote_counts': vote_info['vote_counts']
                })
        
        return conflicts
    
    def get_merger_statistics(
        self,
        voting_details: Dict[str, Dict]
    ) -> Dict[str, Any]:
        """
        Generate statistics about the merger process
        
        Returns metrics like:
        - Agreement distribution
        - Average confidence by field
        - Model contribution
        """
        
        stats = {
            'total_fields': len(voting_details),
            'agreement_distribution': {
                'unanimous': 0,
                'strong': 0,
                'moderate': 0,
                'weak': 0,
                'conflict': 0
            },
            'model_contribution': {
                'docling': 0,
                'impira': 0,
                'layoutlm': 0,
                'donut': 0
            },
            'average_confidence': 0.0,
            'fields_needing_review': []
        }
        
        total_confidence = 0
        
        for field, vote_info in voting_details.items():
            # Agreement distribution
            agreement = vote_info.get('agreement_level', 'unknown')
            if agreement in stats['agreement_distribution']:
                stats['agreement_distribution'][agreement] += 1
            
            # Model contribution
            for model in vote_info.get('selected_from', []):
                if model in stats['model_contribution']:
                    stats['model_contribution'][model] += 1
            
            # Confidence
            total_confidence += vote_info.get('confidence', 0)
            
            # Fields needing review
            if agreement in ['weak', 'conflict']:
                stats['fields_needing_review'].append(field)
        
        # Calculate averages
        if stats['total_fields'] > 0:
            stats['average_confidence'] = total_confidence / stats['total_fields']
        
        return stats

    def _prefer_ocr_fused(
        self,
        field: str,
        model_results: Dict[str, Dict[str, Any]],
        raw_ocr_text: str,
    ) -> Optional[Any]:
        """
        Prefer label-anchored OCR fusion output when other values look invalid or zip-like.
        """
        ocr_fused = model_results.get("ocr_fused", {}).get("extracted_data", {})
        if not ocr_fused or field not in ocr_fused:
            return None

        ocr_value = ocr_fused.get(field)
        if ocr_value in (None, "", []):
            return None

        force_fields = self._ocr_fusion_force_fields()
        if field in force_fields:
            forced = self._normalize_for_field(field, ocr_value)
            if forced is not None:
                return forced

        other_values: List[str] = []
        for model_name, result in model_results.items():
            if model_name == "ocr_fused":
                continue
            value = result.get("extracted_data", {}).get(field)
            if value not in (None, "", []):
                other_values.append(str(value))

        if field in ("invoice_date", "due_date"):
            ok, cleaned = validator.validate_invoice_date(str(ocr_value))
            if not ok or not cleaned:
                return None
            if all(not validator.validate_invoice_date(val)[0] for val in other_values):
                return cleaned
            return None

        if field == "invoice_number":
            ok, cleaned = validator.validate_invoice_number(str(ocr_value))
            if not ok or not cleaned:
                return None
            if all(not validator.validate_invoice_number(val)[0] for val in other_values):
                return cleaned
            if all(not any(ch.isdigit() for ch in val) for val in other_values):
                return cleaned
            return None

        if field == "po_number":
            ok, cleaned = validator.validate_po_number(str(ocr_value))
            if not ok or not cleaned:
                return None
            if all(not validator.validate_po_number(val)[0] for val in other_values):
                return cleaned
            if all(not any(ch.isdigit() for ch in val) for val in other_values):
                return cleaned
            return None

        if field == "total_amount":
            ocr_str = str(ocr_value)
            try:
                amount = validator.normalize_decimal_format(ocr_str)
            except Exception:
                return None

            has_decimal = bool(re.search(r"[.,]\d{2}\b", ocr_str)) or "$" in ocr_str
            ocr_conf = model_results.get("ocr_fused", {}).get("confidence", 0.0)
            if settings.TOTAL_PREFER_FOOTER and has_decimal and ocr_conf >= settings.TOTAL_FOOTER_MIN_CONF:
                return amount
            other_zip_like = any(self._is_zip_like(val, raw_ocr_text) for val in other_values)
            other_no_decimal = all(re.fullmatch(r"\d{4,6}", val.strip()) for val in other_values if val)

            if other_zip_like or (has_decimal and other_no_decimal):
                return amount

        return None

    def _ocr_fusion_force_fields(self) -> List[str]:
        raw = settings.OCR_FUSION_FORCE_FIELDS or ""
        return [field.strip().lower() for field in raw.split(",") if field.strip()]

    def _normalize_for_field(self, field: str, value: Any) -> Optional[Any]:
        if field in ("invoice_date", "due_date"):
            ok, cleaned = validator.validate_invoice_date(str(value))
            return cleaned if ok and cleaned else None
        if field == "invoice_number":
            ok, cleaned = validator.validate_invoice_number(str(value))
            return cleaned if ok and cleaned else None
        if field == "po_number":
            ok, cleaned = validator.validate_po_number(str(value))
            return cleaned if ok and cleaned else None
        if field == "total_amount":
            try:
                return validator.normalize_decimal_format(str(value))
            except Exception:
                return None
        return value

    def _is_zip_like(self, value: str, raw_ocr_text: str) -> bool:
        if not value:
            return False
        text = value.strip()
        if not re.fullmatch(r"\d{5}", text):
            return False
        if raw_ocr_text:
            state_match = re.search(rf"\b[A-Z]{{2}}\s+{re.escape(text)}\b", raw_ocr_text)
            if state_match:
                return True
        return False

    def _add_ocr_voters(self, model_results: Dict[str, Dict[str, Any]], extra_ocr_texts: Dict[str, str]) -> None:
        """
        Convert raw OCR texts into lightweight voter models and attach to model_results.
        """
        for voter_name, text in extra_ocr_texts.items():
            fields = self._extract_fields_from_ocr_text(text)
            if not fields:
                continue

            model_results[voter_name] = {
                'extracted_data': fields,
                'confidence': 75.0,  # Flat confidence for OCR voters
                'metadata': {'source': 'ocr_text'}
            }
            logger.info(f"  OCR voter added: {voter_name} with {len(fields)} fields")

    def _add_template_voter(
        self,
        model_results: Dict[str, Dict[str, Any]],
        template_fields: Dict[str, Any],
        confidence: float = 85.0,
    ) -> None:
        """
        Add a template-based voter that contributes stored field examples.
        """
        if not template_fields:
            return

        model_results["ocr_template"] = {
            "extracted_data": template_fields,
            "confidence": confidence,
            "metadata": {"source": "template_voter"},
        }
        logger.info(f"  Template voter added: ocr_template with {len(template_fields)} fields (conf {confidence:.1f}%)")

    def _add_ocr_field_voter(
        self,
        model_results: Dict[str, Dict[str, Any]],
        ocr_fields: Dict[str, Any],
        confidence: float = 82.0,
    ) -> None:
        """
        Add a label-aware OCR fusion voter that contributes field values.
        """
        if not ocr_fields:
            return

        model_results["ocr_fused"] = {
            "extracted_data": ocr_fields,
            "confidence": confidence,
            "metadata": {"source": "ocr_fusion"},
        }
        logger.info(f"  OCR fusion voter added: ocr_fused with {len(ocr_fields)} fields (conf {confidence:.1f}%)")

    def _extract_fields_from_ocr_text(self, text: str) -> Dict[str, Any]:
        """
        Heuristic extraction of key fields from raw OCR text.
        """
        if not text:
            return {}

        result: Dict[str, Any] = {}
        lower_text = text.lower()

        # Currency detection
        currency_map = {'$': 'USD', '€': 'EUR', '£': 'GBP', '¥': 'JPY', '₹': 'INR'}
        for symbol, code in currency_map.items():
            if symbol in text:
                result.setdefault('currency', code)
                break
        if 'currency' not in result:
            match_curr = re.search(r'\b(usd|eur|gbp|jpy|inr|aud|cad|chf|cny)\b', lower_text)
            if match_curr:
                result['currency'] = match_curr.group(1).upper()

        # Amount near TOTAL
        total_patterns = [
            r'(?:grand\s+)?total[^0-9]{0,20}([-+]?[0-9][0-9.,]{1,})',
            r'(?:amount\s+due)[^0-9]{0,20}([-+]?[0-9][0-9.,]{1,})'
        ]
        amount_candidates: List[str] = []
        for pat in total_patterns:
            for m in re.finditer(pat, lower_text, flags=re.IGNORECASE):
                amount_candidates.append(m.group(1))
        if not amount_candidates:
            for m in re.finditer(r'[-+]?[0-9][0-9.,]{2,}', lower_text):
                amount_candidates.append(m.group(0))

        for cand in amount_candidates:
            # Skip obvious invoice-number fragments like "-2023" or long negatives
            if '-' in cand and len(cand) <= 6:
                continue
            try:
                normalized = validator.normalize_decimal_format(cand)
                result['total_amount'] = normalized
                break
            except Exception:
                continue

        # Dates
        date_strings: List[str] = []
        date_patterns = [
            r'[A-Za-z]{3,9}\s+\d{1,2},\s*\d{2,4}',
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4}'
        ]
        for pat in date_patterns:
            for m in re.finditer(pat, text):
                date_strings.append(m.group(0).strip())

        dedup_dates: List[str] = []
        for ds in date_strings:
            if ds not in dedup_dates:
                dedup_dates.append(ds)

        parsed_dates: List[str] = []
        for ds in dedup_dates:
            ok, cleaned = validator.validate_invoice_date(ds)
            if ok and cleaned:
                parsed_dates.append(cleaned)

        if parsed_dates:
            result['invoice_date'] = parsed_dates[0]
            if len(parsed_dates) > 1:
                result['due_date'] = parsed_dates[1]

        # Invoice number
        inv_patterns = [
            r'(?:invoice|inv|no\.?)\s*[:#-]?\s*([A-Za-z0-9][-A-Za-z0-9]{2,})',
            r'\b([A-Za-z0-9]{3,}[-/][A-Za-z0-9]{2,})\b'
        ]
        inv_candidate = None
        for pat in inv_patterns:
            m = re.search(pat, text, flags=re.IGNORECASE)
            if m:
                inv_candidate = m.group(1)
                break
        if not inv_candidate:
            m = re.search(r'\b[A-Za-z]*\d[A-Za-z0-9-]{2,}\b', text)
            if m:
                inv_candidate = m.group(0)

        if inv_candidate:
            ok, cleaned_inv = validator.validate_invoice_number(inv_candidate)
            if ok and cleaned_inv:
                result['invoice_number'] = cleaned_inv

        return result


# Singleton instance
intelligent_merger = IntelligentMerger()

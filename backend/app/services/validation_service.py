
"""
Validation Service - PHASE 3 COMPLETE
Orchestrates all validation logic with advanced heuristics

PHASE 3 ENHANCEMENTS:
- Impossible date detection (Nov 35, Feb 30)
- Zero amount validation (No Charge invoices)
- Negative amount support (Credit notes)
- Due date validation (same as invoice date)
"""
from typing import Dict, Any, List, Optional, Tuple
import logging
import re
from app.utils.field_validators import validator
from app.utils.cross_field_validator import cross_validator
from app.utils.advanced_heuristics import advanced_heuristics

logger = logging.getLogger(__name__)


class ValidationService:
    """
    Orchestrates invoice data validation - PHASE 3 COMPLETE
    
    Responsibilities:
    1. Field-level validation (types, formats, ALL decimal formats)
    2. Advanced heuristics (vendor, document type, amounts)
    3. Cross-field validation (relationships)
    4. Auto-correction application
    5. Confidence adjustment
    6. Review flagging
    7. PHASE 3: Zero/negative amounts, impossible dates
    """
    
    def __init__(self):
        self.field_validator = validator
        self.cross_validator = cross_validator
        self.heuristics = advanced_heuristics
    
    def validate_and_correct(
        self,
        extracted_data: Dict[str, Any],
        field_confidences: Dict[str, float],
        line_items: List[Dict] = None,
        raw_ocr_text: str = None,
        known_vendor: str = None,
        vendor_id: int = None
    ) -> Dict[str, Any]:
        """
        Main validation pipeline - PHASE 3 COMPLETE
        
        Returns:
            {
                'validated_data': Dict,
                'field_confidences': Dict,
                'overall_confidence': float,
                'validation_warnings': List[str],
                'needs_review': bool,
                'corrections_applied': List[str],
                'validation_metadata': Dict,
                'document_type': str,
                'document_type_confidence': float
            }
        """
        logger.info("🔍 Starting PHASE 3 validation pipeline...")
        
        validated_data = {}
        updated_confidences = field_confidences.copy()
        corrections_applied = []
        validation_warnings = []
        validation_metadata = {}
        
        # PHASE 2: STEP 1 - Document Type Detection
        logger.info("[1/5] Detecting document type...")
        doc_type, doc_type_conf, doc_reason = self.heuristics.detect_document_type(
            title_text=extracted_data.get('invoice_number', ''),
            ocr_text=raw_ocr_text or '',
            total_amount=extracted_data.get('total_amount')
        )
        
        validation_metadata['document_type'] = {
            'type': doc_type,
            'confidence': doc_type_conf,
            'reason': doc_reason
        }
        
        logger.info(f"   Document type: {doc_type.upper()} ({doc_type_conf:.1f}%)")
        
        # PHASE 3: STEP 2 - Field-level validation with heuristics
        logger.info("[2/5] Field-level validation with heuristics...")
        field_results = self._validate_fields_with_heuristics(
            extracted_data, 
            raw_ocr_text,
            doc_type
        )
        
        validated_data = field_results['validated_data']
        corrections_applied.extend(field_results['corrections'])
        validation_warnings.extend(field_results['warnings'])
        validation_metadata['field_validation'] = field_results['metadata']
        
        # Update confidences based on field validation
        updated_confidences = self._adjust_confidences_from_field_validation(
            updated_confidences,
            field_results['metadata']
        )

        if (
            'payment_terms' in field_results['validated_data']
            and 'due_date' not in field_results['validated_data']
            and 'due_date' in updated_confidences
        ):
            updated_confidences['payment_terms'] = max(
                updated_confidences.get('payment_terms', 0.0),
                updated_confidences.get('due_date', 0.0),
            )
            updated_confidences.pop('due_date', None)
        
        # PHASE 2: STEP 3 - Advanced heuristics validation
        logger.info("[3/5] Advanced heuristics validation...")
        heuristic_results = self._apply_advanced_heuristics(
            validated_data,
            updated_confidences,
            line_items,
            raw_ocr_text,
            known_vendor,
            vendor_id
        )
        
        # Apply heuristic corrections
        if heuristic_results['corrections']:
            for field, corrected_value in heuristic_results['corrections'].items():
                logger.info(f"   🔧 Heuristic correction: {field} = {corrected_value}")
                validated_data[field] = corrected_value
                corrections_applied.append(f"{field}_heuristic_corrected")
                
                # Adjust confidence
                if field in updated_confidences:
                    updated_confidences[field] = max(70.0, updated_confidences[field] - 15)
        
        validation_warnings.extend(heuristic_results['warnings'])
        validation_metadata['heuristic_validation'] = heuristic_results['metadata']
        
        # PHASE 2: STEP 4 - Cross-field validation
        logger.info("[4/5] Cross-field validation...")
        cross_results = cross_validator.validate_all_cross_fields(
            validated_data,
            line_items=line_items,
            known_vendor=known_vendor,
            vendor_id=vendor_id,
            raw_ocr_text=raw_ocr_text
        )
        
        validation_warnings.extend(cross_results['warnings'])
        validation_metadata['cross_field_validation'] = cross_results['metadata']
        
        # Apply suggested corrections from cross-field validation
        if cross_results['suggested_corrections']:
            for field, corrected_value in cross_results['suggested_corrections'].items():
                logger.info(f"   ✅ Auto-correction: {field} = {corrected_value} (was {validated_data.get(field)})")
                validated_data[field] = corrected_value
                corrections_applied.append(f"{field}_decimal_format_corrected")
                
                # Lower confidence for corrected fields
                if field in updated_confidences:
                    updated_confidences[field] = max(85.0, updated_confidences[field] - 10)
        
        # PHASE 3: STEP 5 - Calculate final metrics
        logger.info("[5/5] Calculating final metrics...")
        
        # Calculate overall confidence
        overall_confidence = self._calculate_overall_confidence(
            updated_confidences,
            validation_warnings
        )
        
        # Determine if needs review
        needs_review = self._determine_needs_review(
            validation_warnings,
            overall_confidence,
            corrections_applied,
            doc_type
        )
        
        logger.info(f"✅ PHASE 3 Validation complete:")
        logger.info(f"   - Document type: {doc_type}")
        logger.info(f"   - Warnings: {len(validation_warnings)}")
        logger.info(f"   - Corrections: {len(corrections_applied)}")
        logger.info(f"   - Overall confidence: {overall_confidence:.1f}%")
        logger.info(f"   - Needs review: {needs_review}")
        
        return {
            'validated_data': validated_data,
            'field_confidences': updated_confidences,
            'overall_confidence': overall_confidence,
            'validation_warnings': validation_warnings,
            'needs_review': needs_review,
            'corrections_applied': corrections_applied,
            'validation_metadata': validation_metadata,
            'document_type': doc_type,
            'document_type_confidence': doc_type_conf
        }
    
    def _extract_date_from_text(self, raw_text: str, labels: List[str], fallback_year: Optional[int] = None) -> Optional[str]:
        """
        Extract a date string from OCR text using provided labels as anchors.
        Returns the raw matched date substring (not normalized).
        """
        if not raw_text:
            return None
        
        text_lower = raw_text.lower()
        month_names = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december)"
        patterns = [
            rf"{month_names}\s+\d{{1,2}},?\s*\d{{2,4}}",
            rf"{month_names}\s+\d{{1,2}}",  # missing year
            r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}",
            r"\d{1,2}\s*,\s*\d{4}",  # day,year without month (try to repair later)
        ]
        
        # Search near labels first
        for label in labels:
            pos = text_lower.find(label.lower())
            if pos >= 0:
                window = raw_text[pos:pos + 150]
                for pat in patterns:
                    m = re.search(pat, window, re.IGNORECASE)
                    if m:
                        candidate = m.group(0).strip()
                        if re.search(r"\d{4}", candidate):
                            return candidate
                        if fallback_year:
                            return f"{candidate} {fallback_year}"
        
        # Fallback: search entire text
        for pat in patterns:
            m = re.search(pat, raw_text, re.IGNORECASE)
            if m:
                candidate = m.group(0).strip()
                if re.search(r"\d{4}", candidate):
                    return candidate
                if fallback_year:
                    return f"{candidate} {fallback_year}"
        
        return None
    
    def _repair_monthless_date(
        self,
        raw_text: str,
        labels: List[str],
        fallback_year: Optional[int] = None
    ) -> Optional[str]:
        """
        Repair dates like '28,2008' (missing month) by pairing the day/year with a nearby month name.
        """
        if not raw_text:
            return None
        
        month_regex = re.compile(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december)", re.IGNORECASE)
        day_year_regex = re.compile(r"\b(\d{1,2})\s*,\s*(\d{4})\b")
        
        text_lower = raw_text.lower()
        
        # Find a month name globally (first occurrence)
        global_month_match = month_regex.search(raw_text)
        global_month = global_month_match.group(0) if global_month_match else None
        
        # Search near labels for a day,year pattern and a month name in the same window
        for label in labels:
            pos = text_lower.find(label.lower())
            if pos >= 0:
                window = raw_text[max(0, pos):pos + 200]
                dy = day_year_regex.search(window)
                month_in_window = month_regex.search(window)
                if dy:
                    day, year = dy.group(1), dy.group(2)
                    month = month_in_window.group(0) if month_in_window else global_month
                    if month:
                        candidate = f"{month} {day}, {fallback_year or year}"
                        return candidate
        
        # Fallback: if we find a day,year anywhere and a global month
        dy = day_year_regex.search(raw_text)
        if dy and global_month:
            day, year = dy.group(1), dy.group(2)
            candidate = f"{global_month} {day}, {fallback_year or year}"
            return candidate
        
        return None

    def _extract_payment_terms(
        self,
        raw_text: str,
        due_value: Optional[Any],
    ) -> Optional[str]:
        """
        Extract payment terms like "NET 30 DAYS" from OCR text or a numeric due value.
        """
        combined = " ".join(
            part for part in [raw_text or "", str(due_value or "")] if part
        ).strip()
        if not combined:
            return None

        match = re.search(
            r"\\b(?:net|due)(?:\\s+due)?\\s*(\\d{1,3})\\s*(?:day[s5]?|da[vye5]s?)\\b",
            combined,
            re.IGNORECASE,
        )
        if not match:
            match = re.search(r"\\bnet\\s*(\\d{1,3})\\b", combined, re.IGNORECASE)
        if match:
            try:
                days = int(match.group(1))
            except ValueError:
                return None
            if 0 < days <= 365:
                return f"NET {days} DAYS"

        if due_value is not None:
            digits = re.search(r"\\b(\\d{1,3})\\b", str(due_value))
            if digits:
                days = int(digits.group(1))
                if 0 < days <= 365 and re.search(r"\\bnet\\b", raw_text or "", re.IGNORECASE):
                    return f"NET {days} DAYS"

        return None
    
    def _validate_fields_with_heuristics(
        self,
        extracted_data: Dict[str, Any],
        raw_ocr_text: str = None,
        doc_type: str = 'invoice'
    ) -> Dict[str, Any]:
        """
        PHASE 3: Validate individual fields with advanced heuristics
        
        COMPLETE - All fields validated including due_date
        
        Returns:
            {
                'validated_data': Dict,
                'corrections': List[str],
                'warnings': List[str],
                'metadata': Dict
            }
        """
        validated = {}
        corrections = []
        warnings = []
        metadata = {}
        invoice_year: Optional[int] = None
        
        # Validate vendor_name with PHASE 2 heuristics
        if 'vendor_name' in extracted_data:
            is_valid_vendor, suggested_vendor, reason = self.heuristics.detect_vendor_vs_customer(
                extracted_vendor=extracted_data['vendor_name'],
                extracted_customer=extracted_data.get('customer_name'),
                ocr_text=raw_ocr_text or ''
            )
            
            if not is_valid_vendor and suggested_vendor:
                # Use suggested vendor
                validated['vendor_name'] = suggested_vendor
                corrections.append('vendor_name_heuristic_corrected')
                warnings.append(f"Vendor corrected: '{extracted_data['vendor_name']}' → '{suggested_vendor}' ({reason})")
                logger.info(f"   🔧 Vendor corrected: {reason}")
            elif not is_valid_vendor:
                # Flag for review but keep original
                validated['vendor_name'] = extracted_data['vendor_name']
                warnings.append(f"Vendor validation warning: {reason}")
                logger.warning(f"   ⚠️  Vendor warning: {reason}")
            else:
                validated['vendor_name'] = extracted_data['vendor_name']
            
            metadata['vendor_name'] = {
                'is_valid': is_valid_vendor,
                'reason': reason,
                'suggested': suggested_vendor
            }
        
        # Validate invoice_number with PHASE 2 pattern validation
        if 'invoice_number' in extracted_data:
            is_valid, cleaned, reason = self.heuristics.validate_invoice_number_pattern(
                invoice_number=extracted_data['invoice_number'],
                vendor_name=validated.get('vendor_name')
            )
            
            if is_valid and cleaned:
                validated['invoice_number'] = cleaned
                if cleaned != str(extracted_data['invoice_number']):
                    corrections.append('invoice_number_cleaned')
                    logger.info(f"   Cleaned invoice number: '{extracted_data['invoice_number']}' → '{cleaned}'")
            else:
                validated['invoice_number'] = extracted_data['invoice_number']
                warnings.append(f"Invoice number warning: {reason}")
                logger.warning(f"   ⚠️  Invoice number: {reason}")
            
            metadata['invoice_number'] = {
                'is_valid': is_valid,
                'reason': reason
            }
            # Extract year hint from invoice_number if present
            if cleaned:
                match_year = re.search(r"(20\d{2})", cleaned)
                if match_year:
                    invoice_year = int(match_year.group(1))
        
        
        # PHASE 3: Validate invoice_date (with impossible date detection)
        if 'invoice_date' in extracted_data:
            original_invoice_date = extracted_data['invoice_date']
            is_valid, cleaned = self.field_validator.validate_invoice_date(original_invoice_date)
            if is_valid and cleaned:
                validated['invoice_date'] = cleaned
                invoice_year = int(cleaned.split('-')[0]) if len(cleaned) >= 4 else None
                if cleaned != original_invoice_date:
                    corrections.append('invoice_date_standardized')
                    logger.info(f"   Standardized invoice date: '{original_invoice_date}' -> '{cleaned}'")
            else:
                recovered_raw = self._extract_date_from_text(
                    raw_ocr_text or '',
                    labels=['invoice date', 'date', 'invoice']
                )
                if recovered_raw:
                    recovered_valid, recovered_clean = self.field_validator.validate_invoice_date(recovered_raw)
                    if recovered_valid and recovered_clean:
                        validated['invoice_date'] = recovered_clean
                        invoice_year = int(recovered_clean.split('-')[0]) if len(recovered_clean) >= 4 else None
                        corrections.append('invoice_date_from_ocr_text')
                        logger.info(f"   Recovered invoice date from OCR text: '{recovered_raw}' -> '{recovered_clean}'")
                    else:
                        # Try repairing monthless date using invoice number year as hint
                        repaired = self._repair_monthless_date(
                            raw_ocr_text or '',
                            labels=['invoice date', 'date', 'invoice'],
                            fallback_year=invoice_year
                        )
                        if repaired:
                            repaired_valid, repaired_clean = self.field_validator.validate_invoice_date(repaired)
                            if repaired_valid and repaired_clean:
                                validated['invoice_date'] = repaired_clean
                                invoice_year = int(repaired_clean.split('-')[0]) if len(repaired_clean) >= 4 else None
                                corrections.append('invoice_date_from_ocr_text')
                                logger.info(f"   Repaired invoice date: '{repaired}' -> '{repaired_clean}'")
                            else:
                                warnings.append(f"Invalid invoice date: '{original_invoice_date}' - rejected")
                                logger.warning(f"   Rejected invalid invoice date: '{original_invoice_date}'")
                        else:
                            warnings.append(f"Invalid invoice date: '{original_invoice_date}' - rejected")
                            logger.warning(f"   Rejected invalid invoice date: '{original_invoice_date}'")
                else:
                    warnings.append(f"Invalid invoice date: '{original_invoice_date}' - rejected")
                    logger.warning(f"   Rejected invalid invoice date: '{original_invoice_date}'")
                    # Don't include invalid date
                    # validated['invoice_date'] = None
        
        # PHASE 3: Capture payment terms from due_date when OCR shows NET terms
        payment_terms = self._extract_payment_terms(raw_ocr_text or '', extracted_data.get('due_date'))
        if payment_terms:
            validated['payment_terms'] = payment_terms
            corrections.append('payment_terms_from_due_date')
            metadata['payment_terms'] = {
                'source': 'due_date',
                'value': payment_terms
            }

        # PHASE 3: NEW - Validate due_date (same validation as invoice_date)
        if 'due_date' in extracted_data and not payment_terms:
            original_due_date = extracted_data['due_date']
            is_valid, cleaned = self.field_validator.validate_invoice_date(original_due_date)
            if is_valid and cleaned:
                validated['due_date'] = cleaned
                if cleaned != original_due_date:
                    corrections.append('due_date_standardized')
                    logger.info(f"   Standardized due date: '{original_due_date}' -> '{cleaned}'")
            else:
                recovered_raw = self._extract_date_from_text(
                    raw_ocr_text or '',
                    labels=['due date', 'payment due', 'payment terms'],
                    fallback_year=invoice_year
                )
                if recovered_raw:
                    recovered_valid, recovered_clean = self.field_validator.validate_invoice_date(recovered_raw)
                    if recovered_valid and recovered_clean:
                        validated['due_date'] = recovered_clean
                        corrections.append('due_date_from_ocr_text')
                        logger.info(f"   Recovered due date from OCR text: '{recovered_raw}' -> '{recovered_clean}'")
                    else:
                        repaired = self._repair_monthless_date(
                            raw_ocr_text or '',
                            labels=['due date', 'payment due', 'payment terms'],
                            fallback_year=invoice_year
                        )
                        if repaired:
                            repaired_valid, repaired_clean = self.field_validator.validate_invoice_date(repaired)
                            if repaired_valid and repaired_clean:
                                validated['due_date'] = repaired_clean
                                corrections.append('due_date_from_ocr_text')
                                logger.info(f"   Repaired due date: '{repaired}' -> '{repaired_clean}'")
                            else:
                                warnings.append(f"Invalid due date: '{original_due_date}' - impossible date rejected")
                                logger.warning(f"   Rejected impossible due date: '{original_due_date}'")
                        else:
                            warnings.append(f"Invalid due date: '{original_due_date}' - impossible date rejected")
                            logger.warning(f"   Rejected impossible due date: '{original_due_date}'")
                else:
                    warnings.append(f"Invalid due date: '{original_due_date}' - impossible date rejected")
                    logger.warning(f"   Rejected impossible due date: '{original_due_date}'")
                    # Don't include invalid due date in validated data
                    metadata['due_date'] = {
                        'is_valid': False,
                        'reason': 'Impossible date (e.g., November 35)',
                        'original_value': original_due_date
                    }
        
        # PHASE 3: Validate total_amount - CRITICAL - ALL DECIMAL FORMATS + ZERO/NEGATIVE
        if 'total_amount' in extracted_data:
            is_valid, cleaned, amount_metadata = self.field_validator.validate_total_amount(
                extracted_data['total_amount'],
                raw_ocr_text
            )
            
            if is_valid and cleaned is not None:
                validated['total_amount'] = cleaned
                metadata['total_amount'] = amount_metadata
                
                # Check if correction was applied
                if amount_metadata.get('correction_applied'):
                    corrections.append('total_amount_decimal_format_corrected')
                    logger.info(
                        f"   💰 Amount corrected: {amount_metadata['original_value']} → ${cleaned:.2f} "
                        f"(format: {amount_metadata['format_detected']})"
                    )
                
                # PHASE 2: Round number detection
                is_suspicious, round_warning = self.heuristics.detect_suspicious_round_number(
                    amount=cleaned,
                    line_items=[]  # Will be passed in next step
                )
                
                if is_suspicious and round_warning:
                    warnings.append(round_warning)
                    metadata['total_amount']['round_number_warning'] = round_warning
                
                # Add warning if flagged (but don't fail validation for zero/negative)
                if amount_metadata.get('warning'):
                    warning_text = amount_metadata['warning']
                    
                    # PHASE 3: Don't treat zero/negative as critical warnings
                    if 'credit note' in warning_text.lower() or 'no charge' in warning_text.lower():
                        logger.info(f"   ℹ️  {warning_text}")
                        # Add as info, not warning
                    else:
                        warnings.append(warning_text)
            else:
                warnings.append(f"Invalid total amount: '{extracted_data['total_amount']}'")
                validated['total_amount'] = extracted_data['total_amount']
                if amount_metadata:
                    metadata['total_amount'] = amount_metadata
        
        # PHASE 2: Validate currency with inference
        if 'currency' not in extracted_data or not extracted_data['currency']:
            # Infer currency
            amount_text = str(extracted_data.get('total_amount', ''))
            inferred_currency, currency_conf, currency_reason = self.heuristics.infer_currency_from_context(
                amount_text=amount_text,
                ocr_text=raw_ocr_text or ''
            )
            
            validated['currency'] = inferred_currency
            corrections.append('currency_inferred')
            logger.info(f"   💱 Currency inferred: {inferred_currency} ({currency_reason})")
            
            metadata['currency'] = {
                'inferred': True,
                'confidence': currency_conf,
                'reason': currency_reason
            }
        else:
            is_valid, cleaned = self.field_validator.validate_currency(extracted_data['currency'])
            validated['currency'] = cleaned
        
        # Copy over any other fields that weren't validated
        for key, value in extracted_data.items():
            if key not in validated:
                validated[key] = value
        
        return {
            'validated_data': validated,
            'corrections': corrections,
            'warnings': warnings,
            'metadata': metadata
        }
    
    def _apply_advanced_heuristics(
        self,
        validated_data: Dict[str, Any],
        confidences: Dict[str, float],
        line_items: List[Dict] = None,
        raw_ocr_text: str = None,
        known_vendor: str = None,
        vendor_id: int = None
    ) -> Dict[str, Any]:
        """
        PHASE 2: Apply advanced heuristics
        
        Returns:
            {
                'corrections': Dict[field, corrected_value],
                'warnings': List[str],
                'metadata': Dict
            }
        """
        corrections = {}
        warnings = []
        metadata = {}
        
        # Heuristic 1: Multi-amount selection (if multiple amounts detected)
        # This would require detecting multiple amounts in raw OCR
        # For now, we validate the single amount we have
        
        # Heuristic 2: Vendor consistency check
        if 'vendor_name' in validated_data and known_vendor:
            vendor_match = validated_data['vendor_name'].lower() == known_vendor.lower()
            
            if not vendor_match:
                # Check if they're similar
                if known_vendor.lower() in validated_data['vendor_name'].lower():
                    logger.info(f"   ✓ Vendor variation accepted: '{validated_data['vendor_name']}' ≈ '{known_vendor}'")
                else:
                    warnings.append(
                        f"Vendor mismatch: extracted '{validated_data['vendor_name']}' "
                        f"but known vendor is '{known_vendor}'"
                    )
        
        # Heuristic 3: Round number suspicion (with line items)
        if 'total_amount' in validated_data and line_items:
            is_suspicious, round_warning = self.heuristics.detect_suspicious_round_number(
                amount=validated_data['total_amount'],
                line_items=line_items
            )
            
            if is_suspicious and round_warning:
                warnings.append(round_warning)
                metadata['round_number_check'] = {
                    'is_suspicious': True,
                    'warning': round_warning
                }
        
        return {
            'corrections': corrections,
            'warnings': warnings,
            'metadata': metadata
        }
    
    def _adjust_confidences_from_field_validation(
        self,
        confidences: Dict[str, float],
        validation_metadata: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Adjust confidences based on validation results
        """
        adjusted = confidences.copy()
        
        # If amount had format correction, reduce confidence
        if 'total_amount' in validation_metadata:
            meta = validation_metadata['total_amount']
            if meta.get('correction_applied'):
                # Reduce confidence by 10 points for format correction
                if 'total_amount' in adjusted:
                    adjusted['total_amount'] = max(85.0, adjusted['total_amount'] - 10)
                    logger.debug(f"   Reduced total_amount confidence to {adjusted['total_amount']:.1f}%")
            
            if meta.get('warning') and 'credit note' not in meta.get('warning', '').lower():
                # Reduce confidence by 15 points for warnings (except credit note info)
                if 'total_amount' in adjusted:
                    adjusted['total_amount'] = max(70.0, adjusted['total_amount'] - 15)
                    logger.debug(f"   Reduced total_amount confidence to {adjusted['total_amount']:.1f}%")
        
        # Reduce confidence for vendor if heuristic warnings
        if 'vendor_name' in validation_metadata:
            meta = validation_metadata['vendor_name']
            if not meta.get('is_valid'):
                if 'vendor_name' in adjusted:
                    adjusted['vendor_name'] = max(60.0, adjusted['vendor_name'] - 20)
                    logger.debug(f"   Reduced vendor_name confidence to {adjusted['vendor_name']:.1f}%")
        
        # PHASE 3: Reduce confidence for rejected due_date
        if 'due_date' in validation_metadata:
            meta = validation_metadata['due_date']
            if not meta.get('is_valid'):
                if 'due_date' in adjusted:
                    adjusted['due_date'] = max(30.0, adjusted['due_date'] - 50)
                    logger.debug(f"   Reduced due_date confidence to {adjusted['due_date']:.1f}%")
        
        return adjusted
    
    def _calculate_overall_confidence(
        self,
        field_confidences: Dict[str, float],
        warnings: List[str]
    ) -> float:
        """
        Calculate overall confidence score
        
        Factors:
        - Average field confidence
        - Number of warnings
        - Critical field presence
        """
        if not field_confidences:
            return 0.0
        
        # Base confidence = average of field confidences
        avg_confidence = sum(field_confidences.values()) / len(field_confidences)
        
        # PHASE 3: Filter informational warnings before penalty calculation
        info_warnings = ['credit note', 'no charge', 'negative amount', 'zero amount']
        critical_warnings = [
            w for w in warnings 
            if not any(info in w.lower() for info in info_warnings)
        ]
        
        # Penalty for critical warnings (5% per warning, max 30%)
        warning_penalty = min(len(critical_warnings) * 5, 30)
        
        # Apply penalty
        overall = max(0.0, avg_confidence - warning_penalty)
        
        return round(overall, 2)
    
    def _determine_needs_review(
        self,
        warnings: List[str],
        overall_confidence: float,
        corrections_applied: List[str],
        doc_type: str
    ) -> bool:
        """
        PHASE 3: Determine if invoice needs human review
        
        Enhanced:
        - Filters informational warnings (credit note, no charge)
        - Considers impossible date rejection
        """
        # PHASE 3: Filter out informational warnings (not critical)
        info_warnings = ['credit note', 'no charge', 'negative amount', 'zero amount']
        critical_warnings = [
            w for w in warnings 
            if not any(info in w.lower() for info in info_warnings)
        ]
        
        # Flag 1: Has critical warnings
        if len(critical_warnings) > 0:
            logger.info(f"   ⚠️  Needs review: {len(critical_warnings)} critical warnings")
            return True
        
        # Flag 2: Low confidence
        if overall_confidence < 85:
            logger.info(f"   ⚠️  Needs review: Low confidence ({overall_confidence:.1f}%)")
            return True
        
        # Flag 3: Critical corrections applied
        critical_corrections = [
            'total_amount_decimal_format_corrected',
            'total_amount_magnitude_corrected',
            'vendor_name_heuristic_corrected',
            'invoice_date_standardized'
        ]
        
        if any(corr in corrections_applied for corr in critical_corrections):
            logger.info(f"   ⚠️  Needs review: Critical corrections applied")
            return True
        
        # PHASE 3: Flag 4: Credit notes always need review
        if doc_type == 'credit_note':
            logger.info(f"   ⚠️  Needs review: Document is credit note")
            return True
        
        return False


# Singleton
validation_service = ValidationService()

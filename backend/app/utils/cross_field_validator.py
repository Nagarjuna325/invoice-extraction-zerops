import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CrossFieldValidator:
    """Validates relationships between extracted invoice fields - PRODUCTION READY"""

    @staticmethod
    def validate_line_items_vs_total(
        line_items: List[Dict[str, Any]],
        total_amount: float,
        tolerance: float = 0.02,
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """Validate that line items sum matches total amount."""
        if not line_items or not total_amount:
            return True, None, None  # Can't validate if missing

        try:
            amounts = []
            for item in line_items:
                amount = item.get("amount")
                if amount is None:
                    continue
                try:
                    amounts.append(float(amount))
                except Exception:
                    continue
            line_items_sum = sum(amounts)
            difference = abs(line_items_sum - total_amount)
            percent_diff = (difference / total_amount) * 100 if total_amount > 0 else 0

            metadata = {
                "line_items_sum": line_items_sum,
                "declared_total": total_amount,
                "difference": difference,
                "percent_difference": percent_diff,
                "line_item_count": len(line_items),
                "line_item_amount_count": len(amounts),
            }

            if difference <= tolerance:
                logger.info(
                    f"✅ Line items match total: ${line_items_sum:.2f} ≈ ${total_amount:.2f}"
                )
                return True, None, metadata

            warning = (
                f"Line items sum (${line_items_sum:.2f}) doesn't match "
                f"total (${total_amount:.2f}). Difference: ${difference:.2f} ({percent_diff:.1f}%)"
            )
            logger.warning(f"⚠️  {warning}")
            return False, warning, metadata

        except Exception as e:
            logger.error(f"Error validating line items: {e}")
            return True, None, None  # Don't fail validation on error

    @staticmethod
    def validate_amount_magnitude(
        amount: float,
        field_name: str = "total_amount",
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate amount magnitude - PHASE 3 BULLETPROOF

        Now supports:
        - Negative amounts (credit notes)
        - Zero amounts (no charge invoices)
        - STRING amounts (converts automatically)
        """
        if amount is None:
            return True, None

        # BULLETPROOF: Convert to float if string
        try:
            if isinstance(amount, str):
                cleaned = re.sub(r"[^\d\-\.,]", "", str(amount))
                cleaned = cleaned.replace(",", ".")
                amount_val = float(cleaned)
            elif isinstance(amount, (int, float)):
                amount_val = float(amount)
            else:
                logger.warning(f"⚠️  Amount has unexpected type: {type(amount)}")
                return True, None
        except (ValueError, TypeError) as e:
            logger.error(f"❌ Could not parse amount: {amount} ({e})")
            return False, f"Could not parse amount: {amount}"

        if amount_val < 0:
            logger.info(f"✅ Negative amount accepted: ${amount_val:.2f} (credit note)")
            return True, f"Negative amount (${amount_val:.2f}) - this is a credit note"

        if amount_val == 0.0:
            logger.info("✅ Zero amount accepted: $0.00 (no charge invoice)")
            return True, "Zero amount - 'No Charge' invoice"

        is_whole = amount_val % 1 == 0

        if 0.01 < amount_val < 10:
            warning = (
                f"{field_name} is ${amount_val:.2f} - suspiciously small. "
                f"Might be wrong decimal format? (e.g., should be ${amount_val * 100:.2f}?)"
            )
            logger.warning(f"⚠️  {warning}")
            return False, warning

        if amount_val > 10000 and is_whole:
            warning = (
                f"{field_name} is ${amount_val:,.0f} - suspiciously large whole number. "
                f"Might be missing decimal? (e.g., should be ${amount_val/100:.2f}?)"
            )
            logger.warning(f"⚠️  {warning}")
            return False, warning

        if amount_val > 100000:
            warning = f"{field_name} is ${amount_val:,.2f} - unusually high for typical invoice"
            logger.warning(f"⚠️  {warning}")
            return False, warning

        return True, None

    @staticmethod
    def detect_decimal_format_error_from_ocr(
        amount: float,
        raw_ocr_text: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        Detect if amount has decimal format error - BULLETPROOF

        Returns:
            (has_error, warning, suggested_correction)
        """
        if not raw_ocr_text:
            return False, None, None

        # BULLETPROOF: Convert amount to float
        try:
            if isinstance(amount, str):
                cleaned = re.sub(r"[^\d\-\.,]", "", str(amount))
                cleaned = cleaned.replace(",", ".")
                amount_val = float(cleaned)
            elif isinstance(amount, (int, float)):
                amount_val = float(amount)
            else:
                return False, None, None
        except (ValueError, TypeError):
            return False, None, None

        amount_patterns = [
            (r"\$?\s*(\d{1,3})\.(\d{3}),(\d{2})\b", "european_period_thousands"),  # 1.750,00
            (r"\$?\s*(\d+),(\d{2})\b", "european_comma"),  # 824,13
            (r"\$?\s*(\d{1,3}),(\d{3})\.(\d{2})\b", "us"),  # 1,750.00
            (r"\$?\s*(\d+)\.(\d{2})\b", "us_simple"),  # 824.13
        ]

        for pattern, format_type in amount_patterns:
            matches = re.finditer(pattern, raw_ocr_text)
            for match in matches:
                correct_amount = None
                wrong_interpretations: List[float] = []

                if format_type == "european_period_thousands":
                    thousands, hundreds, cents = match.group(1), match.group(2), match.group(3)
                    correct_amount = float(f"{thousands}{hundreds}.{cents}")
                    wrong_interpretations = [
                        float(f"{thousands}.{hundreds}{cents}"),
                        float(f"{thousands}.{hundreds}"),
                        float(thousands),
                    ]
                elif format_type == "european_comma":
                    dollars, cents = match.group(1), match.group(2)
                    correct_amount = float(f"{dollars}.{cents}")
                    wrong_interpretations = [float(f"{dollars}{cents}"), float(dollars)]
                elif format_type == "us":
                    thousands, hundreds, cents = match.group(1), match.group(2), match.group(3)
                    correct_amount = float(f"{thousands}{hundreds}.{cents}")
                elif format_type == "us_simple":
                    dollars, cents = match.group(1), match.group(2)
                    correct_amount = float(f"{dollars}.{cents}")

                for wrong_val in wrong_interpretations:
                    if abs(amount_val - wrong_val) < 0.01:
                        warning = (
                            "Decimal format error! "
                            f"OCR shows {match.group(0)} but extracted as ${amount_val:,.2f}. "
                            f"Should be ${correct_amount:,.2f}"
                        )
                        logger.warning(f"🔍 {warning}")
                        return True, warning, correct_amount

        return False, None, None

    @staticmethod
    def validate_date_consistency(
        invoice_date: str,
        due_date: Optional[str] = None,
        ship_date: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Validate date field consistency."""
        if not invoice_date:
            return True, None

        try:
            inv_date = datetime.strptime(invoice_date, "%Y-%m-%d")
            current_date = datetime.now()

            if inv_date > current_date:
                warning = f"Invoice date {invoice_date} is in the future"
                logger.warning(f"⚠️  {warning}")
                return False, warning

            years_old = (current_date - inv_date).days / 365
            if years_old > 5:
                warning = f"Invoice date {invoice_date} is {years_old:.1f} years old"
                logger.warning(f"⚠️  {warning}")
                return False, warning

            if due_date:
                try:
                    d_date = datetime.strptime(due_date, "%Y-%m-%d")
                    if d_date < inv_date:
                        warning = f"Due date {due_date} is before invoice date {invoice_date}"
                        logger.warning(f"⚠️  {warning}")
                        return False, warning

                    days_diff = (d_date - inv_date).days
                    if days_diff > 180:
                        warning = f"Payment terms too long: {days_diff} days"
                        logger.warning(f"⚠️  {warning}")
                        return False, warning
                except ValueError:
                    pass  # Invalid due date format, skip

            return True, None

        except ValueError as e:
            logger.error(f"Error parsing date: {e}")
            return True, None  # Don't fail on parse error

    @staticmethod
    def validate_vendor_consistency(
        extracted_vendor: str,
        known_vendor_name: Optional[str] = None,
        vendor_id: Optional[int] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Validate vendor name consistency."""
        if not extracted_vendor:
            return True, None

        if known_vendor_name and vendor_id:
            extracted_norm = extracted_vendor.lower().strip()
            known_norm = known_vendor_name.lower().strip()

            if extracted_norm != known_norm:
                if extracted_norm in known_norm or known_norm in extracted_norm:
                    logger.info(
                        f"✅ Vendor name variation accepted: '{extracted_vendor}' ≈ '{known_vendor_name}'"
                    )
                    return True, None
                warning = (
                    f"Extracted vendor '{extracted_vendor}' doesn't match "
                    f"known vendor '{known_vendor_name}' (ID: {vendor_id})"
                )
                logger.warning(f"⚠️  {warning}")
                return False, warning

        return True, None

    @staticmethod
    def validate_all_cross_fields(
        extracted_data: Dict[str, Any],
        line_items: Optional[List[Dict[str, Any]]] = None,
        known_vendor: Optional[str] = None,
        vendor_id: Optional[int] = None,
        raw_ocr_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run all cross-field validations.

        Returns:
            {
                'is_valid': bool,
                'warnings': List[str],
                'needs_review': bool,
                'suggested_corrections': Dict[str, Any],
                'metadata': Dict[str, Any]
            }
        """
        warnings: List[str] = []
        suggested_corrections: Dict[str, Any] = {}
        metadata: Dict[str, Any] = {}

        if "total_amount" in extracted_data:
            is_valid, warning = CrossFieldValidator.validate_amount_magnitude(
                extracted_data["total_amount"]
            )
            if not is_valid and warning:
                warnings.append(warning)

        if "total_amount" in extracted_data and raw_ocr_text:
            has_error, warning, correction = CrossFieldValidator.detect_decimal_format_error_from_ocr(
                extracted_data["total_amount"], raw_ocr_text
            )
            if has_error and warning:
                warnings.append(warning)
                suggested_corrections["total_amount"] = correction

        if line_items and "total_amount" in extracted_data:
            is_valid, warning, line_meta = CrossFieldValidator.validate_line_items_vs_total(
                line_items, extracted_data["total_amount"]
            )
            if not is_valid and warning:
                warnings.append(warning)
            if line_meta:
                metadata["line_items_validation"] = line_meta

        if "invoice_date" in extracted_data:
            is_valid, warning = CrossFieldValidator.validate_date_consistency(
                extracted_data.get("invoice_date"),
                extracted_data.get("due_date"),
                extracted_data.get("ship_date"),
            )
            if not is_valid and warning:
                warnings.append(warning)

        if "vendor_name" in extracted_data:
            is_valid, warning = CrossFieldValidator.validate_vendor_consistency(
                extracted_data["vendor_name"], known_vendor, vendor_id
            )
            if not is_valid and warning:
                warnings.append(warning)

        return {
            "is_valid": len(warnings) == 0,
            "warnings": warnings,
            "needs_review": len(warnings) > 0,
            "suggested_corrections": suggested_corrections,
            "metadata": metadata,
        }


cross_validator = CrossFieldValidator()

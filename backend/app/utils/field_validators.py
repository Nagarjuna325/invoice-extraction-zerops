import calendar
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class FieldValidator:
    """Validates and cleans extracted invoice fields - PRODUCTION READY"""

    @staticmethod
    def detect_decimal_format(value_str: str) -> Tuple[str, str]:
        """
        Detect decimal format - HANDLES ALL CASES

        Formats supported:
        - US: 1,750.00 (comma=thousands, period=decimal)
        - EU Type 1: 824,13 (comma=decimal only)
        - EU Type 2: 1.750,00 (period=thousands, comma=decimal)
        - EU Type 3: 1 750,00 (space=thousands, comma=decimal)

        Returns:
            (format_type, explanation)
        """
        cleaned = re.sub(r"[$€£¥]", "", value_str).strip()

        comma_count = cleaned.count(",")
        period_count = cleaned.count(".")

        last_comma_pos = cleaned.rfind(",")
        last_period_pos = cleaned.rfind(".")

        if comma_count > 0 and period_count > 0:
            if last_comma_pos > last_period_pos:
                digits_after_comma = len(cleaned) - last_comma_pos - 1
                if digits_after_comma == 2:
                    return "european_period_thousands", "European: period for thousands, comma for decimal (1.750,00)"
                return "ambiguous", f"Unusual format: {digits_after_comma} digits after comma"
            digits_after_period = len(cleaned) - last_period_pos - 1
            if digits_after_period == 2:
                return "us", "US: comma for thousands, period for decimal (1,750.00)"
            if digits_after_period == 3:
                return "us_three_decimals", "US format with 3 decimals"
            return "ambiguous", f"Unusual format: {digits_after_period} digits after period"

        if comma_count > 0 and period_count == 0:
            digits_after_comma = len(cleaned) - last_comma_pos - 1
            if digits_after_comma == 2:
                return "european_comma", "European: comma as decimal (824,13)"
            if digits_after_comma == 3:
                return "us_no_decimals", "US: comma as thousands, no decimals"
            return "ambiguous", f"{digits_after_comma} digits after comma"

        if period_count > 0 and comma_count == 0:
            digits_after_period = len(cleaned) - last_period_pos - 1
            if digits_after_period == 2:
                return "us_period", "US: period as decimal (824.13)"
            if digits_after_period == 3:
                return "european_no_decimals", "European: period as thousands, no decimals"
            return "ambiguous", f"{digits_after_period} digits after period"

        if comma_count == 0 and period_count == 0:
            return "no_separator", "No decimal or thousand separator"

        return "ambiguous", "Cannot determine format"

    @staticmethod
    def normalize_decimal_format(value_str: str) -> float:
        """
        Convert ANY decimal format to standard float

        Handles:
        - 1,750.00 → 1750.00 (US)
        - 824,13 → 824.13 (EU comma decimal)
        - 1.750,00 → 1750.00 (EU period thousands)
        - 1 750,00 → 1750.00 (EU space thousands)
        """
        cleaned = re.sub(r"[$€£¥\s]", "", value_str)

        format_type, explanation = FieldValidator.detect_decimal_format(value_str)
        logger.debug(f"Amount format: {format_type} - {explanation} for '{value_str}'")

        if format_type in ["european_comma", "european_period_thousands"]:
            normalized = cleaned.replace(".", "").replace(" ", "").replace(",", ".")
        elif format_type in ["us", "us_period", "us_three_decimals"]:
            normalized = cleaned.replace(",", "").replace(" ", "")
        elif format_type in ["us_no_decimals", "european_no_decimals"]:
            normalized = cleaned.replace(",", "").replace(".", "").replace(" ", "")
        elif format_type == "no_separator":
            normalized = cleaned
        else:
            if "," in cleaned and cleaned.rfind(",") > cleaned.rfind("."):
                normalized = cleaned.replace(".", "").replace(" ", "").replace(",", ".")
            else:
                normalized = cleaned.replace(",", "").replace(" ", "")

        try:
            result = float(normalized)
            logger.info(f"✅ Amount normalized: '{value_str}' → {result} (format: {format_type})")
            return result
        except ValueError as e:
            logger.error(f"❌ Failed to convert '{value_str}' to float after normalization to '{normalized}'")
            raise ValueError(f"Cannot parse amount '{value_str}': {e}")

    @staticmethod
    def validate_vendor_name(value: str) -> Tuple[bool, Optional[str]]:
        """Validate and clean vendor name"""
        if not value or len(value) < 3:
            return False, None

        cleaned = value.strip()
        cleaned = re.sub(r"^[~@#$%^&*()_+=\[\]{};:\"|<>?/\\]+", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)

        if not re.search(r"[A-Za-z]{2,}", cleaned):
            return False, None

        if cleaned.replace(" ", "").isdigit():
            return False, None

        customer_keywords = [r"\bBill\s+To\b", r"\bCustomer\b", r"\bClient\b", r"\bRecipient\b"]
        for pattern in customer_keywords:
            if re.search(pattern, cleaned, re.IGNORECASE):
                logger.warning(f"Rejected vendor name '{cleaned}' - contains customer indicator")
                return False, None

        return True, cleaned

    @staticmethod
    def validate_invoice_number(value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate and clean invoice number
        FIXED: Keep important prefixes like "INV-"
        """
        if not value:
            return False, None

        cleaned = str(value).strip()
        cleaned = re.sub(r"^(invoice|order|#|no\.?)[\s:]+", "", cleaned, flags=re.IGNORECASE)

        if not re.search(r"\d", cleaned):
            return False, None

        if re.match(r"^\d{2}[-/]\d{2}[-/]\d{2,4}$", cleaned):
            return False, None

        if len(cleaned) < 4:
            return False, None

        if len(cleaned) > 30:
            return False, None

        return True, cleaned

    @staticmethod
    def validate_invoice_date(value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate and clean invoice date
        PHASE 3: ENHANCED - Rejects impossible dates and repairs when possible
        """
        if not value:
            return False, None

        cleaned = str(value).strip()

        if re.match(r"^\d{4}$", cleaned):
            logger.warning(f"Rejected date '{cleaned}' - year only")
            return False, None

        cleaned_numeric = cleaned.replace(".", "-").replace("/", "-")

        date_formats = [
            "%B %d, %Y",
            "%b %d, %Y",
            "%B %d %Y",
            "%b %d %Y",
            "%d %B %Y",
            "%d %b %Y",
            "%Y-%m-%d",
            "%m-%d-%Y",
            "%d-%m-%Y",
            "%Y%m%d",
            "%m/%d/%y",
            "%m-%d-%y",
            "%d/%m/%y",
            "%d-%m-%y",
        ]

        def _repair_impossible_date(raw: str) -> Optional[str]:
            text_pattern = re.compile(
                r"^(?P<month>[A-Za-z]+)\s+(?P<day>\d{1,2}),?\s*(?P<year>\d{2,4})$",
                re.IGNORECASE,
            )
            num_pattern = re.compile(r"^(?P<month>\d{1,2})[-/](?P<day>\d{1,2})[-/](?P<year>\d{2,4})$")

            m = text_pattern.match(raw) or num_pattern.match(raw.replace(".", "-"))
            if not m:
                return None

            try:
                month_token = m.group("month")
                day = int(m.group("day"))
                year = int(m.group("year"))
                if year < 100:
                    year += 2000 if year < 50 else 1900

                if month_token.isdigit():
                    month = int(month_token)
                else:
                    month = datetime.strptime(month_token[:3], "%b").month

                if not (1990 <= year <= 2030) or not (1 <= month <= 12):
                    return None

                max_day = calendar.monthrange(year, month)[1]
                repaired_day = min(day, max_day)
                return f"{year:04d}-{month:02d}-{repaired_day:02d}"
            except Exception:
                return None

        for fmt in date_formats[:6]:
            try:
                parsed_date = datetime.strptime(cleaned, fmt)
                datetime(parsed_date.year, parsed_date.month, parsed_date.day)
                if 1990 <= parsed_date.year <= 2030:
                    result = parsed_date.strftime("%Y-%m-%d")
                    logger.info(f"✅ Date parsed: '{cleaned}' → '{result}' (format: {fmt})")
                    return True, result
            except Exception:
                repaired = _repair_impossible_date(cleaned)
                if repaired:
                    logger.warning(f"⚠️  Repaired impossible date '{cleaned}' → '{repaired}'")
                    return True, repaired
                continue

        for fmt in date_formats[6:]:
            try:
                parsed_date = datetime.strptime(cleaned_numeric, fmt)
                datetime(parsed_date.year, parsed_date.month, parsed_date.day)
                if 1990 <= parsed_date.year <= 2030:
                    result = parsed_date.strftime("%Y-%m-%d")
                    logger.info(f"✅ Date parsed: '{cleaned}' → '{result}' (format: {fmt})")
                    return True, result
            except Exception:
                repaired = _repair_impossible_date(cleaned_numeric)
                if repaired:
                    logger.warning(f"⚠️  Repaired impossible date '{cleaned}' → '{repaired}'")
                    return True, repaired
                continue

        logger.warning(f"❌ Could not parse date: '{cleaned}'")
        return False, None

    @staticmethod
    def validate_total_amount(value: Any, raw_text: str = None) -> Tuple[bool, Optional[float], Optional[Dict]]:
        """
        Validate and clean total amount
        PHASE 3: ENHANCED - Supports zero and negative amounts
        """
        metadata = {
            "original_value": value,
            "format_detected": None,
            "correction_applied": False,
            "warning": None,
        }

        if value is None:
            return False, None, metadata

        if isinstance(value, (int, float)):
            amount = float(value)

            if amount < 0:
                logger.info(f"✅ Negative amount accepted: ${amount:.2f} (credit note)")
                metadata["warning"] = "Negative amount - likely credit note"
                return True, amount, metadata

            if amount == 0.0:
                logger.info("✅ Zero amount accepted: $0.00 (no charge invoice)")
                metadata["warning"] = "Zero amount - 'No Charge' invoice"
                return True, 0.0, metadata

            if amount < 0.01:
                metadata["warning"] = f"Amount too small: ${amount:.4f}"
                return False, None, metadata

            if amount > 1_000_000:
                metadata["warning"] = f"Amount too large: ${amount:,.2f}"
                return False, None, metadata

            return True, amount, metadata

        value_str = str(value).strip()

        try:
            format_type, explanation = FieldValidator.detect_decimal_format(value_str)
            metadata["format_detected"] = f"{format_type} ({explanation})"

            amount = FieldValidator.normalize_decimal_format(value_str)
            metadata["correction_applied"] = True

            if amount < 0:
                logger.info(f"✅ Negative amount accepted: ${amount:.2f} (credit note)")
                metadata["warning"] = "Negative amount - likely credit note"
                return True, amount, metadata

            if amount == 0.0:
                if raw_text:
                    no_charge_keywords = ["no charge", "complimentary", "free of charge", "gratis", "waived"]
                    ocr_lower = raw_text.lower()
                    if any(keyword in ocr_lower for keyword in no_charge_keywords):
                        logger.info("✅ Zero amount validated: 'No Charge' invoice detected")
                        metadata["warning"] = "Zero amount invoice (No Charge)"
                        return True, 0.0, metadata

                logger.warning("⚠️  Zero amount detected without 'No Charge' context")
                metadata["warning"] = "Zero amount - verify this is correct"
                return True, 0.0, metadata

            if amount < 0.01:
                metadata["warning"] = f"Amount too small: ${amount:.4f}"
                return False, None, metadata

            if amount > 1_000_000:
                metadata["warning"] = f"Amount too large: ${amount:,.2f}"
                return False, None, metadata

            return True, amount, metadata

        except Exception as e:
            logger.error(f"Failed to parse amount '{value_str}': {e}")
            metadata["warning"] = f"Parse error: {str(e)}"
            return False, None, metadata

    @staticmethod
    def validate_po_number(value: str) -> Tuple[bool, Optional[str]]:
        """Validate PO number"""
        if not value:
            return False, None

        cleaned = str(value).strip()
        cleaned = re.sub(r"^(po|p\.o\.|purchase order)\s*#?\s*:?\s*", "", cleaned, flags=re.IGNORECASE)

        if len(cleaned) < 4:
            return False, None

        if not re.search(r"[A-Za-z0-9]{4,}", cleaned):
            return False, None

        return True, cleaned

    @staticmethod
    def validate_currency(value: str) -> Tuple[bool, Optional[str]]:
        """Validate currency code"""
        if not value:
            return True, "USD"

        cleaned = str(value).strip().upper()
        valid_currencies = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "CNY", "INR"]

        if cleaned in valid_currencies:
            return True, cleaned

        return True, "USD"


validator = FieldValidator()

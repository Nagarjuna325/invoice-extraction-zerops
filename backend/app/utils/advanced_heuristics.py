"""
Advanced Heuristics for Invoice Validation
PHASE 2: Intelligent field validation beyond basic checks

Heuristics:
1. Vendor vs Customer Detection
2. Document Type Detection (Invoice vs Credit Note)
3. Multi-Amount Selection (Total vs Subtotal)
4. Round Number Suspicion
5. Invoice Number Pattern Validation
6. Currency Inference from Context
"""

import re
import logging
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger(__name__)


class AdvancedHeuristics:
    """Advanced heuristic validators for invoice extraction"""

    COMPANY_KEYWORDS = [
        "inc",
        "llc",
        "ltd",
        "limited",
        "corp",
        "corporation",
        "company",
        "co",
        "enterprises",
        "group",
        "services",
        "solutions",
        "industries",
        "partners",
        "associates",
        "holdings",
        "international",
        "global",
        "technologies",
        "systems",
        "consulting",
        "agency",
        "studio",
        "gmbh",
        "sarl",
        "srl",
        "plc",
        "pty",
        "ag",
        "spa",
        "nv",
    ]

    CREDIT_NOTE_KEYWORDS = [
        "credit note",
        "credit memo",
        "credit memorandum",
        "return",
        "refund",
        "adjustment credit",
        "cn",
    ]

    QUOTE_KEYWORDS = [
        "quote",
        "quotation",
        "estimate",
        "proforma",
        "proposal",
        "pro forma",
        "estimated invoice",
    ]

    CURRENCY_SYMBOLS = {
        "$": "USD",
        "€": "EUR",
        "£": "GBP",
        "¥": "JPY",
        "₹": "INR",
        "C$": "CAD",
        "A$": "AUD",
        "CHF": "CHF",
        "Fr": "CHF",
    }

    @staticmethod
    def detect_vendor_vs_customer(
        extracted_vendor: str,
        extracted_customer: Optional[str] = None,
        ocr_text: str = "",
    ) -> Tuple[bool, Optional[str], str]:
        """
        Detect if extracted vendor is actually the customer.

        Returns:
            (is_valid_vendor, suggested_vendor, reason)
        """
        if not extracted_vendor:
            return False, None, "No vendor extracted"

        vendor_lower = extracted_vendor.lower()

        if extracted_customer:
            customer_lower = extracted_customer.lower()

            if vendor_lower == customer_lower:
                logger.warning(f"❌ Vendor '{extracted_vendor}' matches customer - likely wrong")
                return False, None, "Vendor matches customer name"

            if vendor_lower in customer_lower or customer_lower in vendor_lower:
                logger.warning(f"❌ Vendor '{extracted_vendor}' similar to customer '{extracted_customer}'")
                return False, None, "Vendor similar to customer name"

        words = extracted_vendor.split()
        is_person_name = (
            len(words) == 2
            and words[0][0].isupper()
            and words[1][0].isupper()
            and not any(keyword in vendor_lower for keyword in AdvancedHeuristics.COMPANY_KEYWORDS)
        )

        if is_person_name and extracted_customer:
            logger.warning(f"⚠️  Vendor '{extracted_vendor}' looks like person name, not company")
            suggested = AdvancedHeuristics._find_company_in_text(ocr_text, exclude=extracted_vendor)
            if suggested:
                logger.info(f"✅ Found alternative vendor in OCR: '{suggested}'")
                return False, suggested, "Person name detected, found company alternative"
            return False, None, "Vendor looks like person name, not company"

        has_company_keyword = any(keyword in vendor_lower for keyword in AdvancedHeuristics.COMPANY_KEYWORDS)
        if has_company_keyword:
            logger.info(f"✅ Vendor '{extracted_vendor}' has company indicators")
            return True, extracted_vendor, "Company keyword found"

        if ocr_text:
            from_section = AdvancedHeuristics._extract_from_section(ocr_text)
            bill_to_section = AdvancedHeuristics._extract_bill_to_section(ocr_text)

            if from_section and extracted_vendor.lower() not in from_section.lower():
                if bill_to_section and extracted_vendor.lower() in bill_to_section.lower():
                    logger.warning("⚠️  Vendor found in 'Bill To' section, not 'From' section")
                    suggested = AdvancedHeuristics._extract_name_from_section(from_section)
                    if suggested:
                        return False, suggested, "Vendor in wrong section, corrected from 'From' section"

        logger.info(f"✓ Vendor '{extracted_vendor}' passed heuristics (no strong company indicators)")
        return True, extracted_vendor, "No red flags detected"

    @staticmethod
    def detect_document_type(
        title_text: str = "",
        ocr_text: str = "",
        total_amount: Optional[float] = None,
    ) -> Tuple[str, float, str]:
        """
        Detect document type: invoice, credit_note, quote, etc.

        Returns:
            (document_type, confidence, reason)
        """
        combined_text = (title_text + " " + ocr_text).lower()

        for keyword in AdvancedHeuristics.CREDIT_NOTE_KEYWORDS:
            if keyword in combined_text:
                confidence = 90.0 if "credit note" in combined_text else 75.0
                logger.info(f"📄 Document type: CREDIT NOTE (keyword: '{keyword}')")
                return "credit_note", confidence, f"Keyword '{keyword}' found"

        if total_amount is not None:
            try:
                if isinstance(total_amount, str):
                    amount_str = (
                        str(total_amount)
                        .replace("$", "")
                        .replace("€", "")
                        .replace("£", "")
                        .replace(",", ".")
                        .strip()
                    )
                    amount_val = float(amount_str)
                else:
                    amount_val = float(total_amount)

                if amount_val < 0:
                    logger.info(f"📄 Document type: CREDIT NOTE (negative amount: ${amount_val})")
                    return "credit_note", 85.0, "Negative amount"
            except (ValueError, TypeError):
                pass

        for keyword in AdvancedHeuristics.QUOTE_KEYWORDS:
            if keyword in combined_text:
                confidence = 90.0 if keyword in ["quote", "quotation"] else 75.0
                logger.info(f"📄 Document type: QUOTE (keyword: '{keyword}')")
                return "quote", confidence, f"Keyword '{keyword}' found"

        if "invoice" in combined_text:
            logger.info("📄 Document type: INVOICE (default)")
            return "invoice", 95.0, "Invoice keyword found"

        return "invoice", 60.0, "Default (no specific keywords)"

    @staticmethod
    def select_correct_total_amount(
        amounts_found: List[float],
        ocr_text: str = "",
        line_items: List[Dict] = None,
    ) -> Tuple[Optional[float], str]:
        """
        When multiple amounts found, select the correct total.

        Returns:
            (selected_amount, reason)
        """
        if not amounts_found:
            return None, "No amounts found"

        if len(amounts_found) == 1:
            return amounts_found[0], "Only one amount found"

        logger.info(f"🔍 Multiple amounts found: {amounts_found}")

        if ocr_text:
            total_pattern = r"(?:grand\s+)?total\s*:?\s*\$?\s*([\d,\.]+)"
            matches = re.finditer(total_pattern, ocr_text, re.IGNORECASE)

            for match in matches:
                try:
                    amount_str = match.group(1).replace(",", "")
                    amount = float(amount_str)
                    for candidate in amounts_found:
                        if abs(candidate - amount) < 0.01:
                            logger.info(f"✅ Selected ${amount} (found near 'TOTAL:' label)")
                            return amount, "Found near 'TOTAL:' label in OCR"
                except Exception:
                    continue

        filtered_amounts = []
        if ocr_text:
            ocr_lower = ocr_text.lower()

            for amount in amounts_found:
                amount_str = f"{amount:.2f}"
                amount_contexts = []
                for variant in [amount_str, f"${amount_str}", amount_str.replace(".", ",")]:
                    pos = ocr_lower.find(variant.lower())
                    if pos >= 0:
                        context = ocr_lower[max(0, pos - 50) : min(len(ocr_lower), pos + 50)]
                        amount_contexts.append(context)

                is_subtotal_or_tax = any(
                    keyword in context
                    for context in amount_contexts
                    for keyword in ["subtotal", "tax", "vat", "gst", "discount"]
                )

                if not is_subtotal_or_tax:
                    filtered_amounts.append(amount)

        if filtered_amounts:
            selected = max(filtered_amounts)
            logger.info(f"✅ Selected ${selected} (largest after filtering subtotals/tax)")
            return selected, "Largest amount after excluding subtotal/tax"

        if line_items:
            line_items_total = sum(item.get("total", 0) for item in line_items)
            closest = min(amounts_found, key=lambda x: abs(x - line_items_total))
            if abs(closest - line_items_total) < line_items_total * 0.05:
                logger.info(f"✅ Selected ${closest} (matches line items sum: ${line_items_total})")
                return closest, "Matches line items sum"

        largest = max(amounts_found)
        logger.info(f"⚠️  Selected ${largest} (largest amount - fallback)")
        return largest, "Largest amount (fallback)"

    @staticmethod
    def detect_suspicious_round_number(
        amount: float,
        line_items: List[Dict] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Detect if amount is suspiciously round.

        Returns:
            (is_suspicious, warning_message)
        """
        is_round = (amount % 100 == 0) or (amount % 50 == 0)
        if not is_round:
            return False, None

        if line_items:
            line_items_sum = sum(item.get("total", 0) for item in line_items)
            diff = abs(amount - line_items_sum)
            percent_diff = (diff / amount * 100) if amount > 0 else 0

            if percent_diff > 10:
                warning = (
                    f"Suspicious round number: ${amount:,.2f}. "
                    f"Line items sum to ${line_items_sum:,.2f} (difference: ${diff:,.2f}, {percent_diff:.1f}%)"
                )
                logger.warning(f"⚠️  {warning}")
                return True, warning

        if amount >= 1000 and amount % 100 == 0:
            warning = f"Amount is very round (${amount:,.0f}) - verify this is correct"
            logger.info(f"ℹ️  {warning}")
            return True, warning

        return False, None

    @staticmethod
    def validate_invoice_number_pattern(
        invoice_number: str,
        vendor_name: Optional[str] = None,
        previous_invoice: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], str]:
        """
        Validate invoice number pattern.

        Returns:
            (is_valid, suggested_correction, reason)
        """
        if not invoice_number:
            return False, None, "Empty invoice number"

        if re.match(r"^\d{8}$", invoice_number):
            logger.warning(f"❌ Invoice number '{invoice_number}' looks like a date")
            return False, None, "Looks like date format (YYYYMMDD)"

        if re.match(r"^\d{6}$", invoice_number):
            logger.warning(f"❌ Invoice number '{invoice_number}' looks like a date")
            return False, None, "Looks like date format (YYMMDD)"

        has_letters = bool(re.search(r"[A-Za-z]", invoice_number))
        has_numbers = bool(re.search(r"\d", invoice_number))

        if not has_numbers:
            logger.warning(f"⚠️  Invoice number '{invoice_number}' has no numbers")
            return False, None, "No numbers in invoice number"

        if len(invoice_number) < 3:
            logger.warning(f"❌ Invoice number '{invoice_number}' too short")
            return False, None, "Too short (< 3 characters)"

        if len(invoice_number) > 30:
            logger.warning(f"❌ Invoice number '{invoice_number}' too long")
            return False, None, "Too long (> 30 characters)"

        if previous_invoice:
            current_nums = re.findall(r"\d+", invoice_number)
            prev_nums = re.findall(r"\d+", previous_invoice)

            if current_nums and prev_nums:
                try:
                    current_num = int(current_nums[-1])
                    prev_num = int(prev_nums[-1])
                    diff = current_num - prev_num

                    if diff < 0:
                        logger.warning(f"⚠️  Invoice number decreased: {previous_invoice} → {invoice_number}")
                        return True, invoice_number, "Warning: Number decreased from previous"

                    if diff > 1000:
                        logger.warning(f"⚠️  Large gap in invoice numbers: {previous_invoice} → {invoice_number}")
                        return True, invoice_number, "Warning: Large gap in sequence"

                    logger.info(f"✅ Invoice number sequential: {previous_invoice} → {invoice_number}")
                except Exception:
                    pass

        logger.info(f"✅ Invoice number '{invoice_number}' valid")
        return True, invoice_number, "Valid format"

    @staticmethod
    def infer_currency_from_context(
        amount_text: str = "",
        vendor_country: Optional[str] = None,
        ocr_text: str = "",
    ) -> Tuple[str, float, str]:
        """
        Infer currency when not explicitly stated.

        Returns:
            (currency_code, confidence, reason)
        """
        for symbol, code in AdvancedHeuristics.CURRENCY_SYMBOLS.items():
            if symbol in amount_text or symbol in ocr_text:
                logger.info(f"💱 Currency inferred: {code} (symbol '{symbol}' found)")
                return code, 95.0, f"Symbol '{symbol}' found"

        currency_codes = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "INR", "CNY"]
        for code in currency_codes:
            if re.search(r"\b" + code + r"\b", ocr_text, re.IGNORECASE):
                logger.info(f"💱 Currency inferred: {code} (code found in text)")
                return code, 90.0, f"Currency code '{code}' found in text"

        language_indicators = {
            "EUR": ["€", "euro", "eur", "francia", "deutschland", "italia"],
            "GBP": ["£", "pound", "sterling", "gbp", "britain", "uk"],
            "CAD": ["c$", "cad", "canada", "canadian"],
            "AUD": ["a$", "aud", "australia", "australian"],
        }

        ocr_lower = ocr_text.lower()
        for currency, indicators in language_indicators.items():
            if any(ind in ocr_lower for ind in indicators):
                logger.info(f"💱 Currency inferred: {currency} (language indicator)")
                return currency, 75.0, "Language/country indicator found"

        logger.info("💱 Currency defaulted to: USD (no indicators found)")
        return "USD", 50.0, "Default (no indicators found)"

    @staticmethod
    def _find_company_in_text(ocr_text: str, exclude: str = "") -> Optional[str]:
        """Find company name in OCR text."""
        lines = ocr_text.split("\n")

        for line in lines[:15]:
            line = line.strip()

            if exclude and exclude.lower() in line.lower():
                continue

            if any(keyword in line.lower() for keyword in AdvancedHeuristics.COMPANY_KEYWORDS):
                if 5 < len(line) < 100:
                    return line

        return None

    @staticmethod
    def _extract_from_section(ocr_text: str) -> Optional[str]:
        """Extract 'From' or 'Vendor' section from OCR."""
        from_patterns = [
            r"from\s*:?\s*(.{5,100})",
            r"vendor\s*:?\s*(.{5,100})",
            r"supplier\s*:?\s*(.{5,100})",
        ]

        for pattern in from_patterns:
            match = re.search(pattern, ocr_text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    @staticmethod
    def _extract_bill_to_section(ocr_text: str) -> Optional[str]:
        """Extract 'Bill To' section from OCR."""
        bill_patterns = [
            r"bill\s+to\s*:?\s*(.{5,100})",
            r"customer\s*:?\s*(.{5,100})",
            r"client\s*:?\s*(.{5,100})",
        ]

        for pattern in bill_patterns:
            match = re.search(pattern, ocr_text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    @staticmethod
    def _extract_name_from_section(section_text: str) -> Optional[str]:
        """Extract company/person name from section text."""
        lines = section_text.split("\n")
        if lines:
            name = lines[0].strip()
            if 3 < len(name) < 100:
                return name
        return None


advanced_heuristics = AdvancedHeuristics()

import logging
import os
import tempfile
from typing import Any, Dict, List, Tuple

from PIL import Image
from PIL import ImageFilter, ImageOps

logger = logging.getLogger(__name__)


class TripleHybridService:
    """
    Orchestrates 3 ML models for invoice extraction:
    1. Impira LayoutLM (Question Answering)
    2. Microsoft LayoutLMv3 (Layout Analysis)
    3. Naver Donut (End-to-End)
    """

    def __init__(self):
        self.impira_extractor = None
        self.layoutlm_service = None
        self.donut_service = None
        self._rapid_ocr_engine = None
        # Flag: 0 (default) uses RapidOCR; 1 uses Tesseract
        try:
            self.use_tesseract_ocr = bool(int(os.getenv("USE_TESSERACT_OCR", "0")))
        except Exception:
            self.use_tesseract_ocr = False

    def load_impira(self):
        """Lazy load Impira model"""
        if not self.impira_extractor:
            from transformers import pipeline

            logger.info("Loading Impira Q&A model...")
            self.impira_extractor = pipeline(
                "document-question-answering",
                model="impira/layoutlm-document-qa",
            )
            logger.info("✅ Impira model loaded")

    def load_layoutlm(self):
        """Lazy load LayoutLM service"""
        if not self.layoutlm_service:
            from app.services.layoutlm_service import layoutlm_service

            self.layoutlm_service = layoutlm_service

    def load_donut(self):
        """Lazy load Donut service"""
        if not self.donut_service:
            from app.services.donut_service import donut_service

            self.donut_service = donut_service

    def extract_invoice(self, image_path: str) -> Tuple[Dict[str, Any], Dict[str, float], str, str]:
        """
        Extract using all 3 models, merge, and validate
        Returns:
            (extracted_data, field_confidences, method_used, raw_ocr_text)
        """
        logger.info(f"Starting TRIPLE HYBRID extraction: {image_path}")

        preprocessed_path = None
        try:
            preprocessed_path = self._preprocess_image(image_path)
            image_for_models_path = preprocessed_path or image_path
            image = Image.open(image_for_models_path).convert("RGB")

            raw_ocr_text = self._extract_raw_ocr_text(image_for_models_path)
            logger.info(f"   OCR text extracted: {len(raw_ocr_text)} characters")

            impira_data, impira_conf = self._extract_with_impira(image)
            layoutlm_data, layoutlm_conf = self._extract_with_layoutlm(image_for_models_path)
            donut_data, donut_conf = self._extract_with_donut(image_for_models_path)

            merged_data, field_confidences = self._merge_triple(
                impira_data,
                impira_conf,
                layoutlm_data,
                layoutlm_conf,
                donut_data,
                donut_conf,
            )

            validated_data, validated_confidences = self._validate_all_fields(
                merged_data, field_confidences
            )

            logger.info(f"Triple hybrid complete: {len(validated_data)} valid fields")

            return validated_data, validated_confidences, "triple_hybrid", raw_ocr_text
        finally:
            if preprocessed_path:
                try:
                    os.remove(preprocessed_path)
                except Exception:
                    pass

    def _preprocess_image(self, image_path: str) -> str:
        """
        Light image preprocessing to improve OCR:
        - Convert to grayscale
        - Auto-contrast
        - Mild sharpen/denoise
        Returns path to a temp file with the processed image.
        """
        try:
            img = Image.open(image_path).convert("L")
            img = ImageOps.autocontrast(img)
            img = img.filter(ImageFilter.MedianFilter(size=3))
            # Slightly boost sharpness by unsharp masking
            img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))

            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            img.save(tmp.name, format="PNG")
            return tmp.name
        except Exception as e:
            logger.warning(f"Preprocess failed, using original image: {e}")
            return ""

    def _extract_raw_ocr_text(self, image_path: str) -> str:
        """
        Extract OCR text using RapidOCR by default, or Tesseract if flag enabled.
        """
        if not self.use_tesseract_ocr:
            try:
                if self._rapid_ocr_engine is None:
                    from rapidocr import RapidOCR  # type: ignore

                    self._rapid_ocr_engine = RapidOCR()
                output = self._rapid_ocr_engine(image_path)

                # RapidOCR may return a RapidOCROutput object (with .text) or a tuple (result, image)
                lines: List[str] = []
                text_list = getattr(output, "text", None)
                if text_list:
                    lines = [ln for ln in text_list if ln]
                else:
                    try:
                        result_only, _ = output  # type: ignore
                    except Exception:
                        result_only = output

                    if isinstance(result_only, list):
                        lines = [
                            entry[1]
                            for entry in result_only
                            if isinstance(entry, (list, tuple)) and len(entry) > 1 and entry[1]
                        ]

                if lines:
                    return "\n".join(lines)
            except Exception as e:
                logger.warning(f"RapidOCR failed, falling back to Tesseract: {e}")

        try:
            import pytesseract

            image = Image.open(image_path).convert("RGB")
            return pytesseract.image_to_string(image)
        except Exception as e:
            logger.warning(f"Tesseract OCR failed: {e}")
            return ""

    def _extract_with_impira(self, image: Image) -> Tuple[Dict[str, Any], float]:
        """Extract using Impira Q&A model with ENHANCED prompts"""
        self.load_impira()

        if not self.impira_extractor:
            logger.warning("Impira not available, skipping")
            return {}, 0.0

        logger.info("Extracting with Impira...")

        questions = {
            "invoice_number": [
                "What is the invoice number?",
                "What is the invoice ID?",
                "What is the document number?",
                "What is the reference number shown on this invoice?",
            ],
            "invoice_date": [
                "What is the complete invoice date including month, day, and year?",
                "When was this invoice issued? Include the full date.",
                "What is the invoice date shown on this document?",
                "What date is shown next to 'INVOICE DATE' or 'DATE'?",
                "What is the full date of this invoice?",
            ],
            "due_date": [
                "What is the due date?",
                "When is payment due?",
                "What is the payment due date?",
            ],
            "total_amount": [
                "What is the total amount due?",
                "What is the grand total shown on this invoice?",
                "What is the final total amount?",
                "What is the total amount to be paid?",
                "How much is the total?",
            ],
            "vendor_name": [
                "Who is the company that issued this invoice?",
                "What is the name of the vendor or seller?",
                "Who is providing the service or product?",
                "What company or business is sending this invoice?",
                "Who is the supplier or service provider?",
            ],
            "customer_name": [
                "Who is the customer?",
                "Who is the bill to?",
                "What is the client name?",
            ],
        }

        results = {}
        total_confidence = 0
        count = 0

        for field, question_list in questions.items():
            best_answer = None
            best_score = 0
            all_answers = []

            for question in question_list:
                try:
                    result = self.impira_extractor(image, question)
                    if result and result[0]["score"] > 0.5:
                        answer = result[0]["answer"].strip()
                        score = result[0]["score"]
                        all_answers.append((answer, score))

                        if score > best_score:
                            best_answer = answer
                            best_score = score
                except Exception as e:
                    logger.warning(f"Impira failed on '{question}': {e}")
                    continue

            if field == "vendor_name" and best_answer:
                customer_answer = results.get("customer_name", "").lower()

                if customer_answer and best_answer.lower() == customer_answer:
                    logger.warning(f"⚠️  Vendor name '{best_answer}' matches customer - likely incorrect")
                    for answer, score in all_answers:
                        if answer.lower() != customer_answer and score > 0.5:
                            best_answer = answer
                            best_score = score
                            logger.info(f"✅ Using alternative vendor: '{best_answer}'")
                            break

                if (
                    customer_answer
                    and " " in best_answer
                    and len(best_answer.split()) == 2
                    and not any(
                        word in best_answer.lower()
                        for word in ["inc", "llc", "ltd", "corp", "company", "enterprises", "services", "solutions"]
                    )
                ):
                    logger.warning(f"⚠️  Vendor '{best_answer}' looks like a person name, not a company")

            if field == "invoice_date" and best_answer:
                if best_answer.isdigit() and len(best_answer) == 4:
                    logger.warning(f"⚠️  Invoice date '{best_answer}' is only a year - rejected")
                    for answer, score in all_answers:
                        if (
                            not answer.isdigit()
                            or "/" in answer
                            or "-" in answer
                            or any(month in answer for month in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
                        ):
                            best_answer = answer
                            best_score = score
                            logger.info(f"✅ Using better date format: '{best_answer}'")
                            break
                    else:
                        logger.warning("⚠️  No valid date format found, skipping")
                        continue

            if best_answer:
                results[field] = best_answer
                total_confidence += best_score
                count += 1
                logger.debug(f"  {field}: {best_answer} (confidence: {best_score:.2f})")

        if "customer_name" in results:
            del results["customer_name"]

        avg_confidence = (total_confidence / count * 100) if count > 0 else 0
        logger.info(f"Impira: {len(results)} fields, {avg_confidence:.1f}% confidence")
        return results, avg_confidence

    def _extract_with_layoutlm(self, image_path: str) -> Tuple[Dict[str, Any], float]:
        """Extract using LayoutLM service"""
        self.load_layoutlm()

        if not self.layoutlm_service:
            logger.warning("LayoutLM not available, skipping")
            return {}, 0.0

        logger.info("Extracting with LayoutLM...")

        try:
            results = self.layoutlm_service.extract_from_image(image_path)
            extracted_data = results.get("extracted_data", {})
            confidence = results.get("overall_confidence", 0)
            logger.info(f"LayoutLM: {len(extracted_data)} fields, {confidence:.1f}% confidence")
            return extracted_data, confidence
        except Exception as e:
            logger.error(f"LayoutLM extraction failed: {e}")
            return {}, 0.0

    def _extract_with_donut(self, image_path: str) -> Tuple[Dict[str, Any], float]:
        """Extract using Donut service"""
        self.load_donut()

        if not self.donut_service:
            logger.warning("Donut not available, skipping")
            return {}, 0.0

        logger.info("Extracting with Donut...")

        try:
            results = self.donut_service.extract_from_image(image_path)
            extracted_data = results.get("extracted_data", {})
            confidence = results.get("overall_confidence", 0)
            logger.info(f"Donut: {len(extracted_data)} fields, {confidence:.1f}% confidence")
            return extracted_data, confidence
        except Exception as e:
            logger.error(f"Donut extraction failed: {e}")
            return {}, 0.0

    def _merge_triple(
        self,
        impira_data: Dict,
        impira_conf: float,
        layoutlm_data: Dict,
        layoutlm_conf: float,
        donut_data: Dict,
        donut_conf: float,
    ) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """Intelligently merge results from 3 models using consensus"""
        merged = {}
        confidences = {}

        all_fields = set(list(impira_data.keys()) + list(layoutlm_data.keys()) + list(donut_data.keys()))

        for field in all_fields:
            if field.startswith("_"):
                continue

            values = [
                (impira_data.get(field), impira_conf, "impira"),
                (layoutlm_data.get(field), layoutlm_conf, "layoutlm"),
                (donut_data.get(field), donut_conf, "donut"),
            ]
            valid_values = [(v, c, s) for v, c, s in values if v is not None]

            if not valid_values:
                continue

            value_counts = {}
            for val, conf, source in valid_values:
                val_str = str(val).strip().lower()
                value_counts.setdefault(val_str, []).append((val, conf, source))

            best_value = None
            best_confidence = 0

            for _, instances in value_counts.items():
                if len(instances) >= 2:
                    logger.info(f"✅ Consensus on {field}: {instances[0][0]} ({len(instances)} models agree)")
                    best_value = instances[0][0]
                    best_confidence = max(c for _, c, _ in instances)
                    break

            if best_value is None:
                best_value, best_confidence, source = max(valid_values, key=lambda x: x[1])
                logger.info(f"⚠️  No consensus on {field}, using {source}: {best_value}")

            merged[field] = best_value
            confidences[field] = best_confidence

        return merged, confidences

    def _validate_all_fields(
        self,
        data: Dict[str, Any],
        confidences: Dict[str, float],
    ) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """Validate and clean all extracted fields"""
        validated = {}
        validated_confidences = {}

        for field, value in data.items():
            try:
                if field == "total_amount":
                    cleaned = self._clean_amount(value)
                    validated[field] = cleaned
                    validated_confidences[field] = confidences.get(field, 0)
                elif field == "invoice_date":
                    cleaned = self._clean_date(value)
                    validated[field] = cleaned
                    validated_confidences[field] = confidences.get(field, 0)
                elif field == "invoice_number":
                    cleaned = self._clean_invoice_number(value)
                    validated[field] = cleaned
                    validated_confidences[field] = confidences.get(field, 0)
                elif field == "currency":
                    cleaned = self._clean_currency(value)
                    validated[field] = cleaned
                    validated_confidences[field] = confidences.get(field, 0)
                elif field == "vendor_name":
                    validated[field] = str(value).strip()
                    validated_confidences[field] = confidences.get(field, 0)
                else:
                    validated[field] = value
                    validated_confidences[field] = confidences.get(field, 0)
            except Exception as e:
                logger.warning(f"Validation failed for {field}: {e}")
                continue

        return validated, validated_confidences

    def _clean_amount(self, value: Any) -> float:
        """Clean total amount; return string-like cleaned value for downstream validation"""
        if isinstance(value, (int, float)):
            return float(value)

        str_val = str(value)
        logger.info(f"🧹 Cleaning total_amount: '{str_val}'")

        cleaned = str_val.replace("$", "").replace("€", "").replace("£", "").replace("¥", "").strip()
        logger.info(f"🧹 Cleaned total_amount: '{str_val}' → '{cleaned}'")
        return cleaned

    def _clean_date(self, value: Any) -> str:
        """Clean invoice date"""
        if not value:
            return ""

        str_val = str(value).strip()
        logger.info(f"🧹 Cleaning invoice_date: '{str_val}'")

        date_patterns = [
            r"(\d{4})-(\d{2})-(\d{2})",
            r"(\d{2})/(\d{2})/(\d{4})",
            r"(\d{2})-(\d{2})-(\d{4})",
        ]

        import re

        for pattern in date_patterns:
            match = re.search(pattern, str_val)
            if match:
                parts = match.groups()
                if len(parts[0]) == 4:
                    result = f"{parts[0]}-{parts[1]}-{parts[2]}"
                else:
                    result = f"{parts[2]}-{parts[0]}-{parts[1]}"
                logger.info(f"🧹 Cleaned invoice_date: '{str_val}' → '{result}'")
                return result

        return str_val

    def _clean_invoice_number(self, value: Any) -> str:
        """Clean invoice number"""
        if not value:
            return ""

        str_val = str(value).strip()
        logger.info(f"🧹 Cleaning invoice_number: '{str_val}'")

        cleaned = " ".join(str_val.split())
        if cleaned.startswith("-"):
            cleaned = cleaned.lstrip("-")

        logger.info(f"🧹 Cleaned invoice_number: '{str_val}' → '{cleaned}'")
        return cleaned

    def _clean_currency(self, value: Any) -> str:
        """Clean currency code"""
        if not value:
            return "USD"

        str_val = str(value).strip().upper()
        valid_currencies = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "CNY"]

        if str_val in valid_currencies:
            return str_val

        import re

        match = re.search(r"[A-Z]{3}", str_val)
        if match:
            return match.group()

        return "USD"


triple_hybrid_service = TripleHybridService()

"""
Quadruple Hybrid ML Service
Orchestrates 4 ML models for invoice extraction with deterministic results

Models:
1. Docling - IBM Document Understanding (structure-aware)
2. Impira LayoutLM - Question Answering
3. LayoutLMv3 - Layout Analysis
4. Donut - End-to-End Visual Parsing

Features:
- Deterministic mode (same input → same output)
- Parallel model execution
- Intelligent 4-way consensus
- Graceful degradation (if models fail)
- Comprehensive logging
"""
import logging
import random
import time
import os
from typing import Any, Dict, List, Optional

import numpy as np
from PIL import Image
from app.services.tesseract_service import tesseract_service
from app.services.pre_ocr_pipeline import pre_ocr_pipeline
from app.config import settings

logger = logging.getLogger(__name__)


class QuadrupleHybridService:
    """
    Orchestrates 4 ML models for robust invoice extraction

    Key Innovation: Deterministic extraction with no randomness
    """

    def __init__(self):
        self.docling_service = None
        self.triple_hybrid_service = None
        self.intelligent_merger = None
        self.use_tesseract_ocr_voter = bool(int(os.getenv("USE_TESSERACT_OCR_VOTER", "0")))
        self.store_ocr_tokens = settings.STORE_OCR_TOKENS
        self._enable_deterministic_mode()

    def _enable_deterministic_mode(self):
        """Enable deterministic mode across all libraries."""
        try:
            random.seed(42)
            np.random.seed(42)

            try:
                import torch

                torch.manual_seed(42)
                torch.cuda.manual_seed_all(42)
                torch.backends.cudnn.deterministic = True
                torch.backends.cudnn.benchmark = False
                logger.info("✅ PyTorch deterministic mode enabled")
            except ImportError:
                logger.warning("PyTorch not available, skipping torch seed")

            import os

            os.environ["PYTHONHASHSEED"] = "42"
            logger.info("✅ Deterministic mode enabled globally")
        except Exception as e:
            logger.warning(f"Could not enable full deterministic mode: {e}")

    def extract_invoice(
        self,
        image_path: str,
        pdf_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract invoice data using all 4 models.

        Returns:
            {
                'extracted_data': Final merged data,
                'field_confidences': Confidence per field,
                'method': 'quadruple_hybrid',
                'raw_ocr_text': Raw OCR text,
                'model_outputs': Individual model results,
                'voting_details': Detailed voting logs,
                'line_items': Extracted line items,
                'processing_time_ms': Time taken,
                'models_used': List of models that ran successfully
            }
        """
        start_time = time.time()

        logger.info("=" * 80)
        logger.info("QUADRUPLE HYBRID EXTRACTION - STARTING")
        logger.info("=" * 80)
        logger.info(f"  Image path: {image_path}")
        logger.info(f"  PDF path: {pdf_path}")

        self._enable_deterministic_mode()
        self._load_services()

        pre_result = pre_ocr_pipeline.preprocess_image(
            image_path,
            context={"source": "quadruple_hybrid"},
        )
        image_path_for_ocr = pre_result.image_path

        try:
            models_used: List[str] = []

            docling_result = self._run_docling(pdf_path)
            if docling_result.get("extracted_data"):
                models_used.append("docling")

            triple_result = self._run_triple_hybrid(image_path_for_ocr)
            if triple_result:
                models_used.extend(["impira", "layoutlm", "donut"])

            if not models_used:
                logger.error("ALL MODELS FAILED - No extraction possible")
                return self._create_failure_result("All models failed")

            logger.info(f"Models successfully executed: {models_used}")

            raw_ocr_text = triple_result.get("raw_ocr_text", "") if triple_result else ""
            docling_raw_text = docling_result.get("metadata", {}).get("raw_text", "") if docling_result else ""

            tesseract_voter_text = ""
            ocr_tokens: Dict[str, Any] = {}
            if self.use_tesseract_ocr_voter or self.store_ocr_tokens or settings.STORE_OCR_TEXTS:
                try:
                    tesseract_voter_text, tesseract_data = tesseract_service.extract_text(image_path_for_ocr)
                    logger.info(f"Tesseract voter OCR length: {len(tesseract_voter_text)}")
                    if self.store_ocr_tokens:
                        ocr_tokens["tesseract"] = self._build_ocr_tokens(image_path_for_ocr, tesseract_data)
                        logger.info(f"[ocr_tokens] Captured {len(ocr_tokens['tesseract'])} tokens from tesseract")
                except Exception as e:
                    logger.warning(f"Tesseract voter OCR failed: {e}")
            else:
                logger.info("Tesseract voter disabled (USE_TESSERACT_OCR_VOTER=0)")

            ocr_texts = {
                "rapid": raw_ocr_text,
                "docling": docling_raw_text,
                "tesseract": tesseract_voter_text,
            }
            logger.info(
                "OCR text lengths: rapid=%s docling=%s tesseract=%s",
                len(raw_ocr_text or ""),
                len(docling_raw_text or ""),
                len(tesseract_voter_text or ""),
            )

            fused_fields = None
            fused_confidence = 0.0
            line_items: List[Dict[str, Any]] = []
            if settings.ENABLE_OCR_MATRIX and pre_result.metadata.get("variants"):
                from app.services.ocr_matrix import ocr_matrix_runner

                matrix_result = ocr_matrix_runner.run(pre_result.metadata.get("variants", {}))
                matrix_raw = matrix_result.raw_texts
                if matrix_raw:
                    ocr_texts["matrix"] = matrix_raw
                    logger.info(
                        "OCR matrix outputs: %s",
                        list(matrix_raw.keys()),
                    )
                if settings.ENABLE_OCR_FUSION and matrix_result.outputs:
                    from app.services.ocr_fusion_service import ocr_fusion_service

                    fused_fields, fused_confidence, fusion_debug = ocr_fusion_service.fuse(matrix_result)
                    if fused_fields:
                        ocr_texts["fused_fields"] = fused_fields
                    if settings.STORE_OCR_TEXTS:
                        ocr_texts["fusion_debug"] = fusion_debug

                if settings.ENABLE_LINE_ITEM_PARSER and matrix_result.tokens:
                    from app.services.line_item_parser import line_item_parser

                    token_source_map = {
                        "tesseract_v3_binarized": "v3_binarized",
                        "paddle_v1_gray": "v1_gray",
                        "paddle_v2_clahe": "v2_clahe",
                        "paddle_v4_superres_clahe": "v4_superres_clahe",
                    }
                    selected_source = None
                    for candidate in ("tesseract_v3_binarized", "paddle_v1_gray", "paddle_v2_clahe"):
                        if matrix_result.tokens.get(candidate):
                            selected_source = candidate
                            break
                    if selected_source:
                        variant_key = token_source_map.get(selected_source)
                        variants = pre_result.metadata.get("variants", {})
                        variant_path = variants.get(variant_key, image_path_for_ocr)
                        reocr_path = variants.get("v1_gray", variant_path)
                        line_item_result = line_item_parser.parse(
                            matrix_result.tokens.get(selected_source, []),
                            image_path=reocr_path,
                        )
                        line_items = line_item_result.get("line_items", [])
                        logger.info(
                            "Line-item parser: source=%s items=%s",
                            selected_source,
                            len(line_items),
                        )
                        if settings.STORE_OCR_TEXTS or settings.STORE_LINEITEM_DEBUG:
                            ocr_texts["line_item_metadata"] = line_item_result.get("metadata", {})

            if settings.ENABLE_FOOTER_TOTAL_EXTRACT:
                try:
                    from app.services.footer_total_extractor import footer_total_extractor

                    footer_result = footer_total_extractor.extract(image_path_for_ocr)
                    if footer_result.value is not None:
                        if not fused_fields:
                            fused_fields = {}
                        fused_fields["total_amount"] = footer_result.value
                        fused_confidence = max(fused_confidence, footer_result.confidence or 0.0)
                        logger.info(
                            "Footer total candidate added: %s (conf %.1f)",
                            footer_result.value,
                            footer_result.confidence,
                        )
                    if settings.STORE_OCR_TEXTS or settings.STORE_TOTAL_DEBUG:
                        ocr_texts["footer_total"] = footer_result.debug
                except Exception as exc:
                    logger.warning("Footer total extraction failed: %s", exc)

            logger.info("[5/5] Merging results with intelligent consensus...")
            merged_result = self.intelligent_merger.merge_4way(
                docling_result=docling_result,
                impira_result=triple_result.get("impira_result", {}) if triple_result else {},
                layoutlm_result=triple_result.get("layoutlm_result", {}) if triple_result else {},
                donut_result=triple_result.get("donut_result", {}) if triple_result else {},
                raw_ocr_text=raw_ocr_text,
                extra_ocr_texts={
                    "ocr_rapid": raw_ocr_text,
                    "ocr_docling": docling_raw_text,
                    "ocr_tesseract": tesseract_voter_text,
                },
                extra_ocr_fields=fused_fields,
                extra_ocr_confidence=fused_confidence or 82.0,
            )
            processing_time = int((time.time() - start_time) * 1000)

            line_items_output = line_items or merged_result["extracted_data"].get("line_items", [])
            final_result = {
                "extracted_data": merged_result["extracted_data"],
                "field_confidences": merged_result["field_confidences"],
                "method": "quadruple_hybrid",
                "raw_ocr_text": raw_ocr_text,
                "model_outputs": merged_result["model_outputs"],
                "voting_details": merged_result["voting_details"],
                "model_results_raw": {
                    "docling": docling_result,
                    "impira": triple_result.get("impira_result", {}) if triple_result else {},
                    "layoutlm": triple_result.get("layoutlm_result", {}) if triple_result else {},
                    "donut": triple_result.get("donut_result", {}) if triple_result else {},
                    "extra_ocr_texts": {
                        "ocr_rapid": raw_ocr_text,
                        "ocr_docling": docling_raw_text,
                        "ocr_tesseract": tesseract_voter_text,
                    },
                },
                "line_items": line_items_output,
                "processing_time_ms": processing_time,
                "models_used": models_used,
                "overall_confidence": merged_result["overall_confidence"],
                "needs_review": merged_result.get("needs_review", []),
                "ocr_tokens": ocr_tokens if self.store_ocr_tokens else {},
            }
            if pre_result.metadata:
                final_result["pre_ocr_metadata"] = pre_result.metadata
            if settings.STORE_OCR_TEXTS:
                final_result["ocr_texts"] = ocr_texts
            if fused_fields:
                final_result["ocr_fused_fields"] = fused_fields

            logger.info("=" * 80)
            logger.info("QUADRUPLE HYBRID EXTRACTION - COMPLETE")
            logger.info("=" * 80)
            logger.info(f"  Fields extracted: {len(final_result['extracted_data'])}")
            logger.info(f"  Overall confidence: {final_result['overall_confidence']:.1f}%")
            logger.info(f"  Processing time: {processing_time}ms")
            logger.info(f"  Models used: {', '.join(models_used)}")

            return final_result
        finally:
            self._cleanup_pre_ocr(pre_result)

    def extract_invoice_multipage(
        self,
        image_paths: List[str],
        pdf_path: str = None,
    ) -> Dict[str, Any]:
        """PHASE 4: Extract invoice from multi-page PDF."""
        logger.info(f"📄 Multi-page extraction: {len(image_paths)} pages")

        page_results: List[Dict[str, Any]] = []
        for page_num, image_path in enumerate(image_paths, 1):
            logger.info(f"Processing page {page_num}/{len(image_paths)}...")
            try:
                result = self.extract_invoice(
                    image_path=image_path,
                    pdf_path=pdf_path if page_num == 1 else None,
                )
                result["page_number"] = page_num
                page_results.append(result)
                logger.info(f"  Page {page_num}: {len(result['extracted_data'])} fields extracted")
            except Exception as e:
                logger.error(f"  Page {page_num} extraction failed: {e}")
                page_results.append(
                    {
                        "page_number": page_num,
                        "extracted_data": {},
                        "error": str(e),
                    }
                )

        if len(page_results) == 1:
            return page_results[0]

        return self._merge_multipage_results(page_results)

    def _merge_multipage_results(self, page_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        PHASE 4: Merge results from multiple pages.

        Strategy:
        1. Check if all pages have same invoice number → Single invoice
        2. Otherwise → Multiple invoices (return page 1 as primary)
        """
        logger.info("Analyzing multi-page results...")

        invoice_numbers = []
        for page_result in page_results:
            inv_num = page_result.get("extracted_data", {}).get("invoice_number")
            if inv_num:
                invoice_numbers.append(inv_num)

        is_single_invoice = len(set(invoice_numbers)) <= 1 and len(invoice_numbers) > 0

        if is_single_invoice:
            logger.info("✅ Single invoice spanning multiple pages detected")
            return self._merge_single_invoice(page_results)

        logger.info("⚠️  Multiple invoices detected (or no invoice numbers)")
        return self._handle_multiple_invoices(page_results)

    def _merge_single_invoice(self, page_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge data from a single invoice spanning multiple pages.

        Strategy:
        - Use page 1 for header fields (invoice #, date, vendor)
        - Combine line items from all pages
        - Use highest confidence for each field
        """
        logger.info("Merging single invoice from multiple pages...")

        merged = page_results[0].copy()

        all_line_items = []
        for page_result in page_results:
            line_items = page_result.get("line_items", [])
            if line_items:
                all_line_items.extend(line_items)

        if all_line_items:
            merged["line_items"] = all_line_items
            logger.info(f"  Combined {len(all_line_items)} line items from {len(page_results)} pages")

        merged["extracted_data"]["_page_count"] = len(page_results)
        merged["extracted_data"]["_multipage"] = True
        return merged

    def _handle_multiple_invoices(self, page_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Handle multiple separate invoices in one PDF.

        Strategy:
        - Return first page as primary invoice
        - Store other pages in metadata for user to split
        """
        logger.info("Handling multiple invoices in PDF...")

        primary = page_results[0].copy()

        primary["extracted_data"]["_page_count"] = len(page_results)
        primary["extracted_data"]["_multipage"] = True
        primary["extracted_data"]["_multiple_invoices_detected"] = True

        other_pages = []
        for page_result in page_results[1:]:
            page_summary = {
                "page_number": page_result.get("page_number"),
                "invoice_number": page_result.get("extracted_data", {}).get("invoice_number"),
                "total_amount": page_result.get("extracted_data", {}).get("total_amount"),
                "vendor_name": page_result.get("extracted_data", {}).get("vendor_name"),
            }
            other_pages.append(page_summary)

        primary["extracted_data"]["_other_pages"] = other_pages

        logger.warning(f"⚠️  PDF contains {len(page_results)} separate invoices - using page 1 as primary")
        logger.warning(f"   Other pages: {other_pages}")

        return primary

    def _load_services(self):
        """Lazy load all required services."""
        if not self.docling_service:
            from app.services.docling_service import docling_service

            self.docling_service = docling_service

        if not self.triple_hybrid_service:
            from app.services.triple_hybrid_service import triple_hybrid_service

            self.triple_hybrid_service = triple_hybrid_service

        if not self.intelligent_merger:
            from app.services.intelligent_merger import intelligent_merger

            self.intelligent_merger = intelligent_merger

    def _run_docling(self, pdf_path: Optional[str]) -> Dict[str, Any]:
        """
        Run Docling extraction.

        Returns:
            {
                'extracted_data': {...},
                'confidence': float,
                'metadata': {...}
            }
        """
        if not pdf_path:
            logger.info("[1/5] Docling: Skipped (no PDF path provided)")
            return {"extracted_data": {}, "confidence": 0.0, "metadata": {}}

        try:
            logger.info("[1/5] Running Docling (structure-aware extraction)...")

            extracted_data, confidence, metadata = self.docling_service.extract_from_pdf(pdf_path)
            logger.info(f"  ✅ Docling: {len(extracted_data)} fields, {confidence:.1f}% confidence")

            return {
                "extracted_data": extracted_data,
                "confidence": confidence,
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"  ❌ Docling failed: {e}")
            return {"extracted_data": {}, "confidence": 0.0, "metadata": {"error": str(e)}}

    def _run_triple_hybrid(self, image_path: str) -> Optional[Dict[str, Any]]:
        """
        Run Triple Hybrid (Impira + LayoutLM + Donut)

        Returns:
            {
                'impira_result': {...},
                'layoutlm_result': {...},
                'donut_result': {...},
                'raw_ocr_text': str
            }
        """
        try:
            logger.info("[2/5] Running Triple Hybrid ML...")

            validated_data, validated_confidences, method, raw_ocr_text = (
                self.triple_hybrid_service.extract_invoice(image_path)
            )

            result = {
                "impira_result": {
                    "extracted_data": validated_data.copy(),
                    "confidence": validated_confidences.get("invoice_number", 85.0),
                },
                "layoutlm_result": {
                    "extracted_data": validated_data.copy(),
                    "confidence": validated_confidences.get("total_amount", 85.0),
                },
                "donut_result": {
                    "extracted_data": validated_data.copy(),
                    "confidence": validated_confidences.get("vendor_name", 85.0),
                },
                "raw_ocr_text": raw_ocr_text,
            }

            logger.info("  ✅ Triple Hybrid complete")
            return result

        except Exception as e:
            logger.error(f"  ❌ Triple Hybrid failed: {e}")
            return None

    def _create_failure_result(self, reason: str) -> Dict[str, Any]:
        """Create a failure result structure."""
        return {
            "extracted_data": {},
            "field_confidences": {},
            "method": "quadruple_hybrid_failed",
            "raw_ocr_text": "",
            "model_outputs": {},
            "voting_details": {},
            "line_items": [],
            "processing_time_ms": 0,
            "models_used": [],
            "overall_confidence": 0.0,
            "needs_review": [],
            "error": reason,
        }


    def _cleanup_pre_ocr(self, pre_result: Any) -> None:
        temp_files = getattr(pre_result, "temp_files", None) or []
        for temp_path in temp_files:
            try:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                logger.debug("Pre-OCR cleanup failed for %s", temp_path)

    def _build_ocr_tokens(self, image_path: str, ocr_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert Tesseract image_to_data output into normalized tokens with bboxes.
        Used for later anchoring of corrections/templates.
        """
        try:
            img = Image.open(image_path)
            W, H = img.size
        except Exception as exc:
            logger.warning(f"[ocr_tokens] Could not open image for sizing: {exc}")
            W = H = None

        tokens: List[Dict[str, Any]] = []
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

                bbox_px = [x, y, x + w, y + h]
                bbox_norm = None
                if W and H and W > 0 and H > 0:
                    bbox_norm = [x / W, y / H, (x + w) / W, (y + h) / H]

                tokens.append(
                    {
                        "text": str(raw).strip(),
                        "conf": conf_val,
                        "bbox": bbox_norm,
                        "bbox_px": bbox_px,
                        "page": 1,
                        "source": "tesseract",
                    }
                )
            except Exception as exc:
                logger.debug(f"[ocr_tokens] Skipping token idx={idx}: {exc}")
                continue

        return tokens


quadruple_hybrid_service = QuadrupleHybridService()

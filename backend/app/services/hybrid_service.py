from app.services.donut_service import donut_service
from app.services.layoutlm_service import layoutlm_service
from typing import Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class HybridExtractionService:
    """
    Hybrid invoice extraction using both Donut and LayoutLMv3
    Merges results intelligently to maximize accuracy
    """
    
    def extract_invoice(self, image_path: str, use_both: bool = True) -> Tuple[Dict[str, Any], Dict[str, float], str]:
        """
        Extract invoice using hybrid approach
        
        Args:
            image_path: Path to invoice image
            use_both: If True, use both models. If False, auto-select
            
        Returns:
            (extracted_data, field_confidences, method_used)
        """
        logger.info(f"Starting hybrid extraction: {image_path}")
        
        try:
            if use_both:
                # Run both models
                return self._extract_with_both_models(image_path)
            else:
                # Smart selection (future: analyze image complexity)
                return self._extract_with_auto_selection(image_path)
                
        except Exception as e:
            logger.error(f"Hybrid extraction failed: {e}")
            raise
    
    def _extract_with_both_models(self, image_path: str) -> Tuple[Dict[str, Any], Dict[str, float], str]:
        """
        Run both Donut and LayoutLM, merge results
        """
        logger.info("Running both Donut and LayoutLM...")
        
        # Run Donut
        try:
            donut_data, donut_conf = donut_service.extract_invoice(image_path)
            logger.info(f"Donut extracted {len(donut_data)} fields")
        except Exception as e:
            logger.warning(f"Donut failed: {e}")
            donut_data, donut_conf = {}, 0.0
        
        # Run LayoutLM
        try:
            layoutlm_data, layoutlm_conf = layoutlm_service.extract_invoice(image_path)
            logger.info(f"LayoutLM extracted {len(layoutlm_data)} fields")
        except Exception as e:
            logger.warning(f"LayoutLM failed: {e}")
            layoutlm_data, layoutlm_conf = {}, 0.0
        
        # Merge results
        merged_data, field_confidences = self._merge_results(
            donut_data, donut_conf,
            layoutlm_data, layoutlm_conf
        )
        
        method = "hybrid_both"
        logger.info(f"Hybrid merge complete: {len(merged_data)} fields")
        
        return merged_data, field_confidences, method
    
    def _extract_with_auto_selection(self, image_path: str) -> Tuple[Dict[str, Any], Dict[str, float], str]:
        """
        Auto-select best model (future implementation)
        For now, tries Donut first (faster), fallback to LayoutLM
        """
        # Try Donut first (faster)
        try:
            donut_data, donut_conf = donut_service.extract_invoice(image_path)
            if donut_conf >= 85:  # Good confidence
                field_confs = {k: donut_conf for k in donut_data.keys()}
                return donut_data, field_confs, "donut_only"
        except Exception as e:
            logger.warning(f"Donut failed: {e}")
        
        # Fallback to LayoutLM
        try:
            layoutlm_data, layoutlm_conf = layoutlm_service.extract_invoice(image_path)
            field_confs = {k: layoutlm_conf for k in layoutlm_data.keys()}
            return layoutlm_data, field_confs, "layoutlm_fallback"
        except Exception as e:
            logger.error(f"Both models failed!")
            raise
    
    def _merge_results(
        self,
        donut_data: Dict[str, Any],
        donut_conf: float,
        layoutlm_data: Dict[str, Any],
        layoutlm_conf: float
    ) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """
        Intelligently merge results from both models
        
        Strategy:
        - vendor_name: Prefer Donut (better at names)
        - invoice_number: Prefer LayoutLM (better OCR for numbers)
        - date: Cross-validate, prefer match
        - total_amount: Cross-validate, prefer match
        - po_number: Only if both agree OR one has high confidence
        """
        merged_data = {}
        field_confidences = {}
        
        # Vendor Name: Prefer Donut
        if 'vendor_name' in donut_data:
            merged_data['vendor_name'] = donut_data['vendor_name']
            field_confidences['vendor_name'] = donut_conf
        elif 'vendor_name' in layoutlm_data:
            merged_data['vendor_name'] = layoutlm_data['vendor_name']
            field_confidences['vendor_name'] = layoutlm_conf
        
        # Invoice Number: Prefer LayoutLM (better at numbers)
        if 'invoice_number' in layoutlm_data:
            merged_data['invoice_number'] = layoutlm_data['invoice_number']
            field_confidences['invoice_number'] = layoutlm_conf
        elif 'invoice_number' in donut_data:
            merged_data['invoice_number'] = donut_data['invoice_number']
            field_confidences['invoice_number'] = donut_conf
        
        # Date: Cross-validate
        donut_date = donut_data.get('invoice_date')
        layoutlm_date = layoutlm_data.get('invoice_date')
        
        if donut_date and layoutlm_date:
            if donut_date == layoutlm_date:
                # Both agree - high confidence!
                merged_data['invoice_date'] = donut_date
                field_confidences['invoice_date'] = 98.0
            else:
                # Disagree - take higher original confidence
                if donut_conf > layoutlm_conf:
                    merged_data['invoice_date'] = donut_date
                    field_confidences['invoice_date'] = donut_conf * 0.9  # Reduce due to disagreement
                else:
                    merged_data['invoice_date'] = layoutlm_date
                    field_confidences['invoice_date'] = layoutlm_conf * 0.9
        elif donut_date:
            merged_data['invoice_date'] = donut_date
            field_confidences['invoice_date'] = donut_conf
        elif layoutlm_date:
            merged_data['invoice_date'] = layoutlm_date
            field_confidences['invoice_date'] = layoutlm_conf
        
        # Total Amount: Cross-validate
        donut_amount = donut_data.get('total_amount')
        layoutlm_amount = layoutlm_data.get('total_amount')
        
        if donut_amount is not None and layoutlm_amount is not None:
            if donut_amount == layoutlm_amount:
                # Both agree - high confidence!
                merged_data['total_amount'] = donut_amount
                field_confidences['total_amount'] = 98.0
            else:
                # Prefer LayoutLM for amounts (better OCR)
                merged_data['total_amount'] = layoutlm_amount
                field_confidences['total_amount'] = layoutlm_conf * 0.9
        elif donut_amount is not None:
            merged_data['total_amount'] = donut_amount
            field_confidences['total_amount'] = donut_conf
        elif layoutlm_amount is not None:
            merged_data['total_amount'] = layoutlm_amount
            field_confidences['total_amount'] = layoutlm_conf
        
        # Currency: Take from either (usually same)
        if 'currency' in donut_data:
            merged_data['currency'] = donut_data['currency']
            field_confidences['currency'] = 95.0
        elif 'currency' in layoutlm_data:
            merged_data['currency'] = layoutlm_data['currency']
            field_confidences['currency'] = 95.0
        
        # PO Number: Only if both agree OR skip if suspicious
        donut_po = donut_data.get('po_number')
        layoutlm_po = layoutlm_data.get('po_number')
        
        if donut_po and layoutlm_po:
            if donut_po == layoutlm_po:
                # Both found same PO - high confidence
                merged_data['po_number'] = donut_po
                field_confidences['po_number'] = 95.0
        # If only one found it, skip (likely hallucination)
        
        return merged_data, field_confidences


# Create singleton
hybrid_service = HybridExtractionService()
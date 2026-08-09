"""
Correction endpoint for template learning
Allows users to correct extraction errors
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.invoice import Invoice
from app.services.template_service import template_service
from app.services.correction_service import correction_service
from app.config import settings
from pydantic import BaseModel
from typing import Dict, Any, Optional
from pathlib import Path
import json
import re
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


def _guess_image_path(invoice: Invoice, preferred_page: int = 1) -> Optional[Path]:
    """
    Heuristic to find the page image generated during processing.
    """
    try:
        base = Path(invoice.file_path)
        folder = base.parent
        fname = base.name
        preferred = folder / f"{fname}_page_{preferred_page}.png"
        if preferred.exists():
            return preferred
        candidates = sorted(folder.glob(f"{fname}_page_*.png"))
        if candidates:
            return candidates[0]
        pngs = sorted(folder.glob("*.png"))
        if pngs:
            return pngs[0]
        return None
    except Exception:
        return None


def _normalize_token_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _find_bbox_from_tokens(value: Any, ocr_tokens: Dict[str, Any]) -> Optional[tuple]:
    """
    Try to locate a bbox from stored OCR tokens (any source).
    Returns (bbox_norm, page) or None.
    """
    if not value or not ocr_tokens:
        return None
    norm_value = _normalize_token_text(str(value))
    best = None

    for source_tokens in ocr_tokens.values():
        if not isinstance(source_tokens, list):
            continue
        for tok in source_tokens:
            txt = _normalize_token_text(str(tok.get("text", ""))) if tok else ""
            if not txt:
                continue
            if txt == norm_value or txt in norm_value or norm_value in txt:
                bbox = tok.get("bbox") or tok.get("bbox_norm") or tok.get("bbox_normalized")
                page = tok.get("page") or 1
                if bbox:
                    best = (bbox, page)
                    return best
    return best


class CorrectionRequest(BaseModel):
    """Request model for corrections"""
    upload_id: str
    corrected_data: Dict[str, Any]
    bboxes: Optional[Dict[str, Any]] = None  # field -> bbox [x0,y0,x1,y1]
    page_numbers: Optional[Dict[str, int]] = None  # field -> page number


class CorrectionResponse(BaseModel):
    """Response model for corrections"""
    success: bool
    message: str
    template_updated: bool
    vendor_id: int = None
    learned_from_invoices: int = 0


@router.post("/correct", response_model=CorrectionResponse)
async def correct_invoice(
    correction: CorrectionRequest,
    db: Session = Depends(get_db)
):
    """
    Submit corrections for an invoice
    
    This endpoint:
    1. Saves corrected data to invoice
    2. Updates or creates template for vendor
    3. Improves accuracy for future invoices from same vendor
    """
    logger.info(f"Correction request for: {correction.upload_id}")
    
    try:
        # Get invoice
        invoice = db.query(Invoice).filter(
            Invoice.upload_id == correction.upload_id
        ).first()
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Update invoice with corrected data
        invoice.extracted_data = correction.corrected_data
        invoice.status = "CORRECTED"
        bbox_map = correction.bboxes or {}
        page_map = correction.page_numbers or {}
        ocr_tokens = invoice.ocr_tokens or {}
        if isinstance(ocr_tokens, str):
            try:
                ocr_tokens = json.loads(ocr_tokens)
            except Exception:
                ocr_tokens = {}

        # Try to auto-attach bbox from stored OCR tokens if enabled
        if settings.AUTO_ANCHOR_CORRECTIONS and ocr_tokens:
            for field, value in correction.corrected_data.items():
                if field in bbox_map:
                    continue
                token_match = _find_bbox_from_tokens(value, ocr_tokens)
                if token_match:
                    bbox, page = token_match
                    bbox_map[field] = bbox
                    if page is not None:
                        page_map[field] = page

        # If bbox not provided, try to locate on the page image
        img_path = _guess_image_path(invoice, preferred_page=list(page_map.values())[0] if page_map else 1)
        if img_path:
            for field, value in correction.corrected_data.items():
                if field in bbox_map:
                    continue
                auto_bbox = template_service.find_bbox_for_value(str(img_path), str(value))
                if auto_bbox:
                    bbox_map[field] = auto_bbox
                    if field not in page_map:
                        page_map[field] = 1  # default to page 1 for now
        
        template_updated = False
        vendor_id = None
        learned_from = 0
        
        # If invoice has vendor, update template
        if invoice.vendor_id:
            logger.info(f"Updating template for vendor {invoice.vendor_id}")
            
            # Create/update template from corrected data
            template = template_service.create_template_from_invoice(
                db=db,
                vendor_id=invoice.vendor_id,
                extracted_data=invoice.extracted_data,
                field_confidences=invoice.field_confidences or {},
                corrected_data=correction.corrected_data
            )
            
            template_updated = True
            vendor_id = invoice.vendor_id
            learned_from = template.get('learned_from_invoices', 0)
            
            logger.info(f"✅ Template updated! Learned from {learned_from} invoice(s)")

        # Record corrections for learning (with bbox/page when available)
        correction_service.record_corrections(
            db=db,
            invoice_id=invoice.id,
            upload_id=invoice.upload_id,
            vendor_id=invoice.vendor_id,
            corrected_fields=correction.corrected_data,
            page_numbers=page_map if page_map else None,
            bboxes=bbox_map if bbox_map else None,
            source="human_review",
        )
        
        db.commit()
        
        return CorrectionResponse(
            success=True,
            message="Corrections saved successfully. Template updated for future invoices.",
            template_updated=template_updated,
            vendor_id=vendor_id,
            learned_from_invoices=learned_from
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Correction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Correction failed: {str(e)}")

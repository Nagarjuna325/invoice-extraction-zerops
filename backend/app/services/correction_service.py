import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.correction import Correction

logger = logging.getLogger(__name__)


class CorrectionService:
    """
    Lightweight helpers to record and fetch corrections for template learning.
    """

    def record_corrections(
        self,
        db: Session,
        invoice_id,
        upload_id: Optional[str],
        vendor_id: Optional[int],
        corrected_fields: Dict[str, Any],
        source: str = "human_review",
        correction_reason: Optional[str] = None,
        reviewer: Optional[str] = None,
        page_numbers: Optional[Dict[str, int]] = None,
        bboxes: Optional[Dict[str, Any]] = None,
    ) -> List[Correction]:
        """
        Insert one Correction row per field in corrected_fields.
        """
        rows: List[Correction] = []
        for field_name, value in corrected_fields.items():
            field_bbox = None
            if bboxes:
                field_bbox = bboxes.get(field_name)
            field_page = None
            if page_numbers:
                field_page = page_numbers.get(field_name)

            row = Correction(
                invoice_id=invoice_id,
                upload_id=upload_id,
                vendor_id=vendor_id,
                field_name=field_name,
                corrected_value=value,
                page_number=field_page,
                bbox=field_bbox,
                source=source,
                correction_reason=correction_reason,
                reviewer=reviewer,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(row)
            rows.append(row)

        db.commit()
        for row in rows:
            db.refresh(row)

        logger.info(f"Recorded {len(rows)} corrections for vendor_id={vendor_id} invoice_id={invoice_id}")
        return rows

    def get_corrections_for_vendor(
        self,
        db: Session,
        vendor_id: int,
        limit: Optional[int] = None,
    ) -> List[Correction]:
        q = db.query(Correction).filter(Correction.vendor_id == vendor_id).order_by(Correction.created_at.desc())
        if limit:
            q = q.limit(limit)
        return q.all()


correction_service = CorrectionService()

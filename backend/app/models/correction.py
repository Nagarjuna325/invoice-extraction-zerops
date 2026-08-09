from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from app.core.database import Base


class Correction(Base):
    """Stores human or automated corrections for later learning/template updates."""

    __tablename__ = "corrections"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True, index=True)
    upload_id = Column(String(100), nullable=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True, index=True)
    field_name = Column(String(100), nullable=False)
    corrected_value = Column(JSONB, nullable=True)
    page_number = Column(Integer, nullable=True)
    bbox = Column(JSONB, nullable=True)
    source = Column(String(50), nullable=True)  # e.g., human_review, rule, template
    correction_reason = Column(Text, nullable=True)
    reviewer = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Correction field='{self.field_name}' invoice='{self.invoice_id}'>"

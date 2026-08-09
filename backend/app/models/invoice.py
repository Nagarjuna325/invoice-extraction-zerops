
"""
Invoice database model - WITHOUT vendor relationship to avoid circular import
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Numeric, Text, ForeignKey, Boolean, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class Invoice(Base):
    """Invoice database model"""
    
    __tablename__ = "invoices"
    
    # Existing columns (UNCHANGED)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_id = Column(String(100), unique=True, nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(50), nullable=False)
    ocr_engine = Column(String(50), nullable=False)
    ocr_confidence = Column(Numeric(5, 2))
    processing_time_ms = Column(Integer)
    invoice_type = Column(String(100))
    vendor_name = Column(String(255), index=True)
    status = Column(String(50), nullable=False, default='UPLOADED', index=True)
    extracted_data = Column(JSONB, nullable=False, default={})
    raw_ocr_text = Column(Text)
    field_confidences = Column(JSONB, default={})
    overall_confidence = Column(Numeric(5, 2))
    validation_metadata = Column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    ocr_tokens = Column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True))
    ground_truth_locked = Column(Boolean, default=False, server_default=text("false"))
    
    # Vendor relationship columns (just IDs, no SQLAlchemy relationship)
    vendor_id = Column(Integer, nullable=True, index=True)
    used_template = Column(Boolean, default=False)
    template_match_confidence = Column(Float, nullable=True)
    
    # NO relationship() - just store vendor_id as a foreign key reference
    
    def __repr__(self):
        return f"<Invoice(id='{self.id}', vendor='{self.vendor_name}', status='{self.status}')>"

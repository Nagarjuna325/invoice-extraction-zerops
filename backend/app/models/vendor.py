
"""
Vendor database model
Stores vendor information and templates
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, Text, text
from app.core.database import Base
from datetime import datetime


class Vendor(Base):
    """Vendor model - stores vendor info and extraction templates"""
    
    __tablename__ = "vendors"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Vendor identification (from ML extraction)
    vendor_name = Column(String(255), nullable=False, index=True)
    vendor_name_normalized = Column(String(255), index=True)
    vendor_fingerprint = Column(String(64), unique=True, index=True)
    
    # Confidence in vendor identification (from ML)
    confidence = Column(Float, default=0.0)
    
    # Statistics
    invoice_count = Column(Integer, default=0)
    last_seen = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Template data (learned from corrections)
    has_template = Column(Boolean, default=False)
    template_data = Column(JSON, nullable=True)
    template_version = Column(Integer, default=0, server_default=text("0"))
    last_template_applied_at = Column(DateTime(timezone=True), nullable=True)
    
    # Additional metadata (RENAMED from 'metadata' to avoid SQLAlchemy conflict)
    vendor_metadata = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # NO relationship line - removed to avoid circular import
    
    def __repr__(self):
        return f"<Vendor(id={self.id}, name='{self.vendor_name}', invoices={self.invoice_count})>"

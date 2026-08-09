from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class InvoiceUploadResponse(BaseModel):
    """Response schema for invoice upload"""
    upload_id: str
    status: str
    message: str
    estimated_time_seconds: Optional[int] = 15
    polling_url: str


class InvoiceStatusResponse(BaseModel):
    """Response schema for processing status"""
    upload_id: str
    status: str
    progress: int
    current_stage: Optional[str] = None
    processing_time_ms: Optional[int] = None


class ErrorResponse(BaseModel):
    """Error response schema"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
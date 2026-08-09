"""
Vendor recognition and management service
100% AUTOMATIC - extracts vendor from ML results, no hardcoding!
"""
import re
import hashlib
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class VendorService:
    """
    Vendor recognition service - FULLY AUTOMATIC
    
    Takes vendor name from ML extraction results
    Normalizes and creates fingerprint
    Matches to existing vendors or creates new
    """
    
    def extract_vendor_info(self, extracted_data: Dict[str, Any], field_confidences: Dict[str, float]) -> Dict[str, Any]:
        """
        Extract and normalize vendor information from ML results
        
        Args:
            extracted_data: Data extracted by Triple Hybrid ML models
            field_confidences: Confidence scores from ML models
            
        Returns:
            {
                'vendor_name': str (original from ML),
                'vendor_name_normalized': str (cleaned),
                'vendor_fingerprint': str (unique hash),
                'confidence': float (from ML)
            }
        """
        # Get vendor name from ML extraction results
        vendor_name = extracted_data.get('vendor_name')
        confidence = field_confidences.get('vendor_name', 0.0)
        
        if not vendor_name or confidence < 10.0:
            logger.warning("No vendor name extracted or confidence too low")
            return {
                'vendor_name': None,
                'vendor_name_normalized': None,
                'vendor_fingerprint': None,
                'confidence': 0.0
            }
        
        logger.info(f"Processing vendor: '{vendor_name}' (confidence: {confidence:.1f}%)")
        
        # Normalize vendor name (remove Corp, Inc, etc)
        normalized = self._normalize_vendor_name(vendor_name)
        
        # Create unique fingerprint
        fingerprint = self._create_vendor_fingerprint(normalized)
        
        logger.info(f"Vendor normalized: '{normalized}' → fingerprint: {fingerprint}")
        
        return {
            'vendor_name': vendor_name,  # Original from ML
            'vendor_name_normalized': normalized,  # Cleaned version
            'vendor_fingerprint': fingerprint,  # Unique ID
            'confidence': confidence  # From ML
        }
    
    def _normalize_vendor_name(self, vendor_name: str) -> str:
        """
        Normalize vendor name for matching
        
        Removes:
        - Legal entities (Corp, Inc, LLC, Ltd)
        - Common words (Receipt, Invoice)
        - Special characters
        - Extra whitespace
        
        Examples:
            "Hankook Tire America Corp." → "hankooktireamrica"
            "Belle Tire RECEIPT" → "belletire"
            "Global Enterprises, Inc." → "globalenterprises"
        """
        if not vendor_name:
            return ""
        
        # Convert to lowercase
        normalized = vendor_name.lower()
        
        # Remove common legal suffixes
        legal_suffixes = [
            r'\s*corp\.?',
            r'\s*corporation',
            r'\s*inc\.?',
            r'\s*incorporated',
            r'\s*llc',
            r'\s*ltd\.?',
            r'\s*limited',
            r'\s*co\.?',
            r'\s*company',
        ]
        
        for suffix in legal_suffixes:
            normalized = re.sub(suffix, '', normalized, flags=re.IGNORECASE)
        
        # Remove common invoice words
        invoice_words = [
            r'\s*receipt',
            r'\s*invoice',
            r'\s*bill',
        ]
        
        for word in invoice_words:
            normalized = re.sub(word, '', normalized, flags=re.IGNORECASE)
        
        # Remove special characters and punctuation
        normalized = re.sub(r'[^a-z0-9\s]', '', normalized)
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', '', normalized)
        
        # Remove common articles/prepositions
        common_words = ['the', 'and', 'of', 'for', 'at', 'in', 'on']
        for word in common_words:
            normalized = normalized.replace(word, '')
        
        return normalized.strip()
    
    def _create_vendor_fingerprint(self, normalized_name: str) -> str:
        """
        Create unique fingerprint for vendor using SHA256 hash
        
        Args:
            normalized_name: Normalized vendor name
            
        Returns:
            16-character hex string (first 16 chars of SHA256)
        """
        if not normalized_name:
            return None
        
        # Create SHA256 hash
        hash_obj = hashlib.sha256(normalized_name.encode('utf-8'))
        
        # Return first 16 characters
        return hash_obj.hexdigest()[:16]
    
    def find_or_create_vendor(self, db: Session, vendor_info: Dict[str, Any]):
        """
        Find existing vendor or create new one
        
        Args:
            db: Database session
            vendor_info: Result from extract_vendor_info()
            
        Returns:
            Vendor model instance (from database)
        """
        from app.models.vendor import Vendor
        
        fingerprint = vendor_info.get('vendor_fingerprint')
        
        if not fingerprint:
            logger.warning("No vendor fingerprint - creating unknown vendor")
            # Create temporary unknown vendor (not saved to DB)
            return None
        
        # Search for existing vendor by fingerprint
        existing_vendor = db.query(Vendor).filter(
            Vendor.vendor_fingerprint == fingerprint
        ).first()
        
        if existing_vendor:
            # Found existing vendor - update stats
            logger.info(f"✅ Found existing vendor: {existing_vendor.vendor_name} (ID: {existing_vendor.id})")
            
            # Update invoice count
            existing_vendor.invoice_count += 1
            existing_vendor.last_seen = datetime.now()
            
            # Update vendor name if current extraction has higher confidence
            current_confidence = existing_vendor.confidence or 0
            new_confidence = vendor_info.get('confidence', 0)
            
            if new_confidence > current_confidence:
                logger.info(f"Updating vendor name (higher confidence: {new_confidence:.1f}% > {current_confidence:.1f}%)")
                existing_vendor.vendor_name = vendor_info['vendor_name']
                existing_vendor.confidence = new_confidence
            
            db.commit()
            db.refresh(existing_vendor)
            
            return existing_vendor
        
        else:
            # Create new vendor
            new_vendor = Vendor(
                vendor_name=vendor_info['vendor_name'],
                vendor_name_normalized=vendor_info['vendor_name_normalized'],
                vendor_fingerprint=fingerprint,
                confidence=vendor_info['confidence'],
                invoice_count=1,
                has_template=False,
                template_data=None
            )
            
            db.add(new_vendor)
            db.commit()
            db.refresh(new_vendor)
            
            logger.info(f"✅ Created new vendor: {new_vendor.vendor_name} (ID: {new_vendor.id})")
            
            return new_vendor
    
    def match_vendor(self, db: Session, vendor_info: Dict[str, Any]):
        """
        Match invoice to existing vendor (without creating new)
        
        Args:
            db: Database session
            vendor_info: Result from extract_vendor_info()
            
        Returns:
            Vendor if found, None if not found
        """
        from app.models.vendor import Vendor
        
        fingerprint = vendor_info.get('vendor_fingerprint')
        
        if not fingerprint:
            return None
        
        vendor = db.query(Vendor).filter(
            Vendor.vendor_fingerprint == fingerprint
        ).first()
        
        if vendor:
            logger.info(f"Matched to vendor: {vendor.vendor_name} (ID: {vendor.id})")
        else:
            logger.info("No matching vendor found")
        
        return vendor
    
    def get_vendor_stats(self, db: Session, vendor_id: int) -> Dict[str, Any]:
        """
        Get statistics for a vendor
        
        Args:
            db: Database session
            vendor_id: Vendor ID
            
        Returns:
            Dictionary with vendor stats
        """
        from app.models.vendor import Vendor
        from app.models.invoice import Invoice
        from sqlalchemy import func
        
        vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
        
        if not vendor:
            return {}
        
        # Count invoices
        invoice_count = db.query(Invoice).filter(
            Invoice.vendor_id == vendor_id
        ).count()
        
        # Calculate average confidence
        avg_confidence = db.query(func.avg(Invoice.overall_confidence)).filter(
            Invoice.vendor_id == vendor_id
        ).scalar() or 0.0
        
        return {
            'vendor_id': vendor.id,
            'vendor_name': vendor.vendor_name,
            'vendor_name_normalized': vendor.vendor_name_normalized,
            'vendor_fingerprint': vendor.vendor_fingerprint,
            'invoice_count': invoice_count,
            'average_confidence': round(avg_confidence, 2),
            'has_template': vendor.has_template,
            'created_at': vendor.created_at,
            'last_seen': vendor.last_seen
        }


# Create singleton
vendor_service = VendorService()

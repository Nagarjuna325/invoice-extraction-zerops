# """
# Upload endpoint with Quadruple Hybrid + Vendor Recognition + Template Learning
# PHASE 1 INTEGRATION - Quadruple Hybrid ML System
# """
# from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
# from sqlalchemy.orm import Session
# from app.core.database import get_db
# from app.models.invoice import Invoice
# from app.schemas.invoice import InvoiceUploadResponse, InvoiceStatusResponse
# from app.services.storage_service import storage_service
# from app.services.quadruple_hybrid_service import quadruple_hybrid_service
# from app.services.vendor_service import vendor_service
# from app.services.template_service import template_service
# from app.services.document_processor import document_processor
# from app.utils.validators import validate_upload
# from app.utils.file_helper import normalize_file_type
# from datetime import datetime
# import logging
# import time

# router = APIRouter()
# logger = logging.getLogger(__name__)


# def process_invoice_background(upload_id: str, file_path: str, ocr_engine: str):
#     """
#     Background task to process invoice with:
#     1. Document type detection (PDF/Excel/CSV/Image)
#     2. Quadruple Hybrid extraction (Docling + Impira + LayoutLM + Donut)
#     3. Vendor recognition
#     4. Template application (if exists)
#     5. Template learning (from corrections)
#     """
#     from app.core.database import SessionLocal

#     db = SessionLocal()
#     try:
#         logger.info(f"Background processing started: {upload_id}")

#         # Get invoice record
#         invoice = db.query(Invoice).filter(Invoice.upload_id == upload_id).first()
#         if not invoice:
#             logger.error(f"Invoice not found: {upload_id}")
#             return

#         # Update status to PROCESSING
#         invoice.status = "PROCESSING"
#         db.commit()

#         # Start timer
#         start_time = time.time()

#         # STEP 1: Process document (detect type and convert if needed)
#         logger.info(f"[1/5] Processing document type...")
#         try:
#             doc_type, processed_data = document_processor.process_document(file_path)
#             logger.info(f"✅ Document type: {doc_type}")
#         except Exception as e:
#             logger.error(f"Document processing failed: {e}")
#             doc_type = "image"
#             processed_data = file_path

#         # STEP 2: Extract data based on document type
#         logger.info(f"[2/5] Extracting with Quadruple Hybrid ML...")
        
#         if doc_type in ['excel', 'csv']:
#             # Structured data - already extracted
#             extracted_data = processed_data
#             field_confidences = processed_data.get('_confidences', {})
#             if '_confidences' in extracted_data:
#                 del extracted_data['_confidences']
#             method = f"{doc_type}_parsing"
#             raw_ocr_text = ""  # No OCR for structured data
#             line_items = []
#             model_outputs = {}
#             voting_details = {}
            
#         elif doc_type == 'pdf':
#             # PDF - Use Quadruple Hybrid with Docling
#             logger.info(f"   Using Quadruple Hybrid (Docling + Impira + LayoutLM + Donut)")
            
#             # Get first page image and original PDF path
#             image_path = processed_data[0] if processed_data else file_path
#             pdf_path = file_path  # Original PDF for Docling
            
#             # Extract with all 4 models
#             result = quadruple_hybrid_service.extract_invoice(
#                 image_path=image_path,
#                 pdf_path=pdf_path
#             )
            
#             extracted_data = result['extracted_data']
#             field_confidences = result['field_confidences']
#             method = 'quadruple_hybrid'
#             raw_ocr_text = result.get('raw_ocr_text', '')
#             line_items = result.get('line_items', [])
#             model_outputs = result.get('model_outputs', {})
#             voting_details = result.get('voting_details', {})
            
#             logger.info(f"   Models used: {', '.join(result.get('models_used', []))}")
            
#             # Cleanup temp files
#             if len(processed_data) > 0:
#                 document_processor.cleanup_temp_files(processed_data)
                
#         else:
#             # Image - Use Quadruple Hybrid (no PDF available, so 3 models only)
#             logger.info(f"   Using Triple Hybrid (Impira + LayoutLM + Donut)")
            
#             result = quadruple_hybrid_service.extract_invoice(
#                 image_path=processed_data,
#                 pdf_path=None  # No PDF for images
#             )
            
#             extracted_data = result['extracted_data']
#             field_confidences = result['field_confidences']
#             method = 'quadruple_hybrid'
#             raw_ocr_text = result.get('raw_ocr_text', '')
#             line_items = result.get('line_items', [])
#             model_outputs = result.get('model_outputs', {})
#             voting_details = result.get('voting_details', {})
            
#             logger.info(f"   Models used: {', '.join(result.get('models_used', []))}")

#         logger.info(f"✅ Extracted {len(extracted_data)} fields using {method}")

#         # STEP 3: Vendor recognition
#         logger.info(f"[3/5] Recognizing vendor...")
#         vendor_info = vendor_service.extract_vendor_info(extracted_data, field_confidences)
        
#         vendor = None
#         if vendor_info.get('vendor_fingerprint'):
#             vendor = vendor_service.find_or_create_vendor(db, vendor_info)
#             logger.info(f"✅ Vendor: {vendor.vendor_name if vendor else 'Unknown'} (ID: {vendor.id if vendor else 'N/A'})")
#         else:
#             logger.warning("⚠️  No vendor detected")

#         # STEP 4: Apply template if exists
#         template_applied = False
#         template_match_confidence = 0.0
        
#         if vendor and vendor.has_template:
#             logger.info(f"[4/5] Applying existing template...")
#             try:
#                 template_data = vendor.template_data
                
#                 # Apply template to improve extraction
#                 improved_data, improved_confidences = template_service.apply_template(
#                     template_data,
#                     extracted_data,
#                     field_confidences
#                 )
                
#                 # Use improved data
#                 extracted_data = improved_data
#                 field_confidences = improved_confidences
#                 template_applied = True
                
#                 # Calculate template match confidence
#                 template_match_confidence = sum(improved_confidences.values()) / len(improved_confidences) if improved_confidences else 0.0
                
#                 logger.info(f"✅ Template applied! Match confidence: {template_match_confidence:.1f}%")
#             except Exception as e:
#                 logger.error(f"Template application failed: {e}")
#         else:
#             logger.info(f"[4/5] No template exists yet (will be created after first correction)")

#         # Calculate processing time
#         processing_time = int((time.time() - start_time) * 1000)  # milliseconds

#         # Calculate overall confidence
#         if field_confidences:
#             overall_confidence = sum(field_confidences.values()) / len(field_confidences)
#         else:
#             overall_confidence = 0.0

#         # STEP 5: Update invoice with results
#         logger.info(f"[5/5] Saving results...")
        
#         invoice.extracted_data = extracted_data
#         invoice.field_confidences = field_confidences
#         invoice.overall_confidence = round(overall_confidence, 2)
#         invoice.processing_time_ms = processing_time
#         invoice.ocr_engine = f"quadruple_hybrid_{method}"
#         invoice.raw_ocr_text = raw_ocr_text
#         invoice.status = "EXTRACTED"
#         invoice.processed_at = datetime.now()
#         invoice.invoice_type = doc_type
        
#         # Store additional Quadruple Hybrid data
#         if line_items:
#             extracted_data['_line_items'] = line_items
#         if model_outputs:
#             extracted_data['_model_outputs'] = model_outputs
#         if voting_details:
#             extracted_data['_voting_details'] = voting_details
        
#         # Link to vendor
#         if vendor:
#             invoice.vendor_id = vendor.id
#             invoice.vendor_name = vendor.vendor_name
#             invoice.used_template = template_applied
#             invoice.template_match_confidence = template_match_confidence if template_applied else None

#         # Extract vendor name to top-level field (for backward compatibility)
#         if 'vendor_name' in extracted_data:
#             invoice.vendor_name = extracted_data['vendor_name']

#         db.commit()

#         logger.info(f"✅ Processing complete: {upload_id}")
#         logger.info(f"   Document type: {doc_type}")
#         logger.info(f"   Method: {method}")
#         logger.info(f"   Fields extracted: {list(extracted_data.keys())}")
#         logger.info(f"   Line items: {len(line_items)}")
#         logger.info(f"   Overall confidence: {overall_confidence:.2f}%")
#         logger.info(f"   Template applied: {template_applied}")
#         logger.info(f"   Vendor: {vendor.vendor_name if vendor else 'None'}")
#         logger.info(f"   Processing time: {processing_time}ms")

#     except Exception as e:
#         logger.error(f"❌ Background processing failed: {e}", exc_info=True)
#         # Update status to FAILED
#         try:
#             invoice = db.query(Invoice).filter(Invoice.upload_id == upload_id).first()
#             if invoice:
#                 invoice.status = "FAILED"
#                 invoice.extracted_data = {"error": str(e)}
#                 db.commit()
#         except:
#             pass
#     finally:
#         db.close()


# @router.post("/upload", response_model=InvoiceUploadResponse)
# async def upload_invoice(
#     background_tasks: BackgroundTasks,
#     file: UploadFile = File(...),
#     ocr_engine: str = Form(default="quadruple_hybrid"),
#     db: Session = Depends(get_db)
# ):
#     """
#     Upload invoice file for processing
    
#     Supports:
#     - Images (PNG, JPG)
#     - PDFs (single/multi-page)
#     - Excel (XLSX, XLS)
#     - CSV
    
#     Features:
#     - Quadruple Hybrid ML extraction (Docling + Impira + LayoutLM + Donut)
#     - 4-way consensus voting for maximum accuracy
#     - Automatic vendor recognition
#     - Template application for known vendors
#     - Table/line item extraction
#     - 90%+ accuracy
#     """
#     logger.info(f"Upload request: {file.filename}, Engine: {ocr_engine}")

#     try:
#         # Read file
#         file_content = await file.read()
#         file_size = len(file_content)

#         # Validate
#         is_valid, error_message = validate_upload(
#             file_size=file_size,
#             content_type=file.content_type,
#             filename=file.filename
#         )

#         if not is_valid:
#             raise HTTPException(status_code=400, detail=error_message)

#         # Generate upload ID and save file
#         upload_id = storage_service.generate_upload_id()
#         file_path = storage_service.save_file(file_content, file.filename, upload_id)

#         # Create database record
#         invoice = Invoice(
#             upload_id=upload_id,
#             file_name=file.filename,
#             file_path=file_path,
#             file_size=file_size,
#             file_type=normalize_file_type(file.content_type),
#             ocr_engine=ocr_engine,
#             status="UPLOADED",
#             extracted_data={},
#             field_confidences={}
#         )

#         db.add(invoice)
#         db.commit()

#         # Start background processing
#         background_tasks.add_task(
#             process_invoice_background,
#             upload_id=upload_id,
#             file_path=file_path,
#             ocr_engine=ocr_engine
#         )

#         logger.info(f"✅ Upload successful: {upload_id}, processing started")

#         return InvoiceUploadResponse(
#             upload_id=upload_id,
#             status="UPLOADED",
#             message="Invoice uploaded successfully. Processing with Quadruple Hybrid ML (Docling + Impira + LayoutLM + Donut).",
#             estimated_time_seconds=90,
#             polling_url=f"/api/v1/invoices/{upload_id}/status"
#         )

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Upload failed: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# @router.get("/{upload_id}/status", response_model=InvoiceStatusResponse)
# async def get_upload_status(upload_id: str, db: Session = Depends(get_db)):
#     """Get upload/processing status"""

#     invoice = db.query(Invoice).filter(Invoice.upload_id == upload_id).first()

#     if not invoice:
#         raise HTTPException(status_code=404, detail="Upload not found")

#     progress_map = {
#         "UPLOADED": 10,
#         "PROCESSING": 50,
#         "EXTRACTED": 100,
#         "FAILED": 0
#     }

#     return InvoiceStatusResponse(
#         upload_id=upload_id,
#         status=invoice.status,
#         progress=progress_map.get(invoice.status, 0),
#         current_stage=invoice.status,
#         processing_time_ms=invoice.processing_time_ms
#     )


# @router.get("/{upload_id}", response_model=dict)
# async def get_invoice(upload_id: str, db: Session = Depends(get_db)):
#     """Get full invoice data including extracted fields"""
    
#     invoice = db.query(Invoice).filter(Invoice.upload_id == upload_id).first()
    
#     if not invoice:
#         raise HTTPException(status_code=404, detail="Invoice not found")
    
#     # Check for validation warnings in extracted_data
#     validation_warnings = invoice.extracted_data.get('_needs_review', []) if invoice.extracted_data else []
    
#     # Extract special fields
#     line_items = invoice.extracted_data.get('_line_items', []) if invoice.extracted_data else []
#     model_outputs = invoice.extracted_data.get('_model_outputs', {}) if invoice.extracted_data else {}
#     voting_details = invoice.extracted_data.get('_voting_details', {}) if invoice.extracted_data else {}
    
#     # Clean extracted_data (remove internal fields)
#     clean_extracted_data = {k: v for k, v in invoice.extracted_data.items() if not k.startswith('_')} if invoice.extracted_data else {}
    
#     return {
#         "upload_id": invoice.upload_id,
#         "file_name": invoice.file_name,
#         "file_type": invoice.file_type,
#         "status": invoice.status,
#         "invoice_type": invoice.invoice_type,
#         "vendor_name": invoice.vendor_name,
#         "vendor_id": invoice.vendor_id,
#         "used_template": invoice.used_template,
#         "template_match_confidence": invoice.template_match_confidence,
#         "extracted_data": clean_extracted_data,
#         "field_confidences": invoice.field_confidences,
#         "overall_confidence": float(invoice.overall_confidence) if invoice.overall_confidence else 0,
#         "processing_time_ms": invoice.processing_time_ms,
#         "ocr_engine": invoice.ocr_engine,
#         "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
#         "processed_at": invoice.processed_at.isoformat() if invoice.processed_at else None,
#         "validation_warnings": validation_warnings,
#         "needs_review": len(validation_warnings) > 0,
#         "line_items": line_items,
#         "model_outputs": model_outputs if model_outputs else None,
#         "voting_details": voting_details if voting_details else None
#     }

"""
Upload endpoint with Quadruple Hybrid + Validation + Vendor Recognition + Template Learning
PHASE 4: Image Quality Check + Multi-Page Support Added
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.invoice import Invoice
from app.schemas.invoice import InvoiceUploadResponse, InvoiceStatusResponse
from app.services.storage_service import storage_service
from app.services.quadruple_hybrid_service import quadruple_hybrid_service
from app.services.validation_service import validation_service
from app.services.vendor_service import vendor_service
from app.services.template_service import template_service
from app.services.intelligent_merger import intelligent_merger
from app.services.correction_service import correction_service
from app.services.document_processor import document_processor
from app.utils.validators import validate_upload
from app.utils.file_helper import normalize_file_type
from app.utils.image_quality_checker import image_quality_checker  # PHASE 4: NEW
from typing import List, Optional
from app.config import settings
from datetime import datetime
import logging
import time

router = APIRouter()
logger = logging.getLogger(__name__)


def process_invoice_background(upload_id: str, file_path: str, ocr_engine: str):
    """
    Background task to process invoice with:
    1. PHASE 4: Image quality check & enhancement
    2. Document type detection (PDF/Excel/CSV/Image)
    3. PHASE 4: Multi-page PDF support
    4. Quadruple Hybrid extraction (Docling + Impira + LayoutLM + Donut)
    5. PHASE 2: Smart Validation & Auto-correction (ALL decimal formats)
    6. Vendor recognition
    7. Template application (if exists)
    8. Template learning (from corrections)
    """
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        logger.info(f"Background processing started: {upload_id}")

        # Get invoice record
        invoice = db.query(Invoice).filter(Invoice.upload_id == upload_id).first()
        if not invoice:
            logger.error(f"Invoice not found: {upload_id}")
            return

        # Update status to PROCESSING
        invoice.status = "PROCESSING"
        db.commit()

        # Start timer
        start_time = time.time()
        ocr_tokens_payload: dict = {}
        ocr_fused_payload: dict = {}

        # PHASE 4: STEP 0 - Image Quality Check (for PNG/JPG only)
        quality_metrics = {}
        original_file_path = file_path
        
        if settings.ENABLE_ADVANCED_OCR_PIPELINE:
            logger.info("[0/7] Skipping quality check (handled by pre-OCR pipeline)")
        elif invoice.file_type in ['image/png', 'image/jpeg', 'image/jpg']:
            logger.info(f"[0/7] Checking image quality...")
            try:
                is_acceptable, quality_metrics, enhanced_path = image_quality_checker.check_quality(
                    file_path,
                    auto_enhance=True  # Auto-enhance poor quality images
                )
                
                logger.info(f"   Quality metrics:")
                logger.info(f"   - Resolution: {quality_metrics.get('width')}x{quality_metrics.get('height')}")
                logger.info(f"   - DPI: {quality_metrics.get('dpi', 'N/A')}")
                logger.info(f"   - Sharpness: {quality_metrics.get('blur_score', 'N/A')}")
                logger.info(f"   - Contrast: {quality_metrics.get('contrast', 'N/A')}")
                logger.info(f"   - Brightness: {quality_metrics.get('brightness', 'N/A')}")
                
                # Use enhanced image if available
                if enhanced_path:
                    logger.info(f"   ✅ Using enhanced image: {enhanced_path}")
                    file_path = enhanced_path
                    quality_metrics['enhanced'] = True
                elif not is_acceptable:
                    issues = quality_metrics.get('issues', [])
                    logger.warning(f"   ⚠️  Image quality issues detected:")
                    for issue in issues:
                        logger.warning(f"      - {issue}")
                    # Continue anyway but flag for review
                    quality_metrics['quality_warning'] = True
                else:
                    logger.info(f"   ✅ Image quality acceptable")
                    
            except Exception as e:
                logger.error(f"   Image quality check failed: {e}")
                # Continue with original image
                quality_metrics = {'error': str(e)}

        temp_files_for_cleanup: List[str] = []
        template_image_path: Optional[str] = None

        # STEP 1: Process document (detect type and convert if needed)
        logger.info(f"[1/7] Processing document type...")
        try:
            doc_type, processed_data = document_processor.process_document(file_path)
            logger.info(f"✅ Document type: {doc_type}")
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            doc_type = "image"
            processed_data = file_path

        # STEP 2: Extract data based on document type
        logger.info(f"[2/7] Extracting with Quadruple Hybrid ML...")

        if doc_type in ['excel', 'csv']:
            # Structured data - already extracted
            extracted_data = processed_data
            field_confidences = processed_data.get('_confidences', {})
            if '_confidences' in extracted_data:
                del extracted_data['_confidences']
            method = f"{doc_type}_parsing"
            raw_ocr_text = ""  # No OCR for structured data
            line_items = []
            model_outputs = {}
            voting_details = {}
            
        elif doc_type == 'pdf':
            # PHASE 4: Multi-page PDF support
            logger.info(f"   Using Quadruple Hybrid with multi-page support")
            logger.info(f"   PDF has {len(processed_data)} pages")
            
            pdf_path = original_file_path  # Use ORIGINAL PDF (not enhanced image)
            temp_files_for_cleanup = processed_data if isinstance(processed_data, list) else []
            
            # PHASE 4: Check if multi-page
            if len(processed_data) > 1:
                # Multi-page PDF
                logger.info(f"   Processing multi-page PDF ({len(processed_data)} pages)...")
                
                result = quadruple_hybrid_service.extract_invoice_multipage(
                    image_paths=processed_data,
                    pdf_path=pdf_path
                )
                template_image_path = processed_data[0] if processed_data else None
            else:
                # Single page PDF
                image_path = processed_data[0] if processed_data else file_path
                template_image_path = image_path
                
                result = quadruple_hybrid_service.extract_invoice(
                    image_path=image_path,
                    pdf_path=pdf_path
                )
            
            extracted_data = result['extracted_data']
            field_confidences = result['field_confidences']
            method = 'quadruple_hybrid'
            raw_ocr_text = result.get('raw_ocr_text', '')
            line_items = result.get('line_items', [])
            model_outputs = result.get('model_outputs', {})
            voting_details = result.get('voting_details', {})
            ocr_tokens_payload = result.get('ocr_tokens', {}) if settings.STORE_OCR_TOKENS else {}
            ocr_texts_payload = result.get('ocr_texts', {}) if settings.STORE_OCR_TEXTS else {}
            ocr_fused_payload = result.get('ocr_fused_fields', {}) if settings.ENABLE_OCR_FUSION else {}
            if settings.ENABLE_ADVANCED_OCR_PIPELINE:
                pre_ocr_meta = result.get("pre_ocr_metadata", {})
                if pre_ocr_meta:
                    quality_metrics = pre_ocr_meta.get("quality_metrics", {}) or {}
                    if pre_ocr_meta.get("estimated_dpi") is not None:
                        quality_metrics["pre_dpi_estimated"] = pre_ocr_meta.get("estimated_dpi")
                    if pre_ocr_meta.get("dpi_metadata") is not None:
                        quality_metrics["pre_dpi_metadata"] = pre_ocr_meta.get("dpi_metadata")
                    if pre_ocr_meta.get("effective_dpi") is not None:
                        quality_metrics["post_dpi_effective"] = pre_ocr_meta.get("effective_dpi")
                    quality_metrics["pre_ocr_scale_factor"] = pre_ocr_meta.get("scale_factor")
                    logger.info(
                        "Pre-OCR DPI: pre=%s post=%s scale=%s",
                        quality_metrics.get("pre_dpi_estimated"),
                        quality_metrics.get("post_dpi_effective"),
                        quality_metrics.get("pre_ocr_scale_factor"),
                    )
            
            # PHASE 4: Check if multi-page invoice detected
            is_multipage = extracted_data.get('_multipage', False)
            page_count = extracted_data.get('_page_count', 1)
            
            if is_multipage:
                logger.info(f"   ✅ Multi-page invoice: {page_count} pages processed")
                
                if extracted_data.get('_multiple_invoices_detected'):
                    logger.warning(f"   ⚠️  Multiple invoices detected in PDF!")
            
            logger.info(f"   Models used: {', '.join(result.get('models_used', []))}")
            
        else:
            # Image - Use Quadruple Hybrid (no PDF available, so 3 models only)
            logger.info(f"   Using Triple Hybrid (Impira + LayoutLM + Donut)")
            
            result = quadruple_hybrid_service.extract_invoice(
                image_path=file_path,  # Use enhanced image if available
                pdf_path=None  # No PDF for images
            )
            
            extracted_data = result['extracted_data']
            field_confidences = result['field_confidences']
            method = 'quadruple_hybrid'
            raw_ocr_text = result.get('raw_ocr_text', '')
            line_items = result.get('line_items', [])
            model_outputs = result.get('model_outputs', {})
            voting_details = result.get('voting_details', {})
            ocr_tokens_payload = result.get('ocr_tokens', {}) if settings.STORE_OCR_TOKENS else {}
            ocr_texts_payload = result.get('ocr_texts', {}) if settings.STORE_OCR_TEXTS else {}
            ocr_fused_payload = result.get('ocr_fused_fields', {}) if settings.ENABLE_OCR_FUSION else {}
            if settings.ENABLE_ADVANCED_OCR_PIPELINE:
                pre_ocr_meta = result.get("pre_ocr_metadata", {})
                if pre_ocr_meta:
                    quality_metrics = pre_ocr_meta.get("quality_metrics", {}) or {}
                    if pre_ocr_meta.get("estimated_dpi") is not None:
                        quality_metrics["pre_dpi_estimated"] = pre_ocr_meta.get("estimated_dpi")
                    if pre_ocr_meta.get("dpi_metadata") is not None:
                        quality_metrics["pre_dpi_metadata"] = pre_ocr_meta.get("dpi_metadata")
                    if pre_ocr_meta.get("effective_dpi") is not None:
                        quality_metrics["post_dpi_effective"] = pre_ocr_meta.get("effective_dpi")
                    quality_metrics["pre_ocr_scale_factor"] = pre_ocr_meta.get("scale_factor")
                    logger.info(
                        "Pre-OCR DPI: pre=%s post=%s scale=%s",
                        quality_metrics.get("pre_dpi_estimated"),
                        quality_metrics.get("post_dpi_effective"),
                        quality_metrics.get("pre_ocr_scale_factor"),
                    )
            template_image_path = file_path
            
            logger.info(f"   Models used: {', '.join(result.get('models_used', []))}")

        logger.info(f"✅ Extracted {len(extracted_data)} fields using {method}")
        logger.info(f"   Raw extraction: {extracted_data}")

        # Optional template voter BEFORE validation (feature-flagged)
        template_applied = False
        template_match_confidence = 0.0

        if settings.ENABLE_TEMPLATE_VOTER:
            template_vendor_info = vendor_service.extract_vendor_info(extracted_data, field_confidences)
            pre_vendor = None
            if template_vendor_info.get("vendor_fingerprint"):
                pre_vendor = vendor_service.match_vendor(db, template_vendor_info)

            if pre_vendor and pre_vendor.has_template and pre_vendor.template_data and result.get("model_results_raw"):
                # Refresh template from any recorded corrections (Phase 3)
                if settings.AUTO_REFRESH_TEMPLATE_FROM_CORRECTIONS:
                    template_service.update_template_from_corrections(db, pre_vendor.id)

                template_voter_fields = template_service.build_template_voter_fields(
                    pre_vendor.template_data,
                    image_path=template_image_path,
                )
                if template_voter_fields:
                    mr = result.get("model_results_raw", {})
                    logger.info(
                        f"[template-voter] Applying template voter for vendor '{pre_vendor.vendor_name}' "
                        f"with {len(template_voter_fields)} fields"
                    )
                    merged_with_template = intelligent_merger.merge_4way(
                        docling_result=mr.get("docling", {}),
                        impira_result=mr.get("impira", {}),
                        layoutlm_result=mr.get("layoutlm", {}),
                        donut_result=mr.get("donut", {}),
                        raw_ocr_text=mr.get("extra_ocr_texts", {}).get("ocr_rapid", ""),
                        extra_ocr_texts=mr.get("extra_ocr_texts", {}),
                        extra_template_fields=template_voter_fields,
                        template_confidence=settings.TEMPLATE_VOTER_CONFIDENCE,
                    )

                    extracted_data = merged_with_template["extracted_data"]
                    field_confidences = merged_with_template["field_confidences"]
                    voting_details = merged_with_template.get("voting_details", {})
                    # overall_confidence will be recomputed in validation; keep merger output for logging only
                    template_applied = True
                    template_match_confidence = settings.TEMPLATE_VOTER_CONFIDENCE
                else:
                    logger.info("[template-voter] Template has no usable fields; skipping voter")
            else:
                logger.info("[template-voter] No matching vendor template found; skipping voter")

        # Cleanup temp files generated during PDF processing (after template voter uses them)
        if temp_files_for_cleanup:
            document_processor.cleanup_temp_files(temp_files_for_cleanup)
            temp_files_for_cleanup = []

        # STEP 3: PHASE 2 - SMART VALIDATION & AUTO-CORRECTION
        logger.info(f"[3/7] Validating and correcting extracted data...")
        logger.info(f"   Before validation: total_amount = {extracted_data.get('total_amount')}")
        
        validation_result = validation_service.validate_and_correct(
            extracted_data=extracted_data,
            field_confidences=field_confidences,
            line_items=line_items if line_items else [],
            raw_ocr_text=raw_ocr_text,
            known_vendor=None,  # We don't know vendor yet
            vendor_id=None
        )
        
        # Update with validated data
        extracted_data = validation_result['validated_data']
        field_confidences = validation_result['field_confidences']
        overall_confidence = validation_result['overall_confidence']
        validation_warnings = validation_result['validation_warnings']
        needs_review = validation_result['needs_review']
        corrections_applied = validation_result['corrections_applied']
        validation_metadata = validation_result.get('validation_metadata', {})
        
        # PHASE 4: Add image quality warnings if any
        if quality_metrics.get('quality_warning'):
            validation_warnings.insert(0, f"Image quality issues: {', '.join(quality_metrics.get('issues', []))}")
        
        # PHASE 4: Add multi-page warnings if any
        if extracted_data.get('_multiple_invoices_detected'):
            page_count = extracted_data.get('_page_count', 1)
            validation_warnings.insert(0, f"PDF contains {page_count} separate invoices - only first invoice extracted")
        
        logger.info(f"✅ Validation complete:")
        logger.info(f"   After validation: total_amount = {extracted_data.get('total_amount')}")
        logger.info(f"   - Corrections applied: {len(corrections_applied)}")
        logger.info(f"   - Warnings: {len(validation_warnings)}")
        logger.info(f"   - Needs review: {needs_review}")
        
        # Log critical corrections
        if corrections_applied:
            for correction in corrections_applied:
                logger.info(f"   📝 {correction}")
        
        # Log warnings (first 5)
        if validation_warnings:
            for warning in validation_warnings[:5]:
                logger.warning(f"   ⚠️  {warning}")

        # STEP 4: Vendor recognition
        logger.info(f"[4/7] Recognizing vendor...")
        vendor_info = vendor_service.extract_vendor_info(extracted_data, field_confidences)
        
        vendor = None
        if vendor_info.get('vendor_fingerprint'):
            vendor = vendor_service.find_or_create_vendor(db, vendor_info)
            logger.info(f"✅ Vendor: {vendor.vendor_name if vendor else 'Unknown'} (ID: {vendor.id if vendor else 'N/A'})")
        else:
            logger.warning("⚠️  No vendor detected")

        # STEP 5: Apply template if exists (skip if template voter already applied)
        if not template_applied and vendor and vendor.has_template:
            logger.info(f"[5/7] Applying existing template...")
            try:
                template_data = vendor.template_data
                
                # Apply template to improve extraction
                improved_data, improved_confidences = template_service.apply_template(
                    template_data,
                    extracted_data,
                    field_confidences,
                    image_path=template_image_path
                )
                
                # Use improved data
                extracted_data = improved_data
                field_confidences = improved_confidences
                template_applied = True
                
                # Calculate template match confidence
                template_match_confidence = sum(improved_confidences.values()) / len(improved_confidences) if improved_confidences else 0.0
                
                logger.info(f"✅ Template applied! Match confidence: {template_match_confidence:.1f}%")
            except Exception as e:
                logger.error(f"Template application failed: {e}")
        else:
            logger.info(f"[5/7] No template exists yet (will be created after first correction)")

        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)  # milliseconds

        # STEP 6: Update invoice with results
        logger.info(f"[6/7] Saving results...")
        
        # Store validation results in extracted_data
        extracted_data['_validation_warnings'] = validation_warnings
        extracted_data['_needs_review'] = needs_review
        extracted_data['_corrections_applied'] = corrections_applied
        extracted_data['_validation_metadata'] = validation_metadata
        
        # PHASE 4: Store image quality metrics
        if quality_metrics:
            extracted_data['_image_quality'] = quality_metrics
        
        # Store additional Quadruple Hybrid data
        if line_items:
            extracted_data['_line_items'] = line_items
        if model_outputs:
            extracted_data['_model_outputs'] = model_outputs
        if voting_details:
            extracted_data['_voting_details'] = voting_details
        if settings.STORE_OCR_TEXTS and ocr_texts_payload:
            extracted_data['_ocr_texts'] = ocr_texts_payload
        if settings.ENABLE_OCR_FUSION and ocr_fused_payload:
            extracted_data['_ocr_fused_fields'] = ocr_fused_payload
        
        invoice.extracted_data = extracted_data
        invoice.field_confidences = field_confidences
        invoice.overall_confidence = round(overall_confidence, 2)
        invoice.processing_time_ms = processing_time
        invoice.ocr_engine = f"quadruple_hybrid_{method}"
        invoice.raw_ocr_text = raw_ocr_text
        invoice.validation_metadata = validation_metadata
        if settings.STORE_OCR_TOKENS:
            invoice.ocr_tokens = ocr_tokens_payload or {}
        invoice.status = "EXTRACTED"
        invoice.processed_at = datetime.now()
        invoice.invoice_type = doc_type
        
        # Link to vendor
        if vendor:
            invoice.vendor_id = vendor.id
            invoice.vendor_name = vendor.vendor_name
            invoice.used_template = template_applied
            invoice.template_match_confidence = template_match_confidence if template_applied else None

        # Extract vendor name to top-level field (for backward compatibility)
        if 'vendor_name' in extracted_data:
            invoice.vendor_name = extracted_data['vendor_name']

        db.commit()

        logger.info(f"✅ Processing complete: {upload_id}")
        logger.info(f"   Document type: {doc_type}")
        logger.info(f"   Method: {method}")
        logger.info(f"   Image quality: {quality_metrics.get('blur_score', 'N/A')} sharpness")
        if extracted_data.get('_multipage'):
            logger.info(f"   Pages: {extracted_data.get('_page_count', 1)}")
        logger.info(f"   Fields extracted: {list([k for k in extracted_data.keys() if not k.startswith('_')])}")
        logger.info(f"   Line items: {len(line_items)}")
        logger.info(f"   Overall confidence: {overall_confidence:.2f}%")
        logger.info(f"   Validation warnings: {len(validation_warnings)}")
        logger.info(f"   Corrections applied: {len(corrections_applied)}")
        logger.info(f"   Needs review: {needs_review}")
        logger.info(f"   Template applied: {template_applied}")
        logger.info(f"   Vendor: {vendor.vendor_name if vendor else 'None'}")
        logger.info(f"   Processing time: {processing_time}ms")

    except Exception as e:
        logger.error(f"❌ Background processing failed: {e}", exc_info=True)
        # Update status to FAILED
        try:
            invoice = db.query(Invoice).filter(Invoice.upload_id == upload_id).first()
            if invoice:
                invoice.status = "FAILED"
                invoice.extracted_data = {"error": str(e)}
                db.commit()
        except:
            pass
    finally:
        db.close()


@router.post("/upload", response_model=InvoiceUploadResponse)
async def upload_invoice(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    ocr_engine: str = Form(default="quadruple_hybrid"),
    db: Session = Depends(get_db)
):
    """
    Upload invoice file for processing
    
    Supports:
    - Images (PNG, JPG)
    - PDFs (single/multi-page)
    - Excel (XLSX, XLS)
    - CSV
    
    Features:
    - PHASE 4: Image quality check & auto-enhancement
    - PHASE 4: Multi-page PDF support
    - Quadruple Hybrid ML extraction (Docling + Impira + LayoutLM + Donut)
    - 4-way consensus voting for maximum accuracy
    - Smart validation with auto-correction (PHASE 2 COMPLETE)
    - ALL decimal format detection (US, European Type 1 & 2)
    - Automatic vendor recognition
    - Template application for known vendors
    - Table/line item extraction
    - 95%+ accuracy
    """
    logger.info(f"Upload request: {file.filename}, Engine: {ocr_engine}")

    try:
        # Read file
        file_content = await file.read()
        file_size = len(file_content)

        # Validate
        is_valid, error_message = validate_upload(
            file_size=file_size,
            content_type=file.content_type,
            filename=file.filename
        )

        if not is_valid:
            raise HTTPException(status_code=400, detail=error_message)

        # Generate upload ID and save file
        upload_id = storage_service.generate_upload_id()
        file_path = storage_service.save_file(file_content, file.filename, upload_id)

        # Create database record
        invoice = Invoice(
            upload_id=upload_id,
            file_name=file.filename,
            file_path=file_path,
            file_size=file_size,
            file_type=normalize_file_type(file.content_type),
            ocr_engine=ocr_engine,
            status="UPLOADED",
            extracted_data={},
            field_confidences={}
        )

        db.add(invoice)
        db.commit()

        # Start background processing
        background_tasks.add_task(
            process_invoice_background,
            upload_id=upload_id,
            file_path=file_path,
            ocr_engine=ocr_engine
        )

        logger.info(f"✅ Upload successful: {upload_id}, processing started")

        return InvoiceUploadResponse(
            upload_id=upload_id,
            status="UPLOADED",
            message="Invoice uploaded successfully. Processing with PHASE 4: Image Quality Check + Multi-Page Support + Quadruple Hybrid ML + Smart Validation.",
            estimated_time_seconds=90,
            polling_url=f"/api/v1/invoices/{upload_id}/status"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/{upload_id}/status", response_model=InvoiceStatusResponse)
async def get_upload_status(upload_id: str, db: Session = Depends(get_db)):
    """Get upload/processing status"""

    invoice = db.query(Invoice).filter(Invoice.upload_id == upload_id).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Upload not found")

    progress_map = {
        "UPLOADED": 10,
        "PROCESSING": 50,
        "EXTRACTED": 100,
        "FAILED": 0
    }

    return InvoiceStatusResponse(
        upload_id=upload_id,
        status=invoice.status,
        progress=progress_map.get(invoice.status, 0),
        current_stage=invoice.status,
        processing_time_ms=invoice.processing_time_ms
    )


@router.get("/{upload_id}", response_model=dict)
async def get_invoice(upload_id: str, db: Session = Depends(get_db)):
    """Get full invoice data including extracted fields and validation results"""
    
    invoice = db.query(Invoice).filter(Invoice.upload_id == upload_id).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Extract PHASE 2 validation info
    validation_warnings = invoice.extracted_data.get('_validation_warnings', []) if invoice.extracted_data else []
    needs_review = invoice.extracted_data.get('_needs_review', False) if invoice.extracted_data else False
    corrections_applied = invoice.extracted_data.get('_corrections_applied', []) if invoice.extracted_data else []
    validation_metadata = invoice.extracted_data.get('_validation_metadata', {}) if invoice.extracted_data else {}
    
    # PHASE 4: Extract image quality info
    image_quality = invoice.extracted_data.get('_image_quality', {}) if invoice.extracted_data else {}
    
    # PHASE 4: Extract multi-page info
    is_multipage = invoice.extracted_data.get('_multipage', False) if invoice.extracted_data else False
    page_count = invoice.extracted_data.get('_page_count', 1) if invoice.extracted_data else 1
    multiple_invoices = invoice.extracted_data.get('_multiple_invoices_detected', False) if invoice.extracted_data else False
    other_pages = invoice.extracted_data.get('_other_pages', []) if invoice.extracted_data else []
    
    # Extract Quadruple Hybrid info
    line_items = invoice.extracted_data.get('_line_items', []) if invoice.extracted_data else []
    model_outputs = invoice.extracted_data.get('_model_outputs', {}) if invoice.extracted_data else {}
    voting_details = invoice.extracted_data.get('_voting_details', {}) if invoice.extracted_data else {}
    
    # Clean extracted_data (remove internal fields)
    clean_extracted_data = {
        k: v for k, v in invoice.extracted_data.items() 
        if not k.startswith('_')
    } if invoice.extracted_data else {}
    
    response = {
        "upload_id": invoice.upload_id,
        "file_name": invoice.file_name,
        "file_type": invoice.file_type,
        "status": invoice.status,
        "invoice_type": invoice.invoice_type,
        "vendor_name": invoice.vendor_name,
        "vendor_id": invoice.vendor_id,
        "used_template": invoice.used_template,
        "template_match_confidence": invoice.template_match_confidence,
        "extracted_data": clean_extracted_data,
        "field_confidences": invoice.field_confidences,
        "overall_confidence": float(invoice.overall_confidence) if invoice.overall_confidence else 0,
        "processing_time_ms": invoice.processing_time_ms,
        "ocr_engine": invoice.ocr_engine,
        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
        "processed_at": invoice.processed_at.isoformat() if invoice.processed_at else None,
        
        # PHASE 2: Validation results
        "validation_warnings": validation_warnings,
        "needs_review": needs_review,
        "corrections_applied": corrections_applied,
        "validation_metadata": validation_metadata,
        
        # PHASE 4: Image quality metrics
        "image_quality": image_quality if image_quality else None,
        
        # PHASE 4: Multi-page info
        "is_multipage": is_multipage,
        "page_count": page_count,
        "multiple_invoices_detected": multiple_invoices,
        "other_pages": other_pages if other_pages else None,
        
        # Quadruple Hybrid info
        "line_items": line_items,
        "model_outputs": model_outputs if model_outputs else None,
        "voting_details": voting_details if voting_details else None,
        "ocr_texts": invoice.extracted_data.get('_ocr_texts') if settings.STORE_OCR_TEXTS else None,
        "ocr_fused_fields": invoice.extracted_data.get('_ocr_fused_fields') if settings.ENABLE_OCR_FUSION else None,
    }
    
    return response
# ```

# ---

# ## ✅ SAVE AND TEST

# **Save the file, restart, and test with Invoice3.png!**

# You should see in the logs:
# ```
# [0/7] Checking image quality...
#    Quality metrics:
#    - Resolution: 1275x1650
#    - Sharpness: 245.67
#    ...

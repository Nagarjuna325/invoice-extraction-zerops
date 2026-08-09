# import sys

# # Read the upload.py file
# with open('app/api/v1/endpoints/upload.py', 'r') as f:
#     content = f.read()

# # Find and replace the get_invoice function
# old_return = '''    return {
#         "upload_id": invoice.upload_id,
#         "file_name": invoice.file_name,
#         "file_type": invoice.file_type,
#         "status": invoice.status,
#         "invoice_type": invoice.invoice_type,
#         "vendor_name": invoice.vendor_name,
#         "vendor_id": invoice.vendor_id,
#         "used_template": invoice.used_template,
#         "template_match_confidence": invoice.template_match_confidence,
#         "extracted_data": invoice.extracted_data,
#         "field_confidences": invoice.field_confidences,
#         "overall_confidence": float(invoice.overall_confidence) if invoice.overall_confidence else 0,
#         "processing_time_ms": invoice.processing_time_ms,
#         "ocr_engine": invoice.ocr_engine,
#         "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
#         "processed_at": invoice.processed_at.isoformat() if invoice.processed_at else None
#     }'''

# new_return = '''    # Check for validation warnings in extracted_data
#     validation_warnings = invoice.extracted_data.get('_needs_review', []) if invoice.extracted_data else []
    
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
#         "extracted_data": invoice.extracted_data,
#         "field_confidences": invoice.field_confidences,
#         "overall_confidence": float(invoice.overall_confidence) if invoice.overall_confidence else 0,
#         "processing_time_ms": invoice.processing_time_ms,
#         "ocr_engine": invoice.ocr_engine,
#         "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
#         "processed_at": invoice.processed_at.isoformat() if invoice.processed_at else None,
#         "validation_warnings": validation_warnings,
#         "needs_review": len(validation_warnings) > 0
#     }'''

# content = content.replace(old_return, new_return)

# with open('app/api/v1/endpoints/upload.py', 'w') as f:
#     f.write(content)

# print("✅ GET endpoint updated to show validation warnings!")




import sys

# Read the upload.py file with UTF-8 encoding
with open('app/api/v1/endpoints/upload.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the get_invoice function
old_return = '''    return {
        "upload_id": invoice.upload_id,
        "file_name": invoice.file_name,
        "file_type": invoice.file_type,
        "status": invoice.status,
        "invoice_type": invoice.invoice_type,
        "vendor_name": invoice.vendor_name,
        "vendor_id": invoice.vendor_id,
        "used_template": invoice.used_template,
        "template_match_confidence": invoice.template_match_confidence,
        "extracted_data": invoice.extracted_data,
        "field_confidences": invoice.field_confidences,
        "overall_confidence": float(invoice.overall_confidence) if invoice.overall_confidence else 0,
        "processing_time_ms": invoice.processing_time_ms,
        "ocr_engine": invoice.ocr_engine,
        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
        "processed_at": invoice.processed_at.isoformat() if invoice.processed_at else None
    }'''

new_return = '''    # Check for validation warnings in extracted_data
    validation_warnings = invoice.extracted_data.get('_needs_review', []) if invoice.extracted_data else []
    
    return {
        "upload_id": invoice.upload_id,
        "file_name": invoice.file_name,
        "file_type": invoice.file_type,
        "status": invoice.status,
        "invoice_type": invoice.invoice_type,
        "vendor_name": invoice.vendor_name,
        "vendor_id": invoice.vendor_id,
        "used_template": invoice.used_template,
        "template_match_confidence": invoice.template_match_confidence,
        "extracted_data": invoice.extracted_data,
        "field_confidences": invoice.field_confidences,
        "overall_confidence": float(invoice.overall_confidence) if invoice.overall_confidence else 0,
        "processing_time_ms": invoice.processing_time_ms,
        "ocr_engine": invoice.ocr_engine,
        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
        "processed_at": invoice.processed_at.isoformat() if invoice.processed_at else None,
        "validation_warnings": validation_warnings,
        "needs_review": len(validation_warnings) > 0
    }'''

if old_return in content:
    content = content.replace(old_return, new_return)
    
    with open('app/api/v1/endpoints/upload.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ GET endpoint updated to show validation warnings!")
else:
    print("❌ Could not find the return statement to replace")
    print("Manual edit needed - see instructions below")
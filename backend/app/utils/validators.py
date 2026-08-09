# from typing import Tuple
# from app.config import settings
# import logging

# logger = logging.getLogger(__name__)


# def validate_file_size(file_size: int) -> Tuple[bool, str]:
#     """
#     Validate file size
    
#     Returns:
#         (is_valid, error_message)
#     """
#     if file_size > settings.MAX_FILE_SIZE:
#         max_size_mb = settings.MAX_FILE_SIZE / (1024 * 1024)
#         return False, f"File size exceeds maximum allowed size of {max_size_mb}MB"
    
#     if file_size == 0:
#         return False, "File is empty"
    
#     return True, ""


# def validate_file_type(content_type: str, filename: str) -> Tuple[bool, str]:
#     """
#     Validate file type
    
#     Returns:
#         (is_valid, error_message)
#     """
#     # Check content type
#     if content_type not in settings.ALLOWED_FILE_TYPES:
#         return False, f"File type '{content_type}' not allowed. Allowed types: PDF, JPEG, PNG"
    
#     # Check file extension
#     allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
#     file_ext = filename.lower().split('.')[-1]
    
#     if f'.{file_ext}' not in allowed_extensions:
#         return False, f"File extension '.{file_ext}' not allowed"
    
#     return True, ""


# def validate_upload(file_size: int, content_type: str, filename: str) -> Tuple[bool, str]:
#     """
#     Validate complete upload
    
#     Returns:
#         (is_valid, error_message)
#     """
#     # Validate size
#     is_valid, error = validate_file_size(file_size)
#     if not is_valid:
#         return False, error
    
#     # Validate type
#     is_valid, error = validate_file_type(content_type, filename)
#     if not is_valid:
#         return False, error
    
#     logger.info(f"File validation passed: {filename}")
#     return True, ""






"""
File upload validators - UPDATED to support all document types
"""
from typing import Tuple

# Maximum file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes

# Allowed content types - EXPANDED
ALLOWED_CONTENT_TYPES = {
    # Images
    "image/jpeg",
    "image/jpg", 
    "image/png",
    "image/tiff",
    "image/bmp",
    
    # PDFs
    "application/pdf",
    
    # Excel
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "application/vnd.ms-excel",  # .xls
    
    # CSV
    "text/csv",
    "application/csv",
}

# Allowed extensions
ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".tiff", ".bmp",  # Images
    ".pdf",  # PDF
    ".xlsx", ".xls", ".xlsm",  # Excel
    ".csv"  # CSV
}


def validate_upload(
    file_size: int,
    content_type: str,
    filename: str
) -> Tuple[bool, str]:
    """
    Validate uploaded file
    
    Args:
        file_size: File size in bytes
        content_type: MIME type
        filename: Original filename
        
    Returns:
        (is_valid, error_message)
    """
    # Check file size
    if file_size > MAX_FILE_SIZE:
        return False, f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024:.0f}MB"
    
    if file_size == 0:
        return False, "File is empty"
    
    # Check content type
    if content_type not in ALLOWED_CONTENT_TYPES:
        return False, f"File type '{content_type}' not allowed. Allowed types: Images (PNG, JPG), PDF, Excel (XLSX, XLS), CSV"
    
    # Check extension
    import os
    file_ext = os.path.splitext(filename.lower())[1]
    
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"File extension '{file_ext}' not allowed"
    
    return True, ""
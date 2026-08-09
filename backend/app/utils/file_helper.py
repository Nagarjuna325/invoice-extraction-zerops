"""
File helper utilities
Normalizes long MIME types to short names
"""

def normalize_file_type(content_type: str) -> str:
    """
    Normalize long MIME types to short names that fit in database
    
    Args:
        content_type: Original MIME type
        
    Returns:
        Short normalized type (max 50 chars)
    """
    # Mapping of long MIME types to short names
    type_mapping = {
        # Images
        "image/jpeg": "image/jpeg",
        "image/jpg": "image/jpeg",
        "image/png": "image/png",
        "image/tiff": "image/tiff",
        "image/bmp": "image/bmp",
        
        # PDF
        "application/pdf": "application/pdf",
        
        # Excel - COMPRESSED
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "application/xlsx",
        "application/vnd.ms-excel": "application/xls",
        
        # CSV
        "text/csv": "text/csv",
        "application/csv": "text/csv",
    }
    
    # Return normalized type or original if not in mapping
    return type_mapping.get(content_type, content_type[:50])
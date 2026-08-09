import os
import uuid
import shutil
from datetime import datetime
from pathlib import Path
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class StorageService:
    """Handle file storage operations"""
    
    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self._ensure_upload_dir()
    
    def _ensure_upload_dir(self):
        """Create upload directory if it doesn't exist"""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Upload directory: {self.upload_dir}")
    
    def generate_upload_id(self) -> str:
        """Generate unique upload ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"upload_{timestamp}_{unique_id}"
    
    def save_file(self, file_content: bytes, filename: str, upload_id: str) -> str:
        """
        Save uploaded file to disk
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            upload_id: Unique upload identifier
            
        Returns:
            File path where file was saved
        """
        # Create subdirectory for this upload
        upload_subdir = self.upload_dir / upload_id
        upload_subdir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = upload_subdir / filename
        
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        logger.info(f"File saved: {file_path}")
        return str(file_path)
    
    def get_file_path(self, upload_id: str, filename: str) -> Path:
        """Get full path for a file"""
        return self.upload_dir / upload_id / filename
    
    def file_exists(self, upload_id: str, filename: str) -> bool:
        """Check if file exists"""
        return self.get_file_path(upload_id, filename).exists()
    
    def delete_file(self, upload_id: str):
        """Delete uploaded file and its directory"""
        upload_subdir = self.upload_dir / upload_id
        if upload_subdir.exists():
            shutil.rmtree(upload_subdir)
            logger.info(f"Deleted upload: {upload_id}")


# Create singleton instance
storage_service = StorageService()
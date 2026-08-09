from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Invoice Extraction System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/invoice_extraction"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # File Upload
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10485760  # 10MB in bytes
    ALLOWED_FILE_TYPES: List[str] = ["application/pdf", "image/jpeg", "image/png"]
    
    # OCR
    DEFAULT_OCR_ENGINE: str = "tesseract"
    TESSERACT_PATH: str = ""
    TESSERACT_LANG: str = "eng"
    USE_TESSERACT_OCR_VOTER: bool = False
    ENABLE_TEMPLATE_VOTER: bool = False
    TEMPLATE_VOTER_CONFIDENCE: float = 85.0
    AUTO_REFRESH_TEMPLATE_FROM_CORRECTIONS: bool = True
    STORE_OCR_TOKENS: bool = False
    STORE_OCR_TEXTS: bool = False
    AUTO_ANCHOR_CORRECTIONS: bool = False
    # If true, template bbox OCR values override model votes for those fields.
    USE_BBOX_OVERRIDE: bool = False

    # Advanced OCR pipeline (phased rollout)
    ENABLE_ADVANCED_OCR_PIPELINE: bool = False
    PRE_OCR_TARGET_DPI: int = 300
    PRE_OCR_SMALL_FONT_DPI: int = 350
    PRE_OCR_AUTO_DETECT_PAGE_SIZE: bool = True
    PRE_OCR_PAGE_SIZE_FALLBACK: str = "letter"
    PRE_OCR_ENABLE_DESKEW: bool = True
    PRE_OCR_GENERATE_VARIANTS: bool = False
    PRE_OCR_VARIANT_SUPERRES_SCALE: float = 2.0
    PRE_OCR_VARIANT_MAX_DIM: int = 5000
    ENABLE_OCR_MATRIX: bool = False
    OCR_MATRIX_ENABLE_PADDLE: bool = True
    OCR_MATRIX_ENABLE_TESSERACT: bool = True
    OCR_MATRIX_ENABLE_TROCR: bool = True
    OCR_MATRIX_PADDLE_LANG: str = "en"
    OCR_MATRIX_PADDLE_TABLE: bool = True
    ENABLE_OCR_FUSION: bool = False
    OCR_FUSION_FORCE_FIELDS: str = "invoice_number,po_number,invoice_date"
    OCR_FUSION_TOTAL_FALLBACK: bool = False
    OCR_FUSION_TOTAL_REGION_Y: float = 0.4
    OCR_FUSION_TOTAL_REGION_X: float = 0.6
    OCR_FUSION_WEIGHT_PADDLE: float = 1.0
    OCR_FUSION_WEIGHT_TESSERACT: float = 0.9
    OCR_FUSION_WEIGHT_TROCR: float = 0.7
    ENABLE_LABEL_ANCHORED_DATES: bool = False
    LABEL_DATE_PREFER_ANCHORED: bool = True
    LABEL_DATE_MAX_Y_GAP_PX: int = 24
    LABEL_DATE_MAX_X_DIST_PX: int = 420
    LABEL_DATE_MIN_CONF: float = 0.6
    ENABLE_LABEL_ANCHORED_DATES_TEXT: bool = False
    LABEL_DATE_TEXT_LOOKAHEAD_LINES: int = 4
    LABEL_DATE_TEXT_SCORE: float = 0.45
    LABEL_MATCH_MODE: str = "rule"
    ENABLE_LABEL_SEMANTIC_MATCH: bool = False
    LABEL_SEMANTIC_MODEL: str = "all-MiniLM-L6-v2"
    LABEL_MATCH_MIN_SCORE: float = 0.65
    LABEL_MATCH_DEBUG: bool = False
    LABEL_EMBED_PROVIDER: str = "local"
    LABEL_EMBED_MODEL: str = "all-MiniLM-L6-v2"
    LABEL_EMBED_API_KEY: str = ""
    LABEL_EMBED_API_URL: str = "https://api.anthropic.com/v1/embeddings"
    LABEL_EMBED_API_VERSION: str = "2023-06-01"
    LABEL_EMBED_TIMEOUT_S: float = 10.0
    LABEL_EMBED_CACHE_SIZE: int = 256

    # Footer total extraction (targeted OCR)
    ENABLE_FOOTER_TOTAL_EXTRACT: bool = False
    FOOTER_REGION_Y_MIN: float = 0.7
    FOOTER_REGION_X_MIN: float = 0.55
    FOOTER_TOTAL_REQUIRE_DECIMAL: bool = True
    FOOTER_TOTAL_SUPERRES_SCALE: float = 2.0
    FOOTER_TOTAL_WHITELIST: str = "0123456789.,$"

    # Total selection preferences
    TOTAL_PREFER_FOOTER: bool = True
    TOTAL_FOOTER_MIN_CONF: float = 60.0
    STORE_TOTAL_DEBUG: bool = False

    # Line item extraction (image tables)
    ENABLE_LINE_ITEM_PARSER: bool = True
    ENABLE_AMOUNT_COLUMN_REOCR: bool = True
    ENABLE_SUPERRES_CROPS: bool = True
    LINEITEM_REQUIRE_HEADER: bool = True
    LINEITEM_MIN_VALID_ROWS: int = 2
    LINEITEM_REQUIRE_DECIMAL: bool = True
    LINEITEM_ALLOW_NO_DECIMAL_WITH_CURRENCY: bool = True
    LINEITEM_SKIP_NONE_AMOUNT: bool = True
    LINEITEM_MERGE_MULTILINE: bool = True
    LINEITEM_MERGE_MAX_GAP_PX: int = 12
    LINEITEM_MERGE_REQUIRE_AMOUNT: bool = True
    LINEITEM_REOCR_MIN_CONF: float = 0.6
    LINEITEM_SUPERRES_MIN_CONF: float = 0.5
    LINEITEM_SUPERRES_SCALE: float = 2.0
    LINEITEM_SUPERRES_METHOD: str = "opencv"
    STORE_LINEITEM_DEBUG: bool = False
    
    # Processing
    PROCESSING_TIMEOUT: int = 300  # 5 minutes
    CONFIDENCE_THRESHOLD: int = 85
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/app.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()

# Create upload directory if it doesn't exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)

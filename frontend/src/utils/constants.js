// File Upload Constants
export const FILE_UPLOAD = {
  MAX_SIZE: 10 * 1024 * 1024, // 10MB in bytes
  ALLOWED_TYPES: ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png'],
  ALLOWED_EXTENSIONS: ['.pdf', '.jpg', '.jpeg', '.png'],
};

// Invoice Status Constants
export const INVOICE_STATUS = {
  UPLOADED: 'UPLOADED',
  PROCESSING: 'PROCESSING',
  EXTRACTED: 'EXTRACTED',
  REVIEWED: 'REVIEWED',
  APPROVED: 'APPROVED',
  REJECTED: 'REJECTED',
  FAILED: 'FAILED',
};

// Status Labels
export const STATUS_LABELS = {
  UPLOADED: 'Uploaded',
  PROCESSING: 'Processing',
  EXTRACTED: 'Extracted',
  REVIEWED: 'Reviewed',
  APPROVED: 'Approved',
  REJECTED: 'Rejected',
  FAILED: 'Failed',
};

// Status Colors (for chips/badges)
export const STATUS_COLORS = {
  UPLOADED: 'info',
  PROCESSING: 'warning',
  EXTRACTED: 'success',
  REVIEWED: 'success',
  APPROVED: 'success',
  REJECTED: 'error',
  FAILED: 'error',
};

// Confidence Levels
export const CONFIDENCE_LEVELS = {
  HIGH: { min: 95, label: 'High', color: 'success' },
  MEDIUM: { min: 85, label: 'Medium', color: 'warning' },
  LOW: { min: 0, label: 'Low', color: 'error' },
};

// OCR Engines
export const OCR_ENGINES = {
  TESSERACT: 'tesseract',
  EASYOCR: 'easyocr',
};

// OCR Engine Labels
export const OCR_ENGINE_LABELS = {
  tesseract: 'Tesseract OCR',
  easyocr: 'EasyOCR',
};

// Processing Stages
export const PROCESSING_STAGES = {
  UPLOAD: 'UPLOAD',
  OCR: 'OCR',
  EXTRACTION: 'EXTRACTION',
  VALIDATION: 'VALIDATION',
  COMPLETE: 'COMPLETE',
};

// Date Formats
export const DATE_FORMATS = {
  DISPLAY: 'MMM dd, yyyy',
  DISPLAY_WITH_TIME: 'MMM dd, yyyy HH:mm',
  API: 'yyyy-MM-dd',
  ISO: "yyyy-MM-dd'T'HH:mm:ss'Z'",
};

// Pagination
export const PAGINATION = {
  DEFAULT_PAGE: 1,
  DEFAULT_LIMIT: 20,
  PAGE_SIZE_OPTIONS: [10, 20, 50, 100],
};

// Notification Types
export const NOTIFICATION_TYPES = {
  SUCCESS: 'success',
  ERROR: 'error',
  WARNING: 'warning',
  INFO: 'info',
};

// Local Storage Keys
export const STORAGE_KEYS = {
  THEME_MODE: 'theme_mode',
  SIDEBAR_STATE: 'sidebar_state',
  RECENT_UPLOADS: 'recent_uploads',
};

// API Response Messages
export const API_MESSAGES = {
  UPLOAD_SUCCESS: 'Invoice uploaded successfully',
  UPLOAD_ERROR: 'Failed to upload invoice',
  PROCESSING_COMPLETE: 'Processing completed',
  PROCESSING_ERROR: 'Processing failed',
  UPDATE_SUCCESS: 'Invoice updated successfully',
  UPDATE_ERROR: 'Failed to update invoice',
  DELETE_SUCCESS: 'Invoice deleted successfully',
  DELETE_ERROR: 'Failed to delete invoice',
  NETWORK_ERROR: 'Network error. Please check your connection.',
};

// Field Names (common invoice fields)
export const INVOICE_FIELDS = {
  VENDOR_NAME: 'vendor_name',
  INVOICE_NUMBER: 'invoice_number',
  INVOICE_DATE: 'invoice_date',
  DUE_DATE: 'due_date',
  TOTAL_AMOUNT: 'total_amount',
  SUBTOTAL: 'subtotal',
  TAX_AMOUNT: 'tax_amount',
  CURRENCY: 'currency',
  PO_NUMBER: 'po_number',
  LINE_ITEMS: 'line_items',
};

// Field Labels
export const FIELD_LABELS = {
  vendor_name: 'Vendor Name',
  invoice_number: 'Invoice Number',
  invoice_date: 'Invoice Date',
  due_date: 'Due Date',
  total_amount: 'Total Amount',
  subtotal: 'Subtotal',
  tax_amount: 'Tax Amount',
  currency: 'Currency',
  po_number: 'PO Number',
  line_items: 'Line Items',
};

// Error Messages
export const ERROR_MESSAGES = {
  FILE_TOO_LARGE: `File size must be less than ${FILE_UPLOAD.MAX_SIZE / 1024 / 1024}MB`,
  INVALID_FILE_TYPE: 'Invalid file type. Please upload PDF, JPG, or PNG files only.',
  NO_FILE_SELECTED: 'Please select a file to upload',
  UPLOAD_FAILED: 'Upload failed. Please try again.',
  PROCESSING_TIMEOUT: 'Processing is taking longer than expected. Please check back later.',
  NETWORK_ERROR: 'Network error. Please check your internet connection.',
  GENERIC_ERROR: 'An error occurred. Please try again.',
};

export default {
  FILE_UPLOAD,
  INVOICE_STATUS,
  STATUS_LABELS,
  STATUS_COLORS,
  CONFIDENCE_LEVELS,
  OCR_ENGINES,
  OCR_ENGINE_LABELS,
  PROCESSING_STAGES,
  DATE_FORMATS,
  PAGINATION,
  NOTIFICATION_TYPES,
  STORAGE_KEYS,
  API_MESSAGES,
  INVOICE_FIELDS,
  FIELD_LABELS,
  ERROR_MESSAGES,
};
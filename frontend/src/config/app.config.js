// // Application configuration
// const config = {
//   // API Configuration
//   api: {
//     baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
//     timeout: 30000, // 30 seconds
//   },

//   // Application Info
//   app: {
//     name: import.meta.env.VITE_APP_NAME || 'Invoice Extraction System',
//     version: '1.0.0',
//   },

//   // File Upload Configuration
//   upload: {
//     maxFileSize: parseInt(import.meta.env.VITE_MAX_FILE_SIZE) || 10485760, // 10MB in bytes
//     allowedFileTypes: [
//       'application/pdf',
//       'image/jpeg',
//       'image/jpg',
//       'image/png',
//     ],
//     allowedExtensions: ['.pdf', '.jpg', '.jpeg', '.png'],
//   },

//   // OCR Configuration
//   ocr: {
//     engines: [
//       {
//         id: 'tesseract',
//         name: 'Tesseract OCR',
//         description: 'Fast and reliable for clear documents',
//         recommended: true,
//       },
//       {
//         id: 'easyocr',
//         name: 'EasyOCR',
//         description: 'Better for handwritten text and complex layouts',
//         recommended: false,
//       },
//     ],
//     defaultEngine: 'tesseract',
//   },

//   // Confidence Thresholds
//   confidence: {
//     high: 95, // Green - Auto-approve
//     medium: 85, // Yellow - Needs review
//     low: 0, // Red - Likely error
//   },

//   // Polling Configuration (for checking processing status)
//   polling: {
//     interval: 2000, // 2 seconds
//     maxAttempts: 60, // Max 2 minutes (60 * 2 seconds)
//   },

//   // Pagination
//   pagination: {
//     defaultPageSize: 20,
//     pageSizeOptions: [10, 20, 50, 100],
//   },

//   // Date Format
//   dateFormat: 'MMM dd, yyyy',
//   dateTimeFormat: 'MMM dd, yyyy HH:mm',
// };

// export default config;



// Application configuration
const config = {
  // API Configuration
  api: {
    baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
    timeout: 120000, // 120 seconds (for ML processing)
  },

  // Application Info
  app: {
    name: import.meta.env.VITE_APP_NAME || 'Invoice Extraction System',
    version: '1.0.0',
  },

  // File Upload Configuration
  upload: {
    maxFileSize: parseInt(import.meta.env.VITE_MAX_FILE_SIZE) || 10485760, // 10MB in bytes
    allowedFileTypes: [
      'application/pdf',
      'image/jpeg',
      'image/jpg',
      'image/png',
      'image/tiff',
      'image/bmp',
      // NEW: Excel & CSV support
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // .xlsx
      'application/vnd.ms-excel', // .xls
      'text/csv',
      'application/csv',
    ],
    allowedExtensions: [
      '.pdf', 
      '.jpg', 
      '.jpeg', 
      '.png',
      '.tiff',
      '.bmp',
      // NEW: Excel & CSV
      '.xlsx',
      '.xls',
      '.xlsm',
      '.csv'
    ],
  },

  // OCR Configuration - UPDATED
  ocr: {
    engines: [
      {
        id: 'triple_hybrid',
        name: 'Triple Hybrid ML',
        description: 'Best accuracy: Impira + LayoutLM + Donut (90%+)',
        recommended: true,
      },
      {
        id: 'tesseract',
        name: 'Tesseract OCR',
        description: 'Fast and reliable for clear documents',
        recommended: false,
      },
    ],
    defaultEngine: 'triple_hybrid', // CHANGED from 'tesseract'
  },

  // Confidence Thresholds
  confidence: {
    high: 95, // Green - Auto-approve
    medium: 85, // Yellow - Needs review
    low: 0, // Red - Likely error
  },

  // Polling Configuration (for checking processing status)
  polling: {
    interval: 3000, // 3 seconds (ML takes longer)
    maxAttempts: 40, // Max 2 minutes (40 * 3 seconds)
  },

  // Pagination
  pagination: {
    defaultPageSize: 20,
    pageSizeOptions: [10, 20, 50, 100],
  },

  // Date Format
  dateFormat: 'MMM dd, yyyy',
  dateTimeFormat: 'MMM dd, yyyy HH:mm',
};

export default config;
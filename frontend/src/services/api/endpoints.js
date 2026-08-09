// // API Endpoints
// export const ENDPOINTS = {
//   // Invoice Upload
//   UPLOAD_INVOICE: '/invoices/upload',
  
//   // Invoice Status
//   UPLOAD_STATUS: '/invoices',
//   GET_INVOICE_BY_ID: '/invoices',
  
//   // Invoice List
//   GET_ALL_INVOICES: '/invoices',
  
//   // Invoice Update
//   UPDATE_INVOICE: '/invoices',
//   DELETE_INVOICE: '/invoices',
  
//   // Templates
//   GET_TEMPLATES: '/templates',
  
//   // Health Check
//   HEALTH_CHECK: '/health',
// };

// // Helper function to build URL with ID
// export const buildUrl = (endpoint, id) => {
//   return `${endpoint}/${id}`;
// };

// // Helper function to build URL with query params
// export const buildUrlWithParams = (endpoint, params = {}) => {
//   const queryString = Object.keys(params)
//     .filter((key) => params[key] !== undefined && params[key] !== null)
//     .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`)
//     .join('&');

//   return queryString ? `${endpoint}?${queryString}` : endpoint;
// };

// export default ENDPOINTS;




// API Endpoints
export const ENDPOINTS = {
  // Invoice Upload
  UPLOAD_INVOICE: '/invoices/upload',
  
  // Invoice Status
  UPLOAD_STATUS: '/invoices',
  GET_INVOICE_BY_ID: '/invoices',
  
  // Invoice List
  GET_ALL_INVOICES: '/invoices',
  
  // Invoice Update
  UPDATE_INVOICE: '/invoices',
  DELETE_INVOICE: '/invoices',
  
  // NEW: Correction endpoint for template learning
  CORRECT_INVOICE: '/invoices/correct',
  
  // Templates
  GET_TEMPLATES: '/templates',
  
  // Health Check
  HEALTH_CHECK: '/health',
};

// Helper function to build URL with ID
export const buildUrl = (endpoint, id) => {
  return `${endpoint}/${id}`;
};

// Helper function to build URL with query params
export const buildUrlWithParams = (endpoint, params = {}) => {
  const queryString = Object.keys(params)
    .filter((key) => params[key] !== undefined && params[key] !== null)
    .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`)
    .join('&');
  
  return queryString ? `${endpoint}?${queryString}` : endpoint;
};

export default ENDPOINTS;
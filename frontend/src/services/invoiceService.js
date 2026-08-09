// import apiClient from './api/axios.config';
// import { ENDPOINTS, buildUrl, buildUrlWithParams } from './api/endpoints';

// /**
//  * Invoice Service
//  * Handles all invoice data related API calls
//  */
// const invoiceService = {
//   /**
//    * Get all invoices with optional filters
//    * @param {Object} filters - Filter parameters
//    * @returns {Promise} List of invoices
//    */
//   async getAllInvoices(filters = {}) {
//     const params = {
//       page: filters.page || 1,
//       limit: filters.limit || 20,
//       status: filters.status,
//       vendor_name: filters.vendor_name,
//       date_from: filters.date_from,
//       date_to: filters.date_to,
//       min_confidence: filters.min_confidence,
//     };

//     const url = buildUrlWithParams(ENDPOINTS.GET_ALL_INVOICES, params);
//     const response = await apiClient.get(url);
//     return response.data;
//   },

//   /**
//    * Get invoice by ID or upload_id
//    * @param {string} id - Invoice ID or upload_id
//    * @returns {Promise} Invoice details
//    */
//   async getInvoiceById(id) {
//     const response = await apiClient.get(buildUrl(ENDPOINTS.GET_INVOICE_BY_ID, id));
//     return response.data;
//   },

//   /**
//    * Update invoice data
//    * @param {string} id - Invoice ID or upload_id
//    * @param {Object} data - Updated invoice data
//    * @returns {Promise} Updated invoice
//    */
//   async updateInvoice(id, data) {
//     const response = await apiClient.patch(
//       buildUrl(ENDPOINTS.UPDATE_INVOICE, id),
//       data
//     );
//     return response.data;
//   },

//   /**
//    * Delete invoice
//    * @param {string} id - Invoice ID or upload_id
//    * @returns {Promise} Deletion confirmation
//    */
//   async deleteInvoice(id) {
//     const response = await apiClient.delete(
//       buildUrl(ENDPOINTS.DELETE_INVOICE, id)
//     );
//     return response.data;
//   },

//   /**
//    * Get invoice templates/schemas
//    * @returns {Promise} List of templates
//    */
//   async getTemplates() {
//     const response = await apiClient.get(ENDPOINTS.GET_TEMPLATES);
//     return response.data;
//   },

//   /**
//    * Approve invoice
//    * @param {string} id - Invoice ID or upload_id
//    * @returns {Promise} Updated invoice status
//    */
//   async approveInvoice(id) {
//     return this.updateInvoice(id, { status: 'APPROVED' });
//   },

//   /**
//    * Reject invoice
//    * @param {string} id - Invoice ID or upload_id
//    * @param {string} reason - Rejection reason
//    * @returns {Promise} Updated invoice status
//    */
//   async rejectInvoice(id, reason = '') {
//     return this.updateInvoice(id, {
//       status: 'REJECTED',
//       rejection_reason: reason,
//     });
//   },

//   /**
//    * Get invoice statistics
//    * @returns {Promise} Invoice statistics
//    */
//   async getInvoiceStats() {
//     // This would be a custom endpoint in your backend
//     // For now, we'll calculate from the list
//     const allInvoices = await this.getAllInvoices({ limit: 1000 });

//     const stats = {
//       total: allInvoices.total || 0,
//       processed: 0,
//       pending: 0,
//       failed: 0,
//       avgConfidence: 0,
//     };

//     if (allInvoices.invoices && allInvoices.invoices.length > 0) {
//       let totalConfidence = 0;
//       allInvoices.invoices.forEach((invoice) => {
//         if (invoice.status === 'EXTRACTED' || invoice.status === 'APPROVED') {
//           stats.processed++;
//         } else if (invoice.status === 'PROCESSING' || invoice.status === 'UPLOADED') {
//           stats.pending++;
//         } else if (invoice.status === 'FAILED') {
//           stats.failed++;
//         }

//         if (invoice.overall_confidence) {
//           totalConfidence += invoice.overall_confidence;
//         }
//       });

//       stats.avgConfidence = (totalConfidence / allInvoices.invoices.length).toFixed(2);
//     }

//     return stats;
//   },
// };

// export default invoiceService;


import apiClient from './api/axios.config';
import { ENDPOINTS, buildUrl, buildUrlWithParams } from './api/endpoints';

/**
 * Invoice Service
 * Handles all invoice data related API calls
 */
const invoiceService = {
  /**
   * Get all invoices with optional filters
   * @param {Object} filters - Filter parameters
   * @returns {Promise} List of invoices
   */
  async getAllInvoices(filters = {}) {
    const params = {
      page: filters.page || 1,
      limit: filters.limit || 20,
      status: filters.status,
      vendor_name: filters.vendor_name,
      date_from: filters.date_from,
      date_to: filters.date_to,
      min_confidence: filters.min_confidence,
    };

    const url = buildUrlWithParams(ENDPOINTS.GET_ALL_INVOICES, params);
    const response = await apiClient.get(url);
    return response.data;
  },

  /**
   * Get invoice by ID or upload_id
   * @param {string} id - Invoice ID or upload_id
   * @returns {Promise} Invoice details
   */
  async getInvoiceById(id) {
    const response = await apiClient.get(buildUrl(ENDPOINTS.GET_INVOICE_BY_ID, id));
    return response.data;
  },

  /**
   * Update invoice data
   * @param {string} id - Invoice ID or upload_id
   * @param {Object} data - Updated invoice data
   * @returns {Promise} Updated invoice
   */
  async updateInvoice(id, data) {
    const response = await apiClient.patch(
      buildUrl(ENDPOINTS.UPDATE_INVOICE, id),
      data
    );
    return response.data;
  },

  /**
   * Submit corrections for invoice (Template Learning)
   * NEW: This helps the system learn and improve accuracy
   * @param {string} uploadId - Upload ID
   * @param {Object} correctedData - Corrected field values
   * @returns {Promise} Correction result with template info
   */
  async submitCorrection(uploadId, correctedData) {
    const response = await apiClient.post(
      ENDPOINTS.CORRECT_INVOICE,
      {
        upload_id: uploadId,
        corrected_data: correctedData,
      }
    );
    return response.data;
  },

  /**
   * Delete invoice
   * @param {string} id - Invoice ID or upload_id
   * @returns {Promise} Deletion confirmation
   */
  async deleteInvoice(id) {
    const response = await apiClient.delete(
      buildUrl(ENDPOINTS.DELETE_INVOICE, id)
    );
    return response.data;
  },

  /**
   * Get invoice templates/schemas
   * @returns {Promise} List of templates
   */
  async getTemplates() {
    const response = await apiClient.get(ENDPOINTS.GET_TEMPLATES);
    return response.data;
  },

  /**
   * Approve invoice
   * @param {string} id - Invoice ID or upload_id
   * @returns {Promise} Updated invoice status
   */
  async approveInvoice(id) {
    return this.updateInvoice(id, { status: 'APPROVED' });
  },

  /**
   * Reject invoice
   * @param {string} id - Invoice ID or upload_id
   * @param {string} reason - Rejection reason
   * @returns {Promise} Updated invoice status
   */
  async rejectInvoice(id, reason = '') {
    return this.updateInvoice(id, {
      status: 'REJECTED',
      rejection_reason: reason,
    });
  },

  /**
   * Get invoice statistics
   * @returns {Promise} Invoice statistics
   */
  async getInvoiceStats() {
    // This would be a custom endpoint in your backend
    // For now, we'll calculate from the list
    const allInvoices = await this.getAllInvoices({ limit: 1000 });

    const stats = {
      total: allInvoices.total || 0,
      processed: 0,
      pending: 0,
      failed: 0,
      avgConfidence: 0,
    };

    if (allInvoices.invoices && allInvoices.invoices.length > 0) {
      let totalConfidence = 0;
      allInvoices.invoices.forEach((invoice) => {
        if (invoice.status === 'EXTRACTED' || invoice.status === 'APPROVED') {
          stats.processed++;
        } else if (invoice.status === 'PROCESSING' || invoice.status === 'UPLOADED') {
          stats.pending++;
        } else if (invoice.status === 'FAILED') {
          stats.failed++;
        }

        if (invoice.overall_confidence) {
          totalConfidence += invoice.overall_confidence;
        }
      });

      stats.avgConfidence = (totalConfidence / allInvoices.invoices.length).toFixed(2);
    }

    return stats;
  },
};

export default invoiceService;
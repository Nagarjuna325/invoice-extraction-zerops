import apiClient from './api/axios.config';
import { ENDPOINTS, buildUrl } from './api/endpoints';

/**
 * Upload Service
 * Handles all invoice upload related API calls
 */
const uploadService = {
  /**
   * Upload invoice file
   * @param {File} file - The invoice file to upload
   * @param {string} ocrEngine - OCR engine to use ('tesseract' or 'easyocr')
   * @param {function} onUploadProgress - Callback for upload progress
   * @returns {Promise} Upload response with upload_id
   */
  async uploadInvoice(file, ocrEngine = 'tesseract', onUploadProgress = null) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('ocr_engine', ocrEngine);

    const config = {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    };

    // Add progress callback if provided
    if (onUploadProgress) {
      config.onUploadProgress = (progressEvent) => {
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        );
        onUploadProgress(percentCompleted);
      };
    }

    const response = await apiClient.post(
      ENDPOINTS.UPLOAD_INVOICE,
      formData,
      config
    );

    return response.data;
  },

  /**
   * Get upload/processing status
   * @param {string} uploadId - The upload ID
   * @returns {Promise} Status information
   */
  async getUploadStatus(uploadId) {
    const response = await apiClient.get(
      `${ENDPOINTS.UPLOAD_STATUS}/${uploadId}/status`
    );
    return response.data;
  },

  /**
   * Poll for processing completion
   * @param {string} uploadId - The upload ID
   * @param {function} onStatusUpdate - Callback for status updates
   * @param {number} interval - Polling interval in ms (default: 2000)
   * @param {number} maxAttempts - Max polling attempts (default: 60)
   * @returns {Promise} Final status
   */
  async pollProcessingStatus(
    uploadId,
    onStatusUpdate = null,
    interval = 2000,
    maxAttempts = 60
  ) {
    let attempts = 0;

    return new Promise((resolve, reject) => {
      const checkStatus = async () => {
        try {
          const status = await this.getUploadStatus(uploadId);

          // Call status update callback
          if (onStatusUpdate) {
            onStatusUpdate(status);
          }

          // Check if processing is complete
          if (
            status.status === 'EXTRACTED' ||
            status.status === 'FAILED' ||
            status.status === 'COMPLETED'
          ) {
            resolve(status);
            return;
          }

          // Check max attempts
          attempts++;
          if (attempts >= maxAttempts) {
            reject(new Error('Polling timeout: Maximum attempts reached'));
            return;
          }

          // Continue polling
          setTimeout(checkStatus, interval);
        } catch (error) {
          reject(error);
        }
      };

      checkStatus();
    });
  },
};

export default uploadService;
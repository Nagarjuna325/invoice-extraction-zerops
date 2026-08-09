import { FILE_UPLOAD, ERROR_MESSAGES } from './constants';

/**
 * Validate file size
 * @param {File} file - File to validate
 * @returns {Object} { isValid: boolean, error: string }
 */
export const validateFileSize = (file) => {
  if (!file) {
    return { isValid: false, error: ERROR_MESSAGES.NO_FILE_SELECTED };
  }

  if (file.size > FILE_UPLOAD.MAX_SIZE) {
    return { isValid: false, error: ERROR_MESSAGES.FILE_TOO_LARGE };
  }

  return { isValid: true, error: null };
};

/**
 * Validate file type
 * @param {File} file - File to validate
 * @returns {Object} { isValid: boolean, error: string }
 */
export const validateFileType = (file) => {
  if (!file) {
    return { isValid: false, error: ERROR_MESSAGES.NO_FILE_SELECTED };
  }

  const fileType = file.type;
  const fileName = file.name;
  const fileExtension = fileName.substring(fileName.lastIndexOf('.')).toLowerCase();

  const isValidType = FILE_UPLOAD.ALLOWED_TYPES.includes(fileType);
  const isValidExtension = FILE_UPLOAD.ALLOWED_EXTENSIONS.includes(fileExtension);

  if (!isValidType && !isValidExtension) {
    return { isValid: false, error: ERROR_MESSAGES.INVALID_FILE_TYPE };
  }

  return { isValid: true, error: null };
};

/**
 * Validate file (both size and type)
 * @param {File} file - File to validate
 * @returns {Object} { isValid: boolean, error: string }
 */
export const validateFile = (file) => {
  // Check if file exists
  if (!file) {
    return { isValid: false, error: ERROR_MESSAGES.NO_FILE_SELECTED };
  }

  // Validate size
  const sizeValidation = validateFileSize(file);
  if (!sizeValidation.isValid) {
    return sizeValidation;
  }

  // Validate type
  const typeValidation = validateFileType(file);
  if (!typeValidation.isValid) {
    return typeValidation;
  }

  return { isValid: true, error: null };
};

/**
 * Validate email format
 * @param {string} email - Email to validate
 * @returns {boolean}
 */
export const validateEmail = (email) => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

/**
 * Validate invoice number format
 * @param {string} invoiceNumber - Invoice number to validate
 * @returns {boolean}
 */
export const validateInvoiceNumber = (invoiceNumber) => {
  if (!invoiceNumber || invoiceNumber.trim() === '') {
    return false;
  }
  // Basic validation - at least 3 characters
  return invoiceNumber.trim().length >= 3;
};

/**
 * Validate amount (positive number)
 * @param {number|string} amount - Amount to validate
 * @returns {boolean}
 */
export const validateAmount = (amount) => {
  const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount;
  return !isNaN(numAmount) && numAmount >= 0;
};

/**
 * Validate date (not in future)
 * @param {Date|string} date - Date to validate
 * @returns {boolean}
 */
export const validateDate = (date) => {
  if (!date) return false;
  const dateObj = new Date(date);
  const today = new Date();
  return dateObj <= today && !isNaN(dateObj.getTime());
};

/**
 * Validate confidence score (0-100)
 * @param {number} confidence - Confidence score to validate
 * @returns {boolean}
 */
export const validateConfidence = (confidence) => {
  return typeof confidence === 'number' && confidence >= 0 && confidence <= 100;
};

/**
 * Validate required fields
 * @param {Object} data - Data object to validate
 * @param {Array} requiredFields - Array of required field names
 * @returns {Object} { isValid: boolean, missingFields: Array }
 */
export const validateRequiredFields = (data, requiredFields) => {
  const missingFields = requiredFields.filter((field) => {
    const value = data[field];
    return value === undefined || value === null || value === '';
  });

  return {
    isValid: missingFields.length === 0,
    missingFields,
  };
};

export default {
  validateFileSize,
  validateFileType,
  validateFile,
  validateEmail,
  validateInvoiceNumber,
  validateAmount,
  validateDate,
  validateConfidence,
  validateRequiredFields,
};
import { format, parseISO } from 'date-fns';
import { DATE_FORMATS, CONFIDENCE_LEVELS } from './constants';

/**
 * Format file size to human readable format
 * @param {number} bytes - File size in bytes
 * @returns {string} Formatted file size
 */
export const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
};

/**
 * Format currency amount
 * @param {number} amount - Amount to format
 * @param {string} currency - Currency code (default: 'USD')
 * @returns {string} Formatted currency
 */
export const formatCurrency = (amount, currency = 'USD') => {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return '-';
  }

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
};

/**
 * Format date to display format
 * @param {string|Date} date - Date to format
 * @param {string} formatStr - Format string (optional)
 * @returns {string} Formatted date
 */
export const formatDate = (date, formatStr = DATE_FORMATS.DISPLAY) => {
  if (!date) return '-';

  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    return format(dateObj, formatStr);
  } catch (error) {
    console.error('Error formatting date:', error);
    return '-';
  }
};

/**
 * Format date with time
 * @param {string|Date} date - Date to format
 * @returns {string} Formatted date with time
 */
export const formatDateTime = (date) => {
  return formatDate(date, DATE_FORMATS.DISPLAY_WITH_TIME);
};

/**
 * Format confidence score
 * @param {number} confidence - Confidence score (0-100)
 * @returns {string} Formatted confidence with %
 */
export const formatConfidence = (confidence) => {
  if (confidence === null || confidence === undefined || isNaN(confidence)) {
    return '-';
  }

  return `${Math.round(confidence)}%`;
};

/**
 * Get confidence level
 * @param {number} confidence - Confidence score (0-100)
 * @returns {Object} Confidence level object { label, color }
 */
export const getConfidenceLevel = (confidence) => {
  if (confidence >= CONFIDENCE_LEVELS.HIGH.min) {
    return CONFIDENCE_LEVELS.HIGH;
  } else if (confidence >= CONFIDENCE_LEVELS.MEDIUM.min) {
    return CONFIDENCE_LEVELS.MEDIUM;
  } else {
    return CONFIDENCE_LEVELS.LOW;
  }
};

/**
 * Format invoice number
 * @param {string} invoiceNumber - Invoice number
 * @returns {string} Formatted invoice number
 */
export const formatInvoiceNumber = (invoiceNumber) => {
  if (!invoiceNumber) return '-';
  return invoiceNumber.toUpperCase();
};

/**
 * Format phone number
 * @param {string} phone - Phone number
 * @returns {string} Formatted phone number
 */
export const formatPhoneNumber = (phone) => {
  if (!phone) return '-';
  
  // Remove all non-numeric characters
  const cleaned = phone.replace(/\D/g, '');
  
  // Format based on length
  if (cleaned.length === 10) {
    return `(${cleaned.slice(0, 3)}) ${cleaned.slice(3, 6)}-${cleaned.slice(6)}`;
  } else if (cleaned.length === 11) {
    return `+${cleaned.slice(0, 1)} (${cleaned.slice(1, 4)}) ${cleaned.slice(4, 7)}-${cleaned.slice(7)}`;
  }
  
  return phone;
};

/**
 * Format percentage
 * @param {number} value - Value to format
 * @param {number} decimals - Number of decimal places (default: 0)
 * @returns {string} Formatted percentage
 */
export const formatPercentage = (value, decimals = 0) => {
  if (value === null || value === undefined || isNaN(value)) {
    return '-';
  }

  return `${value.toFixed(decimals)}%`;
};

/**
 * Truncate text
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length
 * @returns {string} Truncated text
 */
export const truncateText = (text, maxLength = 50) => {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return `${text.substring(0, maxLength)}...`;
};

/**
 * Format upload ID (for display)
 * @param {string} uploadId - Upload ID
 * @returns {string} Formatted upload ID
 */
export const formatUploadId = (uploadId) => {
  if (!uploadId) return '-';
  // Show first 8 and last 4 characters
  if (uploadId.length > 16) {
    return `${uploadId.substring(0, 8)}...${uploadId.substring(uploadId.length - 4)}`;
  }
  return uploadId;
};

/**
 * Format processing time
 * @param {number} milliseconds - Processing time in milliseconds
 * @returns {string} Formatted time
 */
export const formatProcessingTime = (milliseconds) => {
  if (!milliseconds || milliseconds === 0) return '-';

  if (milliseconds < 1000) {
    return `${milliseconds}ms`;
  } else if (milliseconds < 60000) {
    return `${(milliseconds / 1000).toFixed(1)}s`;
  } else {
    const minutes = Math.floor(milliseconds / 60000);
    const seconds = ((milliseconds % 60000) / 1000).toFixed(0);
    return `${minutes}m ${seconds}s`;
  }
};

/**
 * Capitalize first letter
 * @param {string} text - Text to capitalize
 * @returns {string} Capitalized text
 */
export const capitalizeFirst = (text) => {
  if (!text) return '';
  return text.charAt(0).toUpperCase() + text.slice(1).toLowerCase();
};

/**
 * Format status for display
 * @param {string} status - Status string
 * @returns {string} Formatted status
 */
export const formatStatus = (status) => {
  if (!status) return '-';
  // Convert UPPERCASE_WITH_UNDERSCORES to Title Case
  return status
    .split('_')
    .map((word) => capitalizeFirst(word))
    .join(' ');
};

export default {
  formatFileSize,
  formatCurrency,
  formatDate,
  formatDateTime,
  formatConfidence,
  getConfidenceLevel,
  formatInvoiceNumber,
  formatPhoneNumber,
  formatPercentage,
  truncateText,
  formatUploadId,
  formatProcessingTime,
  capitalizeFirst,
  formatStatus,
};
/**
 * Validation Utilities
 */

import { SUPPORTED_FILE_TYPES, MAX_FILE_SIZE } from './constants';

/**
 * Validate file type
 */
export const isValidFileType = (filename: string): boolean => {
  const extension = filename.toLowerCase().split('.').pop();
  if (!extension) return false;
  return SUPPORTED_FILE_TYPES.some((type) => type === `.${extension}`);
};

/**
 * Validate file size
 */
export const isValidFileSize = (size: number): boolean => {
  return size > 0 && size <= MAX_FILE_SIZE;
};

/**
 * Validate file
 */
export const validateFile = (
  file: File
): { valid: boolean; error?: string } => {
  if (!isValidFileType(file.name)) {
    return {
      valid: false,
      error: `Invalid file type. Supported types: ${SUPPORTED_FILE_TYPES.join(', ')}`,
    };
  }

  if (!isValidFileSize(file.size)) {
    return {
      valid: false,
      error: `File size exceeds maximum allowed size of ${MAX_FILE_SIZE / (1024 * 1024)}MB`,
    };
  }

  return { valid: true };
};

/**
 * Validate query text
 */
export const isValidQuery = (query: string): boolean => {
  return query.trim().length > 0;
};

/**
 * Validate URL
 */
export const isValidUrl = (url: string): boolean => {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
};

/**
 * Sanitize user input to prevent XSS
 */
export const sanitizeInput = (input: string): string => {
  return input
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
    .replace(/\//g, '&#x2F;');
};

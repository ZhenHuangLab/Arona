/**
 * Axios HTTP Client Configuration
 * 
 * Centralized API client with interceptors for error handling and request/response transformation
 */

import axios, { type AxiosError, type AxiosInstance, type InternalAxiosRequestConfig, type AxiosResponse } from 'axios';
import { APIException } from '../types';

/**
 * Backend base URL selection
 *
 * - If `VITE_BACKEND_URL` is provided, use it (works for production and remote backends).
 * - Otherwise, in dev mode default to same-origin so Vite can proxy `/api` to the backend
 *   (configured in `vite.config.ts`). This removes the need for extra env vars during local dev.
 * - In production builds without `VITE_BACKEND_URL`, use same-origin (assumes a reverse proxy
 *   or the backend serves the frontend under the same origin).
 */
const configuredBackendUrl = import.meta.env.VITE_BACKEND_URL as string | undefined;
const BACKEND_URL = configuredBackendUrl || '';

/**
 * Extract a readable error message from common FastAPI error shapes.
 *
 * FastAPI may return:
 * - { detail: "..." }
 * - { detail: { code, message, extra } }  (our /api/chat endpoints)
 * - { detail: [ { loc, msg, type }, ... ] } (validation errors)
 */
const extractErrorDetail = (data: unknown): string => {
  if (typeof data === 'string') return data;

  if (!data || typeof data !== 'object') return 'Unknown error';

  const obj = data as Record<string, unknown>;
  const detail = obj.detail;

  if (typeof detail === 'string') return detail;

  if (Array.isArray(detail)) {
    const msgs = detail
      .map((item) => {
        if (!item || typeof item !== 'object') return undefined;
        const msg = (item as { msg?: unknown }).msg;
        return typeof msg === 'string' ? msg : undefined;
      })
      .filter((msg): msg is string => Boolean(msg));
    return msgs.length ? msgs.join('; ') : 'Validation error';
  }

  if (detail && typeof detail === 'object') {
    const message = (detail as { message?: unknown }).message;
    if (typeof message === 'string') return message;
    const code = (detail as { code?: unknown }).code;
    if (typeof code === 'string') return code;
    try {
      return JSON.stringify(detail);
    } catch {
      return 'Unknown error';
    }
  }

  const message = obj.message;
  if (typeof message === 'string') return message;

  return 'Unknown error';
};

/**
 * Create axios instance with default configuration
 */
const apiClient: AxiosInstance = axios.create({
  baseURL: BACKEND_URL,
  timeout: 120000, // 2 minutes for long-running operations
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Request interceptor
 * Add any auth tokens or custom headers here
 */
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Log request in development
    if (import.meta.env.DEV) {
      console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`);
    }
    return config;
  },
  (error: AxiosError) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

/**
 * Response interceptor
 * Handle errors and transform responses
 */
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    // Log response in development
    if (import.meta.env.DEV) {
      console.log(`[API Response] ${response.config.method?.toUpperCase()} ${response.config.url}`, response.data);
    }
    return response;
  },
  (error: AxiosError) => {
    // Handle different error types
    if (error.response) {
      // Server responded with error status
      const status = error.response.status;
      const detail = extractErrorDetail(error.response.data) || error.message;
      
      console.error(`[API Error ${status}]`, detail);
      
      // Create custom API exception
      return Promise.reject(new APIException(status, detail));
    } else if (error.request) {
      // Request made but no response received
      console.error('[API Network Error]', error.message);
      return Promise.reject(new APIException(0, 'Network error: Unable to reach backend server'));
    } else {
      // Error in request configuration
      console.error('[API Configuration Error]', error.message);
      return Promise.reject(new APIException(0, error.message));
    }
  }
);

/**
 * Create a multipart/form-data client for file uploads
 */
export const createFormDataClient = (): AxiosInstance => {
  return axios.create({
    baseURL: BACKEND_URL,
    timeout: 300000, // 5 minutes for file uploads
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
};

export default apiClient;
export { BACKEND_URL };

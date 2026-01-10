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
      const detail = (error.response.data as { detail?: string })?.detail || error.message;
      
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

import { toast as sonnerToast } from 'sonner';

/**
 * Toast Utility Functions
 *
 * Wrapper around Sonner toast library with predefined styles
 * and common notification patterns
 */

/**
 * Success Toast
 *
 * Displays a success notification
 */
export const toast = {
  success: (message: string, description?: string) => {
    sonnerToast.success(message, {
      description,
      duration: 3000,
    });
  },

  /**
   * Error Toast
   *
   * Displays an error notification
   */
  error: (message: string, description?: string) => {
    sonnerToast.error(message, {
      description,
      duration: 5000,
    });
  },

  /**
   * Info Toast
   *
   * Displays an informational notification
   */
  info: (message: string, description?: string) => {
    sonnerToast.info(message, {
      description,
      duration: 3000,
    });
  },

  /**
   * Warning Toast
   *
   * Displays a warning notification
   */
  warning: (message: string, description?: string) => {
    sonnerToast.warning(message, {
      description,
      duration: 4000,
    });
  },

  /**
   * Loading Toast
   *
   * Displays a loading notification
   * Returns a toast ID that can be used to dismiss or update the toast
   */
  loading: (message: string, description?: string) => {
    return sonnerToast.loading(message, {
      description,
    });
  },

  /**
   * Promise Toast
   *
   * Displays a loading toast that automatically updates based on promise state
   */
  promise: <T,>(
    promise: Promise<T>,
    messages: {
      loading: string;
      success: string | ((data: T) => string);
      error: string | ((error: unknown) => string);
    }
  ) => {
    return sonnerToast.promise(promise, messages);
  },

  /**
   * Dismiss Toast
   *
   * Dismisses a specific toast by ID or all toasts
   */
  dismiss: (toastId?: string | number) => {
    sonnerToast.dismiss(toastId);
  },
};

/**
 * API Error Toast
 *
 * Specialized toast for API errors with better error message extraction
 */
export const apiErrorToast = (error: unknown, fallbackMessage = 'An error occurred') => {
  let message = fallbackMessage;
  let description: string | undefined;

  if (error instanceof Error) {
    message = error.message;
  } else if (typeof error === 'object' && error !== null) {
    const err = error as { detail?: string; message?: string };
    message = err.detail || err.message || fallbackMessage;
  }

  toast.error(message, description);
};

/**
 * Upload Progress Toast
 *
 * Creates a toast for file upload progress
 */
export const uploadProgressToast = (filename: string) => {
  return toast.loading(`Uploading ${filename}...`);
};

/**
 * Upload Success Toast
 *
 * Displays success message for file upload
 */
export const uploadSuccessToast = (filename: string, toastId?: string | number) => {
  if (toastId) {
    sonnerToast.dismiss(toastId);
  }
  toast.success('Upload complete', `${filename} has been uploaded successfully`);
};

/**
 * Upload Error Toast
 *
 * Displays error message for file upload
 */
export const uploadErrorToast = (filename: string, error: unknown, toastId?: string | number) => {
  if (toastId) {
    sonnerToast.dismiss(toastId);
  }

  let errorMessage = 'Upload failed';
  if (error instanceof Error) {
    errorMessage = error.message;
  }

  toast.error('Upload failed', `Failed to upload ${filename}: ${errorMessage}`);
};

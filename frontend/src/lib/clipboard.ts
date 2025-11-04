import { toast } from './toast';

/**
 * Copy text to clipboard using the Clipboard API
 * 
 * Features:
 * - Uses modern navigator.clipboard.writeText API
 * - Fallback to legacy document.execCommand for older browsers
 * - Toast notification on success/failure
 * - Fail-fast error handling
 * 
 * @param text - Text to copy to clipboard
 * @param successMessage - Optional custom success message (default: "Copied to clipboard")
 * @returns Promise<boolean> - true if successful, false otherwise
 * 
 * @example
 * ```tsx
 * <button onClick={() => copyToClipboard('/path/to/file')}>
 *   Copy Path
 * </button>
 * ```
 */
export async function copyToClipboard(
  text: string,
  successMessage: string = 'Copied to clipboard'
): Promise<boolean> {
  // Validate input
  if (!text || typeof text !== 'string') {
    toast.error('Copy failed', 'Invalid text to copy');
    return false;
  }

  try {
    // Modern Clipboard API (preferred)
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      toast.success(successMessage, text);
      return true;
    }

    // Fallback for older browsers
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    const successful = document.execCommand('copy');
    document.body.removeChild(textArea);

    if (successful) {
      toast.success(successMessage, text);
      return true;
    } else {
      throw new Error('execCommand failed');
    }
  } catch (error) {
    // Fail-fast: expose the error immediately
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    toast.error('Failed to copy', errorMessage);
    console.error('Clipboard copy failed:', error);
    return false;
  }
}

/**
 * Check if clipboard API is available
 * 
 * @returns boolean - true if clipboard API is supported
 */
export function isClipboardSupported(): boolean {
  return !!(
    navigator.clipboard?.writeText ||
    document.queryCommandSupported?.('copy')
  );
}


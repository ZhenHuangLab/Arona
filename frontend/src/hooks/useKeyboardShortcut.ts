import { useEffect, useCallback } from 'react';

interface KeyboardShortcutOptions {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
  meta?: boolean;
  preventDefault?: boolean;
  enabled?: boolean;
}

/**
 * useKeyboardShortcut Hook
 * 
 * Registers keyboard shortcuts with modifier key support.
 * Automatically handles cleanup on unmount.
 * 
 * Accessibility:
 * - Supports standard keyboard shortcuts
 * - Respects enabled state for conditional shortcuts
 * - Prevents default browser behavior when needed
 * 
 * @param callback - Function to call when shortcut is triggered
 * @param options - Shortcut configuration
 * 
 * @example
 * ```tsx
 * // Ctrl+K to open search
 * useKeyboardShortcut(() => setSearchOpen(true), {
 *   key: 'k',
 *   ctrl: true,
 *   preventDefault: true,
 * });
 * 
 * // Escape to close modal
 * useKeyboardShortcut(() => setModalOpen(false), {
 *   key: 'Escape',
 *   enabled: modalOpen,
 * });
 * ```
 */
export function useKeyboardShortcut(
  callback: () => void,
  options: KeyboardShortcutOptions
) {
  const {
    key,
    ctrl = false,
    shift = false,
    alt = false,
    meta = false,
    preventDefault = false,
    enabled = true,
  } = options;

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return;

      const matchesKey = event.key.toLowerCase() === key.toLowerCase();
      const matchesCtrl = ctrl ? event.ctrlKey || event.metaKey : !event.ctrlKey && !event.metaKey;
      const matchesShift = shift ? event.shiftKey : !event.shiftKey;
      const matchesAlt = alt ? event.altKey : !event.altKey;
      const matchesMeta = meta ? event.metaKey : !event.metaKey;

      if (matchesKey && matchesCtrl && matchesShift && matchesAlt && matchesMeta) {
        if (preventDefault) {
          event.preventDefault();
        }
        callback();
      }
    },
    [key, ctrl, shift, alt, meta, preventDefault, enabled, callback]
  );

  useEffect(() => {
    if (!enabled) return;

    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleKeyDown, enabled]);
}

/**
 * useEscapeKey Hook
 * 
 * Convenience hook for handling Escape key press.
 * Commonly used for closing modals, dialogs, and dropdowns.
 * 
 * @param callback - Function to call when Escape is pressed
 * @param enabled - Whether the shortcut is active
 */
export function useEscapeKey(callback: () => void, enabled = true) {
  useKeyboardShortcut(callback, {
    key: 'Escape',
    enabled,
  });
}

/**
 * useEnterKey Hook
 * 
 * Convenience hook for handling Enter key press.
 * Commonly used for form submissions and confirmations.
 * 
 * @param callback - Function to call when Enter is pressed
 * @param enabled - Whether the shortcut is active
 * @param preventDefault - Whether to prevent default behavior
 */
export function useEnterKey(
  callback: () => void,
  enabled = true,
  preventDefault = false
) {
  useKeyboardShortcut(callback, {
    key: 'Enter',
    enabled,
    preventDefault,
  });
}


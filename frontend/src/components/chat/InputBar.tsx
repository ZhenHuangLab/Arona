import { useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { Plus, Send, X, Square } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

interface InputBarProps {
  onSend: (message: string, imageFile?: File | null) => void;
  onStop?: () => void;
  disabled?: boolean;
  isLoading?: boolean;
}

 /**
  * InputBar Component
  *
  * Chat input with attachment and send/stop controls.
  * Supports Enter to send, Shift+Enter for new line.
 *
 * Accessibility:
 * - ARIA labels for screen readers
 * - Keyboard shortcuts (Enter, Shift+Enter)
 * - Focus management
 * - Disabled state handling
 *
 * Mobile Responsive:
 * - Adaptive layout (stacked on mobile, horizontal on desktop)
 * - Touch-friendly button sizes
 * - Optimized spacing
 */
export function InputBar({
  onSend,
  onStop,
  disabled = false,
  isLoading = false,
}: InputBarProps) {
  const [message, setMessage] = useState('');
  const [imageFile, setImageFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const autosizeTextarea = (el?: HTMLTextAreaElement | null) => {
    const target = el ?? textareaRef.current;
    if (!target) return;

    // Reset then grow to content. Clamp for usability.
    target.style.height = '0px';
    const maxHeight = 200;
    const nextHeight = Math.min(target.scrollHeight, maxHeight);
    target.style.height = `${nextHeight}px`;
  };

  const handleSend = () => {
    const trimmedMessage = message.trim();
    const canSend = (!disabled && !isLoading) && (trimmedMessage || imageFile);

    if (canSend) {
      const finalMessage = trimmedMessage || 'Search similar images.';
      onSend(finalMessage, imageFile);
      setMessage('');
      setImageFile(null);
      // Reset height after clearing (after React updates the textarea value).
      requestAnimationFrame(() => autosizeTextarea());
    }
  };

  const handlePrimaryAction = () => {
    if (isLoading) {
      onStop?.();
      return;
    }
    handleSend();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Send on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t bg-background/70 backdrop-blur supports-[backdrop-filter]:bg-background/50 p-2 sm:p-4">
      <div className="mx-auto w-full max-w-3xl">
        <div className="rounded-3xl border bg-background shadow-sm px-2 py-2 flex items-end gap-2 focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2">
          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0] || null;
              if (!file) return;
              if (!file.type.startsWith('image/')) return;
              setImageFile(file);
            }}
          />

          {/* Attach button (ChatGPT-style “+”) */}
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-10 w-10 rounded-full shrink-0"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled || isLoading}
            aria-label={imageFile ? 'Replace attached image' : 'Attach an image'}
          >
            <Plus className="h-5 w-5" aria-hidden="true" />
          </Button>

          {/* Message Input */}
          <Textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => {
              setMessage(e.target.value);
              autosizeTextarea(e.target);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything..."
            disabled={disabled || isLoading}
            className="flex-1 min-h-[44px] max-h-[200px] resize-none border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 px-2 py-2"
            rows={1}
            aria-label="Message input"
            aria-describedby="input-hint"
          />

          {/* Primary action: Send / Stop */}
          <Button
            onClick={handlePrimaryAction}
            disabled={disabled || (isLoading ? !onStop : (!message.trim() && !imageFile))}
            size="icon"
            className="h-10 w-10 rounded-full shrink-0"
            aria-label={isLoading ? 'Stop generating' : 'Send message'}
          >
            {isLoading ? (
              <Square className="h-4 w-4" aria-hidden="true" />
            ) : (
              <Send className="h-4 w-4" aria-hidden="true" />
            )}
            <span className="sr-only">{isLoading ? 'Stop generating' : 'Send message'}</span>
          </Button>
        </div>
      </div>

      {/* Attached image indicator */}
      {imageFile && (
        <div className="mx-auto mt-2 w-full max-w-3xl">
          <div className="flex items-center justify-between rounded-md border bg-muted/30 px-3 py-2 text-xs">
            <span className="truncate" title={imageFile.name}>
              Attached image: {imageFile.name}
            </span>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => setImageFile(null)}
              aria-label="Remove attached image"
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>
        </div>
      )}

      {/* Hidden hint for screen readers */}
      <span id="input-hint" className="sr-only">
        Press Enter to send, Shift+Enter for new line
      </span>
    </div>
  );
}

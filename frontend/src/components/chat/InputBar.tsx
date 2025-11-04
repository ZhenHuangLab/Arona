import { useState } from 'react';
import type { KeyboardEvent } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ModeSelector } from './ModeSelector';
import type { QueryMode } from '@/types/chat';

interface InputBarProps {
  onSend: (message: string, mode: QueryMode) => void;
  disabled?: boolean;
  isLoading?: boolean;
  defaultMode?: QueryMode;
}

/**
 * InputBar Component
 *
 * Chat input with mode selector and send button.
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
  disabled = false,
  isLoading = false,
  defaultMode = 'hybrid',
}: InputBarProps) {
  const [message, setMessage] = useState('');
  const [mode, setMode] = useState<QueryMode>(defaultMode);

  const handleSend = () => {
    const trimmedMessage = message.trim();
    if (trimmedMessage && !disabled && !isLoading) {
      onSend(trimmedMessage, mode);
      setMessage('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Send on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t bg-background p-2 sm:p-4">
      {/* Mobile: Stacked layout, Desktop: Horizontal layout */}
      <div className="flex flex-col sm:flex-row gap-2 sm:items-end">
        {/* Mode Selector - Full width on mobile */}
        <div className="sm:w-auto w-full">
          <ModeSelector
            value={mode}
            onChange={setMode}
            disabled={disabled || isLoading}
          />
        </div>

        {/* Message Input */}
        <Textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message..."
          disabled={disabled || isLoading}
          className="flex-1 min-h-[60px] max-h-[200px] resize-none"
          rows={2}
          aria-label="Message input"
          aria-describedby="input-hint"
        />

        {/* Send Button - Touch-friendly size */}
        <Button
          onClick={handleSend}
          disabled={disabled || isLoading || !message.trim()}
          size="icon"
          className="h-[60px] w-[60px] shrink-0"
          aria-label={isLoading ? 'Sending message' : 'Send message'}
        >
          {isLoading ? (
            <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
          ) : (
            <Send className="h-5 w-5" aria-hidden="true" />
          )}
          <span className="sr-only">{isLoading ? 'Sending...' : 'Send message'}</span>
        </Button>
      </div>

      {/* Hidden hint for screen readers */}
      <span id="input-hint" className="sr-only">
        Press Enter to send, Shift+Enter for new line
      </span>
    </div>
  );
}


import { useState } from 'react';
import { Copy, Check } from 'lucide-react';
import { Markdown } from '@/components/common';
import { Button } from '@/components/ui/button';
import { copyToClipboard } from '@/lib/clipboard';
import type { ChatMessage } from '@/types/chat';

interface MessageProps {
  message: ChatMessage;
}

/**
 * Message Component
 *
 * Displays a single chat message with user/assistant styling.
 * Implements the minimalist design with clear visual distinction.
 */
export function Message({ message }: MessageProps) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === 'user';
  const isPending = message.pending;

  const timeText = new Date(message.timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });

  const handleCopy = async () => {
    const ok = await copyToClipboard(message.content, 'Copied', null);
    if (!ok) return;
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isUser) {
    return (
      <div className="group flex justify-end">
        <div className="flex max-w-[85%] flex-col items-end gap-1">
          <div className="rounded-2xl rounded-br-md bg-muted/60 px-4 py-2">
            <Markdown content={message.content} />
          </div>
          {/* Actions row below bubble - copy shown on hover */}
          <div className="flex items-center gap-1">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-6 w-6 text-muted-foreground opacity-0 pointer-events-none transition-opacity hover:text-foreground group-hover:opacity-100 group-hover:pointer-events-auto group-focus-within:opacity-100 group-focus-within:pointer-events-auto"
              onClick={handleCopy}
              aria-label="Copy user message"
            >
              {copied ? (
                <Check className="h-3 w-3 text-green-500" aria-hidden="true" />
              ) : (
                <Copy className="h-3 w-3" aria-hidden="true" />
              )}
            </Button>
            <span className="text-[11px] text-muted-foreground">{timeText}</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="text-sm leading-relaxed">
      <Markdown content={message.content} />
      {/* Copy button - shown after streaming completes, positioned bottom-left */}
      {!isPending && (
        <div className="mt-2">
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 text-muted-foreground hover:text-foreground"
            onClick={handleCopy}
            aria-label="Copy assistant message"
          >
            {copied ? (
              <Check className="h-3 w-3 text-green-500" aria-hidden="true" />
            ) : (
              <Copy className="h-3 w-3" aria-hidden="true" />
            )}
          </Button>
        </div>
      )}
    </div>
  );
}

import { useState } from 'react';
import { Copy, Check, ChevronLeft, ChevronRight, RotateCcw, Loader2 } from 'lucide-react';
import { Markdown } from '@/components/common';
import { Button } from '@/components/ui/button';
import { copyToClipboard } from '@/lib/clipboard';
import type { ChatMessage } from '@/types/chat';

interface MessageProps {
  message: ChatMessage;
  selectedVariantIndex?: number;
  onSelectVariant?: (messageId: string, nextIndex: number) => void;
  onRetry?: (assistantMessageId: string) => Promise<void>;
  canRetry?: boolean;
  isRetrying?: boolean;
}

/**
 * Message Component
 *
 * Displays a single chat message with user/assistant styling.
 * Implements the minimalist design with clear visual distinction.
 */
export function Message({
  message,
  selectedVariantIndex: selectedVariantIndexProp,
  onSelectVariant,
  onRetry,
  canRetry,
  isRetrying,
}: MessageProps) {
  const [copied, setCopied] = useState(false);
  const [isRetryingLocal, setIsRetryingLocal] = useState(false);
  const isUser = message.role === 'user';
  const isPending = message.pending;
  const variants = message.variants;
  const hasVariants = Array.isArray(variants) && variants.length > 0;
  const variantCount = hasVariants ? variants.length : 0;
  const selectedVariantIndex =
    typeof selectedVariantIndexProp === 'number'
      ? selectedVariantIndexProp
      : message.variantIndex ?? (hasVariants ? variants.length - 1 : 0);
  const clampedVariantIndex =
    hasVariants && variantCount > 0
      ? Math.max(0, Math.min(selectedVariantIndex, variantCount - 1))
      : 0;
  const displayContent = hasVariants ? variants[clampedVariantIndex] : message.content;

  const timeText = new Date(message.timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });

  const handleCopy = async () => {
    const ok = await copyToClipboard(displayContent, 'Copied', null);
    if (!ok) return;
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRetry = async () => {
    if (!onRetry) return;
    if (!canRetry) return;
    if (isRetrying || isRetryingLocal) return;
    setIsRetryingLocal(true);
    try {
      await onRetry(message.id);
    } finally {
      setIsRetryingLocal(false);
    }
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
      <Markdown content={displayContent} />
      {/* Copy button - shown after streaming completes, positioned bottom-left */}
      {!isPending && (
        <div className="mt-2 flex items-center gap-1">
          {hasVariants && variantCount > 1 ? (
            <div className="flex items-center gap-0.5">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-6 w-6 text-muted-foreground hover:text-foreground disabled:opacity-40"
                onClick={() =>
                  onSelectVariant?.(message.id, Math.max(0, clampedVariantIndex - 1))
                }
                disabled={!onSelectVariant || clampedVariantIndex <= 0}
                aria-label="Previous assistant version"
              >
                <ChevronLeft className="h-3 w-3" aria-hidden="true" />
              </Button>
              <span className="min-w-[36px] text-center text-[11px] text-muted-foreground tabular-nums">
                {clampedVariantIndex + 1}/{variantCount}
              </span>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-6 w-6 text-muted-foreground hover:text-foreground disabled:opacity-40"
                onClick={() =>
                  onSelectVariant?.(
                    message.id,
                    Math.min(variantCount - 1, clampedVariantIndex + 1)
                  )
                }
                disabled={
                  !onSelectVariant || clampedVariantIndex >= variantCount - 1
                }
                aria-label="Next assistant version"
              >
                <ChevronRight className="h-3 w-3" aria-hidden="true" />
              </Button>
            </div>
          ) : null}
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
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-6 w-6 text-muted-foreground hover:text-foreground disabled:opacity-40"
            onClick={handleRetry}
            disabled={!canRetry || isRetrying || isRetryingLocal}
            aria-label="Retry assistant message"
          >
            {isRetrying || isRetryingLocal ? (
              <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
            ) : (
              <RotateCcw className="h-3 w-3" aria-hidden="true" />
            )}
          </Button>
        </div>
      )}
    </div>
  );
}

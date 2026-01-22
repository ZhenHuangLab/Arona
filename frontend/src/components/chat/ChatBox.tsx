import { useCallback, useEffect, useRef, useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { Message } from './Message';
import { Button } from '@/components/ui/button';
import type { ChatMessage } from '@/types/chat';

interface ChatBoxProps {
  messages: ChatMessage[];
  isLoading?: boolean;
  onRetryAssistant?: (assistantMessageId: string) => Promise<void>;
  isRetrying?: boolean;
  onEditUserMessage?: (userMessageId: string, assistantMessageId: string, newContent: string) => Promise<void>;
  isEditing?: boolean;
}

/**
 * ChatBox Component
 *
 * Container for chat messages with auto-scroll functionality.
 * Displays messages in chronological order with empty state.
 */
export function ChatBox({ messages, isLoading, onRetryAssistant, isRetrying, onEditUserMessage, isEditing }: ChatBoxProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const isAtBottomRef = useRef(true);
  const prevMessageCountRef = useRef(0);
  const [selectedVariantByMessageId, setSelectedVariantByMessageId] = useState<Record<string, number>>(
    {}
  );
  const variantsLenRef = useRef<Record<string, number>>({});

  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'auto') => {
    messagesEndRef.current?.scrollIntoView({ behavior, block: 'end' });
  }, []);

  const computeIsAtBottom = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return true;

    // Allow some leeway so tiny scroll offsets don't disable stick-to-bottom.
    const thresholdPx = 48;
    const remaining = el.scrollHeight - el.scrollTop - el.clientHeight;
    return remaining <= thresholdPx;
  }, []);

  const handleScroll = useCallback(() => {
    const atBottom = computeIsAtBottom();
    isAtBottomRef.current = atBottom;
    setIsAtBottom(atBottom);
  }, [computeIsAtBottom]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    const prevCount = prevMessageCountRef.current;
    const nextCount = messages.length;
    const messageAppended = nextCount > prevCount;
    prevMessageCountRef.current = nextCount;

    // Only keep auto-scrolling when the user is already at/near bottom.
    // This prevents wheel scrolling from being "stolen" during streaming updates.
    if (messageAppended || isAtBottomRef.current) {
      scrollToBottom('auto');
    }
  }, [messages, scrollToBottom]);

  // Initialize isAtBottom on mount (and when the container ref becomes available)
  useEffect(() => {
    handleScroll();
  }, [handleScroll]);

  // Keep selected variant index stable per message, and auto-jump to newest on retry.
  useEffect(() => {
    setSelectedVariantByMessageId((prev) => {
      let changed = false;
      const next = { ...prev };

      for (const m of messages) {
        if (m.role !== 'assistant') continue;
        if (!Array.isArray(m.variants) || m.variants.length === 0) continue;

        const len = m.variants.length;
        const lastSeenLen = variantsLenRef.current[m.id];
        const desiredDefault =
          typeof m.variantIndex === 'number' && m.variantIndex >= 0 && m.variantIndex < len
            ? m.variantIndex
            : len - 1;

        if (typeof next[m.id] !== 'number') {
          next[m.id] = desiredDefault;
          changed = true;
        }

        if (typeof lastSeenLen === 'number' && len > lastSeenLen) {
          next[m.id] = len - 1;
          changed = true;
        }

        if (next[m.id] < 0) {
          next[m.id] = 0;
          changed = true;
        }
        if (next[m.id] >= len) {
          next[m.id] = len - 1;
          changed = true;
        }

        variantsLenRef.current[m.id] = len;
      }

      return changed ? next : prev;
    });
  }, [messages]);

  const handleSelectVariant = useCallback((messageId: string, nextIndex: number) => {
    setSelectedVariantByMessageId((prev) => ({ ...prev, [messageId]: nextIndex }));
  }, []);

  const latestMessageId = messages[messages.length - 1]?.id;
  const latestAssistant = [...messages].reverse().find((m) => m.role === 'assistant');
  const latestAssistantRequestId = latestAssistant?.requestId;

  return (
    <div className="h-full relative">
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="h-full overflow-y-auto scrollbar-thin"
      >
        <div className="mx-auto w-full max-w-3xl px-3 sm:px-6 py-6 space-y-6">
          {messages.map((message, index) => {
            const canRetryMessage =
              !!onRetryAssistant &&
              message.role === 'assistant' &&
              !message.pending &&
              message.id === latestMessageId;

            const canEditMessage =
              !!onEditUserMessage &&
              message.role === 'user' &&
              !message.pending &&
              !!latestAssistant &&
              !latestAssistant.pending &&
              !!latestAssistantRequestId &&
              message.requestId === latestAssistantRequestId;

            return (
              <Message
                key={message.id || index}
                message={message}
                selectedVariantIndex={selectedVariantByMessageId[message.id]}
                onSelectVariant={handleSelectVariant}
                onRetry={onRetryAssistant}
                canRetry={canRetryMessage}
                isRetrying={isRetrying}
                canEdit={canEditMessage}
                onEdit={
                  canEditMessage && latestAssistant && onEditUserMessage
                    ? (messageId, newContent) =>
                        onEditUserMessage(messageId, latestAssistant.id, newContent)
                    : undefined
                }
                isEditing={isEditing}
              />
            );
          })}
          {isLoading ? (
            <div className="text-sm text-muted-foreground">Loading…</div>
          ) : null}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {!isAtBottom && (
        <Button
          type="button"
          variant="secondary"
          size="icon"
          className="absolute bottom-3 right-3 rounded-full shadow-md"
          onClick={() => scrollToBottom('smooth')}
          aria-label="Scroll to bottom"
        >
          <ChevronDown className="h-4 w-4" aria-hidden="true" />
        </Button>
      )}
    </div>
  );
}

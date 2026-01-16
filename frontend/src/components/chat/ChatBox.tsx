import { useCallback, useEffect, useRef, useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { Message } from './Message';
import { EmptyState } from '../common/EmptyState';
import { Button } from '@/components/ui/button';
import type { ChatMessage } from '@/types/chat';

interface ChatBoxProps {
  messages: ChatMessage[];
  isLoading?: boolean;
}

/**
 * ChatBox Component
 * 
 * Container for chat messages with auto-scroll functionality.
 * Displays messages in chronological order with empty state.
 */
export function ChatBox({ messages, isLoading }: ChatBoxProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const isAtBottomRef = useRef(true);
  const prevMessageCountRef = useRef(0);

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

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <EmptyState
          title="No messages yet"
          description="Start a conversation by typing a message below"
        />
      </div>
    );
  }

  return (
    <div className="h-full relative">
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="h-full overflow-y-auto space-y-1 px-2 scrollbar-thin"
      >
        {messages.map((message, index) => (
          <Message key={message.id || index} message={message} />
        ))}
        {isLoading && (
          <div className="flex gap-3 py-4 px-4">
            <div className="flex-shrink-0 h-8 w-8 rounded-full bg-purple-600 flex items-center justify-center">
              <div className="h-5 w-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            </div>
            <div className="flex-1">
              <div className="text-sm font-semibold mb-2">Assistant</div>
              <div className="text-sm text-muted-foreground">Thinking...</div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
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

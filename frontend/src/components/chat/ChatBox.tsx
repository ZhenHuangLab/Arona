import { useEffect, useRef } from 'react';
import { Message } from './Message';
import { EmptyState } from '../common/EmptyState';
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
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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
    <div className="flex-1 overflow-y-auto space-y-1 px-2">
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
  );
}


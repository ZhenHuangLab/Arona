import { User, Bot } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Markdown } from '@/components/common';
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
  const isUser = message.role === 'user';

  return (
    <div
      className={cn(
        'flex gap-3 py-4 px-4 rounded-lg',
        isUser ? 'bg-muted/50' : 'bg-background'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-purple-600 text-white'
        )}
      >
        {isUser ? (
          <User className="h-5 w-5" />
        ) : (
          <Bot className="h-5 w-5" />
        )}
      </div>

      {/* Message Content */}
      <div className="flex-1 space-y-2 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold">
            {isUser ? 'You' : 'Assistant'}
          </span>
          {message.timestamp && (
            <span className="text-xs text-muted-foreground">
              {new Date(message.timestamp).toLocaleTimeString()}
            </span>
          )}
        </div>
        {isUser ? (
          <div className="text-sm whitespace-pre-wrap break-words">{message.content}</div>
        ) : (
          <Markdown content={message.content} />
        )}
      </div>
    </div>
  );
}

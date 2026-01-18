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
  const timeText = new Date(message.timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="flex max-w-[85%] flex-col items-end gap-1">
          <div className="rounded-2xl rounded-br-md bg-muted/60 px-4 py-2">
            <Markdown content={message.content} />
          </div>
          <span className="text-[11px] text-muted-foreground">{timeText}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="text-sm leading-relaxed">
      <Markdown content={message.content} />
    </div>
  );
}

import React from 'react';
import { MessageSquare } from 'lucide-react';
import { ChatBox, InputBar, ClearConversationDialog } from '@/components/chat';
import { useChat } from '@/hooks';
import type { QueryMode } from '@/types/chat';

/**
 * Chat View
 *
 * Main view for the chat interface with full integration.
 *
 * Features:
 * - Centered chat dialog with responsive layout
 * - Message history with auto-scroll
 * - Input bar with mode selector
 * - Clear conversation button with confirmation
 * - Persistent conversation history via Zustand
 * - API integration with React Query
 *
 * Accessibility:
 * - Semantic HTML with proper ARIA labels
 * - Keyboard navigation support
 * - Screen reader friendly
 * - Focus management
 *
 * Mobile Responsive:
 * - Adaptive padding and spacing
 * - Touch-friendly button sizes
 * - Optimized layout for small screens
 */
export const ChatView: React.FC = () => {
  const { messages, currentMode, sendMessage, clearConversation, isSending } = useChat();

  const handleSendMessage = (message: string, mode: QueryMode, imageFile?: File | null) => {
    sendMessage(message, mode, imageFile);
  };

  const handleClearConversation = () => {
    clearConversation();
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 py-4 sm:py-8 px-2 sm:px-4">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="text-center mb-4 sm:mb-6">
          <div className="flex items-center justify-center gap-2 sm:gap-3 mb-2">
            <MessageSquare className="h-6 w-6 sm:h-8 sm:w-8 text-primary" aria-hidden="true" />
            <h1 className="text-2xl sm:text-3xl font-bold">Arona Chat</h1>
          </div>
          <p className="text-sm sm:text-base text-muted-foreground">Ask questions about your documents</p>
        </div>

        {/* Chat Container */}
        <div
          className="bg-card rounded-xl sm:rounded-2xl shadow-xl border overflow-hidden flex flex-col h-[calc(100vh-180px)] sm:h-[calc(100vh-240px)] min-h-[400px] sm:min-h-[500px]"
          role="region"
          aria-label="Chat conversation"
        >
          {/* Chat Header with Clear Button */}
          <div className="border-b bg-muted/50 px-3 sm:px-6 py-3 sm:py-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" aria-hidden="true" />
              <span className="text-xs sm:text-sm font-medium">
                {messages.length} {messages.length === 1 ? 'message' : 'messages'}
              </span>
            </div>
            <ClearConversationDialog
              onConfirm={handleClearConversation}
              disabled={messages.length === 0 || isSending}
            />
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-hidden" role="log" aria-live="polite" aria-atomic="false">
            <ChatBox messages={messages} isLoading={isSending} />
          </div>

          {/* Input Area */}
          <InputBar
            onSend={handleSendMessage}
            disabled={false}
            isLoading={isSending}
            defaultMode={currentMode}
          />
        </div>

        {/* Footer Info - Hidden on mobile */}
        <div className="mt-3 sm:mt-4 text-center text-xs sm:text-sm text-muted-foreground hidden sm:block">
          <p>
            Current mode: <span className="font-semibold">{currentMode}</span>
            {' • '}
            Press <kbd className="px-2 py-1 bg-muted border rounded text-xs">Enter</kbd> to send,{' '}
            <kbd className="px-2 py-1 bg-muted border rounded text-xs">Shift+Enter</kbd> for new line
          </p>
        </div>
      </div>
    </div>
  );
};

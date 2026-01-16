import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { MessageSquare, Plus, Loader2 } from 'lucide-react';
import { ChatBox, InputBar } from '@/components/chat';
import { useChat, useChatSession, useCreateSession } from '@/hooks';
import { Button } from '@/components/ui/button';

/**
 * Chat View
 *
 * Main view for the chat interface with session support.
 *
 * Features:
 * - Supports /chat (empty state) and /chat/:sessionId routes
 * - Message history from backend via React Query
 * - ChatGPT-style input bar (no mode selector)
 * - Session-aware message sending via /api/chat/.../turn:stream
 *
 * Accessibility:
 * - Semantic HTML with proper ARIA labels
 * - Keyboard navigation support
 * - Screen reader friendly
 *
 * Mobile Responsive:
 * - Adaptive padding and spacing
 * - Touch-friendly button sizes
 */
export const ChatView: React.FC = () => {
  const { sessionId } = useParams<{ sessionId?: string }>();
  const navigate = useNavigate();

  // Fetch session details if we have an ID
  const { data: session, isLoading: isLoadingSession } = useChatSession(sessionId);

  // Chat hook with session context
  const { messages, sendMessage, stopGenerating, isSending, isLoadingMessages } = useChat(sessionId);

  // Create session mutation
  const createSessionMutation = useCreateSession();

  const handleSendMessage = (message: string, imageFile?: File | null) => {
    // Backend currently enforces hybrid mode; keep UI simple and consistent.
    sendMessage(message, 'hybrid', imageFile);
  };

  const handleCreateSession = async () => {
    try {
      const newSession = await createSessionMutation.mutateAsync(undefined);
      navigate(`/chat/${newSession.id}`);
    } catch {
      // Error already handled by mutation
    }
  };

  // Empty state: no session selected
  if (!sessionId) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-gradient-to-b from-background to-muted/20 p-4">
        <div className="text-center max-w-md">
          <MessageSquare className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
          <h1 className="text-2xl font-bold mb-2">Welcome to Arona Chat</h1>
          <p className="text-muted-foreground mb-6">
            Start a new conversation to ask questions about your documents.
          </p>
          <Button
            onClick={handleCreateSession}
            disabled={createSessionMutation.isPending}
            size="lg"
          >
            {createSessionMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Creating...
              </>
            ) : (
              <>
                <Plus className="h-4 w-4 mr-2" />
                New Chat
              </>
            )}
          </Button>
        </div>
      </div>
    );
  }

  // Loading session
  if (isLoadingSession) {
    return (
      <div className="h-full flex items-center justify-center bg-gradient-to-b from-background to-muted/20">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-gradient-to-b from-background to-muted/20">
      {/* Chat Container - takes full height of flex parent */}
      <div
        className="flex-1 flex flex-col overflow-hidden"
        role="region"
        aria-label="Chat conversation"
      >
        {/* Chat Header */}
        <div className="border-b bg-muted/50 px-3 sm:px-6 py-3 sm:py-4 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium truncate max-w-[200px] sm:max-w-none">
              {session?.title || 'Chat'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" aria-hidden="true" />
            <span className="text-xs sm:text-sm text-muted-foreground">
              {messages.length} {messages.length === 1 ? 'message' : 'messages'}
            </span>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-hidden" role="log" aria-live="polite" aria-atomic="false">
          <ChatBox messages={messages} isLoading={isLoadingMessages && messages.length === 0} />
        </div>

        {/* Input Area */}
        <InputBar
          onSend={handleSendMessage}
          onStop={stopGenerating}
          disabled={!sessionId}
          isLoading={isSending}
        />
      </div>
    </div>
  );
};

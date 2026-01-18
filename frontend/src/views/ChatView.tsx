import { useCallback, useEffect, useRef, useState, type FC } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { MessageSquare, Loader2 } from 'lucide-react';
import { ChatBox, InputBar } from '@/components/chat';
import { useChat, useChatSession, useCreateSession } from '@/hooks';

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
export const ChatView: FC = () => {
  const { sessionId } = useParams<{ sessionId?: string }>();
  const navigate = useNavigate();
  const location = useLocation();

  const [isStartingSession, setIsStartingSession] = useState(false);
  const hasSentInitialMessageRef = useRef(false);

  // Fetch session details if we have an ID
  const { isLoading: isLoadingSession } = useChatSession(sessionId);

  // Chat hook with session context
  const { messages, sendMessage, stopGenerating, isSending, isLoadingMessages } = useChat(sessionId);

  // Create session mutation
  const createSessionMutation = useCreateSession();

  const handleSendMessage = useCallback((message: string, imageFile?: File | null) => {
    // Backend currently enforces hybrid mode; keep UI simple and consistent.
    sendMessage(message, 'hybrid', imageFile);
  }, [sendMessage]);

  const handleStartNewSessionFromDraft = async (message: string, imageFile?: File | null) => {
    if (isStartingSession || createSessionMutation.isPending) return;

    setIsStartingSession(true);
    try {
      const title = message.trim().slice(0, 60) || undefined;
      const newSession = await createSessionMutation.mutateAsync(title);
      navigate(`/chat/${newSession.id}`, {
        state: { initialMessage: message, initialImageFile: imageFile ?? null },
      });
    } catch {
      // Error already handled by mutation
    } finally {
      setIsStartingSession(false);
    }
  };

  // If we navigated from /chat (draft) with an initial message, send it once.
  const navigationState = (location.state || null) as
    | { initialMessage?: string; initialImageFile?: File | null }
    | null;
  const initialMessage = navigationState?.initialMessage;
  const initialImageFile = navigationState?.initialImageFile ?? null;

  useEffect(() => {
    if (!sessionId) return;
    if (!initialMessage) return;
    if (hasSentInitialMessageRef.current) return;

    hasSentInitialMessageRef.current = true;
    // Clear history state so refresh/back-forward doesn't resend.
    navigate(`/chat/${sessionId}`, { replace: true, state: null });
    handleSendMessage(initialMessage, initialImageFile);
  }, [sessionId, initialMessage, initialImageFile, navigate, handleSendMessage]);

  // Draft view: no session selected yet (no session is created until first send).
  if (!sessionId) {
    return (
      <div className="h-full flex items-center justify-center bg-gradient-to-b from-background to-muted/20">
        <div className="w-full max-w-3xl px-4">
          <div className="flex flex-col items-center gap-6">
            <MessageSquare className="h-10 w-10 text-muted-foreground" aria-hidden="true" />
            <InputBar
              placement="centered"
              onSend={handleStartNewSessionFromDraft}
              disabled={false}
              isStarting={isStartingSession || createSessionMutation.isPending}
            />
          </div>
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
        {/* Messages Area */}
        <div className="flex-1 overflow-hidden" role="log" aria-live="polite" aria-atomic="false">
          <ChatBox messages={messages} isLoading={isLoadingMessages && messages.length === 0} />
        </div>

        {/* Input Area */}
        <InputBar
          onSend={handleSendMessage}
          onStop={stopGenerating}
          disabled={false}
          isLoading={isSending}
        />
      </div>
    </div>
  );
};

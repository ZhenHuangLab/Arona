import { useCallback, useEffect, useMemo, useRef, useState, type FC } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
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

  const landingHeadline = useMemo(() => {
    const lines = [
      'How can I help you today?',
      'Ask me anything.',
      'What are we building?',
      'Drop a question, and we’ll take it from there.',
      'Let’s solve something together.',
      'Need a second brain?',
      'What’s on your mind?',
      'Let’s make progress — one message at a time.',
    ];
    return lines[Math.floor(Math.random() * lines.length)];
  }, []);

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
      <div className="h-full relative bg-gradient-to-b from-background to-muted/20">
        {/* Headline (centered above the input) */}
        <div className="absolute inset-x-0 top-1/2 -translate-y-full -mt-10">
          <div className="mx-auto w-full max-w-3xl px-4">
            <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-center">
              {landingHeadline}
            </h1>
          </div>
        </div>

        {/* Input (centered vertically) */}
        <div className="absolute inset-x-0 top-1/2 -translate-y-1/2">
          <div className="mx-auto w-full max-w-3xl px-4">
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

/**
 * useChat Hook
 *
 * Session-aware chat hook using React Query.
 * Handles message sending via /api/chat/.../turn with idempotency.
 */

import { useMutation, useQueryClient, type InfiniteData } from '@tanstack/react-query';
import { useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useChatStore } from '@/store/chatStore';
import { createTurn, createTurnStream, retryAssistantMessage } from '@/api/chat';
import { toast } from '@/lib/toast';
import { APIException } from '@/types';
import type { QueryMode, MessageListResponse, TurnRequest } from '@/types/chat';
import { chatMessagesKeys, chatSessionsKeys, useChatMessagesFlat } from './useChatSessions';

/**
 * Convert File to base64 data URL.
 */
const fileToDataURL = (file: File): Promise<string> =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(new Error('Failed to read image file'));
    reader.readAsDataURL(file);
  });

/**
 * Session-aware chat hook.
 *
 * @param sessionId - The active session ID (undefined for empty state).
 */
export function useChat(sessionId?: string) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { currentMode, setMode } = useChatStore();
  const abortControllerRef = useRef<AbortController | null>(null);
  const activeRequestIdRef = useRef<string | null>(null);

  // Fetch messages from backend via React Query
  const {
    messages,
    isLoading: isLoadingMessages,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    refetch,
  } = useChatMessagesFlat(sessionId);

  /**
   * Mutation for sending a message (turn).
   */
  const sendMessageMutation = useMutation({
    mutationFn: async ({
      message,
      mode,
      imageFile,
    }: {
      message: string;
      mode: QueryMode;
      imageFile?: File | null;
    }) => {
      if (!sessionId) {
        throw new Error('No active session');
      }

      // Cancel any previous in-flight stream (safety)
      abortControllerRef.current?.abort();
      abortControllerRef.current = new AbortController();

      const request_id = crypto.randomUUID();
      activeRequestIdRef.current = request_id;

      const displayMessage = imageFile
        ? `${message}\n[Attached image: ${imageFile.name}]`
        : message;
      const nowIso = new Date().toISOString();

      // Build multimodal content if image provided
      let multimodal_content: TurnRequest['multimodal_content'] = null;
      if (imageFile) {
        const maxBytes = 8 * 1024 * 1024; // 8MB
        if (imageFile.size > maxBytes) {
          throw new Error(
            `Image too large (${Math.round(imageFile.size / 1024 / 1024)}MB). Please use an image <= 8MB.`
          );
        }
        const img_base64 = await fileToDataURL(imageFile);
        multimodal_content = { img_base64 };
      }

      const userTempId = `temp-user-${request_id}`;
      const assistantTempId = `temp-assistant-${request_id}`;

      const userPlaceholderDto: MessageListResponse['messages'][number] = {
        id: userTempId,
        session_id: sessionId,
        role: 'user',
        content: displayMessage,
        created_at: nowIso,
        metadata: { mode, pending: true, request_id },
      };

      const assistantPlaceholderDto: MessageListResponse['messages'][number] = {
        id: assistantTempId,
        session_id: sessionId,
        role: 'assistant',
        content: '...',
        created_at: nowIso,
        metadata: { mode, pending: true, request_id },
      };

      // Add optimistic messages to React Query cache
      await queryClient.cancelQueries({ queryKey: chatMessagesKeys.list(sessionId) });
      queryClient.setQueryData<InfiniteData<MessageListResponse>>(
        chatMessagesKeys.list(sessionId),
        (old) => {
          if (!old || old.pages.length === 0) {
            return {
              pages: [
                {
                  messages: [userPlaceholderDto, assistantPlaceholderDto],
                  next_cursor: null,
                  has_more: false,
                },
              ],
              pageParams: [null],
            };
          }

          const newPages = old.pages.slice();
          const firstPage = newPages[0];
          newPages[0] = {
            ...firstPage,
            messages: [...firstPage.messages, userPlaceholderDto, assistantPlaceholderDto],
          };

          return { ...old, pages: newPages };
        }
      );

      // Call the streaming turn API (SSE) and update the assistant placeholder progressively.
      let assistantText = '';
      let response: Awaited<ReturnType<typeof createTurn>> | null = null;

      const signal = abortControllerRef.current.signal;
      const prefersReducedMotion =
        typeof window !== 'undefined' &&
        typeof window.matchMedia === 'function' &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches;

      const updateAssistantPlaceholder = (text: string) => {
        queryClient.setQueryData<InfiniteData<MessageListResponse>>(
          chatMessagesKeys.list(sessionId),
          (old) => {
            if (!old || old.pages.length === 0) return old;

            const newPages = old.pages.slice();
            const firstPage = newPages[0];
            newPages[0] = {
              ...firstPage,
              messages: firstPage.messages.map((m) =>
                m.id === assistantTempId ? { ...m, content: text } : m
              ),
            };

            return { ...old, pages: newPages };
          }
        );
      };

      const applyDeltaWithTypewriter = async (delta: string) => {
        if (!delta) return;

        // If the provider already streams small chunks, the natural stream is the typing effect.
        // When we only get a single large chunk, simulate a ChatGPT-like typewriter feel.
        const shouldAnimate = !prefersReducedMotion && delta.length >= 40;
        if (!shouldAnimate) {
          assistantText += delta;
          updateAssistantPlaceholder(assistantText);
          return;
        }

        const tickMs = 16; // ~60fps
        const maxDurationMs = 900;
        const maxSteps = Math.max(1, Math.floor(maxDurationMs / tickMs));
        const chunkSize = Math.max(8, Math.ceil(delta.length / maxSteps));

        for (let i = 0; i < delta.length; i += chunkSize) {
          if (signal.aborted) {
            throw new DOMException('Aborted', 'AbortError');
          }
          assistantText += delta.slice(i, i + chunkSize);
          updateAssistantPlaceholder(assistantText);
          // Small delay so the UI can visually “type”.
          await new Promise((resolve) => setTimeout(resolve, tickMs));
        }
      };

      try {
        for await (const event of createTurnStream(sessionId, {
          request_id,
          query: message,
          mode,
          multimodal_content,
        }, { signal: abortControllerRef.current.signal })) {
          if (event.type === 'delta') {
            await applyDeltaWithTypewriter(event.delta || '');
          } else if (event.type === 'final') {
            response = event.response;
          }
        }
      } catch (error) {
        // Fallback to non-streaming endpoint if the streaming route is unavailable.
        if (error instanceof APIException && (error.status === 404 || error.status === 405)) {
          response = await createTurn(sessionId, {
            request_id,
            query: message,
            mode,
            multimodal_content,
          });
        } else {
          throw error;
        }
      }

      if (!response) {
        throw new Error('Streaming ended without final response');
      }

      return { response, request_id, sessionId };
    },
    onSettled: () => {
      abortControllerRef.current = null;
      activeRequestIdRef.current = null;
    },
    onSuccess: ({ response, request_id, sessionId: sid }) => {
      // Replace placeholder messages with real ones from backend
      queryClient.setQueryData<InfiniteData<MessageListResponse>>(
        chatMessagesKeys.list(sid),
        (old) => {
          if (!old) return old;

          const userMsgId = `temp-user-${request_id}`;
          const assistantMsgId = `temp-assistant-${request_id}`;
          const append = [
            response.user_message,
            ...(response.assistant_message ? [response.assistant_message] : []),
          ];

          if (old.pages.length === 0) return old;

          const newPages = old.pages.slice();
          const firstPage = newPages[0];

          const withoutPlaceholders = firstPage.messages.filter(
            (m) => m.id !== userMsgId && m.id !== assistantMsgId
          );

          const deduped = withoutPlaceholders.filter(
            (m) => !append.some((a) => a.id === m.id)
          );

          newPages[0] = {
            ...firstPage,
            messages: [...deduped, ...append],
          };

          return { ...old, pages: newPages };
        }
      );

      // Session metadata may have changed (title auto-update, updated_at bump)
      queryClient.invalidateQueries({ queryKey: chatSessionsKeys.lists() });
      queryClient.invalidateQueries({ queryKey: chatSessionsKeys.detail(sid) });

      // If turn failed at LLM level, show error
      if (response.status === 'failed' && response.error) {
        toast.error('Assistant error', response.error.message);
      }
    },
    onError: (error: Error) => {
      const sid = sessionId;
      if (!sid) return;

      // AbortController cancellation: keep whatever has been streamed so far.
      if ((error as { name?: string }).name === 'AbortError') {
        const requestId = activeRequestIdRef.current;
        if (requestId) {
          queryClient.setQueryData<InfiniteData<MessageListResponse>>(
            chatMessagesKeys.list(sid),
            (old) => {
              if (!old) return old;
              const newPages = old.pages.map((page) => ({
                ...page,
                messages: page.messages.map((m) => {
                  if (m.metadata?.request_id !== requestId) return m;
                  return {
                    ...m,
                    metadata: {
                      ...(m.metadata || {}),
                      pending: false,
                      cancelled: true,
                    },
                  };
                }),
              }));
              return { ...old, pages: newPages };
            }
          );
        }
        toast.info('Stopped', 'Generation cancelled.');
        return;
      }

      // Handle specific error cases
      if (error instanceof APIException) {
        if (error.status === 409) {
          // Idempotency conflict
          toast.error('Request conflict', 'Please try again with a new message.');
          // Refetch to get current state
          queryClient.invalidateQueries({ queryKey: chatMessagesKeys.list(sid) });
        } else if (error.status === 404) {
          // Session not found
          toast.error('Session not found', 'Redirecting to chat...');
          navigate('/chat');
        } else {
          toast.error('Failed to send message', error.message);
        }
      } else {
        toast.error('Failed to send message', error.message);
      }

      // Remove placeholder messages
      queryClient.setQueryData<InfiniteData<MessageListResponse>>(
        chatMessagesKeys.list(sid),
        (old) => {
          if (!old) return old;
          const newPages = old.pages.map((page) => ({
            ...page,
            messages: page.messages.filter(
              (m) => !(m.metadata?.pending === true)
            ),
          }));
          return { ...old, pages: newPages };
        }
      );
    },
  });

  /**
   * Retry (regenerate) an assistant message in-place.
   */
  const retryAssistantMutation = useMutation({
    mutationFn: async ({ assistantMessageId }: { assistantMessageId: string }) => {
      if (!sessionId) {
        throw new Error('No active session');
      }
      return retryAssistantMessage(sessionId, assistantMessageId);
    },
    onSuccess: (assistantDto) => {
      const sid = sessionId;
      if (!sid) return;

      // Update the message in React Query cache (in-place).
      queryClient.setQueryData<InfiniteData<MessageListResponse>>(
        chatMessagesKeys.list(sid),
        (old) => {
          if (!old) return old;
          const newPages = old.pages.map((page) => ({
            ...page,
            messages: page.messages.map((m) => (m.id === assistantDto.id ? assistantDto : m)),
          }));
          return { ...old, pages: newPages };
        }
      );

      // Session updated_at may have changed (we bump it when updating message content).
      queryClient.invalidateQueries({ queryKey: chatSessionsKeys.lists() });
      queryClient.invalidateQueries({ queryKey: chatSessionsKeys.detail(sid) });
    },
    onError: (error: Error) => {
      toast.error('Failed to retry message', error.message);
    },
  });

  /**
   * Send a message to the current session.
   */
  const sendMessage = (message: string, mode?: QueryMode, imageFile?: File | null) => {
    if (!sessionId) {
      toast.error('No active session', 'Please create or select a chat session.');
      return;
    }
    const queryMode = mode || currentMode;
    sendMessageMutation.mutate({ message, mode: queryMode, imageFile });
  };

  /**
   * Change query mode.
   */
  const changeMode = (mode: QueryMode) => {
    setMode(mode);
  };

  /**
   * Stop an in-flight streaming request (best-effort).
   */
  const stopGenerating = () => {
    abortControllerRef.current?.abort();
  };

  /**
   * Retry (regenerate) a specific assistant message.
   */
  const retryAssistant = async (assistantMessageId: string) => {
    if (!sessionId) {
      toast.error('No active session', 'Please create or select a chat session.');
      return;
    }
    await retryAssistantMutation.mutateAsync({ assistantMessageId });
  };

  return {
    messages,
    isLoadingMessages,
    currentMode,
    sendMessage,
    changeMode,
    stopGenerating,
    retryAssistant,
    isSending: sendMessageMutation.isPending,
    isRetrying: retryAssistantMutation.isPending,
    // Pagination for loading older messages
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    refetchMessages: refetch,
  };
}

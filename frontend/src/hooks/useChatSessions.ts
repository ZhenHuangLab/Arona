/**
 * useChatSessions Hook
 *
 * React Query hooks for chat sessions and messages.
 * Provides data fetching, mutations, and optimistic updates.
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  useInfiniteQuery,
  type InfiniteData,
} from '@tanstack/react-query';
import {
  listSessions,
  createSession,
  updateSession,
  deleteSession,
  listMessages,
  getSession,
} from '@/api/chat';
import { toast } from '@/lib/toast';
import type {
  SessionListResponse,
  MessageListResponse,
  ChatMessage,
} from '@/types/chat';
import { dtosToUiMessages } from '@/types/chat';

// =============================================================================
// Query Keys
// =============================================================================

export const chatSessionsKeys = {
  all: ['chatSessions'] as const,
  lists: () => [...chatSessionsKeys.all, 'list'] as const,
  list: (params: { limit?: number; search?: string }) =>
    [...chatSessionsKeys.lists(), params] as const,
  detail: (id: string) => [...chatSessionsKeys.all, 'detail', id] as const,
};

export const chatMessagesKeys = {
  all: ['chatMessages'] as const,
  list: (sessionId: string) => [...chatMessagesKeys.all, sessionId] as const,
};

// =============================================================================
// Session List Hook (Infinite Query for pagination)
// =============================================================================

export interface UseChatSessionsOptions {
  limit?: number;
  search?: string;
  enabled?: boolean;
}

export function useChatSessions(options: UseChatSessionsOptions = {}) {
  const { limit = 20, search = '', enabled = true } = options;

  return useInfiniteQuery<
    SessionListResponse,
    Error,
    InfiniteData<SessionListResponse>,
    ReturnType<typeof chatSessionsKeys.list>,
    string | null
  >({
    queryKey: chatSessionsKeys.list({ limit, search }),
    queryFn: async ({ pageParam }) => {
      return listSessions({
        limit,
        cursor: pageParam,
        q: search || undefined,
      });
    },
    initialPageParam: null,
    getNextPageParam: (lastPage) =>
      lastPage.has_more ? lastPage.next_cursor : undefined,
    enabled,
    staleTime: 30_000, // 30 seconds
  });
}

// =============================================================================
// Single Session Hook
// =============================================================================

export function useChatSession(sessionId: string | undefined) {
  return useQuery({
    queryKey: chatSessionsKeys.detail(sessionId ?? ''),
    queryFn: () => getSession(sessionId!),
    enabled: !!sessionId,
    staleTime: 60_000,
  });
}

// =============================================================================
// Messages Hook (Infinite Query for pagination)
// =============================================================================

export interface UseChatMessagesOptions {
  limit?: number;
  enabled?: boolean;
}

export function useChatMessages(
  sessionId: string | undefined,
  options: UseChatMessagesOptions = {}
) {
  const { limit = 50, enabled = true } = options;

  return useInfiniteQuery<
    MessageListResponse,
    Error,
    InfiniteData<MessageListResponse>,
    ReturnType<typeof chatMessagesKeys.list>,
    string | null
  >({
    queryKey: chatMessagesKeys.list(sessionId ?? ''),
    queryFn: async ({ pageParam }) => {
      return listMessages(sessionId!, { limit, cursor: pageParam });
    },
    initialPageParam: null,
    getNextPageParam: (lastPage) =>
      lastPage.has_more ? lastPage.next_cursor : undefined,
    enabled: enabled && !!sessionId,
    staleTime: 10_000, // 10 seconds
  });
}

/**
 * Hook to get all messages as UI ChatMessage[] (flattened from infinite query pages).
 */
export function useChatMessagesFlat(sessionId: string | undefined) {
  const query = useChatMessages(sessionId);

  // Flatten all pages and convert DTOs to UI messages
  const messages: ChatMessage[] = query.data?.pages
    ? query.data.pages
        .slice()
        .reverse()
        .flatMap((page) => dtosToUiMessages(page.messages))
    : [];

  return {
    ...query,
    messages,
  };
}

// =============================================================================
// Session Mutations
// =============================================================================

export function useCreateSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (title?: string) => createSession({ title }),
    onSuccess: (newSession) => {
      // Invalidate sessions list to refetch
      queryClient.invalidateQueries({ queryKey: chatSessionsKeys.lists() });
      // Optionally add to cache immediately
      queryClient.setQueryData(chatSessionsKeys.detail(newSession.id), newSession);
    },
    onError: (error: Error) => {
      toast.error('Failed to create session', error.message);
    },
  });
}

export function useRenameSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sessionId, title }: { sessionId: string; title: string }) =>
      updateSession(sessionId, { title }),
    onMutate: async ({ sessionId, title }) => {
      // Cancel outgoing queries
      await queryClient.cancelQueries({ queryKey: chatSessionsKeys.lists() });

      // Optimistic update in the infinite query cache
      queryClient.setQueriesData<InfiniteData<SessionListResponse>>(
        { queryKey: chatSessionsKeys.lists() },
        (old) => {
          if (!old) return old;
          return {
            ...old,
            pages: old.pages.map((page) => ({
              ...page,
              sessions: page.sessions.map((s) =>
                s.id === sessionId ? { ...s, title } : s
              ),
            })),
          };
        }
      );
    },
    onSuccess: (updatedSession) => {
      queryClient.setQueryData(
        chatSessionsKeys.detail(updatedSession.id),
        updatedSession
      );
    },
    onError: (error: Error) => {
      // Rollback by invalidating
      queryClient.invalidateQueries({ queryKey: chatSessionsKeys.lists() });
      toast.error('Failed to rename session', error.message);
    },
  });
}

export function useDeleteSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sessionId, hard = false }: { sessionId: string; hard?: boolean }) =>
      deleteSession(sessionId, hard),
    onMutate: async ({ sessionId }) => {
      // Optimistic remove from list
      await queryClient.cancelQueries({ queryKey: chatSessionsKeys.lists() });

      const previousData = queryClient.getQueriesData<InfiniteData<SessionListResponse>>({
        queryKey: chatSessionsKeys.lists(),
      });

      queryClient.setQueriesData<InfiniteData<SessionListResponse>>(
        { queryKey: chatSessionsKeys.lists() },
        (old) => {
          if (!old) return old;
          return {
            ...old,
            pages: old.pages.map((page) => ({
              ...page,
              sessions: page.sessions.filter((s) => s.id !== sessionId),
            })),
          };
        }
      );

      return { previousData };
    },
    onSuccess: (data, { sessionId }) => {
      void data;
      // Remove from detail cache
      queryClient.removeQueries({ queryKey: chatSessionsKeys.detail(sessionId) });
      queryClient.removeQueries({ queryKey: chatMessagesKeys.list(sessionId) });
    },
    onError: (error: Error, variables, context) => {
      void variables;
      // Rollback
      if (context?.previousData) {
        context.previousData.forEach(([key, data]) => {
          if (data) {
            queryClient.setQueryData(key, data);
          }
        });
      }
      toast.error('Failed to delete session', error.message);
    },
  });
}

// =============================================================================
// Utility: Invalidate messages for a session
// =============================================================================

export function useInvalidateChatMessages() {
  const queryClient = useQueryClient();

  return (sessionId: string) => {
    queryClient.invalidateQueries({ queryKey: chatMessagesKeys.list(sessionId) });
  };
}

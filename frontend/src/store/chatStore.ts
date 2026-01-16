import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { QueryMode } from '../types/chat';

/**
 * Chat Store - UI-only state for chat interface
 *
 * Responsibilities:
 * - Store UI state (current mode, loading indicator)
 * - NO message persistence (messages now come from backend via React Query)
 *
 * Note: Messages are now managed by useChatSessions / useChatMessagesFlat hooks
 * using React Query, not Zustand.
 */
interface ChatState {
  currentMode: QueryMode;
  isLoading: boolean;

  // Actions
  setMode: (mode: QueryMode) => void;
  setLoading: (loading: boolean) => void;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      currentMode: 'hybrid',
      isLoading: false,

      setMode: (mode) => set({ currentMode: mode }),

      setLoading: (loading) => set({ isLoading: loading }),
    }),
    {
      name: 'rag-chat-ui-storage',
      partialize: (state) => ({
        currentMode: state.currentMode,
      }),
    }
  )
);

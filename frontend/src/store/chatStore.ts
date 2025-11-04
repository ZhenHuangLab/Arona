import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ChatMessage, QueryMode } from '../types/chat';

/**
 * Chat Store - Manages conversation state and history
 *
 * Responsibilities:
 * - Store conversation messages
 * - Add/remove messages
 * - Clear conversation
 * - Persist to localStorage
 */
interface ChatState {
  messages: ChatMessage[];
  currentMode: QueryMode;
  isLoading: boolean;

  // Actions
  addMessage: (message: ChatMessage) => void;
  updateLastMessage: (content: string) => void;
  clearMessages: () => void;
  setMode: (mode: QueryMode) => void;
  setLoading: (loading: boolean) => void;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      messages: [],
      currentMode: 'hybrid',
      isLoading: false,

      addMessage: (message) =>
        set((state) => ({
          messages: [...state.messages, {
            ...message,
            timestamp: message.timestamp || new Date().toISOString(),
          }],
        })),

      updateLastMessage: (content) =>
        set((state) => {
          const messages = [...state.messages];
          if (messages.length > 0) {
            messages[messages.length - 1] = {
              ...messages[messages.length - 1],
              content,
            };
          }
          return { messages };
        }),

      clearMessages: () => set({ messages: [] }),

      setMode: (mode) => set({ currentMode: mode }),

      setLoading: (loading) => set({ isLoading: loading }),
    }),
    {
      name: 'rag-chat-storage',
      partialize: (state) => ({
        messages: state.messages,
        currentMode: state.currentMode,
      }),
    }
  )
);


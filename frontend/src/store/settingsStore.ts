import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * Settings Store - Manages UI settings and preferences
 *
 * Responsibilities:
 * - Modal visibility state
 * - Theme preferences
 * - Current view mode (chat/document)
 * - Document sub-view (upload/graph/library)
 */
interface SettingsState {
  // Modal state
  isSettingsModalOpen: boolean;

  // View state
  currentView: 'chat' | 'document';
  documentSubView: 'upload' | 'graph' | 'library';

  // Theme
  theme: 'light' | 'dark' | 'system';

  // Actions
  openSettingsModal: () => void;
  closeSettingsModal: () => void;
  toggleSettingsModal: () => void;

  setCurrentView: (view: 'chat' | 'document') => void;
  setDocumentSubView: (subView: 'upload' | 'graph' | 'library') => void;

  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  toggleTheme: () => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      isSettingsModalOpen: false,
      currentView: 'chat',
      documentSubView: 'upload',
      theme: 'system',

      openSettingsModal: () => set({ isSettingsModalOpen: true }),
      closeSettingsModal: () => set({ isSettingsModalOpen: false }),
      toggleSettingsModal: () =>
        set((state) => ({ isSettingsModalOpen: !state.isSettingsModalOpen })),

      setCurrentView: (view) => set({ currentView: view }),
      setDocumentSubView: (subView) => set({ documentSubView: subView }),

      setTheme: (theme) => set({ theme }),
      toggleTheme: () =>
        set((state) => ({
          theme: state.theme === 'light' ? 'dark' : 'light',
        })),
    }),
    {
      name: 'rag-settings-storage',
      partialize: (state) => ({
        currentView: state.currentView,
        documentSubView: state.documentSubView,
        theme: state.theme,
      }),
    }
  )
);

/**
 * useChat Hook
 * 
 * Custom hook for chat operations with React Query integration.
 * Handles message sending, streaming responses, and conversation history.
 */

import { useMutation } from '@tanstack/react-query';
import { useChatStore } from '@/store/chatStore';
import { executeConversationQuery } from '@/api/query';
import { toast } from '@/lib/toast';
import type { QueryMode } from '@/types/chat';
import type { ConversationMessage } from '@/types/api';

/**
 * Convert ChatMessage to ConversationMessage for API
 */
const convertToAPIMessage = (message: { role: 'user' | 'assistant'; content: string; timestamp?: string }): ConversationMessage => {
  return {
    role: message.role,
    content: message.content,
    timestamp: message.timestamp,
  };
};

/**
 * Custom hook for chat functionality
 */
export function useChat() {
  const { messages, currentMode, isLoading, addMessage, setLoading, clearMessages, setMode } = useChatStore();

  const fileToDataURL = (file: File): Promise<string> =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || ''));
      reader.onerror = () => reject(new Error('Failed to read image file'));
      reader.readAsDataURL(file);
    });

  // Mutation for sending messages
  const sendMessageMutation = useMutation({
    mutationFn: async ({ message, mode, imageFile }: { message: string; mode: QueryMode; imageFile?: File | null }) => {
      // Add user message to store
      const displayMessage = imageFile ? `${message}\n[Attached image: ${imageFile.name}]` : message;
      addMessage({
        id: `user-${Date.now()}`,
        role: 'user',
        content: displayMessage,
        timestamp: new Date().toISOString(),
        mode,
      });

      // Convert messages to API format
      const history: ConversationMessage[] = messages.map(convertToAPIMessage);

      // Call API
      let multimodal_content: Array<{ type: 'image'; img_base64: string }> | undefined;
      if (imageFile) {
        // Basic client-side guard to avoid huge JSON payloads.
        const maxBytes = 8 * 1024 * 1024; // 8MB
        if (imageFile.size > maxBytes) {
          throw new Error(`Image too large (${Math.round(imageFile.size / 1024 / 1024)}MB). Please use an image <= 8MB.`);
        }
        const img_base64 = await fileToDataURL(imageFile);
        multimodal_content = [{ type: 'image', img_base64 }];
      }

      const response = await executeConversationQuery({
        query: message,
        history,
        mode,
        multimodal_content,
      });

      return response;
    },
    onMutate: () => {
      setLoading(true);
    },
    onSuccess: (response) => {
      // Add assistant response to store
      addMessage({
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.response,
        timestamp: new Date().toISOString(),
        mode: response.mode as QueryMode,
      });
      setLoading(false);
    },
    onError: (error: Error) => {
      // Add error message to store
      addMessage({
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: `Error: ${error.message}`,
        timestamp: new Date().toISOString(),
        error: true,
      });
      setLoading(false);
      toast.error('Failed to send message', error.message);
    },
  });

  /**
   * Send a message
   */
  const sendMessage = (message: string, mode?: QueryMode, imageFile?: File | null) => {
    const queryMode = mode || currentMode;
    sendMessageMutation.mutate({ message, mode: queryMode, imageFile });
  };

  /**
   * Clear conversation with confirmation
   */
  const clearConversation = () => {
    clearMessages();
    toast.success('Conversation cleared');
  };

  /**
   * Change query mode
   */
  const changeMode = (mode: QueryMode) => {
    setMode(mode);
  };

  return {
    messages,
    isLoading,
    currentMode,
    sendMessage,
    clearConversation,
    changeMode,
    isSending: sendMessageMutation.isPending,
  };
}

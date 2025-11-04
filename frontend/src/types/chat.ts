/**
 * Chat-related type definitions
 */

import type { QueryMode as APIQueryMode } from './api';

// Re-export QueryMode for convenience
export type QueryMode = APIQueryMode;

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  mode?: QueryMode;
  error?: boolean;
}

export interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  currentMode: QueryMode;
}

export interface ChatSettings {
  mode: QueryMode;
  top_k?: number;
  max_tokens?: number;
  temperature?: number;
}


/**
 * Chat-related type definitions
 *
 * Types aligned with backend models/chat.py for session-based chat.
 */

import type { QueryMode as APIQueryMode } from './api';

// Re-export QueryMode for convenience
export type QueryMode = APIQueryMode;

// =============================================================================
// Enums (matching backend)
// =============================================================================

export type MessageRole = 'user' | 'assistant' | 'system';

export type TurnStatus = 'pending' | 'completed' | 'failed';

// =============================================================================
// Backend-aligned types (ChatSession, ChatMessageDTO)
// =============================================================================

/**
 * Chat session from backend.
 */
export interface ChatSession {
  id: string;
  title: string;
  user_id?: string | null;
  created_at: string;
  updated_at: string;
  deleted_at?: string | null;
  metadata?: Record<string, unknown> | null;
}

/**
 * Chat session with computed stats (for list responses).
 */
export interface ChatSessionWithStats extends ChatSession {
  message_count: number;
  last_message_preview?: string | null;
}

/**
 * Chat message DTO from backend (matches backend ChatMessage).
 */
export interface ChatMessageDTO {
  id: string;
  session_id: string;
  role: MessageRole;
  content: string;
  token_count?: number | null;
  user_id?: string | null;
  created_at: string;
  metadata?: Record<string, unknown> | null;
}

/**
 * Error detail structure from backend.
 */
export interface ErrorDetail {
  code: string;
  message: string;
  extra?: Record<string, unknown> | null;
}

// =============================================================================
// Request types
// =============================================================================

export interface CreateSessionRequest {
  title?: string;
  metadata?: Record<string, unknown> | null;
}

export interface UpdateSessionRequest {
  title?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface MultimodalContent {
  img_base64?: string | null;
  img_mime_type?: string | null;
}

export interface TurnRequest {
  request_id: string;
  query: string;
  mode?: string;
  multimodal_content?: MultimodalContent | null;
  max_tokens?: number | null;
  temperature?: number | null;
  history_limit?: number;
  max_history_tokens?: number;
}

// =============================================================================
// Response types
// =============================================================================

export interface SessionListResponse {
  sessions: ChatSessionWithStats[];
  next_cursor?: string | null;
  has_more: boolean;
}

export interface MessageListResponse {
  messages: ChatMessageDTO[];
  next_cursor?: string | null;
  has_more: boolean;
}

export interface DeleteSessionResponse {
  id: string;
  deleted: boolean;
  hard: boolean;
  deleted_at?: string | null;
}

export interface TurnResponse {
  turn_id: string;
  status: TurnStatus;
  user_message: ChatMessageDTO;
  assistant_message?: ChatMessageDTO | null;
  error?: { code: string; message: string } | null;
}

// =============================================================================
// UI-level types (kept for existing components)
// =============================================================================

/**
 * UI ChatMessage - used by chat components.
 * Slightly different from backend ChatMessageDTO.
 */
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  mode?: QueryMode;
  error?: boolean;
  /** Indicates a placeholder message pending backend confirmation */
  pending?: boolean;
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

// =============================================================================
// Conversion utilities
// =============================================================================

/**
 * Convert backend ChatMessageDTO to UI ChatMessage.
 */
export function dtoToUiMessage(dto: ChatMessageDTO): ChatMessage {
  const role = dto.role === 'system' ? 'assistant' : dto.role;
  const mode = (dto.metadata?.mode as QueryMode) ?? undefined;
  return {
    id: dto.id,
    role,
    content: dto.content,
    timestamp: dto.created_at,
    mode,
    error: dto.metadata?.error === true,
    pending: dto.metadata?.pending === true,
  };
}

/**
 * Convert array of DTOs to UI messages.
 */
export function dtosToUiMessages(dtos: ChatMessageDTO[]): ChatMessage[] {
  return dtos.filter((d) => d.role !== 'system').map(dtoToUiMessage);
}

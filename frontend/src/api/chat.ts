/**
 * Chat API - /api/chat endpoints
 *
 * Wraps backend chat session and message endpoints with proper error handling.
 */

import apiClient from './client';
import { APIException } from '../types';
import type {
  ChatSession,
  SessionListResponse,
  MessageListResponse,
  TurnRequest,
  TurnResponse,
  CreateSessionRequest,
  UpdateSessionRequest,
  DeleteSessionResponse,
  ErrorDetail,
} from '../types/chat';

/**
 * Parse error detail from backend response.
 * Backend returns { detail: { code, message, extra } } for 4xx/5xx errors.
 */
function parseErrorDetail(data: unknown): string {
  if (!data || typeof data !== 'object') {
    return 'Unknown error';
  }
  const obj = data as Record<string, unknown>;
  const detail = obj.detail;
  if (typeof detail === 'string') {
    return detail;
  }
  if (detail && typeof detail === 'object') {
    const d = detail as ErrorDetail;
    return d.message || d.code || 'Unknown error';
  }
  return 'Unknown error';
}

/**
 * Wrap axios errors into APIException with readable messages.
 */
function handleAPIError(error: unknown): never {
  if (error instanceof APIException) {
    throw error;
  }
  // Axios errors have response property
  const axiosError = error as { response?: { status?: number; data?: unknown }; message?: string };
  if (axiosError.response) {
    const status = axiosError.response.status || 500;
    const message = parseErrorDetail(axiosError.response.data);
    throw new APIException(status, message);
  }
  throw new APIException(0, axiosError.message || 'Network error');
}

// =============================================================================
// Sessions
// =============================================================================

/**
 * Create a new chat session.
 */
export async function createSession(
  req: CreateSessionRequest = {}
): Promise<ChatSession> {
  try {
    const response = await apiClient.post<ChatSession>('/api/chat/sessions', req);
    return response.data;
  } catch (error) {
    handleAPIError(error);
  }
}

/**
 * List chat sessions with optional pagination and search.
 */
export async function listSessions(params: {
  limit?: number;
  cursor?: string | null;
  q?: string;
} = {}): Promise<SessionListResponse> {
  try {
    const response = await apiClient.get<SessionListResponse>('/api/chat/sessions', {
      params: {
        limit: params.limit ?? 20,
        cursor: params.cursor || undefined,
        q: params.q || undefined,
      },
    });
    return response.data;
  } catch (error) {
    handleAPIError(error);
  }
}

/**
 * Get a single session by ID.
 */
export async function getSession(sessionId: string): Promise<ChatSession> {
  try {
    const response = await apiClient.get<ChatSession>(`/api/chat/sessions/${sessionId}`);
    return response.data;
  } catch (error) {
    handleAPIError(error);
  }
}

/**
 * Update session (rename, metadata).
 */
export async function updateSession(
  sessionId: string,
  req: UpdateSessionRequest
): Promise<ChatSession> {
  try {
    const response = await apiClient.patch<ChatSession>(
      `/api/chat/sessions/${sessionId}`,
      req
    );
    return response.data;
  } catch (error) {
    handleAPIError(error);
  }
}

/**
 * Delete session (soft by default, hard if specified).
 */
export async function deleteSession(
  sessionId: string,
  hard: boolean = false
): Promise<DeleteSessionResponse> {
  try {
    const response = await apiClient.delete<DeleteSessionResponse>(
      `/api/chat/sessions/${sessionId}`,
      { params: { hard } }
    );
    return response.data;
  } catch (error) {
    handleAPIError(error);
  }
}

// =============================================================================
// Messages
// =============================================================================

/**
 * List messages for a session with optional pagination.
 */
export async function listMessages(
  sessionId: string,
  params: { limit?: number; cursor?: string | null } = {}
): Promise<MessageListResponse> {
  try {
    const response = await apiClient.get<MessageListResponse>(
      `/api/chat/sessions/${sessionId}/messages`,
      {
        params: {
          limit: params.limit ?? 50,
          cursor: params.cursor || undefined,
        },
      }
    );
    return response.data;
  } catch (error) {
    handleAPIError(error);
  }
}

// =============================================================================
// Turn
// =============================================================================

/**
 * Create a chat turn (user message -> assistant response).
 */
export async function createTurn(
  sessionId: string,
  req: TurnRequest
): Promise<TurnResponse> {
  try {
    const response = await apiClient.post<TurnResponse>(
      `/api/chat/sessions/${sessionId}/turn`,
      req
    );
    return response.data;
  } catch (error) {
    handleAPIError(error);
  }
}

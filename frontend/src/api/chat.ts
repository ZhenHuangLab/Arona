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
 * Search chat sessions by title or message content.
 */
export async function searchSessions(params: {
  q: string;
  limit?: number;
  cursor?: string | null;
}): Promise<SessionListResponse> {
  try {
    const response = await apiClient.get<SessionListResponse>('/api/chat/search', {
      params: {
        q: params.q,
        limit: params.limit ?? 20,
        cursor: params.cursor || undefined,
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
// Message Update (User Edit)
// =============================================================================

export interface UpdateMessageRequest {
  content: string;
}

/**
 * Update the latest user message content in-place.
 *
 * Backend enforces that only the latest turn's user message is editable to
 * avoid branching histories.
 */
export async function updateUserMessage(
  sessionId: string,
  messageId: string,
  req: UpdateMessageRequest
): Promise<MessageListResponse['messages'][number]> {
  try {
    const response = await apiClient.patch<MessageListResponse['messages'][number]>(
      `/api/chat/sessions/${sessionId}/messages/${messageId}`,
      req
    );
    return response.data;
  } catch (error) {
    handleAPIError(error);
  }
}

// =============================================================================
// Message (Retry / Regenerate)
// =============================================================================

export interface RetryAssistantMessageRequest {
  max_tokens?: number | null;
  temperature?: number | null;
  history_limit?: number;
  max_history_tokens?: number;
}

/**
 * Retry (regenerate) an assistant message in-place, storing variants history in metadata.
 */
export async function retryAssistantMessage(
  sessionId: string,
  assistantMessageId: string,
  req: RetryAssistantMessageRequest = {}
): Promise<MessageListResponse['messages'][number]> {
  try {
    const response = await apiClient.post<MessageListResponse['messages'][number]>(
      `/api/chat/sessions/${sessionId}/messages/${assistantMessageId}/retry`,
      req
    );
    return response.data;
  } catch (error) {
    handleAPIError(error);
  }
}

// =============================================================================
// Message Retry (Regenerate) - Streaming
// =============================================================================

export type RetryStreamEvent =
  | { type: 'delta'; delta: string }
  | { type: 'final'; message: MessageListResponse['messages'][number] }
  | { type: 'error'; error: { code: string; message: string } };

/**
 * Retry (regenerate) an assistant message with SSE streaming.
 *
 * Server emits `text/event-stream` with JSON `data:` lines:
 * - {"type":"delta","delta":"..."}
 * - {"type":"final","message":{...ChatMessage...}}
 * - {"type":"error","error":{"code":"...","message":"..."}}
 */
export async function* retryAssistantMessageStream(
  sessionId: string,
  assistantMessageId: string,
  req: RetryAssistantMessageRequest = {},
  options: { signal?: AbortSignal } = {}
): AsyncGenerator<RetryStreamEvent> {
  const baseURL = (apiClient.defaults.baseURL ?? '').replace(/\/$/, '');
  const url = `${baseURL}/api/chat/sessions/${sessionId}/messages/${assistantMessageId}/retry:stream`;

  const resp = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify(req),
    signal: options.signal,
  });

  if (!resp.ok) {
    // Try to parse backend error shape {detail:{code,message,...}}.
    let message = `${resp.status} ${resp.statusText}`.trim();
    try {
      const data = (await resp.json()) as unknown;
      message = parseErrorDetail(data);
    } catch {
      // ignore
    }
    throw new APIException(resp.status, message);
  }

  if (!resp.body) {
    throw new APIException(0, 'Streaming not supported by browser');
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE events are separated by a blank line.
    while (true) {
      const match = buffer.match(/\r?\n\r?\n/);
      if (!match || match.index == null) break;

      const sepIndex = match.index;
      const sepLen = match[0].length;

      const rawEvent = buffer.slice(0, sepIndex);
      buffer = buffer.slice(sepIndex + sepLen);

      const lines = rawEvent.split(/\r?\n/);
      const dataLines = lines
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.slice('data:'.length).trimStart());

      const data = dataLines.join('\n').trim();
      if (!data) continue;

      const event: unknown = JSON.parse(data);
      yield event as RetryStreamEvent;
    }
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

// =============================================================================
// Turn (Streaming)
// =============================================================================

export type TurnStreamEvent =
  | { type: 'delta'; delta: string }
  | { type: 'final'; response: TurnResponse };

/**
 * Create a chat turn with SSE streaming (user message -> assistant response).
 *
 * Server emits `text/event-stream` with JSON `data:` lines:
 * - {"type":"delta","delta":"..."}
 * - {"type":"final","response":{...TurnResponse...}}
 */
export async function* createTurnStream(
  sessionId: string,
  req: TurnRequest,
  options: { signal?: AbortSignal } = {}
): AsyncGenerator<TurnStreamEvent> {
  const baseURL = (apiClient.defaults.baseURL ?? '').replace(/\/$/, '');
  const url = `${baseURL}/api/chat/sessions/${sessionId}/turn:stream`;

  const resp = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify(req),
    signal: options.signal,
  });

  if (!resp.ok) {
    // Try to parse backend error shape {detail:{code,message,...}}.
    let message = `${resp.status} ${resp.statusText}`.trim();
    try {
      const data = (await resp.json()) as unknown;
      message = parseErrorDetail(data);
    } catch {
      // ignore
    }
    throw new APIException(resp.status, message);
  }

  if (!resp.body) {
    throw new APIException(0, 'Streaming not supported by browser');
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE events are separated by a blank line.
    while (true) {
      const match = buffer.match(/\r?\n\r?\n/);
      if (!match || match.index == null) break;

      const sepIndex = match.index;
      const sepLen = match[0].length;

      const rawEvent = buffer.slice(0, sepIndex);
      buffer = buffer.slice(sepIndex + sepLen);

      const lines = rawEvent.split(/\r?\n/);
      const dataLines = lines
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.slice('data:'.length).trimStart());

      const data = dataLines.join('\n').trim();
      if (!data) continue;

      const event: unknown = JSON.parse(data);
      yield event as TurnStreamEvent;
    }
  }
}

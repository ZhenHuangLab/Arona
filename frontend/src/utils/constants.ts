/**
 * Application Constants
 */

import type { QueryMode } from '../types';

// Query modes
export const QUERY_MODES: { value: QueryMode; label: string; description: string }[] = [
  {
    value: 'hybrid',
    label: 'Hybrid',
    description: 'Combines local and global search for best results',
  },
  {
    value: 'local',
    label: 'Local',
    description: 'Searches within specific document contexts',
  },
  {
    value: 'global',
    label: 'Global',
    description: 'Searches across the entire knowledge graph',
  },
  {
    value: 'naive',
    label: 'Naive',
    description: 'Simple keyword-based search',
  },
];

// Supported file types
export const SUPPORTED_FILE_TYPES = [
  '.pdf',
  '.docx',
  '.pptx',
  '.xlsx',
  '.txt',
  '.md',
  '.html',
];

export const SUPPORTED_FILE_TYPES_DISPLAY = 'PDF, DOCX, PPTX, XLSX, TXT, MD, HTML';

// File size limits (in bytes)
export const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB
export const MAX_FILE_SIZE_DISPLAY = '100MB';

// API timeouts
export const API_TIMEOUT_DEFAULT = 120000; // 2 minutes
export const API_TIMEOUT_UPLOAD = 300000; // 5 minutes

// Local storage keys
export const STORAGE_KEYS = {
  CHAT_HISTORY: 'rag-anything-chat-history',
  SETTINGS: 'rag-anything-settings',
  THEME: 'rag-anything-theme',
} as const;

// Default query settings
export const DEFAULT_QUERY_SETTINGS = {
  mode: 'hybrid' as QueryMode,
  top_k: 10,
  max_tokens: 2000,
  temperature: 0.7,
};

// UI Constants
export const CHAT_MESSAGE_MAX_HEIGHT = 600;
export const GRAPH_DEFAULT_NODE_LIMIT = 100;
export const GRAPH_MAX_NODE_LIMIT = 1000;

// Parse methods
export const PARSE_METHODS = [
  { value: 'auto', label: 'Auto' },
  { value: 'ocr', label: 'OCR' },
  { value: 'txt', label: 'Text' },
];

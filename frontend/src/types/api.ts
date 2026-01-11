/**
 * API Type Definitions
 * 
 * TypeScript interfaces matching backend Pydantic models
 */

// ============================================================================
// Health & Config Types
// ============================================================================

export interface HealthResponse {
  status: string;
  version: string;
  rag_initialized: boolean;
  models: Record<string, unknown>;
}

export interface ReadyResponse {
  ready: boolean;
  status: string;
}

export interface ConfigResponse {
  backend: {
    host: string;
    port: number;
    cors_origins: string[];
    env_file_loaded?: string | null;
  };
  models: {
    llm: ModelInfo;
    embedding: ModelInfo;
    vision?: ModelInfo;
    reranker?: RerankerInfo;
  };
  storage: {
    working_dir: string;
    upload_dir: string;
  };
  processing: {
    parser: string;
    enable_image_processing: boolean;
    enable_table_processing: boolean;
    enable_equation_processing: boolean;
  };
}

export interface ModelInfo {
  provider: string;
  model_name: string;
  base_url?: string;
  temperature?: number;
  max_tokens?: number;
  embedding_dim?: number;
  device?: string;
  dtype?: string;
  attn_implementation?: string;
  max_length?: number;
  default_instruction?: string;
  normalize?: boolean;
  allow_image_urls?: boolean;
  min_image_tokens?: number;
  max_image_tokens?: number;
}

export interface RerankerInfo {
  enabled: boolean;
  provider: string;
  model_name?: string;
  model_path?: string;
  device?: string;
  dtype?: string;
  attn_implementation?: string;
  batch_size?: number;
  max_length?: number;
  min_image_tokens?: number;
  max_image_tokens?: number;
  allow_image_urls?: boolean;
  base_url?: string;
}

export interface ConfigReloadRequest {
  config_files?: string[];
  apply?: boolean;
}

export interface ConfigReloadResponse {
  status: string;
  reloaded_files: string[];
  errors: Record<string, string>;
  message: string;
}

// ============================================================================
// Editable Model Config (UI → Backend)
// ============================================================================

export interface ModelConfigUpdate {
  provider?: string;
  model_name?: string;
  api_key?: string;
  base_url?: string;
  temperature?: number;
  max_tokens?: number;
  embedding_dim?: number;
  device?: string;
  dtype?: string;
  attn_implementation?: string;
  max_length?: number;
  default_instruction?: string;
  normalize?: boolean;
  allow_image_urls?: boolean;
  min_image_tokens?: number;
  max_image_tokens?: number;
}

export interface RerankerConfigUpdate {
  enabled?: boolean;
  provider?: string;
  model_name?: string;
  model_path?: string;
  device?: string;
  dtype?: string;
  attn_implementation?: string;
  batch_size?: number;
  max_length?: number;
  instruction?: string;
  system_prompt?: string;
  api_key?: string;
  base_url?: string;
  min_image_tokens?: number;
  max_image_tokens?: number;
  allow_image_urls?: boolean;
}

export interface ModelsUpdateRequest {
  llm?: ModelConfigUpdate;
  embedding?: ModelConfigUpdate;
  vision?: ModelConfigUpdate;
  multimodal_embedding?: ModelConfigUpdate;
  reranker?: RerankerConfigUpdate;
  apply?: boolean;
  target_env_file?: string;
}

export interface ModelsUpdateResponse {
  status: string;
  message: string;
  applied: boolean;
  env_file?: string;
  reloaded_components: string[];
  warnings: string[];
}

// ============================================================================
// Document Types
// ============================================================================

export interface DocumentUploadResponse {
  filename: string;
  file_path: string;
  file_size: number;
  content_type?: string;
}

export interface DocumentProcessRequest {
  file_path: string;
  parse_method?: string;
  output_dir?: string;
}

export interface DocumentProcessResponse {
  status: string;
  file_path: string;
  output_dir?: string;
  error?: string;
  metadata?: Record<string, unknown>;
}

export interface BatchProcessRequest {
  folder_path: string;
  file_extensions?: string[];
  recursive?: boolean;
  max_workers?: number;
  parse_method?: string;
}

export interface BatchProcessResponse {
  total_files: number;
  successful: number;
  failed: number;
  results: DocumentProcessResponse[];
}

export interface DocumentListResponse {
  documents: string[];
  total: number;
}

export interface DocumentDetailItem {
  filename: string;
  file_path: string;
  file_size: number;
  upload_date: string; // ISO 8601 datetime string from backend
  status: string;
  storage_location: string;
}

export interface DocumentDetailsResponse {
  documents: DocumentDetailItem[];
  total: number;
}

export interface DocumentDeleteResponse {
  status: string;
  message: string;
  trash_location: string;
  original_path: string;
}

// ============================================================================
// Query Types
// ============================================================================

export type QueryMode = 'naive' | 'local' | 'global' | 'hybrid';

export interface QueryRequest {
  query: string;
  mode?: QueryMode;
  top_k?: number;
  max_tokens?: number;
  temperature?: number;
}

export interface QueryResponse {
  query: string;
  response: string;
  mode: string;
  metadata?: Record<string, unknown>;
}

export interface MultimodalContent {
  type: 'text' | 'image' | 'table' | 'equation';
  content: string;
  metadata?: Record<string, unknown>;
}

export interface MultimodalQueryRequest {
  query: string;
  contents: MultimodalContent[];
  mode?: QueryMode;
  top_k?: number;
  max_tokens?: number;
  temperature?: number;
}

export interface ConversationMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
}

export interface ConversationRequest {
  query: string;
  history: ConversationMessage[];
  mode?: QueryMode;
  top_k?: number;
  max_tokens?: number;
  temperature?: number;
  multimodal_content?: Array<{
    type: 'image' | 'table' | 'equation';
    img_path?: string;
    img_base64?: string;
    image_caption?: string;
    table_data?: string;
    table_caption?: string;
    latex?: string;
    equation_caption?: string;
  }>;
}

export interface ConversationResponse {
  query: string;
  response: string;
  mode: string;
  history: ConversationMessage[];
  metadata?: Record<string, unknown>;
}

// ============================================================================
// Graph Types
// ============================================================================

export interface GraphNode {
  id: string;
  label: string;
  type?: string;
  description?: string;
  metadata?: Record<string, unknown>;
}

/**
 * GraphEdge interface
 *
 * Note: react-force-graph-2d mutates edge.source and edge.target at runtime:
 * - Initial state: source and target are strings (node IDs)
 * - After mutation: source and target become node object references with { id, ...nodeProps }
 *
 * The union type accurately represents both states for type safety.
 */
export interface GraphEdge {
  source: string | { id: string; [key: string]: any };
  target: string | { id: string; [key: string]: any };
  label: string;
  weight?: number;
  metadata?: Record<string, unknown>;
}

export interface GraphDataResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: Record<string, unknown>;
}

// ============================================================================
// API Error Types
// ============================================================================

export interface APIError {
  detail: string;
  status?: number;
}

export class APIException extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'APIException';
    this.status = status;
    this.detail = detail;
  }
}

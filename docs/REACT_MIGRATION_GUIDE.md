# React Frontend Migration Guide

## Executive Summary

This guide provides a comprehensive plan to migrate the RAG-Anything frontend from Gradio to a modern React + TypeScript stack using Vite, while keeping the FastAPI backend unchanged.

## Why Migrate?

### Current Gradio Limitations

1. **Icon Rendering Issues**: SVG icons display as raw HTML code in buttons
2. **Limited Customization**: Difficult to implement custom UI/UX
3. **Poor Mobile Support**: Not responsive on mobile devices
4. **Production Deployment**: Gradio is designed for prototyping, not production
5. **Complex Interactions**: Hard to implement advanced features

### React Benefits

1. **Full Control**: Complete control over UI/UX
2. **Better Icons**: Proper icon libraries (Lucide React)
3. **Mobile-First**: Responsive design with Tailwind CSS
4. **Production-Ready**: Optimized builds, code splitting, lazy loading
5. **Rich Ecosystem**: Vast library of components and tools
6. **Type Safety**: TypeScript for better DX and fewer bugs

---

## Tech Stack Recommendations

### Core Stack

| Category | Choice | Rationale |
|----------|--------|-----------|
| **Framework** | React 18.3+ | Industry standard, huge ecosystem, excellent performance |
| **Language** | TypeScript 5.3+ | Type safety, better IDE support, fewer runtime errors |
| **Build Tool** | Vite 5.0+ | Fast HMR, optimized builds, modern tooling |
| **UI Library** | shadcn/ui | Accessible, customizable, Tailwind-based, copy-paste components |
| **Styling** | Tailwind CSS 3.4+ | Utility-first, fast development, consistent design |
| **Icons** | Lucide React | Beautiful line icons, tree-shakeable, TypeScript support |

### State Management

| Purpose | Choice | Rationale |
|---------|--------|-----------|
| **Server State** | React Query (TanStack Query) | Caching, refetching, optimistic updates, devtools |
| **Client State** | Zustand | Simple, minimal boilerplate, TypeScript-friendly |
| **Form State** | React Hook Form + Zod | Performance, validation, TypeScript integration |

### Additional Libraries

| Purpose | Library | Rationale |
|---------|---------|-----------|
| **Routing** | React Router 6+ | Standard routing solution, type-safe |
| **HTTP Client** | Axios | Interceptors, request/response transformation |
| **Notifications** | Sonner | Beautiful toast notifications, accessible |
| **File Upload** | react-dropzone | Drag-and-drop, file validation |
| **Graph Viz** | React Flow | Interactive graph visualization, customizable |
| **Testing** | Vitest + RTL + Playwright | Fast unit tests, component tests, E2E tests |

---

## Project Structure

```
frontend-react/
├── public/
│   └── favicon.ico
├── src/
│   ├── api/                    # API client and endpoints
│   │   ├── client.ts           # Axios instance with interceptors
│   │   ├── documents.ts        # Document API calls
│   │   ├── query.ts            # Query API calls
│   │   ├── graph.ts            # Graph API calls
│   │   ├── config.ts           # Config API calls
│   │   └── health.ts           # Health check API calls
│   │
│   ├── components/             # React components
│   │   ├── ui/                 # shadcn/ui base components
│   │   │   ├── button.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── input.tsx
│   │   │   ├── dropdown-menu.tsx
│   │   │   └── ...
│   │   │
│   │   ├── layout/             # Layout components
│   │   │   ├── Header.tsx
│   │   │   ├── ModeSwitch.tsx
│   │   │   └── SettingsModal.tsx
│   │   │
│   │   ├── chat/               # Chat-related components
│   │   │   ├── ChatDialog.tsx
│   │   │   ├── Message.tsx
│   │   │   ├── InputBar.tsx
│   │   │   └── ModeSelector.tsx
│   │   │
│   │   ├── documents/          # Document management components
│   │   │   ├── UploadView.tsx
│   │   │   ├── FileUploader.tsx
│   │   │   ├── GraphView.tsx
│   │   │   └── LibraryView.tsx
│   │   │
│   │   └── common/             # Shared components
│   │       ├── LoadingSpinner.tsx
│   │       ├── ErrorBoundary.tsx
│   │       └── Toast.tsx
│   │
│   ├── hooks/                  # Custom React hooks
│   │   ├── useQuery.ts         # React Query hooks
│   │   ├── useDocuments.ts     # Document operations
│   │   ├── useGraph.ts         # Graph operations
│   │   ├── useConfig.ts        # Config operations
│   │   └── useChat.ts          # Chat operations
│   │
│   ├── store/                  # Zustand stores
│   │   ├── chatStore.ts        # Chat state (conversation history)
│   │   ├── settingsStore.ts    # Settings state (modal visibility)
│   │   └── index.ts            # Store exports
│   │
│   ├── types/                  # TypeScript type definitions
│   │   ├── api.ts              # API request/response types
│   │   ├── chat.ts             # Chat-related types
│   │   ├── document.ts         # Document types
│   │   └── graph.ts            # Graph types
│   │
│   ├── utils/                  # Utility functions
│   │   ├── constants.ts        # App constants
│   │   ├── formatters.ts       # Data formatters
│   │   └── validators.ts       # Validation functions
│   │
│   ├── views/                  # Page-level components
│   │   ├── ChatView.tsx        # Chat mode view
│   │   └── DocumentView.tsx    # Document viewer mode
│   │
│   ├── App.tsx                 # Root component
│   ├── main.tsx                # Entry point
│   └── index.css               # Global styles
│
├── .env.example                # Environment variables template
├── .eslintrc.cjs               # ESLint configuration
├── .prettierrc                 # Prettier configuration
├── index.html                  # HTML template
├── package.json                # Dependencies
├── tsconfig.json               # TypeScript config
├── tsconfig.node.json          # TypeScript config for Vite
├── vite.config.ts              # Vite configuration
└── README.md                   # Frontend documentation
```

---

## API Type Definitions

All backend API models need TypeScript equivalents. Here's the mapping:

### Health API

```typescript
// src/types/api.ts
export interface HealthResponse {
  status: string;
  version: string;
  rag_initialized: boolean;
  models: {
    llm?: ModelInfo;
    embedding?: ModelInfo;
    vision?: ModelInfo;
    reranker?: ModelInfo;
  };
}

export interface ModelInfo {
  provider: string;
  model_name: string;
  base_url?: string;
  [key: string]: any;
}
```

### Query API

```typescript
// src/types/api.ts
export interface QueryRequest {
  query: string;
  mode?: 'naive' | 'local' | 'global' | 'hybrid';
  top_k?: number;
  max_tokens?: number;
  temperature?: number;
}

export interface QueryResponse {
  query: string;
  response: string;
  mode: string;
  metadata?: Record<string, any>;
}

export interface ConversationMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

export interface ConversationRequest {
  query: string;
  history: ConversationMessage[];
  mode?: string;
  top_k?: number;
  max_tokens?: number;
  temperature?: number;
}

export interface ConversationResponse {
  query: string;
  response: string;
  mode: string;
  history: ConversationMessage[];
  metadata?: Record<string, any>;
}
```

### Document API

```typescript
// src/types/api.ts
export interface DocumentUploadResponse {
  filename: string;
  file_path: string;
  size: number;
  message: string;
}

export interface DocumentProcessRequest {
  file_path: string;
  output_dir?: string;
  parse_method?: string;
}

export interface DocumentProcessResponse {
  status: string;
  file_path: string;
  chunks_created?: number;
  message: string;
  error?: string;
}

export interface DocumentInfo {
  filename: string;
  file_path: string;
  size: number;
  status: string;
  chunks?: number;
  processed_at?: string;
}

export interface DocumentListResponse {
  documents: DocumentInfo[];
  total: number;
}
```

### Graph API

```typescript
// src/types/api.ts
export interface GraphNode {
  id: string;
  label: string;
  type: string;
  metadata?: Record<string, any>;
}

export interface GraphEdge {
  source: string;
  target: string;
  label: string;
  weight?: number;
  metadata?: Record<string, any>;
}

export interface GraphDataResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: {
    node_count: number;
    edge_count: number;
    [key: string]: any;
  };
}
```

### Config API

```typescript
// src/types/api.ts
export interface ConfigReloadRequest {
  config_files?: string[];
}

export interface ConfigReloadResponse {
  status: string;
  message: string;
  reloaded_files: string[];
}

export interface CurrentConfigResponse {
  backend: {
    host: string;
    port: number;
    cors_origins: string[];
  };
  models: {
    llm: ModelConfig;
    embedding: ModelConfig;
    vision?: ModelConfig;
    reranker?: RerankerConfig;
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

export interface ModelConfig {
  provider: string;
  model_name: string;
  base_url?: string;
  temperature?: number;
  max_tokens?: number;
  embedding_dim?: number;
}

export interface RerankerConfig {
  enabled: boolean;
  provider: string;
  model_name?: string;
  model_path?: string;
}
```

---

## Migration Strategy

### Phase 1: Parallel Development

1. **Keep Gradio Frontend Running**
   - Gradio stays at `frontend/app.py`
   - Runs on `http://localhost:7860`
   - Used for reference and testing

2. **Create React Frontend**
   - New directory: `frontend-react/`
   - Runs on `http://localhost:5173`
   - Both frontends share same backend

3. **Shared Backend**
   - Backend at `http://localhost:8000`
   - CORS already configured for all origins
   - No backend changes needed

### Phase 2: Feature Parity

Implement features incrementally, testing against Gradio:

1. **Week 1**: Project setup, core infrastructure
2. **Week 2**: Chat interface
3. **Week 3**: Document upload and library
4. **Week 4**: Knowledge graph visualization
5. **Week 5**: Settings and configuration
6. **Week 6**: Polish, testing, documentation

### Phase 3: Cutover

Once React frontend is complete:

1. **Backup Gradio**
   ```bash
   mv frontend frontend-gradio-legacy
   ```

2. **Promote React**
   ```bash
   mv frontend-react frontend
   ```

3. **Update Scripts**
   - Update `scripts/start_frontend.sh`
   - Update documentation
   - Update README

4. **Keep Rollback Option**
   - Keep `frontend-gradio-legacy/` for 1-2 months
   - Delete after React frontend is stable

---

## Development Workflow

### Initial Setup

```bash
# 1. Create React project
cd /path/to/RAG-Anything
npm create vite@latest frontend-react -- --template react-ts
cd frontend-react

# 2. Install dependencies
npm install

# 3. Install UI library (shadcn/ui)
npx shadcn-ui@latest init

# 4. Install additional packages
npm install \
  @tanstack/react-query \
  zustand \
  react-router-dom \
  axios \
  react-hook-form \
  zod \
  @hookform/resolvers \
  lucide-react \
  sonner \
  react-dropzone

# 5. Install dev dependencies
npm install -D \
  @types/node \
  @vitejs/plugin-react \
  autoprefixer \
  postcss \
  tailwindcss \
  eslint \
  prettier \
  vitest \
  @testing-library/react \
  @testing-library/jest-dom \
  @playwright/test
```

### Running Development Servers

```bash
# Terminal 1: Backend
cd backend
python main.py

# Terminal 2: React Frontend
cd frontend-react
npm run dev

# Terminal 3: Gradio Frontend (for comparison)
cd frontend
python app.py
```

### Environment Variables

Create `frontend-react/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_TITLE=RAG-Anything
VITE_APP_VERSION=2.0.0
```

---

## Key Implementation Details

### 1. API Client Setup

```typescript
// src/api/client.ts
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if needed
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle errors globally
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);
```

### 2. React Query Setup

```typescript
// src/main.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>
);
```

### 3. Zustand Store Example

```typescript
// src/store/chatStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ConversationMessage } from '@/types/api';

interface ChatState {
  messages: ConversationMessage[];
  addMessage: (message: ConversationMessage) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      messages: [],
      addMessage: (message) =>
        set((state) => ({ messages: [...state.messages, message] })),
      clearMessages: () => set({ messages: [] }),
    }),
    {
      name: 'chat-storage',
    }
  )
);
```

---

## Estimated Complexity

| Phase | Complexity | Time Estimate | Risk Level |
|-------|-----------|---------------|------------|
| P1: Project Setup | Low | 1-2 days | Low |
| P2: Core Infrastructure | Medium | 2-3 days | Low |
| P3: UI Components | Medium | 3-4 days | Low |
| P4: Chat Mode | Medium | 3-4 days | Medium |
| P5: Document Viewer | Medium | 4-5 days | Medium |
| P6: Settings | Low | 2-3 days | Low |
| P7: Polish | Medium | 3-4 days | Low |
| P8: Testing & Docs | Medium | 3-4 days | Low |
| **Total** | **Medium** | **3-4 weeks** | **Low-Medium** |

---

## Potential Challenges & Solutions

### Challenge 1: Icon Rendering
**Problem**: Gradio shows SVG as raw HTML  
**Solution**: Use Lucide React - proper React components for icons

### Challenge 2: File Upload Progress
**Problem**: Need real-time upload progress  
**Solution**: Axios upload progress events + React state

### Challenge 3: Graph Visualization
**Problem**: Complex interactive graph  
**Solution**: Use React Flow library with custom nodes

### Challenge 4: Conversation History
**Problem**: Persist chat across page reloads  
**Solution**: Zustand persist middleware with localStorage

### Challenge 5: Mobile Responsiveness
**Problem**: Gradio not mobile-friendly  
**Solution**: Tailwind responsive utilities + mobile-first design

---

## Next Steps

1. **Review and Approve Plan**: Confirm tech stack and approach
2. **Create Branch**: `git checkout -b feature/T2-react-frontend`
3. **Initialize Project**: Run Vite setup commands
4. **Start Phase 1**: Project setup and architecture
5. **Incremental Development**: Build features phase by phase
6. **Continuous Testing**: Test against Gradio and backend
7. **Documentation**: Update docs as we go
8. **Deployment**: Production build and deployment guide

---

## Questions to Answer

1. **UI Library**: Confirm shadcn/ui or prefer Ant Design/MUI?
2. **Graph Viz**: React Flow or D3.js for knowledge graph?
3. **Dark Mode**: Implement from start or later?
4. **Testing**: How much test coverage needed?
5. **Deployment**: Static hosting (Vercel/Netlify) or self-hosted?

Let me know your preferences and I'll proceed with implementation!


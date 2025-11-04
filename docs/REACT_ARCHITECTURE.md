# React Frontend Architecture

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              React Frontend (Port 5173)                   │ │
│  │                                                           │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │ │
│  │  │   Views     │  │ Components  │  │   Hooks     │      │ │
│  │  │             │  │             │  │             │      │ │
│  │  │ ChatView    │  │ ChatDialog  │  │ useChat     │      │ │
│  │  │ DocumentView│  │ FileUploader│  │ useDocuments│      │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘      │ │
│  │         │                 │                 │            │ │
│  │         └─────────────────┴─────────────────┘            │ │
│  │                           │                              │ │
│  │                  ┌────────▼────────┐                     │ │
│  │                  │  State Layer    │                     │ │
│  │                  │                 │                     │ │
│  │                  │ React Query     │ (Server State)      │ │
│  │                  │ Zustand         │ (Client State)      │ │
│  │                  └────────┬────────┘                     │ │
│  │                           │                              │ │
│  │                  ┌────────▼────────┐                     │ │
│  │                  │   API Client    │                     │ │
│  │                  │                 │                     │ │
│  │                  │ Axios Instance  │                     │ │
│  │                  │ Interceptors    │                     │ │
│  │                  └────────┬────────┘                     │ │
│  └───────────────────────────┼───────────────────────────────┘ │
│                              │                                 │
│                              │ HTTP/REST                       │
│                              │                                 │
└──────────────────────────────┼─────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (Port 8000)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Routers    │  │   Services   │  │   Models     │         │
│  │              │  │              │  │              │         │
│  │ /api/query   │  │ RAGService   │  │ QueryRequest │         │
│  │ /api/docs    │  │ ModelFactory │  │ QueryResponse│         │
│  │ /api/graph   │  │              │  │ ...          │         │
│  │ /health      │  │              │  │              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Hierarchy

```
App
├── QueryClientProvider (React Query)
│   └── Router
│       ├── Layout
│       │   ├── Header
│       │   │   ├── Logo
│       │   │   └── SettingsButton
│       │   │
│       │   ├── ModeSwitch
│       │   │   ├── ChatModeButton
│       │   │   └── DocumentModeButton
│       │   │
│       │   └── SettingsModal
│       │       ├── HealthCheck
│       │       ├── ConfigViewer
│       │       └── ConfigReloader
│       │
│       ├── Routes
│       │   ├── ChatView
│       │   │   └── ChatDialog
│       │   │       ├── Chatbot
│       │   │       │   └── Message[]
│       │   │       │       ├── UserMessage
│       │   │       │       └── AssistantMessage
│       │   │       │
│       │   │       └── InputBar
│       │   │           ├── ModeSelector
│       │   │           ├── QueryInput
│       │   │           ├── SendButton
│       │   │           └── ClearButton
│       │   │
│       │   └── DocumentView
│       │       ├── SecondaryMenu
│       │       │   ├── UploadButton
│       │       │   ├── GraphButton
│       │       │   └── LibraryButton
│       │       │
│       │       ├── UploadView
│       │       │   ├── FileUploader
│       │       │   │   ├── DropZone
│       │       │   │   └── FileList
│       │       │   └── UploadProgress
│       │       │
│       │       ├── GraphView
│       │       │   ├── GraphStats
│       │       │   └── GraphVisualization
│       │       │       └── ReactFlow
│       │       │
│       │       └── LibraryView
│       │           ├── DocumentList
│       │           │   └── DocumentCard[]
│       │           └── RefreshButton
│       │
│       └── Toaster (Notifications)
```

---

## Data Flow

### Query Flow (Chat)

```
User Input
    │
    ▼
InputBar Component
    │
    ├─> Validate Input
    │
    ├─> Update Local State (Zustand)
    │   └─> Add User Message to Chat
    │
    ├─> Call API Hook (React Query)
    │   └─> useChat.sendMessage()
    │       │
    │       ▼
    │   API Client (Axios)
    │       │
    │       ├─> POST /api/query/conversation
    │       │   {
    │       │     query: "...",
    │       │     history: [...],
    │       │     mode: "hybrid"
    │       │   }
    │       │
    │       ▼
    │   Backend API
    │       │
    │       ├─> Process Query
    │       ├─> Generate Response
    │       │
    │       ▼
    │   Response
    │       {
    │         query: "...",
    │         response: "...",
    │         history: [...]
    │       }
    │       │
    │       ▼
    │   React Query Cache
    │       │
    │       ├─> Update Cache
    │       ├─> Trigger Re-render
    │       │
    │       ▼
    │   Zustand Store
    │       │
    │       ├─> Add Assistant Message
    │       │
    │       ▼
    │   ChatDialog Component
    │       │
    │       └─> Render New Message
```

### Document Upload Flow

```
User Selects File
    │
    ▼
FileUploader Component
    │
    ├─> Validate File (type, size)
    │
    ├─> Show Preview
    │
    ├─> User Confirms Upload
    │
    ▼
useDocuments.uploadAndProcess()
    │
    ├─> Create FormData
    │
    ├─> Axios POST with Progress
    │   │
    │   ├─> onUploadProgress
    │   │   └─> Update Progress Bar
    │   │
    │   ▼
    │   POST /api/documents/upload-and-process
    │   FormData: { file: File }
    │   │
    │   ▼
    │   Backend Processing
    │   │
    │   ├─> Save File
    │   ├─> Parse Document
    │   ├─> Create Chunks
    │   ├─> Add to Knowledge Base
    │   │
    │   ▼
    │   Response
    │   {
    │     status: "success",
    │     file_path: "...",
    │     chunks_created: 42
    │   }
    │   │
    │   ▼
    │   React Query Cache
    │   │
    │   ├─> Invalidate Document List
    │   ├─> Show Success Toast
    │   │
    │   ▼
    │   UI Update
    │   └─> Show Success Message
```

---

## State Management

### Server State (React Query)

```typescript
// Managed by React Query
{
  queries: {
    'health': { data: HealthResponse, ... },
    'documents': { data: DocumentListResponse, ... },
    'graph-stats': { data: GraphDataResponse, ... },
    'config': { data: CurrentConfigResponse, ... }
  },
  mutations: {
    'send-message': { ... },
    'upload-document': { ... },
    'reload-config': { ... }
  }
}
```

**Benefits:**
- Automatic caching
- Background refetching
- Optimistic updates
- Loading/error states
- Devtools for debugging

### Client State (Zustand)

```typescript
// Chat Store
{
  messages: ConversationMessage[],
  addMessage: (msg) => void,
  clearMessages: () => void
}

// Settings Store
{
  isModalOpen: boolean,
  openModal: () => void,
  closeModal: () => void,
  currentMode: 'chat' | 'document',
  setMode: (mode) => void
}

// UI Store
{
  theme: 'light' | 'dark',
  toggleTheme: () => void,
  sidebarOpen: boolean,
  toggleSidebar: () => void
}
```

**Benefits:**
- Simple API
- No boilerplate
- TypeScript support
- Persist middleware (localStorage)

---

## API Integration

### API Client Structure

```typescript
// src/api/client.ts
export const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 30000
});

// src/api/query.ts
export const queryAPI = {
  sendQuery: (req: QueryRequest) => 
    apiClient.post<QueryResponse>('/api/query/', req),
  
  sendConversation: (req: ConversationRequest) =>
    apiClient.post<ConversationResponse>('/api/query/conversation', req)
};

// src/api/documents.ts
export const documentsAPI = {
  upload: (file: File) =>
    apiClient.post<DocumentUploadResponse>('/api/documents/upload', formData),
  
  list: () =>
    apiClient.get<DocumentListResponse>('/api/documents/list')
};

// src/api/graph.ts
export const graphAPI = {
  getData: (limit: number) =>
    apiClient.get<GraphDataResponse>('/api/graph/data', { params: { limit } })
};

// src/api/config.ts
export const configAPI = {
  getCurrent: () =>
    apiClient.get<CurrentConfigResponse>('/api/config/current'),
  
  reload: (files?: string[]) =>
    apiClient.post<ConfigReloadResponse>('/api/config/reload', { config_files: files })
};

// src/api/health.ts
export const healthAPI = {
  check: () =>
    apiClient.get<HealthResponse>('/health')
};
```

### React Query Hooks

```typescript
// src/hooks/useChat.ts
export const useChat = () => {
  const chatStore = useChatStore();
  
  const sendMessage = useMutation({
    mutationFn: (req: ConversationRequest) => 
      queryAPI.sendConversation(req),
    onSuccess: (data) => {
      chatStore.addMessage({
        role: 'assistant',
        content: data.response
      });
    }
  });
  
  return { sendMessage, messages: chatStore.messages };
};

// src/hooks/useDocuments.ts
export const useDocuments = () => {
  const listQuery = useQuery({
    queryKey: ['documents'],
    queryFn: () => documentsAPI.list()
  });
  
  const uploadMutation = useMutation({
    mutationFn: (file: File) => documentsAPI.upload(file),
    onSuccess: () => {
      queryClient.invalidateQueries(['documents']);
    }
  });
  
  return { documents: listQuery.data, upload: uploadMutation };
};
```

---

## Routing Structure

```typescript
// src/App.tsx
<BrowserRouter>
  <Routes>
    <Route path="/" element={<Layout />}>
      <Route index element={<Navigate to="/chat" />} />
      <Route path="chat" element={<ChatView />} />
      <Route path="documents" element={<DocumentView />}>
        <Route index element={<Navigate to="upload" />} />
        <Route path="upload" element={<UploadView />} />
        <Route path="graph" element={<GraphView />} />
        <Route path="library" element={<LibraryView />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Route>
  </Routes>
</BrowserRouter>
```

**URLs:**
- `/` → Redirect to `/chat`
- `/chat` → Chat interface
- `/documents/upload` → Document upload
- `/documents/graph` → Knowledge graph
- `/documents/library` → Document library

---

## Styling Architecture

### Tailwind CSS Utility Classes

```tsx
// Example: ChatDialog Component
<div className="max-w-[900px] mx-auto my-8 rounded-2xl border border-gray-200 bg-white shadow-lg">
  <div className="h-[500px] overflow-y-auto p-4 space-y-4">
    {messages.map(msg => (
      <div className={cn(
        "flex gap-3 p-3 rounded-lg",
        msg.role === 'user' 
          ? "bg-blue-50 ml-auto max-w-[80%]" 
          : "bg-gray-50 mr-auto max-w-[80%]"
      )}>
        {msg.content}
      </div>
    ))}
  </div>
</div>
```

### shadcn/ui Components

```tsx
// Example: Settings Modal
<Dialog open={isOpen} onOpenChange={setIsOpen}>
  <DialogContent className="sm:max-w-[600px]">
    <DialogHeader>
      <DialogTitle>Settings</DialogTitle>
    </DialogHeader>
    <div className="space-y-4">
      {/* Settings content */}
    </div>
  </DialogContent>
</Dialog>
```

### CSS Modules (Optional)

```css
/* ChatDialog.module.css */
.chatDialog {
  max-width: 900px;
  margin: 2rem auto;
  border-radius: 1rem;
}

.message {
  padding: 0.75rem;
  border-radius: 0.5rem;
}

.userMessage {
  background-color: var(--blue-50);
  margin-left: auto;
}

.assistantMessage {
  background-color: var(--gray-50);
  margin-right: auto;
}
```

---

## Performance Optimization

### Code Splitting

```typescript
// Lazy load views
const ChatView = lazy(() => import('./views/ChatView'));
const DocumentView = lazy(() => import('./views/DocumentView'));

// Lazy load heavy components
const GraphVisualization = lazy(() => import('./components/documents/GraphVisualization'));

// Usage with Suspense
<Suspense fallback={<LoadingSpinner />}>
  <ChatView />
</Suspense>
```

### React Query Optimization

```typescript
// Prefetch data on hover
const prefetchDocuments = () => {
  queryClient.prefetchQuery({
    queryKey: ['documents'],
    queryFn: () => documentsAPI.list()
  });
};

<Button onMouseEnter={prefetchDocuments}>
  Documents
</Button>
```

### Virtual Scrolling

```typescript
// For long message lists
import { useVirtualizer } from '@tanstack/react-virtual';

const virtualizer = useVirtualizer({
  count: messages.length,
  getScrollElement: () => scrollRef.current,
  estimateSize: () => 100
});
```

---

## Testing Strategy

### Unit Tests (Vitest)

```typescript
// src/components/chat/Message.test.tsx
describe('Message Component', () => {
  it('renders user message correctly', () => {
    render(<Message role="user" content="Hello" />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });
  
  it('applies correct styling for user message', () => {
    const { container } = render(<Message role="user" content="Hello" />);
    expect(container.firstChild).toHaveClass('bg-blue-50');
  });
});
```

### Integration Tests (React Testing Library)

```typescript
// src/views/ChatView.test.tsx
describe('ChatView', () => {
  it('sends message and displays response', async () => {
    render(<ChatView />);
    
    const input = screen.getByPlaceholderText('Ask a question...');
    const sendButton = screen.getByRole('button', { name: /send/i });
    
    await userEvent.type(input, 'What is RAG?');
    await userEvent.click(sendButton);
    
    await waitFor(() => {
      expect(screen.getByText(/RAG stands for/i)).toBeInTheDocument();
    });
  });
});
```

### E2E Tests (Playwright)

```typescript
// e2e/chat.spec.ts
test('complete chat flow', async ({ page }) => {
  await page.goto('http://localhost:5173');
  
  // Navigate to chat
  await page.click('text=Chat Mode');
  
  // Send message
  await page.fill('[placeholder="Ask a question..."]', 'Hello');
  await page.click('button[aria-label="Send"]');
  
  // Wait for response
  await page.waitForSelector('text=/Hello/i');
  
  // Verify response appears
  const response = await page.textContent('.assistant-message');
  expect(response).toBeTruthy();
});
```

---

## Deployment

### Build for Production

```bash
npm run build
```

**Output:**
```
dist/
├── index.html
├── assets/
│   ├── index-[hash].js      # ~200KB (gzipped)
│   ├── index-[hash].css     # ~20KB (gzipped)
│   └── vendor-[hash].js     # ~150KB (gzipped)
└── favicon.ico
```

### Deployment Options

#### Option 1: Vercel (Recommended)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

#### Option 2: Netlify

```bash
# Install Netlify CLI
npm i -g netlify-cli

# Deploy
netlify deploy --prod
```

#### Option 3: Static Hosting (Nginx)

```nginx
server {
    listen 80;
    server_name rag-anything.com;
    
    root /var/www/frontend-react/dist;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Summary

The React frontend architecture provides:

✅ **Clean Separation**: Views, Components, Hooks, API, State  
✅ **Type Safety**: TypeScript throughout  
✅ **Performance**: Code splitting, lazy loading, caching  
✅ **Maintainability**: Clear structure, reusable components  
✅ **Testability**: Unit, integration, E2E tests  
✅ **Scalability**: Easy to add features, optimize  

**Ready to build! 🚀**


# RAG-Anything React Frontend

Modern React frontend for RAG-Anything, built with React 19, TypeScript, and Vite.

## Tech Stack

- **React 19.1.1** - Latest React with concurrent features
- **TypeScript 5.9.3** - Type-safe development
- **Vite 7.1.7** - Lightning-fast build tool
- **shadcn/ui** - Beautiful, accessible UI components
- **Tailwind CSS 3.4+** - Utility-first CSS framework
- **React Query 5.90.6** - Powerful data fetching and caching
- **Zustand 5.0.8** - Lightweight state management
- **React Router 7.9.5** - Client-side routing
- **Lucide React** - Beautiful icon library

## Features

- ✅ **Chat Interface** - Interactive RAG query interface with conversation history
- ✅ **Document Management** - Upload, process, and manage documents
- ✅ **Graph Visualization** - Knowledge graph visualization
- ✅ **Settings Management** - Configure LLM, embedding, and reranking models
- ✅ **Dark Mode** - Full dark mode support
- ✅ **Responsive Design** - Mobile-friendly interface
- ✅ **Error Handling** - Comprehensive error boundaries and user feedback
- ✅ **Loading States** - Smooth loading indicators
- ✅ **Accessibility** - WCAG 2.1 compliant

## Getting Started

### Prerequisites

- Node.js 18+ or 20+
- npm 9+ or yarn 1.22+
- Backend API running on `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The app will be available at `http://localhost:5173`.

### Build for Production

```bash
# Build the app
npm run build

# Preview production build
npm run preview
```

## Development

### Project Structure

```
frontend-react/
├── src/
│   ├── api/              # API client and endpoints
│   ├── components/       # React components
│   │   ├── chat/        # Chat-related components
│   │   ├── common/      # Shared components
│   │   ├── documents/   # Document management
│   │   ├── layout/      # Layout components
│   │   ├── theme/       # Theme provider
│   │   └── ui/          # shadcn/ui components
│   ├── hooks/           # Custom React hooks
│   ├── store/           # Zustand stores
│   ├── types/           # TypeScript types
│   ├── utils/           # Utility functions
│   ├── views/           # Page components
│   └── __tests__/       # Test files
├── e2e/                 # Playwright E2E tests
└── public/              # Static assets
```

### Available Scripts

```bash
# Development
npm run dev              # Start dev server
npm run build            # Build for production
npm run preview          # Preview production build
npm run lint             # Run ESLint

# Testing
npm run test             # Run tests in watch mode
npm run test:ui          # Run tests with UI
npm run test:run         # Run tests once
npm run test:coverage    # Generate coverage report
npm run e2e              # Run E2E tests
npm run e2e:ui           # Run E2E tests with UI
npm run e2e:headed       # Run E2E tests in headed mode
```

## Testing

### Test Coverage

- **Unit Tests**: 39 tests covering components, hooks, and utilities
- **Integration Tests**: 29 tests covering API integration and data flows
- **E2E Tests**: 31 tests covering user journeys (requires dev server)
- **Total**: 99 tests
- **Pass Rate**: 100% ✅ (68/68 unit + integration tests passing)

### Running Tests

```bash
# Run all unit and integration tests
npm run test:run

# Run tests in watch mode
npm run test

# Run tests with UI
npm run test:ui

# Generate coverage report
npm run test:coverage

# Run E2E tests
npm run e2e
```

### Test Structure

```
src/__tests__/
├── setup.ts                    # Test setup and global mocks
├── utils/
│   └── test-utils.tsx         # Custom render function with providers
├── unit/
│   ├── components/            # Component tests
│   ├── hooks/                 # Hook tests
│   └── utils/                 # Utility tests
└── integration/               # Integration tests
    ├── api-client.test.ts
    ├── document-upload.test.ts
    └── query-flow.test.ts

e2e/                           # Playwright E2E tests
├── chat.spec.ts
├── documents.spec.ts
└── settings.spec.ts
```

## API Integration

The frontend connects to the FastAPI backend at `http://localhost:8000`.

### Environment Variables

Create a `.env` file in the root directory:

```env
VITE_API_BASE_URL=http://localhost:8000
```

### API Endpoints

- `POST /api/query/` - Execute RAG query
- `POST /api/query/conversation` - Conversational query
- `POST /api/query/multimodal` - Multimodal query
- `POST /api/documents/upload` - Upload document
- `POST /api/documents/process` - Process document
- `GET /api/documents/list` - List documents
- `GET /health` - Health check
- `GET /api/config` - Get configuration

## Deployment

For detailed deployment instructions, see [React Deployment Guide](../docs/deployment/REACT_DEPLOYMENT.md).

### Quick Deploy

**Docker**:
```bash
docker build -t rag-anything-frontend .
docker run -p 80:80 -e VITE_API_BASE_URL=https://api.your-domain.com rag-anything-frontend
```

**Static Hosting** (Vercel, Netlify, etc.):
```bash
npm run build
# Upload dist/ folder to your hosting service
```

**Environment Variables**:
- `VITE_API_BASE_URL`: Backend API URL (required)

## Contributing

1. Follow the existing code style
2. Write tests for new features
3. Update documentation as needed
4. Ensure all tests pass before submitting PR

## License

MIT License - see LICENSE file for details


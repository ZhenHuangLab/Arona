import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { Layout } from './components/layout/Layout';
import { LoadingSpinner } from './components/common/LoadingSpinner';

// Lazy load views for code splitting and better performance
const ChatView = lazy(() => import('./views/ChatView').then(m => ({ default: m.ChatView })));
const DocumentView = lazy(() => import('./views/DocumentView').then(m => ({ default: m.DocumentView })));
const GraphView = lazy(() => import('./views/GraphView').then(m => ({ default: m.GraphView })));
const LibraryView = lazy(() => import('./views/LibraryView').then(m => ({ default: m.LibraryView })));
const NotFound = lazy(() => import('./views/NotFound').then(m => ({ default: m.NotFound })));

/**
 * Loading Fallback Component
 *
 * Displays while lazy-loaded components are being fetched
 */
function LoadingFallback() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <LoadingSpinner size="lg" />
    </div>
  );
}

/**
 * App Component
 *
 * Root component with routing configuration and lazy loading
 *
 * Routes:
 * - / → Redirect to /chat
 * - /chat → Chat interface (lazy loaded)
 * - /chat/:sessionId → Chat session (lazy loaded, uses same ChatView)
 * - /documents → Document management (lazy loaded, with nested routes)
 *   - /documents/upload → Upload documents
 *   - /documents/graph → Knowledge graph visualization
 *   - /documents/library → Document library
 * - * → 404 Not Found
 *
 * Performance:
 * - Lazy loading for all route components
 * - Code splitting for optimal bundle size
 * - Suspense boundaries with loading fallbacks
 */
function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Suspense fallback={<LoadingFallback />}>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<Navigate to="/chat" replace />} />
              <Route path="chat" element={<ChatView />} />
              <Route path="chat/:sessionId" element={<ChatView />} />
              <Route path="documents" element={<DocumentView />}>
                <Route index element={<Navigate to="library" replace />} />
                <Route path="upload" element={<Navigate to="library" replace />} />
                <Route path="graph" element={<GraphView />} />
                <Route path="library" element={<LibraryView />} />
              </Route>
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </Suspense>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;

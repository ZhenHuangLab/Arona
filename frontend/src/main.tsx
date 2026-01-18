import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import { queryClient } from './lib/queryClient';
import { ThemeProvider } from './components/theme';
import './index.css';
import 'katex/dist/katex.min.css';
import App from './App.tsx';

/**
 * Application Entry Point
 *
 * Providers:
 * - ThemeProvider: Dark mode and theme management
 * - QueryClientProvider: React Query for server state management
 * - Toaster: Sonner toast notifications
 */
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="system">
      <QueryClientProvider client={queryClient}>
        <App />
        <Toaster
          position="top-right"
          expand={false}
          richColors
          closeButton
        />
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
);

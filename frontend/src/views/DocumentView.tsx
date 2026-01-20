import React from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { Library, Network } from 'lucide-react';

/**
 * Document View
 *
 * Main view for document management with nested routing.
 * Unified with ChatView styling for consistent AppShell experience.
 *
 * Features:
 * - Secondary navigation (Upload/Graph/Library)
 * - Nested routes for sub-views
 * - Responsive layout matching ChatView
 */
export const DocumentView: React.FC = () => {
  const location = useLocation();
  const isGraphActive = location.pathname.startsWith('/documents/graph');
  const isLibraryActive = location.pathname.startsWith('/documents/library');

  return (
    <div className="h-full flex flex-col bg-gradient-to-b from-background to-muted/20">
      {/* Scrollable Content Area */}
      <div className="flex-1 overflow-auto p-4 sm:p-6 pb-24">
        <div className="max-w-6xl mx-auto">
          <Outlet />
        </div>
      </div>

      {/* Bottom floating switcher (Graph/Library) */}
      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50">
        <div className="flex items-center gap-1 bg-background/95 backdrop-blur-sm border border-border rounded-full p-1 shadow-lg">
          <Link
            to="/documents/graph"
            aria-current={isGraphActive ? 'page' : undefined}
            className={`p-3 rounded-full transition-all ${
              isGraphActive
                ? 'bg-primary text-primary-foreground shadow-md'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted'
            }`}
            title="Knowledge graph"
          >
            <Network className="h-5 w-5" aria-hidden="true" />
            <span className="sr-only">Graph</span>
          </Link>
          <Link
            to="/documents/library"
            aria-current={isLibraryActive ? 'page' : undefined}
            className={`p-3 rounded-full transition-all ${
              isLibraryActive
                ? 'bg-primary text-primary-foreground shadow-md'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted'
            }`}
            title="Document library"
          >
            <Library className="h-5 w-5" aria-hidden="true" />
            <span className="sr-only">Library</span>
          </Link>
        </div>
      </div>
    </div>
  );
};

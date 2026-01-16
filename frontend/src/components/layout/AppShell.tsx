import { useEffect, useState, type ReactNode } from 'react';
import { PanelLeftOpen } from 'lucide-react';
import { Sidebar } from './Sidebar';
import { Button } from '@/components/ui/button';

/**
 * AppShell Component
 *
 * Full-height flex layout with fixed-width Sidebar and flexible main content area.
 *
 * Structure:
 * - Left: Sidebar (fixed width, full height)
 * - Right: Main content area (fills remaining width, scrollable)
 *
 * Accessibility:
 * - Main content has id="main-content" for SkipToContent link
 * - tabIndex={-1} allows programmatic focus
 */
interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.localStorage.getItem('arona.sidebar.collapsed') === '1';
  });

  useEffect(() => {
    try {
      window.localStorage.setItem('arona.sidebar.collapsed', isSidebarCollapsed ? '1' : '0');
    } catch {
      // ignore
    }
  }, [isSidebarCollapsed]);

  return (
    <div className="relative flex h-screen overflow-hidden bg-background">
      {!isSidebarCollapsed ? (
        <Sidebar onCollapse={() => setIsSidebarCollapsed(true)} />
      ) : null}
      <main
        id="main-content"
        tabIndex={-1}
        className={`flex-1 overflow-auto focus:outline-none ${isSidebarCollapsed ? 'pl-14' : ''}`}
      >
        {children}
      </main>

      {isSidebarCollapsed ? (
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="absolute left-3 top-3 z-50 h-10 w-10 rounded-full border bg-background/60 shadow-sm backdrop-blur-xl supports-[backdrop-filter]:bg-background/40"
          onClick={() => setIsSidebarCollapsed(false)}
          aria-label="Open sidebar"
        >
          <PanelLeftOpen className="h-5 w-5" aria-hidden="true" />
        </Button>
      ) : null}
    </div>
  );
}

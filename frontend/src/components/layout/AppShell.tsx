import { useEffect, useState, type ReactNode } from 'react';
import { Sidebar } from './Sidebar';
import { SidebarRail } from './SidebarRail';
import { cn } from '@/lib/utils';

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
    <div className="flex h-screen overflow-hidden bg-background">
      <div
        className={cn(
          'h-full flex-shrink-0 overflow-hidden transition-[width] duration-200 ease-in-out',
          isSidebarCollapsed ? 'w-14' : 'w-64'
        )}
      >
        {isSidebarCollapsed ? (
          <SidebarRail onExpand={() => setIsSidebarCollapsed(false)} />
        ) : (
          <Sidebar onCollapse={() => setIsSidebarCollapsed(true)} />
        )}
      </div>
      <main
        id="main-content"
        tabIndex={-1}
        className="flex-1 overflow-auto focus:outline-none"
      >
        {children}
      </main>
    </div>
  );
}

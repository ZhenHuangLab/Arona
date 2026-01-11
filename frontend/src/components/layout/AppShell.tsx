import { Sidebar } from './Sidebar';

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
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
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

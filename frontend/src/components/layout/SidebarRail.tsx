import { Link, useLocation } from 'react-router-dom';
import { FileText, MessageSquare, PanelLeftOpen } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { ThemeToggle } from '@/components/theme';
import { SettingsModal } from './SettingsModal';

interface SidebarRailProps {
  onExpand: () => void;
}

/**
 * SidebarRail Component
 *
 * Collapsed sidebar variant that still exposes primary navigation affordances.
 *
 * Requirements:
 * - Show Chat + Documents icons when sidebar is collapsed
 * - Provide a clear affordance to expand the full sidebar
 */
export function SidebarRail({ onExpand }: SidebarRailProps) {
  const location = useLocation();

  const isChatMode = location.pathname.startsWith('/chat');
  const isDocumentMode = location.pathname.startsWith('/documents');

  const navItemBase =
    'flex h-10 w-10 items-center justify-center rounded-xl transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';

  return (
    <aside className="flex flex-col w-14 border-r bg-background">
      {/* Top: Expand control */}
      <div className="p-2 border-b flex items-center justify-center">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="h-10 w-10 rounded-xl"
          onClick={onExpand}
          aria-label="Open sidebar"
          title="Open sidebar"
        >
          <PanelLeftOpen className="h-5 w-5" aria-hidden="true" />
        </Button>
      </div>

      {/* Primary navigation */}
      <nav className="flex-1 p-2 flex flex-col items-center gap-1" aria-label="Main navigation">
        <Link
          to="/chat"
          className={cn(
            navItemBase,
            isChatMode
              ? 'bg-primary text-primary-foreground hover:bg-primary/90'
              : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
          )}
          aria-current={isChatMode ? 'page' : undefined}
          title="Chat"
        >
          <MessageSquare className="h-5 w-5" aria-hidden="true" />
          <span className="sr-only">Chat</span>
        </Link>

        <Link
          to="/documents/library"
          className={cn(
            navItemBase,
            isDocumentMode
              ? 'bg-purple-600 text-white dark:bg-purple-700'
              : 'text-muted-foreground hover:bg-purple-100 hover:text-purple-700 dark:hover:bg-purple-950 dark:hover:text-purple-300'
          )}
          aria-current={isDocumentMode ? 'page' : undefined}
          title="Documents"
        >
          <FileText className="h-5 w-5" aria-hidden="true" />
          <span className="sr-only">Documents</span>
        </Link>
      </nav>

      {/* Bottom: Settings/theme still reachable */}
      <div className="p-2 border-t flex flex-col items-center gap-1">
        <ThemeToggle />
        <SettingsModal />
      </div>
    </aside>
  );
}

import { Link, useLocation } from 'react-router-dom';
import { MessageSquare, FileText, Plus, Search } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ThemeToggle } from '@/components/theme';
import { SettingsModal } from './SettingsModal';

/**
 * Sidebar Component
 *
 * Left sidebar with navigation, placeholder chat list, and user controls.
 *
 * Structure:
 * - Top: Logo/brand link
 * - Navigation: Chat and Documents links
 * - Middle: Placeholder Chats section (search + new chat button)
 * - Bottom: Theme toggle and Settings
 *
 * Accessibility:
 * - Semantic nav element with aria-label
 * - ARIA current for active navigation items
 * - Keyboard navigation support
 */
export function Sidebar() {
  const location = useLocation();
  const isChatMode = location.pathname.startsWith('/chat');
  const isDocumentMode = location.pathname.startsWith('/documents');

  return (
    <aside className="flex flex-col w-64 border-r bg-background">
      {/* Top: Logo/Brand */}
      <div className="p-4 border-b">
        <Link to="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
          <div className="h-8 w-8 bg-primary rounded-lg flex items-center justify-center">
            <span className="text-primary-foreground font-bold text-lg">A</span>
          </div>
          <span className="text-xl font-semibold tracking-tight">Arona</span>
        </Link>
      </div>

      {/* Navigation Links */}
      <nav className="p-3 space-y-1" aria-label="Main navigation">
        <Link
          to="/chat"
          className={cn(
            'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
            'hover:bg-accent hover:text-accent-foreground',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            isChatMode
              ? 'bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground'
              : 'text-muted-foreground'
          )}
          aria-current={isChatMode ? 'page' : undefined}
        >
          <MessageSquare className="h-4 w-4" aria-hidden="true" />
          Chat
        </Link>
        <Link
          to="/documents/library"
          className={cn(
            'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
            'hover:bg-purple-100 hover:text-purple-700 dark:hover:bg-purple-950 dark:hover:text-purple-300',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            isDocumentMode
              ? 'bg-purple-600 text-white dark:bg-purple-700'
              : 'text-muted-foreground'
          )}
          aria-current={isDocumentMode ? 'page' : undefined}
        >
          <FileText className="h-4 w-4" aria-hidden="true" />
          Documents
        </Link>
      </nav>

      {/* Placeholder Chats Section */}
      <div className="flex-1 overflow-auto p-3 border-t">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Chats
            </h2>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              aria-label="New chat"
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Search chats..."
              className="pl-8 h-9"
            />
          </div>
          {/* Placeholder for chat list - will be wired up in future phases */}
          <div className="text-xs text-muted-foreground text-center py-4">
            No conversations yet
          </div>
        </div>
      </div>

      {/* Bottom: User Area with Theme and Settings */}
      <div className="p-3 border-t">
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <SettingsModal />
        </div>
      </div>
    </aside>
  );
}

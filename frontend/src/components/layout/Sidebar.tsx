import { useState, useCallback, useRef, useEffect } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import {
  MessageSquare,
  FileText,
  Search,
  MoreHorizontal,
  Pencil,
  Trash2,
  Loader2,
  Check,
  X,
  PanelLeftClose,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ThemeToggle } from '@/components/theme';
import { SettingsModal } from './SettingsModal';
import { useChatSessions, useRenameSession, useDeleteSession } from '@/hooks';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { ChatSessionWithStats } from '@/types/chat';

/**
 * Sidebar Component
 *
 * Left sidebar with navigation, chat session list, and user controls.
 *
 * Features:
 * - Real chat sessions from backend
 * - Search with debounce
 * - New/Rename/Delete sessions
 * - Infinite scroll (load more)
 * - Active session highlighting
 */
interface SidebarProps {
  onCollapse?: () => void;
}

export function Sidebar({ onCollapse }: SidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { sessionId: activeSessionId } = useParams<{ sessionId?: string }>();

  const isChatMode = location.pathname.startsWith('/chat');
  const isDocumentMode = location.pathname.startsWith('/documents');

  // Search state with debounce
  const [searchInput, setSearchInput] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Update debounced search after 300ms
  useEffect(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    debounceTimerRef.current = setTimeout(() => {
      setDebouncedSearch(searchInput);
    }, 300);
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [searchInput]);

  // Fetch sessions
  const {
    data: sessionsData,
    isLoading: isLoadingSessions,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useChatSessions({ limit: 20, search: debouncedSearch });

  // Flatten pages into session list
  const sessions: ChatSessionWithStats[] =
    sessionsData?.pages.flatMap((page) => page.sessions) ?? [];

  // Mutations
  const renameSessionMutation = useRenameSession();
  const deleteSessionMutation = useDeleteSession();

  // Inline rename state
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const renameInputRef = useRef<HTMLInputElement>(null);

  // Handle rename start
  const handleStartRename = (session: ChatSessionWithStats) => {
    setRenamingId(session.id);
    setRenameValue(session.title);
    setTimeout(() => {
      renameInputRef.current?.focus();
      renameInputRef.current?.select();
    }, 0);
  };

  // Handle rename save
  const handleSaveRename = () => {
    if (renamingId && renameValue.trim()) {
      renameSessionMutation.mutate({ sessionId: renamingId, title: renameValue.trim() });
    }
    setRenamingId(null);
  };

  // Handle rename cancel
  const handleCancelRename = () => {
    setRenamingId(null);
  };

  // Handle delete
  const handleDelete = (sessionId: string) => {
    deleteSessionMutation.mutate({ sessionId });
    // If we deleted the active session, navigate to /chat
    if (activeSessionId === sessionId) {
      navigate('/chat');
    }
  };

  // Handle load more (scroll to bottom)
  const handleLoadMore = useCallback(() => {
    if (hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  // Scroll container ref for detecting scroll-to-bottom
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const handleScroll = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) return;
    const { scrollTop, scrollHeight, clientHeight } = container;
    // Load more when scrolled near bottom
    if (scrollHeight - scrollTop - clientHeight < 50) {
      handleLoadMore();
    }
  }, [handleLoadMore]);

  return (
    <aside className="flex flex-col w-64 border-r bg-background">
      {/* Top: Logo/Brand */}
      <div className="p-4 border-b flex items-center justify-between gap-2">
        <Link to="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity min-w-0">
          <div className="h-8 w-8 bg-primary rounded-lg flex items-center justify-center shrink-0">
            <span className="text-primary-foreground font-bold text-lg">A</span>
          </div>
          <span className="text-xl font-semibold tracking-tight truncate">Arona</span>
        </Link>
        {onCollapse ? (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0"
            onClick={onCollapse}
            aria-label="Collapse sidebar"
          >
            <PanelLeftClose className="h-5 w-5" aria-hidden="true" />
          </Button>
        ) : null}
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

      {/* Chats Section */}
      <div className="flex-1 overflow-hidden flex flex-col p-3 border-t">
        <div className="space-y-3 flex flex-col flex-1 min-h-0">
          <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider shrink-0">
            Chats
          </h2>

          {/* Search input */}
          <div className="relative shrink-0">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Search chats..."
              className="pl-8 h-9"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
            />
          </div>

          {/* Sessions list */}
          <div
            ref={scrollContainerRef}
            className="flex-1 overflow-y-auto space-y-1"
            onScroll={handleScroll}
          >
            {isLoadingSessions && sessions.length === 0 ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : sessions.length === 0 ? (
              <div className="text-xs text-muted-foreground text-center py-4">
                {debouncedSearch ? 'No matching chats' : 'No conversations yet'}
              </div>
            ) : (
              <>
                {sessions.map((session) => {
                  const isActive = activeSessionId === session.id;
                  const isRenaming = renamingId === session.id;

                  return (
                    <div
                      key={session.id}
                      className={cn(
                        'group flex items-center gap-2 px-2 py-1.5 rounded-md text-sm transition-colors',
                        isActive
                          ? 'bg-accent text-accent-foreground'
                          : 'hover:bg-muted text-foreground'
                      )}
                    >
                      {isRenaming ? (
                        <div className="flex-1 flex items-center gap-1">
                          <Input
                            ref={renameInputRef}
                            value={renameValue}
                            onChange={(e) => setRenameValue(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') handleSaveRename();
                              if (e.key === 'Escape') handleCancelRename();
                            }}
                            onBlur={handleSaveRename}
                            className="h-6 text-sm px-1"
                          />
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-5 w-5 shrink-0"
                            onClick={handleSaveRename}
                          >
                            <Check className="h-3 w-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-5 w-5 shrink-0"
                            onClick={handleCancelRename}
                          >
                            <X className="h-3 w-3" />
                          </Button>
                        </div>
                      ) : (
                        <>
                          <Link
                            to={`/chat/${session.id}`}
                            className="flex-1 truncate"
                            title={session.title}
                          >
                            {session.title}
                          </Link>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-6 w-6 opacity-0 group-hover:opacity-100 shrink-0"
                                aria-label="Session options"
                              >
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={() => handleStartRename(session)}>
                                <Pencil className="h-4 w-4 mr-2" />
                                Rename
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onClick={() => handleDelete(session.id)}
                                className="text-destructive focus:text-destructive"
                              >
                                <Trash2 className="h-4 w-4 mr-2" />
                                Delete
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </>
                      )}
                    </div>
                  );
                })}

                {/* Load more indicator */}
                {isFetchingNextPage && (
                  <div className="flex items-center justify-center py-2">
                    <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  </div>
                )}
              </>
            )}
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

import { MessageSquare, FileText } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';

/**
 * Mode Switch Component
 *
 * Rounded tab switcher for Chat/Documents modes.
 * Implements the minimalist design with rounded rectangles and color differentiation.
 *
 * Accessibility:
 * - Semantic navigation with <nav> element
 * - ARIA current for active tab
 * - Keyboard navigation support
 * - Clear visual feedback
 *
 * Mobile Responsive:
 * - Adaptive padding and spacing
 * - Touch-friendly button sizes
 * - Responsive text sizing
 */
export function ModeSwitch() {
  const location = useLocation();
  const isChatMode = location.pathname.startsWith('/chat');
  const isDocumentMode = location.pathname.startsWith('/documents');

  return (
    <nav className="flex justify-center gap-2 sm:gap-3 py-4 sm:py-8" aria-label="Main navigation">
      {/* Chat Mode Tab */}
      <Link
        to="/chat"
        className={cn(
          'inline-flex items-center gap-1.5 sm:gap-2 px-4 sm:px-6 py-2.5 sm:py-3 rounded-xl border-2 font-medium transition-all',
          'hover:border-primary/50 hover:bg-accent/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
          isChatMode
            ? 'bg-primary text-primary-foreground border-primary'
            : 'bg-background text-muted-foreground border-border'
        )}
        aria-current={isChatMode ? 'page' : undefined}
      >
        <MessageSquare className="h-4 w-4 sm:h-5 sm:w-5" aria-hidden="true" />
        <span className="text-sm sm:text-base">Chat</span>
      </Link>

      {/* Documents Mode Tab */}
      <Link
        to="/documents"
        className={cn(
          'inline-flex items-center gap-1.5 sm:gap-2 px-4 sm:px-6 py-2.5 sm:py-3 rounded-xl border-2 font-medium transition-all',
          'hover:border-purple-500/50 hover:bg-purple-50 dark:hover:bg-purple-950/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
          isDocumentMode
            ? 'bg-purple-600 text-white border-purple-600 dark:bg-purple-700 dark:border-purple-700'
            : 'bg-background text-muted-foreground border-border'
        )}
        aria-current={isDocumentMode ? 'page' : undefined}
      >
        <FileText className="h-4 w-4 sm:h-5 sm:w-5" aria-hidden="true" />
        <span className="text-sm sm:text-base">Documents</span>
      </Link>
    </nav>
  );
}

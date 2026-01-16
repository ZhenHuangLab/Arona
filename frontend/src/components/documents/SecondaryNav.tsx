import { Upload, Network, Library } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';

/**
 * Secondary Navigation Component
 *
 * Compact navigation tabs for document sub-views (Upload/Graph/Library).
 * Unified theme-aware styling to match AppShell visual system.
 */
export function SecondaryNav() {
  const location = useLocation();

  const tabs = [
    {
      path: '/documents/upload',
      label: 'Upload',
      icon: Upload,
    },
    {
      path: '/documents/graph',
      label: 'Graph',
      icon: Network,
    },
    {
      path: '/documents/library',
      label: 'Library',
      icon: Library,
    },
  ];

  return (
    <nav className="flex flex-wrap gap-1" aria-label="Document sections">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = location.pathname === tab.path;

        return (
          <Link
            key={tab.path}
            to={tab.path}
            aria-current={isActive ? 'page' : undefined}
            className={cn(
              'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium border border-transparent transition-colors',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
              isActive
                ? 'bg-background text-foreground border-border shadow-sm'
                : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
            )}
          >
            <Icon className="h-4 w-4" />
            <span>{tab.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

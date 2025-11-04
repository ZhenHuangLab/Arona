import { Upload, Network, Library } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';

/**
 * Secondary Navigation Component
 * 
 * Navigation tabs for document sub-views (Upload/Graph/Library).
 * Implements minimalist design with rounded tabs and color differentiation.
 */
export function SecondaryNav() {
  const location = useLocation();
  
  const tabs = [
    {
      path: '/documents/upload',
      label: 'Upload',
      icon: Upload,
      color: 'blue',
    },
    {
      path: '/documents/graph',
      label: 'Graph',
      icon: Network,
      color: 'purple',
    },
    {
      path: '/documents/library',
      label: 'Library',
      icon: Library,
      color: 'green',
    },
  ];

  return (
    <div className="flex justify-center gap-3 mb-8">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = location.pathname === tab.path;
        
        return (
          <Link
            key={tab.path}
            to={tab.path}
            className={cn(
              'inline-flex items-center gap-2 px-6 py-3 rounded-xl border-2 font-medium transition-all',
              isActive
                ? tab.color === 'blue'
                  ? 'bg-blue-600 text-white border-blue-600'
                  : tab.color === 'purple'
                  ? 'bg-purple-600 text-white border-purple-600'
                  : 'bg-green-600 text-white border-green-600'
                : 'bg-background text-muted-foreground border-border hover:border-gray-400 hover:bg-gray-50'
            )}
          >
            <Icon className="h-5 w-5" />
            <span>{tab.label}</span>
          </Link>
        );
      })}
    </div>
  );
}


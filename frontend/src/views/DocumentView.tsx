import React from 'react';
import { Outlet } from 'react-router-dom';
import { FileText } from 'lucide-react';
import { SecondaryNav } from '@/components/documents/SecondaryNav';

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
  return (
    <div className="h-full flex flex-col bg-gradient-to-b from-background to-muted/20">
      {/* Compact Header Bar with Navigation */}
      <div className="border-b bg-muted/50 px-3 sm:px-6 py-3 sm:py-4 shrink-0">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium">Documents</span>
          </div>
          <SecondaryNav />
        </div>
      </div>

      {/* Scrollable Content Area */}
      <div className="flex-1 overflow-auto p-4 sm:p-6">
        <div className="max-w-6xl mx-auto">
          <Outlet />
        </div>
      </div>
    </div>
  );
};

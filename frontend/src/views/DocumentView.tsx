import React from 'react';
import { Outlet } from 'react-router-dom';
import { FileText } from 'lucide-react';
import { SecondaryNav } from '@/components/documents/SecondaryNav';

/**
 * Document View
 *
 * Main view for document management with nested routing.
 *
 * Features:
 * - Secondary navigation (Upload/Graph/Library)
 * - Nested routes for sub-views
 * - Responsive layout
 */
export const DocumentView: React.FC = () => {
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-6">
          <div className="flex items-center justify-center gap-3 mb-2">
            <FileText className="h-8 w-8 text-purple-600" />
            <h1 className="text-3xl font-bold text-gray-900">Document Management</h1>
          </div>
          <p className="text-gray-600">Upload, visualize, and manage your documents</p>
        </div>

        {/* Secondary Navigation */}
        <SecondaryNav />

        {/* Nested routes render here */}
        <Outlet />
      </div>
    </div>
  );
};


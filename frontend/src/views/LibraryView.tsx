import React from 'react';
import { Library, Search, HardDrive, Database, Copy } from 'lucide-react';
import { DocumentCard, DocumentDetailsModal } from '@/components/documents';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { EmptyState, LoadingSpinner } from '@/components/common';
import { useDocuments } from '@/hooks/useDocuments';
import { useConfig } from '@/hooks/useConfig';
import { copyToClipboard } from '@/lib/clipboard';
import type { DocumentInfo } from '@/types/document';

/**
 * Library View
 *
 * Document library with list view and search.
 *
 * Features:
 * - Document list with cards
 * - Search/filter functionality
 * - Document status display
 * - Empty state handling
 * - Document details modal
 */
export const LibraryView: React.FC = () => {
  const { documents, isLoading } = useDocuments();
  const { config } = useConfig();
  const [searchQuery, setSearchQuery] = React.useState('');
  const [selectedDocument, setSelectedDocument] = React.useState<DocumentInfo | null>(null);
  const [detailsModalOpen, setDetailsModalOpen] = React.useState(false);

  const filteredDocuments = React.useMemo(() => {
    if (!documents) return [];
    if (!searchQuery) return documents;
    
    const query = searchQuery.toLowerCase();
    return documents.filter(doc =>
      doc.name.toLowerCase().includes(query) ||
      doc.type?.toLowerCase().includes(query)
    );
  }, [documents, searchQuery]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="p-6 bg-gradient-to-r from-green-50 to-emerald-50 border-green-200">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-green-600 rounded-lg">
            <Library className="h-6 w-6 text-white" />
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-bold text-gray-900 mb-2">
              Document Library
            </h2>
            <p className="text-gray-600 mb-4">
              Browse and manage your uploaded documents. All documents are indexed and ready for queries.
            </p>

            {/* Storage Directories */}
            {config?.storage && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4">
                {/* Upload Directory */}
                <div className="flex items-center gap-2 bg-white px-3 py-2 rounded-lg border border-green-200">
                  <HardDrive className="h-4 w-4 text-green-600 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-gray-700">Upload Directory</p>
                    <code className="text-xs text-gray-600 font-mono truncate block">
                      {config.storage.upload_dir}
                    </code>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => copyToClipboard(config.storage.upload_dir, 'Upload directory copied')}
                    className="flex-shrink-0 h-8 w-8 p-0"
                    title="Copy upload directory"
                  >
                    <Copy className="h-3 w-3" />
                  </Button>
                </div>

                {/* Working Directory */}
                <div className="flex items-center gap-2 bg-white px-3 py-2 rounded-lg border border-green-200">
                  <Database className="h-4 w-4 text-green-600 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-gray-700">Working Directory</p>
                    <code className="text-xs text-gray-600 font-mono truncate block">
                      {config.storage.working_dir}
                    </code>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => copyToClipboard(config.storage.working_dir, 'Working directory copied')}
                    className="flex-shrink-0 h-8 w-8 p-0"
                    title="Copy working directory"
                  >
                    <Copy className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* Search Bar */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
        <Input
          type="text"
          placeholder="Search documents by name or type..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Document List */}
      {isLoading ? (
        <Card className="p-12">
          <LoadingSpinner size="lg" text="Loading documents..." />
        </Card>
      ) : filteredDocuments.length === 0 ? (
        <Card className="p-12">
          {searchQuery ? (
            <EmptyState
              icon={Search}
              title="No documents found"
              description={`No documents match "${searchQuery}". Try a different search term.`}
            />
          ) : (
            <EmptyState
              icon={Library}
              title="No documents yet"
              description="Upload documents to get started. They will appear here once processed."
            />
          )}
        </Card>
      ) : (
        <>
          {/* Document Count */}
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-600">
              {filteredDocuments.length} {filteredDocuments.length === 1 ? 'document' : 'documents'}
              {searchQuery && ` matching "${searchQuery}"`}
            </p>
          </div>

          {/* Document Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredDocuments.map((doc) => (
              <DocumentCard
                key={doc.id}
                document={doc}
                onClick={() => {
                  setSelectedDocument(doc);
                  setDetailsModalOpen(true);
                }}
              />
            ))}
          </div>
        </>
      )}

      {/* Document Details Modal */}
      {selectedDocument && (
        <DocumentDetailsModal
          open={detailsModalOpen}
          onOpenChange={setDetailsModalOpen}
          document={selectedDocument}
        />
      )}
    </div>
  );
};


import React from 'react';
import { Library, Search, Upload, HardDrive, Database, Copy, RefreshCw, Settings, RotateCcw, LayoutGrid, List } from 'lucide-react';
import { DocumentCard, DocumentDetailsModal, FileUploader, DocumentListItem } from '@/components/documents';
import { IndexingSettingsDialog } from '@/components/documents/IndexingSettingsDialog';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import { EmptyState, LoadingSpinner } from '@/components/common';
import { useDocuments } from '@/hooks/useDocuments';
import { useConfig } from '@/hooks/useConfig';
import { useTriggerIndex, useReindexDocuments } from '@/hooks/useIndexingConfig';
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
  const { documents, isLoading, uploadAndProcess, isUploading } = useDocuments();
  const { config } = useConfig();
  const { triggerScan, isTriggering } = useTriggerIndex();
  const { reindex, isReindexing } = useReindexDocuments();
  const [searchQuery, setSearchQuery] = React.useState('');
  const [viewMode, setViewMode] = React.useState<'grid' | 'list'>(() => {
    try {
      return window.localStorage.getItem('arona.documents.library.view') === 'list' ? 'list' : 'grid';
    } catch {
      return 'grid';
    }
  });
  const [selectedDocument, setSelectedDocument] = React.useState<DocumentInfo | null>(null);
  const [detailsModalOpen, setDetailsModalOpen] = React.useState(false);
  const [settingsDialogOpen, setSettingsDialogOpen] = React.useState(false);
  const [uploadDialogOpen, setUploadDialogOpen] = React.useState(false);

  React.useEffect(() => {
    try {
      window.localStorage.setItem('arona.documents.library.view', viewMode);
    } catch {
      // ignore
    }
  }, [viewMode]);

  const filteredDocuments = React.useMemo(() => {
    if (!documents) return [];
    if (!searchQuery) return documents;

    const query = searchQuery.toLowerCase();
    return documents.filter(doc =>
      doc.name.toLowerCase().includes(query) ||
      doc.type?.toLowerCase().includes(query)
    );
  }, [documents, searchQuery]);

  const handleUpload = async (files: File[]) => {
    for (const file of files) {
      await uploadAndProcess(file);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <Library className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
          <h2 className="text-lg font-semibold">Library</h2>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setUploadDialogOpen(true)}
            className="gap-2"
            title="Upload documents"
          >
            <Upload className="h-4 w-4" aria-hidden="true" />
            Upload
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => triggerScan()}
            disabled={isTriggering}
            className="gap-2"
            title="Scan upload dir and process new files"
          >
            <RefreshCw className={`h-4 w-4 ${isTriggering ? 'animate-spin' : ''}`} aria-hidden="true" />
            Refresh
          </Button>

          {/* Re-index Dropdown Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                disabled={isReindexing}
                className="gap-2"
                title="Re-index documents"
              >
                <RotateCcw className={`h-4 w-4 ${isReindexing ? 'animate-spin' : ''}`} aria-hidden="true" />
                Re-index
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onClick={() => reindex({ force: false })}
                disabled={isReindexing}
              >
                <RotateCcw className="h-4 w-4 mr-2" />
                Re-index Failed Files
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => reindex({ force: true })}
                disabled={isReindexing}
                className="text-orange-600"
              >
                <RotateCcw className="h-4 w-4 mr-2" />
                Force Re-index All Files
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setSettingsDialogOpen(true)}
            className="gap-2"
            title="Indexing settings"
          >
            <Settings className="h-4 w-4" aria-hidden="true" />
            Settings
          </Button>
        </div>
      </div>

      {/* Upload Dialog (integrated from /documents/upload) */}
      <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Upload documents</DialogTitle>
            <DialogDescription>
              Drag & drop files here. They will be uploaded and processed automatically.
            </DialogDescription>
          </DialogHeader>
          <FileUploader
            onUpload={handleUpload}
            accept=".pdf,.txt,.md,.doc,.docx"
            multiple={true}
            maxSize={50}
            disabled={isUploading}
          />
        </DialogContent>
      </Dialog>

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

      {/* Storage Directories (compact) */}
      {config?.storage ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="flex items-center gap-2 rounded-lg border bg-card px-3 py-2">
            <HardDrive className="h-4 w-4 text-muted-foreground flex-shrink-0" aria-hidden="true" />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium">Upload directory</p>
              <code className="text-xs text-muted-foreground font-mono truncate block">
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
              <Copy className="h-3 w-3" aria-hidden="true" />
            </Button>
          </div>

          <div className="flex items-center gap-2 rounded-lg border bg-card px-3 py-2">
            <Database className="h-4 w-4 text-muted-foreground flex-shrink-0" aria-hidden="true" />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium">Working directory</p>
              <code className="text-xs text-muted-foreground font-mono truncate block">
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
              <Copy className="h-3 w-3" aria-hidden="true" />
            </Button>
          </div>
        </div>
      ) : null}

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
            <p className="text-sm text-muted-foreground">
              {filteredDocuments.length} {filteredDocuments.length === 1 ? 'document' : 'documents'}
              {searchQuery && ` matching "${searchQuery}"`}
            </p>
            <div className="flex items-center gap-1">
              <Button
                variant={viewMode === 'grid' ? 'secondary' : 'outline'}
                size="icon"
                className="h-9 w-9"
                onClick={() => setViewMode('grid')}
                aria-label="Grid view"
                title="Grid view"
              >
                <LayoutGrid className="h-4 w-4" aria-hidden="true" />
              </Button>
              <Button
                variant={viewMode === 'list' ? 'secondary' : 'outline'}
                size="icon"
                className="h-9 w-9"
                onClick={() => setViewMode('list')}
                aria-label="List view"
                title="List view"
              >
                <List className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
          </div>

          {viewMode === 'list' ? (
            <div className="space-y-2">
              {filteredDocuments.map((doc) => (
                <DocumentListItem
                  key={doc.id}
                  document={doc}
                  onClick={() => {
                    setSelectedDocument(doc);
                    setDetailsModalOpen(true);
                  }}
                />
              ))}
            </div>
          ) : (
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
          )}
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

      {/* Indexing Settings Dialog */}
      <IndexingSettingsDialog
        open={settingsDialogOpen}
        onOpenChange={setSettingsDialogOpen}
      />
    </div>
  );
};

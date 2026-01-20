import { useState } from 'react';
import { Calendar, FileText, FileType, RefreshCw, Trash2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ConfirmDeleteDialog } from './ConfirmDeleteDialog';
import { IndexStatusBadge } from './IndexStatusBadge';
import { useDocuments } from '@/hooks/useDocuments';
import { useIndexStatus } from '@/hooks/useIndexStatus';
import { useReindexDocuments } from '@/hooks/useIndexingConfig';
import type { DocumentInfo } from '@/types/document';

interface DocumentListItemProps {
  document: DocumentInfo;
  onClick?: () => void;
}

/**
 * DocumentListItem Component
 *
 * Compact document row for list view.
 * Keeps the most important metadata visible while minimizing vertical space.
 */
export function DocumentListItem({ document, onClick }: DocumentListItemProps) {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const { deleteDocument, isDeleting } = useDocuments();
  const { indexStatuses } = useIndexStatus();
  const { reindex, isReindexing } = useReindexDocuments();

  const indexStatus = indexStatuses.find(
    (status) => status.file_path === document.path
  );

  const formatDate = (date?: Date | string) => {
    if (!date) return 'Unknown';
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    return dateObj.toLocaleDateString();
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'Unknown';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  const handleDeleteConfirm = async () => {
    try {
      await deleteDocument(document.name);
      setDeleteDialogOpen(false);
    } catch (error) {
      console.error('Delete failed:', error);
    }
  };

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setDeleteDialogOpen(true);
  };

  const handleReindexClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    reindex({ file_paths: [document.path], force: true });
  };

  const showReindexButton = indexStatus &&
    (indexStatus.status === 'indexed' || indexStatus.status === 'failed');

  return (
    <>
      <div
        role="button"
        tabIndex={0}
        className="group flex items-center gap-3 rounded-lg border bg-card px-3 py-2 hover:bg-muted/40 transition-colors cursor-pointer"
        onClick={onClick}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onClick?.();
          }
        }}
      >
        <FileText className="h-5 w-5 text-muted-foreground flex-shrink-0" aria-hidden="true" />

        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="text-sm font-medium truncate">{document.name}</div>
              <div className="text-xs text-muted-foreground flex items-center gap-2 flex-wrap">
                <span className="inline-flex items-center gap-1">
                  <FileType className="h-3 w-3" aria-hidden="true" />
                  {document.type || 'Unknown type'}
                </span>
                {document.size ? <span>• {formatFileSize(document.size)}</span> : null}
                {document.uploadedAt ? (
                  <span className="inline-flex items-center gap-1">
                    • <Calendar className="h-3 w-3" aria-hidden="true" /> {formatDate(document.uploadedAt)}
                  </span>
                ) : null}
              </div>
            </div>

            <div className="flex items-center gap-2 flex-shrink-0">
              {document.status ? (
                <Badge
                  variant={
                    document.status === 'indexed' || document.status === 'success'
                      ? 'default'
                      : document.status === 'processing' || document.status === 'uploading'
                      ? 'secondary'
                      : document.status === 'uploaded' || document.status === 'pending'
                      ? 'outline'
                      : document.status === 'error'
                      ? 'destructive'
                      : 'outline'
                  }
                  className="text-xs"
                >
                  {document.status}
                </Badge>
              ) : null}

              {indexStatus ? (
                <IndexStatusBadge
                  status={indexStatus.status}
                  errorMessage={indexStatus.error_message}
                />
              ) : null}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1 flex-shrink-0">
          {showReindexButton ? (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-muted-foreground hover:text-blue-600"
              onClick={handleReindexClick}
              disabled={isReindexing}
              aria-label={`Re-index ${document.name}`}
              title="Re-index this document"
            >
              <RefreshCw className={`h-4 w-4 ${isReindexing ? 'animate-spin' : ''}`} />
            </Button>
          ) : null}
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-muted-foreground hover:text-destructive"
            onClick={handleDeleteClick}
            aria-label={`Delete ${document.name}`}
            title="Delete this document"
          >
            <Trash2 className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>
      </div>

      <ConfirmDeleteDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        documentName={document.name}
        onConfirm={handleDeleteConfirm}
        isDeleting={isDeleting}
      />
    </>
  );
}


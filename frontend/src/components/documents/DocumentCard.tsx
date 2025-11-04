import { useState } from 'react';
import { FileText, Calendar, FileType, Trash2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ConfirmDeleteDialog } from './ConfirmDeleteDialog';
import { useDocuments } from '@/hooks/useDocuments';
import type { DocumentInfo } from '@/types/document';

interface DocumentCardProps {
  document: DocumentInfo;
  onClick?: () => void;
}

/**
 * DocumentCard Component
 *
 * Displays document information in a card format.
 * Used in the document library view.
 *
 * Features:
 * - Click to view document details
 * - Delete button with confirmation dialog
 * - Status badge and metadata display
 */
export function DocumentCard({ document, onClick }: DocumentCardProps) {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const { deleteDocument, isDeleting } = useDocuments();
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

  // Handle delete confirmation
  const handleDeleteConfirm = async () => {
    try {
      await deleteDocument(document.name);
      setDeleteDialogOpen(false);
    } catch (error) {
      // Error is already handled by the mutation's onError callback
      console.error('Delete failed:', error);
    }
  };

  // Handle delete button click (stop propagation to prevent card onClick)
  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setDeleteDialogOpen(true);
  };

  return (
    <>
      <Card
        className="hover:shadow-md transition-shadow cursor-pointer relative"
        onClick={onClick}
      >
        <CardHeader className="pb-3">
          <CardTitle className="flex items-start gap-2 text-base pr-8">
            <FileText className="h-5 w-5 text-muted-foreground flex-shrink-0 mt-0.5" />
            <span className="flex-1 break-words">{document.name}</span>
          </CardTitle>
          {/* Delete button - positioned absolute top-right */}
          <Button
            variant="ghost"
            size="icon"
            className="absolute top-4 right-4 h-8 w-8 text-muted-foreground hover:text-destructive"
            onClick={handleDeleteClick}
            aria-label={`Delete ${document.name}`}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <FileType className="h-4 w-4" />
          <span>{document.type || 'Unknown type'}</span>
          {document.size && (
            <>
              <span>•</span>
              <span>{formatFileSize(document.size)}</span>
            </>
          )}
        </div>
        {document.uploadedAt && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Calendar className="h-4 w-4" />
            <span>Uploaded {formatDate(document.uploadedAt)}</span>
          </div>
        )}
        {document.status && (
          <div className="flex items-center gap-2">
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
            >
              {document.status}
            </Badge>
          </div>
        )}
      </CardContent>
    </Card>

    {/* Confirmation dialog for deletion */}
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


import { useState } from 'react';
import { FileText, HardDrive, Calendar, Database, Copy, Check } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { toast } from '@/lib/toast';
import type { DocumentInfo } from '@/types/document';

interface DocumentDetailsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  document: DocumentInfo;
}

/**
 * Document Details Modal Component
 *
 * Displays comprehensive document metadata in a modal dialog.
 * Follows minimalist design with clean layout and line-style icons.
 *
 * Features:
 * - Document metadata display (filename, size, date, status, location)
 * - Copy-to-clipboard functionality for storage path
 * - Accessible dialog with proper ARIA attributes
 * - Toast notifications for user feedback
 * - Responsive design with proper spacing
 */
export function DocumentDetailsModal({
  open,
  onOpenChange,
  document,
}: DocumentDetailsModalProps) {
  const [copied, setCopied] = useState(false);

  /**
   * Format file size to human-readable format
   * Reused from DocumentCard component
   */
  const formatFileSize = (bytes?: number): string => {
    if (!bytes) return 'Unknown';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  /**
   * Format date to localized string
   * Reused from DocumentCard component
   */
  const formatDate = (date?: Date | string): string => {
    if (!date) return 'Unknown';
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    return dateObj.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  /**
   * Copy storage path to clipboard
   * Uses modern Clipboard API with toast feedback
   */
  const handleCopyPath = async () => {
    try {
      await navigator.clipboard.writeText(document.path);
      setCopied(true);
      toast.success('Copied to clipboard', 'Storage path copied successfully');

      // Reset copied state after 2 seconds
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy to clipboard:', error);
      toast.error('Copy failed', 'Failed to copy storage path to clipboard');
    }
  };

  /**
   * Get badge variant based on document status
   * Matches DocumentCard status badge logic
   */
  const getStatusVariant = (status: string) => {
    if (status === 'indexed' || status === 'success') return 'default';
    if (status === 'processing' || status === 'uploading') return 'secondary';
    if (status === 'uploaded' || status === 'pending') return 'outline';
    if (status === 'error') return 'destructive';
    return 'outline';
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Document Details
          </DialogTitle>
          <DialogDescription>
            Comprehensive metadata for {document.name}
          </DialogDescription>
        </DialogHeader>

        <Separator />

        {/* Metadata Grid */}
        <div className="space-y-4">
          {/* Filename */}
          <div className="flex items-start gap-3">
            <div className="p-2 bg-muted rounded-lg">
              <FileText className="h-5 w-5 text-muted-foreground" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-muted-foreground mb-1">
                Filename
              </p>
              <p className="text-sm font-mono break-words">
                {document.name}
              </p>
            </div>
          </div>

          {/* File Size */}
          <div className="flex items-start gap-3">
            <div className="p-2 bg-muted rounded-lg">
              <HardDrive className="h-5 w-5 text-muted-foreground" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-muted-foreground mb-1">
                File Size
              </p>
              <p className="text-sm">
                {formatFileSize(document.size)}
                {document.size > 0 && (
                  <span className="text-muted-foreground ml-2">
                    ({document.size.toLocaleString()} bytes)
                  </span>
                )}
              </p>
            </div>
          </div>

          {/* Upload Date */}
          <div className="flex items-start gap-3">
            <div className="p-2 bg-muted rounded-lg">
              <Calendar className="h-5 w-5 text-muted-foreground" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-muted-foreground mb-1">
                Upload Date
              </p>
              <p className="text-sm">
                {formatDate(document.uploadedAt)}
              </p>
            </div>
          </div>

          {/* Status */}
          {document.status && (
            <div className="flex items-start gap-3">
              <div className="p-2 bg-muted rounded-lg">
                <Database className="h-5 w-5 text-muted-foreground" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-muted-foreground mb-1">
                  Status
                </p>
                <Badge variant={getStatusVariant(document.status)}>
                  {document.status}
                </Badge>
              </div>
            </div>
          )}

          {/* Storage Location */}
          <div className="flex items-start gap-3">
            <div className="p-2 bg-muted rounded-lg">
              <HardDrive className="h-5 w-5 text-muted-foreground" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-muted-foreground mb-1">
                Storage Location
              </p>
              <div className="flex items-start gap-2">
                <p className="text-sm font-mono break-all flex-1 bg-muted/50 p-2 rounded">
                  {document.path}
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCopyPath}
                  className="flex-shrink-0"
                  aria-label="Copy storage path to clipboard"
                >
                  {copied ? (
                    <>
                      <Check className="h-4 w-4 mr-2" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="h-4 w-4 mr-2" />
                      Copy
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>

          {/* File Type (if available) */}
          {document.type && (
            <div className="flex items-start gap-3">
              <div className="p-2 bg-muted rounded-lg">
                <FileText className="h-5 w-5 text-muted-foreground" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-muted-foreground mb-1">
                  File Type
                </p>
                <p className="text-sm uppercase">
                  {document.type}
                </p>
              </div>
            </div>
          )}
        </div>

        <Separator />

        {/* Footer */}
        <div className="flex justify-end">
          <Button variant="default" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Confirm Delete Dialog
 * 
 * Confirmation dialog for deleting documents.
 * Follows minimalist design with modal/popup pattern.
 * Uses AlertDialog for proper accessibility and destructive action UX.
 */

import { Trash2 } from 'lucide-react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

interface ConfirmDeleteDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  documentName: string;
  onConfirm: () => void;
  isDeleting: boolean;
}

/**
 * Dialog component for confirming document deletion
 * 
 * Features:
 * - Shows document name in confirmation message
 * - Disables confirm button while deleting
 * - Uses destructive button variant for delete action
 * - Proper ARIA attributes via AlertDialog
 * - Follows UX best practices for destructive actions
 */
export function ConfirmDeleteDialog({
  open,
  onOpenChange,
  documentName,
  onConfirm,
  isDeleting,
}: ConfirmDeleteDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <Trash2 className="h-5 w-5 text-destructive" />
            Delete document?
          </AlertDialogTitle>
          <AlertDialogDescription>
            Are you sure you want to delete <strong>{documentName}</strong>? 
            It will be moved to trash and can be recovered if needed.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            disabled={isDeleting}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {isDeleting ? 'Deleting...' : 'Delete'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}


import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { uploadAndProcessDocument, getDocumentDetails, deleteDocument as deleteDocumentAPI } from '@/api/documents';
import { toast } from '@/lib/toast';
import type { DocumentFile } from '@/types/document';

/**
 * useDocuments Hook
 * 
 * Custom hook for document operations with React Query.
 * 
 * Features:
 * - Upload and process documents
 * - List all documents
 * - Loading states
 * - Error handling with toast notifications
 * - Automatic cache invalidation
 */
export function useDocuments() {
  const queryClient = useQueryClient();

  // Query: Get document details
  const {
    data: documentsData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['documents'],
    queryFn: getDocumentDetails,
    staleTime: 30 * 1000, // 30 seconds
  });

  // Mutation: Upload and process document
  const uploadAndProcessMutation = useMutation({
    mutationFn: async (file: File) => {
      return uploadAndProcessDocument(file, 'auto', (progress) => {
        // Progress callback - could be used to update UI
        console.log(`Upload progress: ${progress}%`);
      });
    },
    onSuccess: (_data, file) => {
      toast.success('Document processed', `${file.name} has been uploaded and processed successfully`);
      // Invalidate documents list to refetch
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      // Invalidate graph data as it may have changed
      queryClient.invalidateQueries({ queryKey: ['graph'] });
    },
    onError: (error, file) => {
      const message = error instanceof Error ? error.message : 'Upload failed';
      toast.error('Upload failed', `Failed to upload ${file.name}: ${message}`);
    },
  });

  // Mutation: Delete document
  const deleteMutation = useMutation({
    mutationFn: async (filename: string) => {
      return deleteDocumentAPI(filename);
    },
    onSuccess: (data, filename) => {
      toast.success(
        'Document deleted',
        `${filename} has been moved to trash: ${data.trash_location}`
      );
      // Invalidate documents list to refetch
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      // Invalidate graph data as it may have changed
      queryClient.invalidateQueries({ queryKey: ['graph'] });
    },
    onError: (error, filename) => {
      const message = error instanceof Error ? error.message : 'Delete failed';
      toast.error('Delete failed', `Failed to delete ${filename}: ${message}`);
    },
  });

  // Transform API response to DocumentFile format
  // Note: Backend now returns detailed metadata from /details endpoint
  const documents: DocumentFile[] = documentsData?.documents?.map((detail) => {
    const fileExt = detail.filename.split('.').pop()?.toLowerCase() || '';

    return {
      id: detail.file_path,
      name: detail.filename,
      path: detail.file_path,
      size: detail.file_size,
      type: fileExt,
      status: detail.status as 'indexed' | 'uploaded' | 'processing' | 'error',
      uploadedAt: new Date(detail.upload_date),
    };
  }) || [];

  return {
    documents,
    isLoading,
    error,
    refetch,
    uploadAndProcess: uploadAndProcessMutation.mutateAsync,
    isUploading: uploadAndProcessMutation.isPending,
    deleteDocument: deleteMutation.mutateAsync,
    isDeleting: deleteMutation.isPending,
  };
}


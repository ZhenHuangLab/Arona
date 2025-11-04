import { useCallback, useState } from 'react';
import { Upload, File, X, CheckCircle2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface FileUploaderProps {
  onUpload: (files: File[]) => Promise<void>;
  accept?: string;
  multiple?: boolean;
  maxSize?: number; // in MB
  disabled?: boolean;
}

interface FileWithStatus {
  file: File;
  status: 'pending' | 'uploading' | 'success' | 'error';
  progress?: number;
  error?: string;
}

/**
 * FileUploader Component
 * 
 * Drag-and-drop file uploader with progress tracking.
 * Supports multiple files and displays upload status.
 */
export function FileUploader({
  onUpload,
  accept = '.pdf,.txt,.md,.doc,.docx',
  multiple = true,
  maxSize = 50, // 50MB default
  disabled = false,
}: FileUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [files, setFiles] = useState<FileWithStatus[]>([]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) {
      setIsDragging(true);
    }
  }, [disabled]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const validateFile = useCallback((file: File): string | null => {
    // Check file size
    if (file.size > maxSize * 1024 * 1024) {
      return `File size exceeds ${maxSize}MB`;
    }

    // Check file type
    if (accept) {
      const extensions = accept.split(',').map(ext => ext.trim());
      const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();
      if (!extensions.includes(fileExt)) {
        return `File type not supported. Accepted: ${accept}`;
      }
    }

    return null;
  }, [maxSize, accept]);

  const handleFiles = useCallback(async (fileList: FileList | null) => {
    if (!fileList || disabled) return;

    const newFiles: FileWithStatus[] = Array.from(fileList).map(file => ({
      file,
      status: 'pending' as const,
    }));

    // Validate files
    const validatedFiles = newFiles.map(item => {
      const error = validateFile(item.file);
      return error
        ? { ...item, status: 'error' as const, error }
        : item;
    });

    setFiles(prev => [...prev, ...validatedFiles]);

    // Upload valid files
    const validFiles = validatedFiles
      .filter(item => item.status === 'pending')
      .map(item => item.file);

    if (validFiles.length > 0) {
      try {
        // Update status to uploading
        setFiles(prev =>
          prev.map(item =>
            validFiles.includes(item.file)
              ? { ...item, status: 'uploading' as const }
              : item
          )
        );

        await onUpload(validFiles);

        // Update status to success
        setFiles(prev =>
          prev.map(item =>
            validFiles.includes(item.file)
              ? { ...item, status: 'success' as const }
              : item
          )
        );
      } catch (error) {
        // Update status to error
        setFiles(prev =>
          prev.map(item =>
            validFiles.includes(item.file)
              ? {
                  ...item,
                  status: 'error' as const,
                  error: error instanceof Error ? error.message : 'Upload failed',
                }
              : item
          )
        );
      }
    }
  }, [disabled, onUpload, validateFile]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  }, [handleFiles]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    handleFiles(e.target.files);
  }, [handleFiles]);

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-4">
      {/* Drop Zone */}
      <Card
        className={cn(
          'border-2 border-dashed transition-colors',
          isDragging && 'border-primary bg-primary/5',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="p-8 text-center">
          <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
          <h3 className="text-lg font-semibold mb-2">
            Drop files here or click to browse
          </h3>
          <p className="text-sm text-muted-foreground mb-4">
            Supported formats: {accept}
            <br />
            Maximum size: {maxSize}MB per file
          </p>
          <input
            type="file"
            id="file-upload"
            className="hidden"
            accept={accept}
            multiple={multiple}
            onChange={handleFileInput}
            disabled={disabled}
          />
          <Button asChild disabled={disabled}>
            <label htmlFor="file-upload" className="cursor-pointer">
              Select Files
            </label>
          </Button>
        </div>
      </Card>

      {/* File List */}
      {files.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-semibold">Files ({files.length})</h4>
          {files.map((item, index) => (
            <Card key={index} className="p-3">
              <div className="flex items-center gap-3">
                <File className="h-5 w-5 text-muted-foreground flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">
                    {item.file.name}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {(item.file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                  {item.error && (
                    <p className="text-xs text-destructive mt-1">{item.error}</p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {item.status === 'uploading' && (
                    <div className="h-5 w-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                  )}
                  {item.status === 'success' && (
                    <CheckCircle2 className="h-5 w-5 text-green-600" />
                  )}
                  {item.status === 'error' && (
                    <AlertCircle className="h-5 w-5 text-destructive" />
                  )}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => removeFile(index)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}


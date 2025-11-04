import React, { useState } from 'react';
import { Upload, CheckCircle2, HardDrive, Copy } from 'lucide-react';
import { FileUploader } from '@/components/documents';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useDocuments } from '@/hooks/useDocuments';
import { useConfig } from '@/hooks/useConfig';
import { copyToClipboard } from '@/lib/clipboard';

/**
 * Upload View
 *
 * Document upload interface with drag-and-drop support.
 *
 * Features:
 * - Drag-and-drop file upload
 * - Upload progress tracking
 * - Automatic processing after upload
 * - Success/error feedback
 * - Storage location display after upload
 */
export const UploadView: React.FC = () => {
  const { uploadAndProcess, isUploading } = useDocuments();
  const { config } = useConfig();
  const [lastUploadedFile, setLastUploadedFile] = useState<string | null>(null);

  const handleUpload = async (files: File[]) => {
    for (const file of files) {
      await uploadAndProcess(file);
      // Track last uploaded file for storage location display
      setLastUploadedFile(file.name);
    }
  };

  const handleCopyPath = () => {
    if (config?.storage.upload_dir) {
      copyToClipboard(config.storage.upload_dir, 'Upload directory copied');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="p-6 bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-blue-600 rounded-lg">
            <Upload className="h-6 w-6 text-white" />
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-bold text-gray-900 mb-2">
              Upload Documents
            </h2>
            <p className="text-gray-600 mb-4">
              Upload your documents to build a knowledge base. Supported formats include PDF, TXT, MD, DOC, and DOCX.
            </p>
            <div className="flex items-start gap-2 text-sm text-gray-700">
              <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">Automatic Processing</p>
                <p className="text-gray-600">
                  Documents are automatically processed and indexed after upload
                </p>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* File Uploader */}
      <FileUploader
        onUpload={handleUpload}
        accept=".pdf,.txt,.md,.doc,.docx"
        multiple={true}
        maxSize={50}
        disabled={isUploading}
      />

      {/* Storage Location Info (shown after upload) */}
      {lastUploadedFile && config?.storage.upload_dir && (
        <Card className="p-4 bg-gradient-to-r from-blue-50 to-cyan-50 border-blue-200">
          <div className="flex items-start gap-3">
            <div className="p-2 bg-blue-600 rounded-lg">
              <HardDrive className="h-5 w-5 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-semibold text-gray-900 mb-1">
                Storage Location
              </h3>
              <p className="text-xs text-gray-600 mb-2">
                File uploaded successfully: <span className="font-medium">{lastUploadedFile}</span>
              </p>
              <div className="flex items-center gap-2">
                <code className="flex-1 text-xs bg-white px-3 py-2 rounded border border-blue-200 text-gray-800 font-mono truncate">
                  {config.storage.upload_dir}
                </code>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCopyPath}
                  className="flex-shrink-0"
                  title="Copy path to clipboard"
                >
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Instructions */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-3">How it works</h3>
        <ol className="space-y-2 text-sm text-gray-600">
          <li className="flex gap-2">
            <span className="font-semibold text-gray-900">1.</span>
            <span>Select or drag files to the upload area</span>
          </li>
          <li className="flex gap-2">
            <span className="font-semibold text-gray-900">2.</span>
            <span>Files are uploaded and automatically processed</span>
          </li>
          <li className="flex gap-2">
            <span className="font-semibold text-gray-900">3.</span>
            <span>Content is extracted and indexed for RAG queries</span>
          </li>
          <li className="flex gap-2">
            <span className="font-semibold text-gray-900">4.</span>
            <span>View processed documents in the Library tab</span>
          </li>
        </ol>
      </Card>
    </div>
  );
};


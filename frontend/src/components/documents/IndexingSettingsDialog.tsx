/**
 * Indexing Settings Dialog
 * 
 * Modal dialog for configuring automatic background indexing settings.
 * Uses react-hook-form + zod for form validation.
 */

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Settings, Loader2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { useIndexingConfig, useUpdateIndexingConfig } from '@/hooks/useIndexingConfig';

/**
 * Form validation schema
 *
 * Validation rules:
 * - auto_indexing_enabled: boolean (required)
 * - indexing_scan_interval: number >= 1 (required)
 * - indexing_max_files_per_batch: number >= 1 (required)
 */
const formSchema = z.object({
  auto_indexing_enabled: z.boolean(),
  indexing_scan_interval: z.number().int().min(1, 'Scan interval must be at least 1 second'),
  indexing_max_files_per_batch: z.number().int().min(1, 'Max files per batch must be at least 1'),
});

type FormData = z.infer<typeof formSchema>;

interface IndexingSettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * Dialog component for configuring indexing settings
 * 
 * Features:
 * - Fetch current configuration on open
 * - Form validation with zod
 * - Switch for auto_indexing_enabled
 * - Number inputs for scan_interval and max_files_per_batch
 * - Submit updates configuration via PUT /api/config/indexing
 * - Success/error toast notifications
 * - Loading states during fetch and submit
 */
export function IndexingSettingsDialog({ open, onOpenChange }: IndexingSettingsDialogProps) {
  const { config, isLoading: isLoadingConfig } = useIndexingConfig();
  const { updateConfig, isUpdating } = useUpdateIndexingConfig();

  // Initialize form with react-hook-form + zod validation
  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    setValue,
    watch,
  } = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      auto_indexing_enabled: true,
      indexing_scan_interval: 60,
      indexing_max_files_per_batch: 5,
    },
  });

  // Watch the switch value for controlled component
  const autoIndexingEnabled = watch('auto_indexing_enabled');

  // Reset form with fetched config when dialog opens or config changes
  useEffect(() => {
    if (config && open) {
      reset({
        auto_indexing_enabled: config.auto_indexing_enabled,
        indexing_scan_interval: config.indexing_scan_interval,
        indexing_max_files_per_batch: config.indexing_max_files_per_batch,
      });
    }
  }, [config, open, reset]);

  /**
   * Handle form submission
   * Updates configuration and closes dialog on success
   */
  const onSubmit = (data: FormData) => {
    updateConfig(data, {
      onSuccess: () => {
        onOpenChange(false);
      },
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Indexing Settings
          </DialogTitle>
          <DialogDescription>
            Configure automatic background indexing for new and modified documents.
            Changes take effect immediately.
          </DialogDescription>
        </DialogHeader>

        {isLoadingConfig ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {/* Auto Indexing Enabled Switch */}
            <div className="flex items-center justify-between space-x-4">
              <div className="flex-1 space-y-1">
                <Label htmlFor="auto_indexing_enabled" className="text-sm font-medium">
                  Enable Auto Indexing
                </Label>
                <p className="text-xs text-muted-foreground">
                  Automatically scan and index new documents in the background
                </p>
              </div>
              <Switch
                id="auto_indexing_enabled"
                checked={autoIndexingEnabled}
                onCheckedChange={(checked) => setValue('auto_indexing_enabled', checked)}
                disabled={isUpdating}
              />
            </div>

            {/* Scan Interval Input */}
            <div className="space-y-2">
              <Label htmlFor="indexing_scan_interval" className="text-sm font-medium">
                Scan Interval (seconds)
              </Label>
              <Input
                id="indexing_scan_interval"
                type="number"
                min="1"
                step="1"
                {...register('indexing_scan_interval', { valueAsNumber: true })}
                disabled={isUpdating}
                className={errors.indexing_scan_interval ? 'border-destructive' : ''}
              />
              {errors.indexing_scan_interval && (
                <p className="text-xs text-destructive">
                  {errors.indexing_scan_interval.message}
                </p>
              )}
              <p className="text-xs text-muted-foreground">
                How often to scan the upload directory for new files (minimum: 1 second)
              </p>
            </div>

            {/* Max Files Per Batch Input */}
            <div className="space-y-2">
              <Label htmlFor="indexing_max_files_per_batch" className="text-sm font-medium">
                Max Files Per Batch
              </Label>
              <Input
                id="indexing_max_files_per_batch"
                type="number"
                min="1"
                step="1"
                {...register('indexing_max_files_per_batch', { valueAsNumber: true })}
                disabled={isUpdating}
                className={errors.indexing_max_files_per_batch ? 'border-destructive' : ''}
              />
              {errors.indexing_max_files_per_batch && (
                <p className="text-xs text-destructive">
                  {errors.indexing_max_files_per_batch.message}
                </p>
              )}
              <p className="text-xs text-muted-foreground">
                Maximum number of files to process per iteration (minimum: 1)
              </p>
            </div>

            {/* Action Buttons */}
            <div className="flex justify-end gap-3 pt-4 border-t">
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isUpdating}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isUpdating}>
                {isUpdating ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  'Save Changes'
                )}
              </Button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}


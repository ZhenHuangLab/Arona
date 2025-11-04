import { useState, useEffect } from 'react';
import { Settings, CheckCircle2, XCircle, Loader2, RefreshCw, AlertCircle, Server, Database } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { useQuery, useMutation } from '@tanstack/react-query';
import { healthApi, configApi } from '@/api';
import type { HealthResponse, ReadyResponse, ConfigResponse } from '@/types/api';
import { toast } from '@/lib/toast';

/**
 * Settings Modal Component
 *
 * Modal dialog for viewing backend health status and configuration.
 * Includes hot-reload functionality and comprehensive status display.
 *
 * Phase 6 Features:
 * - Backend health check with real-time status
 * - Readiness check for service availability
 * - Configuration viewer (read-only, no API keys)
 * - Hot-reload configuration without restart
 * - Visual indicators for health states
 */
export function SettingsModal() {
  const [open, setOpen] = useState(false);

  // Query backend health status
  const {
    data: healthData,
    isLoading: healthLoading,
    error: healthError,
    refetch: refetchHealth,
  } = useQuery<HealthResponse>({
    queryKey: ['health'],
    queryFn: healthApi.checkHealth,
    enabled: open,
    refetchInterval: open ? 5000 : false, // Auto-refresh every 5s when open
  });

  // Query backend readiness
  const {
    data: readyData,
    isLoading: readyLoading,
    error: readyError,
    refetch: refetchReady,
  } = useQuery<ReadyResponse>({
    queryKey: ['ready'],
    queryFn: healthApi.checkReady,
    enabled: open,
    refetchInterval: open ? 5000 : false,
  });

  // Query backend configuration
  const {
    data: configData,
    isLoading: configLoading,
    error: configError,
    refetch: refetchConfig,
  } = useQuery<ConfigResponse>({
    queryKey: ['config'],
    queryFn: configApi.getConfig,
    enabled: open,
  });

  // Hot-reload configuration mutation
  const reloadMutation = useMutation({
    mutationFn: configApi.reloadConfig,
    onSuccess: (data) => {
      if (data.status === 'success') {
        toast.success('Configuration Reloaded', data.message);
        refetchConfig();
      } else if (data.status === 'partial') {
        toast.warning('Partial Reload', data.message);
        refetchConfig();
      } else {
        toast.error('Reload Failed', data.message);
      }
    },
    onError: (error: Error) => {
      toast.error('Reload Failed', error.message);
    },
  });

  // Refresh all data on modal open
  useEffect(() => {
    if (open) {
      refetchHealth();
      refetchReady();
      refetchConfig();
    }
  }, [open, refetchHealth, refetchReady, refetchConfig]);

  const isHealthy = healthData?.status === 'healthy';
  const isReady = readyData?.ready === true;
  const isLoading = healthLoading || readyLoading || configLoading;

  const handleReloadConfig = () => {
    reloadMutation.mutate(undefined);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" className="h-9 w-9">
          <Settings className="h-5 w-5" />
          <span className="sr-only">Settings</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Settings & Configuration
          </DialogTitle>
          <DialogDescription>
            Backend health status, configuration details, and hot-reload controls
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Health Status Section */}
          <section>
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <Server className="h-4 w-4" />
              Backend Health
              {(healthLoading || readyLoading) && <Loader2 className="h-4 w-4 animate-spin" />}
            </h3>

            {healthError || readyError ? (
              <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
                <div className="flex items-center gap-2 text-sm text-destructive">
                  <XCircle className="h-5 w-5" />
                  <span className="font-medium">Failed to connect to backend</span>
                </div>
                <p className="text-xs text-muted-foreground mt-2 ml-7">
                  Make sure the backend server is running at the configured URL
                </p>
              </div>
            ) : healthData && readyData ? (
              <div className="rounded-lg border p-4 space-y-3">
                {/* Health Status */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {isHealthy ? (
                      <CheckCircle2 className="h-5 w-5 text-green-600" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-600" />
                    )}
                    <span className="font-medium">Health Status</span>
                  </div>
                  <Badge variant={isHealthy ? 'default' : 'destructive'}>
                    {healthData.status}
                  </Badge>
                </div>

                {/* Readiness Status */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {isReady ? (
                      <CheckCircle2 className="h-5 w-5 text-green-600" />
                    ) : (
                      <AlertCircle className="h-5 w-5 text-yellow-600" />
                    )}
                    <span className="font-medium">Readiness</span>
                  </div>
                  <Badge variant={isReady ? 'default' : 'secondary'}>
                    {readyData.status}
                  </Badge>
                </div>

                {/* Version and RAG Status */}
                <Separator />
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="text-muted-foreground">Version:</div>
                  <div className="font-mono text-xs">{healthData.version}</div>

                  <div className="text-muted-foreground">RAG Initialized:</div>
                  <div className="flex items-center gap-1">
                    {healthData.rag_initialized ? (
                      <>
                        <CheckCircle2 className="h-3 w-3 text-green-600" />
                        <span className="text-xs">Yes</span>
                      </>
                    ) : (
                      <>
                        <XCircle className="h-3 w-3 text-red-600" />
                        <span className="text-xs">No</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ) : null}
          </section>

          <Separator />

          {/* Configuration Section */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <Database className="h-4 w-4" />
                Configuration
                {configLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              </h3>
              <Button
                variant="outline"
                size="sm"
                onClick={handleReloadConfig}
                disabled={reloadMutation.isPending || configLoading}
              >
                {reloadMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <RefreshCw className="h-4 w-4 mr-2" />
                )}
                Hot Reload
              </Button>
            </div>

            {configError ? (
              <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
                <div className="text-sm text-destructive">Failed to load configuration</div>
              </div>
            ) : configData ? (
              <div className="space-y-3">
                {/* Backend Configuration */}
                <div className="rounded-lg border p-3 space-y-2">
                  <h4 className="text-sm font-medium flex items-center gap-2">
                    <Server className="h-3 w-3" />
                    Backend Server
                  </h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="text-muted-foreground">Host:</div>
                    <div className="font-mono text-xs">{configData.backend.host}</div>

                    <div className="text-muted-foreground">Port:</div>
                    <div className="font-mono text-xs">{configData.backend.port}</div>

                    <div className="text-muted-foreground">CORS Origins:</div>
                    <div className="font-mono text-xs truncate" title={configData.backend.cors_origins.join(', ')}>
                      {configData.backend.cors_origins.join(', ')}
                    </div>
                  </div>
                </div>

                {/* LLM Configuration */}
                <div className="rounded-lg border p-3 space-y-2">
                  <h4 className="text-sm font-medium">LLM Provider</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="text-muted-foreground">Provider:</div>
                    <div className="font-mono text-xs">{configData.models.llm.provider}</div>

                    <div className="text-muted-foreground">Model:</div>
                    <div className="font-mono text-xs">{configData.models.llm.model_name}</div>

                    {configData.models.llm.base_url && (
                      <>
                        <div className="text-muted-foreground">Base URL:</div>
                        <div className="font-mono text-xs truncate" title={configData.models.llm.base_url}>
                          {configData.models.llm.base_url}
                        </div>
                      </>
                    )}

                    {configData.models.llm.temperature !== undefined && (
                      <>
                        <div className="text-muted-foreground">Temperature:</div>
                        <div className="font-mono text-xs">{configData.models.llm.temperature}</div>
                      </>
                    )}

                    {configData.models.llm.max_tokens !== undefined && (
                      <>
                        <div className="text-muted-foreground">Max Tokens:</div>
                        <div className="font-mono text-xs">{configData.models.llm.max_tokens}</div>
                      </>
                    )}
                  </div>
                </div>

                {/* Embedding Configuration */}
                <div className="rounded-lg border p-3 space-y-2">
                  <h4 className="text-sm font-medium">Embedding Model</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="text-muted-foreground">Provider:</div>
                    <div className="font-mono text-xs">{configData.models.embedding.provider}</div>

                    <div className="text-muted-foreground">Model:</div>
                    <div className="font-mono text-xs">{configData.models.embedding.model_name}</div>

                    {configData.models.embedding.base_url && (
                      <>
                        <div className="text-muted-foreground">Base URL:</div>
                        <div className="font-mono text-xs truncate" title={configData.models.embedding.base_url}>
                          {configData.models.embedding.base_url}
                        </div>
                      </>
                    )}

                    {configData.models.embedding.embedding_dim !== undefined && (
                      <>
                        <div className="text-muted-foreground">Dimension:</div>
                        <div className="font-mono text-xs">{configData.models.embedding.embedding_dim}</div>
                      </>
                    )}
                  </div>
                </div>

                {/* Vision Model (if configured) */}
                {configData.models.vision && (
                  <div className="rounded-lg border p-3 space-y-2">
                    <h4 className="text-sm font-medium">Vision Model</h4>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div className="text-muted-foreground">Provider:</div>
                      <div className="font-mono text-xs">{configData.models.vision.provider}</div>

                      <div className="text-muted-foreground">Model:</div>
                      <div className="font-mono text-xs">{configData.models.vision.model_name}</div>

                      {configData.models.vision.base_url && (
                        <>
                          <div className="text-muted-foreground">Base URL:</div>
                          <div className="font-mono text-xs truncate" title={configData.models.vision.base_url}>
                            {configData.models.vision.base_url}
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                )}

                {/* Reranker (if configured) */}
                {configData.models.reranker && configData.models.reranker.enabled && (
                  <div className="rounded-lg border p-3 space-y-2">
                    <h4 className="text-sm font-medium">Reranker</h4>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div className="text-muted-foreground">Provider:</div>
                      <div className="font-mono text-xs">{configData.models.reranker.provider}</div>

                      {configData.models.reranker.model_name && (
                        <>
                          <div className="text-muted-foreground">Model:</div>
                          <div className="font-mono text-xs">{configData.models.reranker.model_name}</div>
                        </>
                      )}

                      {configData.models.reranker.model_path && (
                        <>
                          <div className="text-muted-foreground">Model Path:</div>
                          <div className="font-mono text-xs truncate" title={configData.models.reranker.model_path}>
                            {configData.models.reranker.model_path}
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                )}

                {/* Storage Configuration */}
                <div className="rounded-lg border p-3 space-y-2">
                  <h4 className="text-sm font-medium">Storage</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="text-muted-foreground">Working Directory:</div>
                    <div className="font-mono text-xs truncate" title={configData.storage.working_dir}>
                      {configData.storage.working_dir}
                    </div>

                    <div className="text-muted-foreground">Upload Directory:</div>
                    <div className="font-mono text-xs truncate" title={configData.storage.upload_dir}>
                      {configData.storage.upload_dir}
                    </div>
                  </div>
                </div>

                {/* Processing Configuration */}
                <div className="rounded-lg border p-3 space-y-2">
                  <h4 className="text-sm font-medium">Processing</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="text-muted-foreground">Parser:</div>
                    <div className="font-mono text-xs">{configData.processing.parser}</div>

                    <div className="text-muted-foreground">Image Processing:</div>
                    <div className="flex items-center gap-1">
                      {configData.processing.enable_image_processing ? (
                        <>
                          <CheckCircle2 className="h-3 w-3 text-green-600" />
                          <span className="text-xs">Enabled</span>
                        </>
                      ) : (
                        <>
                          <XCircle className="h-3 w-3 text-gray-400" />
                          <span className="text-xs">Disabled</span>
                        </>
                      )}
                    </div>

                    <div className="text-muted-foreground">Table Processing:</div>
                    <div className="flex items-center gap-1">
                      {configData.processing.enable_table_processing ? (
                        <>
                          <CheckCircle2 className="h-3 w-3 text-green-600" />
                          <span className="text-xs">Enabled</span>
                        </>
                      ) : (
                        <>
                          <XCircle className="h-3 w-3 text-gray-400" />
                          <span className="text-xs">Disabled</span>
                        </>
                      )}
                    </div>

                    <div className="text-muted-foreground">Equation Processing:</div>
                    <div className="flex items-center gap-1">
                      {configData.processing.enable_equation_processing ? (
                        <>
                          <CheckCircle2 className="h-3 w-3 text-green-600" />
                          <span className="text-xs">Enabled</span>
                        </>
                      ) : (
                        <>
                          <XCircle className="h-3 w-3 text-gray-400" />
                          <span className="text-xs">Disabled</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ) : null}
          </section>
        </div>

        {/* Footer with action buttons */}
        <div className="flex justify-between items-center pt-4 border-t">
          <p className="text-xs text-muted-foreground">
            {reloadMutation.isPending ? 'Reloading configuration...' : 'Configuration updates require hot-reload'}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                refetchHealth();
                refetchReady();
                refetchConfig();
              }}
              disabled={isLoading}
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <RefreshCw className="h-4 w-4 mr-2" />
              )}
              Refresh All
            </Button>
            <Button variant="default" size="sm" onClick={() => setOpen(false)}>
              Close
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}


import { useState, useEffect, useRef } from 'react';
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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { useQuery, useMutation } from '@tanstack/react-query';
import { healthApi, configApi } from '@/api';
import type { HealthResponse, ReadyResponse, ConfigResponse, ModelsUpdateRequest } from '@/types/api';
import { toast } from '@/lib/toast';

type ModelEditorState = {
  llm: {
    provider: string;
    model_name: string;
    base_url: string;
    api_key: string;
    temperature: string;
    max_tokens: string;
  };
  vision: {
    provider: string;
    model_name: string;
    base_url: string;
    api_key: string;
  };
  embedding: {
    provider: string;
    model_name: string;
    base_url: string;
    api_key: string;
    embedding_dim: string;
    device: string;
    dtype: string;
    attn_implementation: string;
    max_length: string;
    default_instruction: string;
    normalize: boolean;
    allow_image_urls: boolean;
    min_image_tokens: string;
    max_image_tokens: string;
  };
  reranker: {
    enabled: boolean;
    provider: string;
    model_name: string;
    model_path: string;
    device: string;
    dtype: string;
    attn_implementation: string;
    batch_size: string;
    max_length: string;
    instruction: string;
    system_prompt: string;
    api_key: string;
    base_url: string;
    min_image_tokens: string;
    max_image_tokens: string;
    allow_image_urls: boolean;
  };
};

const DEFAULT_EDITOR_STATE: ModelEditorState = {
  llm: {
    provider: 'openai',
    model_name: '',
    base_url: '',
    api_key: '',
    temperature: '',
    max_tokens: '',
  },
  vision: {
    provider: 'openai',
    model_name: '',
    base_url: '',
    api_key: '',
  },
  embedding: {
    provider: 'local_gpu',
    model_name: '',
    base_url: '',
    api_key: '',
    embedding_dim: '',
    device: 'cuda:0',
    dtype: 'float16',
    attn_implementation: 'sdpa',
    max_length: '8192',
    default_instruction: '',
    normalize: true,
    allow_image_urls: false,
    min_image_tokens: '4',
    max_image_tokens: '1280',
  },
  reranker: {
    enabled: false,
    provider: 'local_gpu',
    model_name: '',
    model_path: '',
    device: 'cuda:0',
    dtype: 'float16',
    attn_implementation: 'sdpa',
    batch_size: '8',
    max_length: '8192',
    instruction: '',
    system_prompt: '',
    api_key: '',
    base_url: '',
    min_image_tokens: '4',
    max_image_tokens: '1280',
    allow_image_urls: false,
  },
};

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
  const [showModelEditor, setShowModelEditor] = useState(false);
  const [editorState, setEditorState] = useState<ModelEditorState>(DEFAULT_EDITOR_STATE);
  const baselineStateRef = useRef<ModelEditorState>(DEFAULT_EDITOR_STATE);
  const showLegacyModelEditor = import.meta.env.VITE_LEGACY_MODEL_EDITOR === '1';

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
        refetchHealth();
        refetchReady();
        refetchConfig();
      } else if (data.status === 'partial') {
        toast.warning('Partial Reload', data.message);
        refetchHealth();
        refetchReady();
        refetchConfig();
      } else {
        toast.error('Reload Failed', data.message);
      }
    },
    onError: (error: Error) => {
      toast.error('Reload Failed', error.message);
    },
  });

  const updateModelsMutation = useMutation({
    mutationFn: configApi.updateModelsConfig,
    onSuccess: (data) => {
      if (data.status === 'success') {
        toast.success('Models Updated', data.env_file ? `${data.message} (${data.env_file})` : data.message);
        refetchConfig();
        setShowModelEditor(false);
      } else if (data.status === 'noop') {
        toast.info('No Changes', data.message);
      } else {
        toast.error('Update Failed', data.message);
      }
    },
    onError: (error: Error) => {
      toast.error('Update Failed', error.message);
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

  // Prefill editor state from backend config (API keys are intentionally not returned)
  useEffect(() => {
    if (!open || !configData) return;

    setEditorState(prev => {
      const next: ModelEditorState = {
        ...prev,
        llm: {
          provider: configData.models.llm.provider || prev.llm.provider,
          model_name: configData.models.llm.model_name || prev.llm.model_name,
          base_url: configData.models.llm.base_url ?? '',
          api_key: '',
          temperature: configData.models.llm.temperature !== undefined ? String(configData.models.llm.temperature) : '',
          max_tokens: configData.models.llm.max_tokens !== undefined ? String(configData.models.llm.max_tokens) : '',
        },
        vision: configData.models.vision
          ? {
              provider: configData.models.vision.provider || prev.vision.provider,
              model_name: configData.models.vision.model_name || prev.vision.model_name,
              base_url: configData.models.vision.base_url ?? '',
              api_key: '',
            }
          : prev.vision,
        embedding: {
          provider: configData.models.embedding.provider || prev.embedding.provider,
          model_name: configData.models.embedding.model_name || prev.embedding.model_name,
          base_url: configData.models.embedding.base_url ?? '',
          api_key: '',
          embedding_dim: configData.models.embedding.embedding_dim !== undefined ? String(configData.models.embedding.embedding_dim) : '',
          device: configData.models.embedding.device ?? prev.embedding.device,
          dtype: configData.models.embedding.dtype ?? prev.embedding.dtype,
          attn_implementation: configData.models.embedding.attn_implementation ?? prev.embedding.attn_implementation,
          max_length: configData.models.embedding.max_length !== undefined ? String(configData.models.embedding.max_length) : prev.embedding.max_length,
          default_instruction: configData.models.embedding.default_instruction ?? '',
          normalize: configData.models.embedding.normalize ?? prev.embedding.normalize,
          allow_image_urls: configData.models.embedding.allow_image_urls ?? prev.embedding.allow_image_urls,
          min_image_tokens: configData.models.embedding.min_image_tokens !== undefined ? String(configData.models.embedding.min_image_tokens) : prev.embedding.min_image_tokens,
          max_image_tokens: configData.models.embedding.max_image_tokens !== undefined ? String(configData.models.embedding.max_image_tokens) : prev.embedding.max_image_tokens,
        },
        reranker: {
          enabled: configData.models.reranker?.enabled ?? false,
          provider: configData.models.reranker?.provider ?? prev.reranker.provider,
          model_name: configData.models.reranker?.model_name ?? '',
          model_path: configData.models.reranker?.model_path ?? '',
          device: configData.models.reranker?.device ?? prev.reranker.device,
          dtype: configData.models.reranker?.dtype ?? prev.reranker.dtype,
          attn_implementation: configData.models.reranker?.attn_implementation ?? prev.reranker.attn_implementation,
          batch_size: configData.models.reranker?.batch_size !== undefined ? String(configData.models.reranker.batch_size) : prev.reranker.batch_size,
          max_length: configData.models.reranker?.max_length !== undefined ? String(configData.models.reranker.max_length) : prev.reranker.max_length,
          instruction: '',
          system_prompt: '',
          api_key: '',
          base_url: configData.models.reranker?.base_url ?? '',
          min_image_tokens: configData.models.reranker?.min_image_tokens !== undefined ? String(configData.models.reranker.min_image_tokens) : prev.reranker.min_image_tokens,
          max_image_tokens: configData.models.reranker?.max_image_tokens !== undefined ? String(configData.models.reranker.max_image_tokens) : prev.reranker.max_image_tokens,
          allow_image_urls: configData.models.reranker?.allow_image_urls ?? prev.reranker.allow_image_urls,
        },
      };

      // Save baseline snapshot for diffing; this prevents "Save & Apply" from
      // re-sending unchanged embedding/reranker config (which can cause reloads).
      baselineStateRef.current = next;
      return next;
    });
  }, [open, configData]);

  const isHealthy = healthData?.status === 'healthy';
  const isReady = readyData?.ready === true;

  const handleReloadConfig = () => {
    reloadMutation.mutate(undefined);
  };

  const handleSaveModels = () => {
    const toFloat = (raw: string): number | undefined => {
      const trimmed = raw.trim();
      if (!trimmed) return undefined;
      const num = Number(trimmed);
      return Number.isFinite(num) ? num : undefined;
    };

    const toInt = (raw: string): number | undefined => {
      const trimmed = raw.trim();
      if (!trimmed) return undefined;
      const num = Number.parseInt(trimmed, 10);
      return Number.isFinite(num) ? num : undefined;
    };

    const baseline = baselineStateRef.current;
    const requestBody: ModelsUpdateRequest = { apply: true };

    const llmUpdate: NonNullable<ModelsUpdateRequest['llm']> = {};
    if (editorState.llm.provider !== baseline.llm.provider) llmUpdate.provider = editorState.llm.provider;
    if (editorState.llm.model_name !== baseline.llm.model_name) llmUpdate.model_name = editorState.llm.model_name;
    if (editorState.llm.base_url !== baseline.llm.base_url) llmUpdate.base_url = editorState.llm.base_url;
    if (editorState.llm.api_key.trim()) llmUpdate.api_key = editorState.llm.api_key;
    if (editorState.llm.temperature.trim() !== baseline.llm.temperature.trim()) llmUpdate.temperature = toFloat(editorState.llm.temperature);
    if (editorState.llm.max_tokens.trim() !== baseline.llm.max_tokens.trim()) llmUpdate.max_tokens = toInt(editorState.llm.max_tokens);
    if (Object.keys(llmUpdate).length > 0) {
      if (llmUpdate.model_name !== undefined && !llmUpdate.model_name.trim()) {
        toast.error('Missing LLM Model', 'Please fill LLM model_name');
        return;
      }
      requestBody.llm = llmUpdate;
    }

    const visionUpdate: NonNullable<ModelsUpdateRequest['vision']> = {};
    if (editorState.vision.provider !== baseline.vision.provider) visionUpdate.provider = editorState.vision.provider;
    if (editorState.vision.model_name !== baseline.vision.model_name) visionUpdate.model_name = editorState.vision.model_name;
    if (editorState.vision.base_url !== baseline.vision.base_url) visionUpdate.base_url = editorState.vision.base_url;
    if (editorState.vision.api_key.trim()) visionUpdate.api_key = editorState.vision.api_key;
    if (Object.keys(visionUpdate).length > 0) {
      if (visionUpdate.model_name !== undefined && !visionUpdate.model_name.trim()) {
        toast.error('Missing Vision Model', 'Please fill vision model_name');
        return;
      }
      requestBody.vision = visionUpdate;
    }

    const embeddingUpdate: NonNullable<ModelsUpdateRequest['embedding']> = {};
    if (editorState.embedding.provider !== baseline.embedding.provider) embeddingUpdate.provider = editorState.embedding.provider;
    if (editorState.embedding.model_name !== baseline.embedding.model_name) embeddingUpdate.model_name = editorState.embedding.model_name;
    if (editorState.embedding.base_url !== baseline.embedding.base_url) embeddingUpdate.base_url = editorState.embedding.base_url;
    if (editorState.embedding.api_key.trim()) embeddingUpdate.api_key = editorState.embedding.api_key;
    if (editorState.embedding.embedding_dim.trim() !== baseline.embedding.embedding_dim.trim()) embeddingUpdate.embedding_dim = toInt(editorState.embedding.embedding_dim);
    if (editorState.embedding.device !== baseline.embedding.device) embeddingUpdate.device = editorState.embedding.device;
    if (editorState.embedding.dtype !== baseline.embedding.dtype) embeddingUpdate.dtype = editorState.embedding.dtype;
    if (editorState.embedding.attn_implementation !== baseline.embedding.attn_implementation) embeddingUpdate.attn_implementation = editorState.embedding.attn_implementation;
    if (editorState.embedding.max_length.trim() !== baseline.embedding.max_length.trim()) embeddingUpdate.max_length = toInt(editorState.embedding.max_length);
    if (editorState.embedding.default_instruction !== baseline.embedding.default_instruction) embeddingUpdate.default_instruction = editorState.embedding.default_instruction;
    if (editorState.embedding.normalize !== baseline.embedding.normalize) embeddingUpdate.normalize = editorState.embedding.normalize;
    if (editorState.embedding.allow_image_urls !== baseline.embedding.allow_image_urls) embeddingUpdate.allow_image_urls = editorState.embedding.allow_image_urls;
    if (editorState.embedding.min_image_tokens.trim() !== baseline.embedding.min_image_tokens.trim()) embeddingUpdate.min_image_tokens = toInt(editorState.embedding.min_image_tokens);
    if (editorState.embedding.max_image_tokens.trim() !== baseline.embedding.max_image_tokens.trim()) embeddingUpdate.max_image_tokens = toInt(editorState.embedding.max_image_tokens);
    if (Object.keys(embeddingUpdate).length > 0) {
      if (embeddingUpdate.model_name !== undefined && !embeddingUpdate.model_name.trim()) {
        toast.error('Missing Embedding Model', 'Please fill embedding model_name');
        return;
      }
      requestBody.embedding = embeddingUpdate;
    }

    const rerankerUpdate: NonNullable<ModelsUpdateRequest['reranker']> = {};
    if (editorState.reranker.enabled !== baseline.reranker.enabled) rerankerUpdate.enabled = editorState.reranker.enabled;
    if (editorState.reranker.provider !== baseline.reranker.provider) rerankerUpdate.provider = editorState.reranker.provider;
    if (editorState.reranker.model_name !== baseline.reranker.model_name) rerankerUpdate.model_name = editorState.reranker.model_name;
    if (editorState.reranker.model_path !== baseline.reranker.model_path) rerankerUpdate.model_path = editorState.reranker.model_path;
    if (editorState.reranker.device !== baseline.reranker.device) rerankerUpdate.device = editorState.reranker.device;
    if (editorState.reranker.dtype !== baseline.reranker.dtype) rerankerUpdate.dtype = editorState.reranker.dtype;
    if (editorState.reranker.attn_implementation !== baseline.reranker.attn_implementation) rerankerUpdate.attn_implementation = editorState.reranker.attn_implementation;
    if (editorState.reranker.batch_size.trim() !== baseline.reranker.batch_size.trim()) rerankerUpdate.batch_size = toInt(editorState.reranker.batch_size);
    if (editorState.reranker.max_length.trim() !== baseline.reranker.max_length.trim()) rerankerUpdate.max_length = toInt(editorState.reranker.max_length);
    // Write-only fields: only send if user explicitly provided a value.
    if (editorState.reranker.instruction.trim()) rerankerUpdate.instruction = editorState.reranker.instruction;
    if (editorState.reranker.system_prompt.trim()) rerankerUpdate.system_prompt = editorState.reranker.system_prompt;
    if (editorState.reranker.api_key.trim()) rerankerUpdate.api_key = editorState.reranker.api_key;
    if (editorState.reranker.base_url !== baseline.reranker.base_url) rerankerUpdate.base_url = editorState.reranker.base_url;
    if (editorState.reranker.min_image_tokens.trim() !== baseline.reranker.min_image_tokens.trim()) rerankerUpdate.min_image_tokens = toInt(editorState.reranker.min_image_tokens);
    if (editorState.reranker.max_image_tokens.trim() !== baseline.reranker.max_image_tokens.trim()) rerankerUpdate.max_image_tokens = toInt(editorState.reranker.max_image_tokens);
    if (editorState.reranker.allow_image_urls !== baseline.reranker.allow_image_urls) rerankerUpdate.allow_image_urls = editorState.reranker.allow_image_urls;
    if (Object.keys(rerankerUpdate).length > 0) {
      requestBody.reranker = rerankerUpdate;
    }

    if (!requestBody.llm && !requestBody.vision && !requestBody.embedding && !requestBody.reranker) {
      toast.info('No Changes', 'No model settings were changed');
      return;
    }

    updateModelsMutation.mutate(requestBody);
  };

  const handleCancelModelEdit = () => {
    setEditorState(baselineStateRef.current);
    setShowModelEditor(false);
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
            Backend health status, configuration details, and model settings
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
              <div className="flex items-center gap-2">
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
                  Reload Config
                </Button>
                {showModelEditor ? (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleCancelModelEdit}
                      disabled={updateModelsMutation.isPending || configLoading}
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="default"
                      size="sm"
                      onClick={handleSaveModels}
                      disabled={updateModelsMutation.isPending || configLoading}
                    >
                      {updateModelsMutation.isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      ) : null}
                      Save & Apply
                    </Button>
                  </>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowModelEditor(true)}
                    disabled={configLoading}
                  >
                    Modify
                  </Button>
                )}
              </div>
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

                    <div className="text-muted-foreground">Env File:</div>
                    <div
                      className="font-mono text-xs truncate"
                      title={configData.backend.env_file_loaded ? configData.backend.env_file_loaded : 'Not loaded from file'}
                    >
                      {configData.backend.env_file_loaded ? configData.backend.env_file_loaded : 'Not loaded from file'}
                    </div>

                    <div className="text-muted-foreground">CORS Origins:</div>
                    <div className="font-mono text-xs truncate" title={configData.backend.cors_origins.join(', ')}>
                      {configData.backend.cors_origins.join(', ')}
                    </div>
                  </div>
                </div>

                {/* LLM Configuration */}
                <div className="rounded-lg border p-3 space-y-2">
                  <h4 className="text-sm font-medium">LLM Provider</h4>
                  {showModelEditor ? (
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-2">
                        <Label>Provider</Label>
                        <Select
                          value={editorState.llm.provider}
                          onValueChange={(v) =>
                            setEditorState(s => ({ ...s, llm: { ...s.llm, provider: v } }))
                          }
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select provider" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="openai">openai</SelectItem>
                            <SelectItem value="azure">azure</SelectItem>
                            <SelectItem value="custom">custom</SelectItem>
                            <SelectItem value="local">local</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label>Model Name</Label>
                        <Input
                          value={editorState.llm.model_name}
                          onChange={(e) =>
                            setEditorState(s => ({ ...s, llm: { ...s.llm, model_name: e.target.value } }))
                          }
                          placeholder="e.g. gpt-4o-mini"
                        />
                      </div>
                      <div className="space-y-2 col-span-2">
                        <Label>Base URL (optional)</Label>
                        <Input
                          value={editorState.llm.base_url}
                          onChange={(e) =>
                            setEditorState(s => ({ ...s, llm: { ...s.llm, base_url: e.target.value } }))
                          }
                          placeholder="e.g. https://api.openai.com/v1"
                        />
                      </div>
                      <div className="space-y-2 col-span-2">
                        <Label>API Key (leave blank to keep)</Label>
                        <Input
                          type="password"
                          value={editorState.llm.api_key}
                          onChange={(e) =>
                            setEditorState(s => ({ ...s, llm: { ...s.llm, api_key: e.target.value } }))
                          }
                          placeholder="sk-..."
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Temperature</Label>
                        <Input
                          type="number"
                          value={editorState.llm.temperature}
                          onChange={(e) =>
                            setEditorState(s => ({ ...s, llm: { ...s.llm, temperature: e.target.value } }))
                          }
                          placeholder="0.7"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Max Tokens</Label>
                        <Input
                          type="number"
                          value={editorState.llm.max_tokens}
                          onChange={(e) =>
                            setEditorState(s => ({ ...s, llm: { ...s.llm, max_tokens: e.target.value } }))
                          }
                          placeholder="4096"
                        />
                      </div>
                    </div>
                  ) : (
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
                  )}
                </div>

                {/* Embedding Configuration */}
                <div className="rounded-lg border p-3 space-y-2">
                  <h4 className="text-sm font-medium">Embedding Model</h4>
                  {showModelEditor ? (
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-2">
                        <Label>Provider</Label>
                        <Select
                          value={editorState.embedding.provider}
                          onValueChange={(v) =>
                            setEditorState(s => ({ ...s, embedding: { ...s.embedding, provider: v } }))
                          }
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select provider" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="openai">openai</SelectItem>
                            <SelectItem value="azure">azure</SelectItem>
                            <SelectItem value="custom">custom</SelectItem>
                            <SelectItem value="local">local</SelectItem>
                            <SelectItem value="local_gpu">local_gpu</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label>Model Name</Label>
                        <Input
                          value={editorState.embedding.model_name}
                          onChange={(e) =>
                            setEditorState(s => ({ ...s, embedding: { ...s.embedding, model_name: e.target.value } }))
                          }
                          placeholder="e.g. Qwen/Qwen3-VL-Embedding-2B"
                        />
                      </div>
                      <div className="space-y-2 col-span-2">
                        <Label>Base URL (optional)</Label>
                        <Input
                          value={editorState.embedding.base_url}
                          onChange={(e) =>
                            setEditorState(s => ({ ...s, embedding: { ...s.embedding, base_url: e.target.value } }))
                          }
                          placeholder="(leave empty for local_gpu)"
                        />
                      </div>
                      <div className="space-y-2 col-span-2">
                        <Label>API Key (leave blank to keep)</Label>
                        <Input
                          type="password"
                          value={editorState.embedding.api_key}
                          onChange={(e) =>
                            setEditorState(s => ({ ...s, embedding: { ...s.embedding, api_key: e.target.value } }))
                          }
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Embedding Dim</Label>
                        <Input
                          type="number"
                          value={editorState.embedding.embedding_dim}
                          onChange={(e) =>
                            setEditorState(s => ({ ...s, embedding: { ...s.embedding, embedding_dim: e.target.value } }))
                          }
                          placeholder="e.g. 2048"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Device</Label>
                        <Input
                          value={editorState.embedding.device}
                          onChange={(e) =>
                            setEditorState(s => ({ ...s, embedding: { ...s.embedding, device: e.target.value } }))
                          }
                          placeholder="cuda:0 / cpu"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>DType</Label>
                        <Input
                          value={editorState.embedding.dtype}
                          onChange={(e) =>
                            setEditorState(s => ({ ...s, embedding: { ...s.embedding, dtype: e.target.value } }))
                          }
                          placeholder="float16"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Attention</Label>
                        <Input
                          value={editorState.embedding.attn_implementation}
                          onChange={(e) =>
                            setEditorState(s => ({ ...s, embedding: { ...s.embedding, attn_implementation: e.target.value } }))
                          }
                          placeholder="sdpa / eager"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Max Length</Label>
                        <Input
                          type="number"
                          value={editorState.embedding.max_length}
                          onChange={(e) =>
                            setEditorState(s => ({ ...s, embedding: { ...s.embedding, max_length: e.target.value } }))
                          }
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Min Image Tokens</Label>
                        <Input
                          type="number"
                          value={editorState.embedding.min_image_tokens}
                          onChange={(e) =>
                            setEditorState(s => ({ ...s, embedding: { ...s.embedding, min_image_tokens: e.target.value } }))
                          }
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Max Image Tokens</Label>
                        <Input
                          type="number"
                          value={editorState.embedding.max_image_tokens}
                          onChange={(e) =>
                            setEditorState(s => ({ ...s, embedding: { ...s.embedding, max_image_tokens: e.target.value } }))
                          }
                        />
                      </div>
                      <div className="space-y-2 col-span-2">
                        <Label>Default Instruction</Label>
                        <Input
                          value={editorState.embedding.default_instruction}
                          onChange={(e) =>
                            setEditorState(s => ({ ...s, embedding: { ...s.embedding, default_instruction: e.target.value } }))
                          }
                          placeholder="Represent the user's input."
                        />
                      </div>
                      <div className="flex items-center justify-between rounded-md border p-3 col-span-2">
                        <div className="space-y-1">
                          <Label>Normalize</Label>
                          <div className="text-xs text-muted-foreground">L2-normalize output embeddings</div>
                        </div>
                        <Switch
                          checked={editorState.embedding.normalize}
                          onCheckedChange={(checked) =>
                            setEditorState(s => ({ ...s, embedding: { ...s.embedding, normalize: checked } }))
                          }
                        />
                      </div>
                      <div className="flex items-center justify-between rounded-md border p-3 col-span-2">
                        <div className="space-y-1">
                          <Label>Allow Image URLs</Label>
                          <div className="text-xs text-muted-foreground">Security risk: keep off unless trusted</div>
                        </div>
                        <Switch
                          checked={editorState.embedding.allow_image_urls}
                          onCheckedChange={(checked) =>
                            setEditorState(s => ({ ...s, embedding: { ...s.embedding, allow_image_urls: checked } }))
                          }
                        />
                      </div>
                    </div>
                  ) : (
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
                  )}
                </div>

                {/* Vision Model (if configured) */}
                {configData.models.vision && (
                  <div className="rounded-lg border p-3 space-y-2">
                    <h4 className="text-sm font-medium">Vision Model</h4>
                    {showModelEditor ? (
                      <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-2">
                          <Label>Provider</Label>
                          <Select
                            value={editorState.vision.provider}
                            onValueChange={(v) =>
                              setEditorState(s => ({ ...s, vision: { ...s.vision, provider: v } }))
                            }
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Select provider" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="openai">openai</SelectItem>
                              <SelectItem value="azure">azure</SelectItem>
                              <SelectItem value="custom">custom</SelectItem>
                              <SelectItem value="local">local</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-2">
                          <Label>Model Name</Label>
                          <Input
                            value={editorState.vision.model_name}
                            onChange={(e) =>
                              setEditorState(s => ({ ...s, vision: { ...s.vision, model_name: e.target.value } }))
                            }
                            placeholder="e.g. gpt-4o-mini"
                          />
                        </div>
                        <div className="space-y-2 col-span-2">
                          <Label>Base URL (optional)</Label>
                          <Input
                            value={editorState.vision.base_url}
                            onChange={(e) =>
                              setEditorState(s => ({ ...s, vision: { ...s.vision, base_url: e.target.value } }))
                            }
                            placeholder="e.g. https://api.openai.com/v1"
                          />
                        </div>
                        <div className="space-y-2 col-span-2">
                          <Label>API Key (leave blank to keep)</Label>
                          <Input
                            type="password"
                            value={editorState.vision.api_key}
                            onChange={(e) =>
                              setEditorState(s => ({ ...s, vision: { ...s.vision, api_key: e.target.value } }))
                            }
                            placeholder="sk-..."
                          />
                        </div>
                      </div>
                    ) : (
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
                    )}
                  </div>
                )}

                {/* Reranker */}
                {showModelEditor || (configData.models.reranker && configData.models.reranker.enabled) ? (
                  <div className="rounded-lg border p-3 space-y-2">
                    <h4 className="text-sm font-medium">Reranker</h4>
                    {showModelEditor ? (
                      <div className="grid grid-cols-2 gap-3">
                        <div className="flex items-center justify-between rounded-md border p-3 col-span-2">
                          <div className="space-y-1">
                            <Label>Enable Reranker</Label>
                            <div className="text-xs text-muted-foreground">Applies to retrieval ranking</div>
                          </div>
                          <Switch
                            checked={editorState.reranker.enabled}
                            onCheckedChange={(checked) =>
                              setEditorState(s => ({ ...s, reranker: { ...s.reranker, enabled: checked } }))
                            }
                          />
                        </div>

                        <div className="space-y-2">
                          <Label>Provider</Label>
                          <Select
                            value={editorState.reranker.provider}
                            onValueChange={(v) =>
                              setEditorState(s => ({ ...s, reranker: { ...s.reranker, provider: v } }))
                            }
                            disabled={!editorState.reranker.enabled}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Select provider" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="local">local</SelectItem>
                              <SelectItem value="local_gpu">local_gpu</SelectItem>
                              <SelectItem value="api">api</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>

                        <div className="space-y-2">
                          <Label>Model Name</Label>
                          <Input
                            value={editorState.reranker.model_name}
                            onChange={(e) =>
                              setEditorState(s => ({ ...s, reranker: { ...s.reranker, model_name: e.target.value } }))
                            }
                            disabled={!editorState.reranker.enabled}
                            placeholder="e.g. Qwen/Qwen3-VL-Reranker-2B"
                          />
                        </div>

                        <div className="space-y-2 col-span-2">
                          <Label>Model Path (optional)</Label>
                          <Input
                            value={editorState.reranker.model_path}
                            onChange={(e) =>
                              setEditorState(s => ({ ...s, reranker: { ...s.reranker, model_path: e.target.value } }))
                            }
                            disabled={!editorState.reranker.enabled}
                            placeholder="/path/to/local/model (optional)"
                          />
                        </div>

                        <div className="space-y-2">
                          <Label>Device</Label>
                          <Input
                            value={editorState.reranker.device}
                            onChange={(e) =>
                              setEditorState(s => ({ ...s, reranker: { ...s.reranker, device: e.target.value } }))
                            }
                            disabled={!editorState.reranker.enabled}
                            placeholder="cuda:0 / cpu"
                          />
                        </div>

                        <div className="space-y-2">
                          <Label>DType</Label>
                          <Input
                            value={editorState.reranker.dtype}
                            onChange={(e) =>
                              setEditorState(s => ({ ...s, reranker: { ...s.reranker, dtype: e.target.value } }))
                            }
                            disabled={!editorState.reranker.enabled}
                            placeholder="float16"
                          />
                        </div>

                        <div className="space-y-2">
                          <Label>Attention</Label>
                          <Input
                            value={editorState.reranker.attn_implementation}
                            onChange={(e) =>
                              setEditorState(s => ({ ...s, reranker: { ...s.reranker, attn_implementation: e.target.value } }))
                            }
                            disabled={!editorState.reranker.enabled}
                            placeholder="sdpa / eager"
                          />
                        </div>

                        <div className="space-y-2">
                          <Label>Batch Size</Label>
                          <Input
                            type="number"
                            value={editorState.reranker.batch_size}
                            onChange={(e) =>
                              setEditorState(s => ({ ...s, reranker: { ...s.reranker, batch_size: e.target.value } }))
                            }
                            disabled={!editorState.reranker.enabled}
                          />
                        </div>

                        <div className="space-y-2">
                          <Label>Max Length</Label>
                          <Input
                            type="number"
                            value={editorState.reranker.max_length}
                            onChange={(e) =>
                              setEditorState(s => ({ ...s, reranker: { ...s.reranker, max_length: e.target.value } }))
                            }
                            disabled={!editorState.reranker.enabled}
                          />
                        </div>

                        <div className="space-y-2">
                          <Label>Min Image Tokens</Label>
                          <Input
                            type="number"
                            value={editorState.reranker.min_image_tokens}
                            onChange={(e) =>
                              setEditorState(s => ({ ...s, reranker: { ...s.reranker, min_image_tokens: e.target.value } }))
                            }
                            disabled={!editorState.reranker.enabled}
                          />
                        </div>

                        <div className="space-y-2">
                          <Label>Max Image Tokens</Label>
                          <Input
                            type="number"
                            value={editorState.reranker.max_image_tokens}
                            onChange={(e) =>
                              setEditorState(s => ({ ...s, reranker: { ...s.reranker, max_image_tokens: e.target.value } }))
                            }
                            disabled={!editorState.reranker.enabled}
                          />
                        </div>

                        <div className="space-y-2 col-span-2">
                          <Label>Base URL (optional)</Label>
                          <Input
                            value={editorState.reranker.base_url}
                            onChange={(e) =>
                              setEditorState(s => ({ ...s, reranker: { ...s.reranker, base_url: e.target.value } }))
                            }
                            disabled={!editorState.reranker.enabled}
                            placeholder="(optional)"
                          />
                        </div>

                        <div className="space-y-2 col-span-2">
                          <Label>API Key (leave blank to keep)</Label>
                          <Input
                            type="password"
                            value={editorState.reranker.api_key}
                            onChange={(e) =>
                              setEditorState(s => ({ ...s, reranker: { ...s.reranker, api_key: e.target.value } }))
                            }
                            disabled={!editorState.reranker.enabled}
                          />
                        </div>

                        <div className="flex items-center justify-between rounded-md border p-3 col-span-2">
                          <div className="space-y-1">
                            <Label>Allow Image URLs</Label>
                            <div className="text-xs text-muted-foreground">Security risk: keep off unless trusted</div>
                          </div>
                          <Switch
                            checked={editorState.reranker.allow_image_urls}
                            onCheckedChange={(checked) =>
                              setEditorState(s => ({ ...s, reranker: { ...s.reranker, allow_image_urls: checked } }))
                            }
                            disabled={!editorState.reranker.enabled}
                          />
                        </div>

                        <div className="space-y-2 col-span-2">
                          <Label>Instruction (optional)</Label>
                          <Textarea
                            value={editorState.reranker.instruction}
                            onChange={(e) =>
                              setEditorState(s => ({ ...s, reranker: { ...s.reranker, instruction: e.target.value } }))
                            }
                            disabled={!editorState.reranker.enabled}
                            placeholder="(optional)"
                            className="min-h-[80px]"
                          />
                        </div>

                        <div className="space-y-2 col-span-2">
                          <Label>System Prompt (optional)</Label>
                          <Textarea
                            value={editorState.reranker.system_prompt}
                            onChange={(e) =>
                              setEditorState(s => ({ ...s, reranker: { ...s.reranker, system_prompt: e.target.value } }))
                            }
                            disabled={!editorState.reranker.enabled}
                            placeholder="(optional)"
                            className="min-h-[80px]"
                          />
                        </div>
                      </div>
                    ) : (
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div className="text-muted-foreground">Provider:</div>
                        <div className="font-mono text-xs">{configData.models.reranker?.provider}</div>

                        {configData.models.reranker?.model_name ? (
                          <>
                            <div className="text-muted-foreground">Model:</div>
                            <div className="font-mono text-xs">{configData.models.reranker.model_name}</div>
                          </>
                        ) : null}

                        {configData.models.reranker?.model_path ? (
                          <>
                            <div className="text-muted-foreground">Model Path:</div>
                            <div
                              className="font-mono text-xs truncate"
                              title={configData.models.reranker.model_path}
                            >
                              {configData.models.reranker.model_path}
                            </div>
                          </>
                        ) : null}
                      </div>
                    )}
                  </div>
                ) : null}

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

          {/* Model Editor Section (deprecated: editing is inline above) */}
          {showLegacyModelEditor && showModelEditor && (
            <>
              <Separator />
              <section className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold">Model Settings (Editable)</h3>
                  <Button
                    variant="default"
                    size="sm"
                    onClick={handleSaveModels}
                    disabled={updateModelsMutation.isPending || configLoading}
                  >
                    {updateModelsMutation.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : null}
                    Save & Apply
                  </Button>
                </div>

                <Tabs defaultValue="llm" className="w-full">
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="llm">LLM</TabsTrigger>
                    <TabsTrigger value="embedding">Embedding</TabsTrigger>
                    <TabsTrigger value="reranker">Reranker</TabsTrigger>
                  </TabsList>

                  <TabsContent value="llm" className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-2">
                        <Label>Provider</Label>
                        <Select
                          value={editorState.llm.provider}
                          onValueChange={(v) => setEditorState(s => ({ ...s, llm: { ...s.llm, provider: v } }))}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select provider" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="openai">openai</SelectItem>
                            <SelectItem value="azure">azure</SelectItem>
                            <SelectItem value="custom">custom</SelectItem>
                            <SelectItem value="local">local</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label>Model Name</Label>
                        <Input
                          value={editorState.llm.model_name}
                          onChange={(e) => setEditorState(s => ({ ...s, llm: { ...s.llm, model_name: e.target.value } }))}
                          placeholder="e.g. gpt-4o-mini"
                        />
                      </div>
                      <div className="space-y-2 col-span-2">
                        <Label>Base URL (optional)</Label>
                        <Input
                          value={editorState.llm.base_url}
                          onChange={(e) => setEditorState(s => ({ ...s, llm: { ...s.llm, base_url: e.target.value } }))}
                          placeholder="e.g. https://api.openai.com/v1"
                        />
                      </div>
                      <div className="space-y-2 col-span-2">
                        <Label>API Key (leave blank to keep)</Label>
                        <Input
                          type="password"
                          value={editorState.llm.api_key}
                          onChange={(e) => setEditorState(s => ({ ...s, llm: { ...s.llm, api_key: e.target.value } }))}
                          placeholder="sk-..."
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Temperature</Label>
                        <Input
                          type="number"
                          value={editorState.llm.temperature}
                          onChange={(e) => setEditorState(s => ({ ...s, llm: { ...s.llm, temperature: e.target.value } }))}
                          placeholder="0.7"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Max Tokens</Label>
                        <Input
                          type="number"
                          value={editorState.llm.max_tokens}
                          onChange={(e) => setEditorState(s => ({ ...s, llm: { ...s.llm, max_tokens: e.target.value } }))}
                          placeholder="4096"
                        />
                      </div>
                    </div>
                  </TabsContent>

                  <TabsContent value="embedding" className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-2">
                        <Label>Provider</Label>
                        <Select
                          value={editorState.embedding.provider}
                          onValueChange={(v) => setEditorState(s => ({ ...s, embedding: { ...s.embedding, provider: v } }))}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select provider" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="openai">openai</SelectItem>
                            <SelectItem value="azure">azure</SelectItem>
                            <SelectItem value="custom">custom</SelectItem>
                            <SelectItem value="local">local</SelectItem>
                            <SelectItem value="local_gpu">local_gpu</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label>Model Name</Label>
                        <Input
                          value={editorState.embedding.model_name}
                          onChange={(e) => setEditorState(s => ({ ...s, embedding: { ...s.embedding, model_name: e.target.value } }))}
                          placeholder="e.g. Qwen/Qwen3-VL-Embedding-2B"
                        />
                      </div>
                      <div className="space-y-2 col-span-2">
                        <Label>Base URL (optional)</Label>
                        <Input
                          value={editorState.embedding.base_url}
                          onChange={(e) => setEditorState(s => ({ ...s, embedding: { ...s.embedding, base_url: e.target.value } }))}
                          placeholder="(leave empty for local_gpu)"
                        />
                      </div>
                      <div className="space-y-2 col-span-2">
                        <Label>API Key (leave blank to keep)</Label>
                        <Input
                          type="password"
                          value={editorState.embedding.api_key}
                          onChange={(e) => setEditorState(s => ({ ...s, embedding: { ...s.embedding, api_key: e.target.value } }))}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Embedding Dim</Label>
                        <Input
                          type="number"
                          value={editorState.embedding.embedding_dim}
                          onChange={(e) => setEditorState(s => ({ ...s, embedding: { ...s.embedding, embedding_dim: e.target.value } }))}
                          placeholder="e.g. 2048"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Device</Label>
                        <Input
                          value={editorState.embedding.device}
                          onChange={(e) => setEditorState(s => ({ ...s, embedding: { ...s.embedding, device: e.target.value } }))}
                          placeholder="cuda:0 / cpu"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>DType</Label>
                        <Input
                          value={editorState.embedding.dtype}
                          onChange={(e) => setEditorState(s => ({ ...s, embedding: { ...s.embedding, dtype: e.target.value } }))}
                          placeholder="float16"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Attention</Label>
                        <Input
                          value={editorState.embedding.attn_implementation}
                          onChange={(e) => setEditorState(s => ({ ...s, embedding: { ...s.embedding, attn_implementation: e.target.value } }))}
                          placeholder="sdpa / eager"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Max Length</Label>
                        <Input
                          type="number"
                          value={editorState.embedding.max_length}
                          onChange={(e) => setEditorState(s => ({ ...s, embedding: { ...s.embedding, max_length: e.target.value } }))}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Min Image Tokens</Label>
                        <Input
                          type="number"
                          value={editorState.embedding.min_image_tokens}
                          onChange={(e) => setEditorState(s => ({ ...s, embedding: { ...s.embedding, min_image_tokens: e.target.value } }))}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Max Image Tokens</Label>
                        <Input
                          type="number"
                          value={editorState.embedding.max_image_tokens}
                          onChange={(e) => setEditorState(s => ({ ...s, embedding: { ...s.embedding, max_image_tokens: e.target.value } }))}
                        />
                      </div>
                      <div className="space-y-2 col-span-2">
                        <Label>Default Instruction</Label>
                        <Input
                          value={editorState.embedding.default_instruction}
                          onChange={(e) => setEditorState(s => ({ ...s, embedding: { ...s.embedding, default_instruction: e.target.value } }))}
                          placeholder="Represent the user's input."
                        />
                      </div>
                      <div className="flex items-center justify-between rounded-md border p-3 col-span-2">
                        <div className="space-y-1">
                          <Label>Normalize</Label>
                          <div className="text-xs text-muted-foreground">L2-normalize output embeddings</div>
                        </div>
                        <Switch
                          checked={editorState.embedding.normalize}
                          onCheckedChange={(checked) => setEditorState(s => ({ ...s, embedding: { ...s.embedding, normalize: checked } }))}
                        />
                      </div>
                      <div className="flex items-center justify-between rounded-md border p-3 col-span-2">
                        <div className="space-y-1">
                          <Label>Allow Image URLs</Label>
                          <div className="text-xs text-muted-foreground">Security risk: keep off unless trusted</div>
                        </div>
                        <Switch
                          checked={editorState.embedding.allow_image_urls}
                          onCheckedChange={(checked) => setEditorState(s => ({ ...s, embedding: { ...s.embedding, allow_image_urls: checked } }))}
                        />
                      </div>
                    </div>
                  </TabsContent>

                  <TabsContent value="reranker" className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="flex items-center justify-between rounded-md border p-3 col-span-2">
                        <div className="space-y-1">
                          <Label>Enable Reranker</Label>
                          <div className="text-xs text-muted-foreground">Applies to retrieval ranking</div>
                        </div>
                        <Switch
                          checked={editorState.reranker.enabled}
                          onCheckedChange={(checked) => setEditorState(s => ({ ...s, reranker: { ...s.reranker, enabled: checked } }))}
                        />
                      </div>

                      <div className="space-y-2">
                        <Label>Provider</Label>
                        <Select
                          value={editorState.reranker.provider}
                          onValueChange={(v) => setEditorState(s => ({ ...s, reranker: { ...s.reranker, provider: v } }))}
                          disabled={!editorState.reranker.enabled}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select provider" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="local">local</SelectItem>
                            <SelectItem value="local_gpu">local_gpu</SelectItem>
                            <SelectItem value="api">api</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label>Model Name</Label>
                        <Input
                          value={editorState.reranker.model_name}
                          onChange={(e) => setEditorState(s => ({ ...s, reranker: { ...s.reranker, model_name: e.target.value } }))}
                          disabled={!editorState.reranker.enabled}
                          placeholder="e.g. Qwen/Qwen3-VL-Reranker-2B"
                        />
                      </div>
                      <div className="space-y-2 col-span-2">
                        <Label>Model Path (optional)</Label>
                        <Input
                          value={editorState.reranker.model_path}
                          onChange={(e) => setEditorState(s => ({ ...s, reranker: { ...s.reranker, model_path: e.target.value } }))}
                          disabled={!editorState.reranker.enabled}
                          placeholder="/path/to/local/model (optional)"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Device</Label>
                        <Input
                          value={editorState.reranker.device}
                          onChange={(e) => setEditorState(s => ({ ...s, reranker: { ...s.reranker, device: e.target.value } }))}
                          disabled={!editorState.reranker.enabled}
                          placeholder="cuda:0 / cpu"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>DType</Label>
                        <Input
                          value={editorState.reranker.dtype}
                          onChange={(e) => setEditorState(s => ({ ...s, reranker: { ...s.reranker, dtype: e.target.value } }))}
                          disabled={!editorState.reranker.enabled}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Attention</Label>
                        <Input
                          value={editorState.reranker.attn_implementation}
                          onChange={(e) => setEditorState(s => ({ ...s, reranker: { ...s.reranker, attn_implementation: e.target.value } }))}
                          disabled={!editorState.reranker.enabled}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Batch Size</Label>
                        <Input
                          type="number"
                          value={editorState.reranker.batch_size}
                          onChange={(e) => setEditorState(s => ({ ...s, reranker: { ...s.reranker, batch_size: e.target.value } }))}
                          disabled={!editorState.reranker.enabled}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Max Length</Label>
                        <Input
                          type="number"
                          value={editorState.reranker.max_length}
                          onChange={(e) => setEditorState(s => ({ ...s, reranker: { ...s.reranker, max_length: e.target.value } }))}
                          disabled={!editorState.reranker.enabled}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Min Image Tokens</Label>
                        <Input
                          type="number"
                          value={editorState.reranker.min_image_tokens}
                          onChange={(e) => setEditorState(s => ({ ...s, reranker: { ...s.reranker, min_image_tokens: e.target.value } }))}
                          disabled={!editorState.reranker.enabled}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Max Image Tokens</Label>
                        <Input
                          type="number"
                          value={editorState.reranker.max_image_tokens}
                          onChange={(e) => setEditorState(s => ({ ...s, reranker: { ...s.reranker, max_image_tokens: e.target.value } }))}
                          disabled={!editorState.reranker.enabled}
                        />
                      </div>
                      <div className="flex items-center justify-between rounded-md border p-3 col-span-2">
                        <div className="space-y-1">
                          <Label>Allow Image URLs</Label>
                          <div className="text-xs text-muted-foreground">Security risk: keep off unless trusted</div>
                        </div>
                        <Switch
                          checked={editorState.reranker.allow_image_urls}
                          onCheckedChange={(checked) => setEditorState(s => ({ ...s, reranker: { ...s.reranker, allow_image_urls: checked } }))}
                          disabled={!editorState.reranker.enabled}
                        />
                      </div>
                      <div className="space-y-2 col-span-2">
                        <Label>Instruction (optional)</Label>
                        <Textarea
                          value={editorState.reranker.instruction}
                          onChange={(e) => setEditorState(s => ({ ...s, reranker: { ...s.reranker, instruction: e.target.value } }))}
                          disabled={!editorState.reranker.enabled}
                          placeholder="Given a search query, retrieve relevant candidates that answer the query."
                        />
                      </div>
                      <div className="space-y-2 col-span-2">
                        <Label>System Prompt (optional)</Label>
                        <Textarea
                          value={editorState.reranker.system_prompt}
                          onChange={(e) => setEditorState(s => ({ ...s, reranker: { ...s.reranker, system_prompt: e.target.value } }))}
                          disabled={!editorState.reranker.enabled}
                        />
                      </div>
                      <div className="space-y-2 col-span-2">
                        <Label>API Key (api provider only; leave blank to keep)</Label>
                        <Input
                          type="password"
                          value={editorState.reranker.api_key}
                          onChange={(e) => setEditorState(s => ({ ...s, reranker: { ...s.reranker, api_key: e.target.value } }))}
                          disabled={!editorState.reranker.enabled}
                        />
                      </div>
                      <div className="space-y-2 col-span-2">
                        <Label>Base URL (api provider only)</Label>
                        <Input
                          value={editorState.reranker.base_url}
                          onChange={(e) => setEditorState(s => ({ ...s, reranker: { ...s.reranker, base_url: e.target.value } }))}
                          disabled={!editorState.reranker.enabled}
                        />
                      </div>
                    </div>
                  </TabsContent>
                </Tabs>
              </section>
            </>
          )}
        </div>

        {/* Footer with action buttons */}
        <div className="flex justify-between items-center pt-4 border-t">
          <p className="text-xs text-muted-foreground">
            {reloadMutation.isPending
              ? 'Reloading configuration...'
              : updateModelsMutation.isPending
                ? 'Applying model configuration...'
                : ''}
          </p>
          <div className="flex gap-2">
            <Button variant="default" size="sm" onClick={() => setOpen(false)}>
              Close
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

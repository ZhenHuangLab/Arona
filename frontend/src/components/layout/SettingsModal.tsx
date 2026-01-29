import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Settings,
  CheckCircle2,
  XCircle,
  Loader2,
  RefreshCw,
  AlertCircle,
  Server,
  Database,
  Cpu,
  FolderCog,
  Palette,
  Sun,
  Moon,
  Monitor,
  MessageSquare,
} from 'lucide-react';
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
import type { HealthResponse, ReadyResponse, ConfigResponse, ModelsUpdateRequest, ConfigReloadResponse } from '@/types/api';
import { useIndexingConfig, useUpdateIndexingConfig } from '@/hooks/useIndexingConfig';
import { useChatConfig, useUpdateChatConfig } from '@/hooks/useChatConfig';
import { toast } from '@/lib/toast';
import { useTheme } from '@/components/theme/ThemeProvider';

// ============================================================================
// Types
// ============================================================================

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

// ============================================================================
// Sub-components
// ============================================================================

/** Read-only key-value display row */
function ConfigRow({ label, value, mono = true }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <>
      <div className="text-muted-foreground text-sm">{label}:</div>
      <div className={`text-sm truncate ${mono ? 'font-mono text-xs' : ''}`} title={typeof value === 'string' ? value : undefined}>
        {value}
      </div>
    </>
  );
}

/** Status indicator with icon */
function StatusIndicator({ ok, yesText = 'Yes', noText = 'No' }: { ok: boolean; yesText?: string; noText?: string }) {
  return (
    <div className="flex items-center gap-1">
      {ok ? (
        <>
          <CheckCircle2 className="h-3 w-3 text-green-600" />
          <span className="text-xs">{yesText}</span>
        </>
      ) : (
        <>
          <XCircle className="h-3 w-3 text-red-600" />
          <span className="text-xs">{noText}</span>
        </>
      )}
    </div>
  );
}

/** Card wrapper for settings sections */
function SettingsCard({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-lg border p-4 space-y-3 ${className}`}>{children}</div>;
}

// ============================================================================
// Status Tab Content
// ============================================================================

function StatusTabContent({
  healthData,
  healthLoading,
  healthError,
  readyData,
  readyLoading,
  readyError,
}: {
  healthData?: HealthResponse;
  healthLoading: boolean;
  healthError: Error | null;
  readyData?: ReadyResponse;
  readyLoading: boolean;
  readyError: Error | null;
}) {
  const isHealthy = healthData?.status === 'healthy';
  const isReady = readyData?.ready === true;

  if (healthError || readyError) {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
        <div className="flex items-center gap-2 text-sm text-destructive">
          <XCircle className="h-5 w-5" />
          <span className="font-medium">Failed to connect to backend</span>
        </div>
        <p className="text-xs text-muted-foreground mt-2 ml-7">
          Make sure the backend server is running at the configured URL
        </p>
      </div>
    );
  }

  if (healthLoading || readyLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!healthData || !readyData) return null;

  return (
    <div className="space-y-4">
      <SettingsCard>
        <h4 className="text-sm font-medium flex items-center gap-2">
          <Server className="h-4 w-4" />
          Backend Health
        </h4>
        <div className="grid grid-cols-2 gap-3">
          {/* Health Status */}
          <div className="flex items-center justify-between col-span-2 p-3 rounded-md bg-muted/50">
            <div className="flex items-center gap-2">
              {isHealthy ? (
                <CheckCircle2 className="h-5 w-5 text-green-600" />
              ) : (
                <XCircle className="h-5 w-5 text-red-600" />
              )}
              <span className="font-medium">Health Status</span>
            </div>
            <Badge variant={isHealthy ? 'default' : 'destructive'}>{healthData.status}</Badge>
          </div>

          {/* Readiness Status */}
          <div className="flex items-center justify-between col-span-2 p-3 rounded-md bg-muted/50">
            <div className="flex items-center gap-2">
              {isReady ? (
                <CheckCircle2 className="h-5 w-5 text-green-600" />
              ) : (
                <AlertCircle className="h-5 w-5 text-yellow-600" />
              )}
              <span className="font-medium">Readiness</span>
            </div>
            <Badge variant={isReady ? 'default' : 'secondary'}>{readyData.status}</Badge>
          </div>
        </div>

        <Separator />

        <div className="grid grid-cols-2 gap-2">
          <ConfigRow label="Version" value={healthData.version} />
          <ConfigRow
            label="RAG Initialized"
            value={<StatusIndicator ok={healthData.rag_initialized} />}
            mono={false}
          />
        </div>
      </SettingsCard>
    </div>
  );
}

// ============================================================================
// Appearance Tab Content
// ============================================================================

function AppearanceTabContent() {
  const { theme, setTheme, actualTheme } = useTheme();

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Customize the appearance of the application.
      </p>

      <SettingsCard>
        <h4 className="text-sm font-medium flex items-center gap-2">
          <Palette className="h-4 w-4" />
          Theme
        </h4>
        <p className="text-xs text-muted-foreground">
          Select a theme for the application. Current applied theme: <span className="font-medium">{actualTheme}</span>
        </p>

        <div className="grid grid-cols-3 gap-3 mt-3">
          <button
            type="button"
            onClick={() => setTheme('light')}
            className={`flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-colors hover:bg-accent ${
              theme === 'light' ? 'border-primary bg-primary/5' : 'border-muted'
            }`}
          >
            <Sun className="h-6 w-6" />
            <span className="text-sm font-medium">Light</span>
            {theme === 'light' && <CheckCircle2 className="h-4 w-4 text-primary" />}
          </button>

          <button
            type="button"
            onClick={() => setTheme('dark')}
            className={`flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-colors hover:bg-accent ${
              theme === 'dark' ? 'border-primary bg-primary/5' : 'border-muted'
            }`}
          >
            <Moon className="h-6 w-6" />
            <span className="text-sm font-medium">Dark</span>
            {theme === 'dark' && <CheckCircle2 className="h-4 w-4 text-primary" />}
          </button>

          <button
            type="button"
            onClick={() => setTheme('system')}
            className={`flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-colors hover:bg-accent ${
              theme === 'system' ? 'border-primary bg-primary/5' : 'border-muted'
            }`}
          >
            <Monitor className="h-6 w-6" />
            <span className="text-sm font-medium">System</span>
            {theme === 'system' && <CheckCircle2 className="h-4 w-4 text-primary" />}
          </button>
        </div>
      </SettingsCard>
    </div>
  );
}

// ============================================================================
// Models Tab Content (Direct Editing - No Modify Button)
// ============================================================================

function ModelsTabContent({
  configData,
  configLoading,
  configError,
  editorState,
  setEditorState,
  onAutoSave,
  updateModelsMutation,
  hasChanges,
}: {
  configData?: ConfigResponse;
  configLoading: boolean;
  configError: Error | null;
  editorState: ModelEditorState;
  setEditorState: React.Dispatch<React.SetStateAction<ModelEditorState>>;
  onAutoSave: () => void;
  updateModelsMutation: { isPending: boolean };
  hasChanges: boolean;
}) {
  const [showEmbeddingAdvanced, setShowEmbeddingAdvanced] = useState(false);
  const [showRerankerAdvanced, setShowRerankerAdvanced] = useState(false);

  if (configError) {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
        <div className="text-sm text-destructive">Failed to load configuration</div>
      </div>
    );
  }

  if (configLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!configData) return null;

  return (
    <div className="space-y-4">
      {/* Action Bar - Auto save */}
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          Click any setting to edit. Changes are automatically saved and applied. Leave API key blank to keep existing.
        </p>
        {updateModelsMutation.isPending ? (
          <Badge variant="secondary" className="gap-2">
            <Loader2 className="h-3 w-3 animate-spin" />
            Saving…
          </Badge>
        ) : hasChanges ? (
          <Badge variant="outline">Unsaved changes</Badge>
        ) : (
          <Badge variant="outline">All changes saved</Badge>
        )}
      </div>

      {/* LLM Configuration */}
      <SettingsCard>
        <h4 className="text-sm font-medium">LLM Provider</h4>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-2">
            <Label>Provider</Label>
            <Select
              value={editorState.llm.provider}
              onValueChange={(v) => {
                setEditorState((s) => ({ ...s, llm: { ...s.llm, provider: v } }));
                onAutoSave();
              }}
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
              onChange={(e) => setEditorState((s) => ({ ...s, llm: { ...s.llm, model_name: e.target.value } }))}
              onBlur={onAutoSave}
              placeholder="e.g. gpt-4o-mini"
            />
          </div>
          <div className="space-y-2 col-span-2">
            <Label>Base URL (optional)</Label>
            <Input
              value={editorState.llm.base_url}
              onChange={(e) => setEditorState((s) => ({ ...s, llm: { ...s.llm, base_url: e.target.value } }))}
              onBlur={onAutoSave}
              placeholder="e.g. https://api.openai.com/v1"
            />
          </div>
          <div className="space-y-2 col-span-2">
            <Label>API Key (leave blank to keep)</Label>
            <Input
              type="password"
              value={editorState.llm.api_key}
              onChange={(e) => setEditorState((s) => ({ ...s, llm: { ...s.llm, api_key: e.target.value } }))}
              onBlur={onAutoSave}
              placeholder="sk-..."
            />
          </div>
          <div className="space-y-2">
            <Label>Temperature</Label>
            <Input
              type="number"
              value={editorState.llm.temperature}
              onChange={(e) => setEditorState((s) => ({ ...s, llm: { ...s.llm, temperature: e.target.value } }))}
              onBlur={onAutoSave}
              placeholder="0.7"
            />
          </div>
          <div className="space-y-2">
            <Label>Max Tokens</Label>
            <Input
              type="number"
              value={editorState.llm.max_tokens}
              onChange={(e) => setEditorState((s) => ({ ...s, llm: { ...s.llm, max_tokens: e.target.value } }))}
              onBlur={onAutoSave}
              placeholder="4096"
            />
          </div>
        </div>
      </SettingsCard>

      {/* Embedding Configuration */}
      <SettingsCard>
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-medium">Embedding Model</h4>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowEmbeddingAdvanced((v) => !v)}
          >
            {showEmbeddingAdvanced ? 'Hide Advanced' : 'Advanced'}
          </Button>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-2">
            <Label>Provider</Label>
            <Select
              value={editorState.embedding.provider}
              onValueChange={(v) => {
                setEditorState((s) => ({ ...s, embedding: { ...s.embedding, provider: v } }));
                onAutoSave();
              }}
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
                setEditorState((s) => ({ ...s, embedding: { ...s.embedding, model_name: e.target.value } }))
              }
              onBlur={onAutoSave}
              placeholder="e.g. Qwen/Qwen3-VL-Embedding-2B"
            />
          </div>
          <div className="space-y-2">
            <Label>Device</Label>
            <Input
              value={editorState.embedding.device}
              onChange={(e) =>
                setEditorState((s) => ({ ...s, embedding: { ...s.embedding, device: e.target.value } }))
              }
              onBlur={onAutoSave}
              placeholder="cuda:0 / cpu"
            />
          </div>
          <div className="space-y-2">
            <Label>Embedding Dim</Label>
            <Input
              type="number"
              value={editorState.embedding.embedding_dim}
              onChange={(e) =>
                setEditorState((s) => ({ ...s, embedding: { ...s.embedding, embedding_dim: e.target.value } }))
              }
              onBlur={onAutoSave}
              placeholder="e.g. 2048"
            />
          </div>
          <div className="space-y-2">
            <Label>DType</Label>
            <Input
              value={editorState.embedding.dtype}
              onChange={(e) =>
                setEditorState((s) => ({ ...s, embedding: { ...s.embedding, dtype: e.target.value } }))
              }
              onBlur={onAutoSave}
              placeholder="float16"
            />
          </div>
          <div className="space-y-2">
            <Label>Max Length</Label>
            <Input
              type="number"
              value={editorState.embedding.max_length}
              onChange={(e) =>
                setEditorState((s) => ({ ...s, embedding: { ...s.embedding, max_length: e.target.value } }))
              }
              onBlur={onAutoSave}
            />
          </div>
          <div className="space-y-2 col-span-2">
            <Label>Base URL (optional)</Label>
            <Input
              value={editorState.embedding.base_url}
              onChange={(e) =>
                setEditorState((s) => ({ ...s, embedding: { ...s.embedding, base_url: e.target.value } }))
              }
              onBlur={onAutoSave}
              placeholder="(leave empty for local_gpu)"
            />
          </div>
          <div className="space-y-2 col-span-2">
            <Label>API Key (leave blank to keep)</Label>
            <Input
              type="password"
              value={editorState.embedding.api_key}
              onChange={(e) =>
                setEditorState((s) => ({ ...s, embedding: { ...s.embedding, api_key: e.target.value } }))
              }
              onBlur={onAutoSave}
            />
          </div>
          <div className="flex items-center justify-between rounded-md border p-3 col-span-2">
            <div className="space-y-1">
              <Label>Normalize</Label>
              <div className="text-xs text-muted-foreground">L2-normalize output embeddings</div>
            </div>
            <Switch
              checked={editorState.embedding.normalize}
              onCheckedChange={(checked) => {
                setEditorState((s) => ({ ...s, embedding: { ...s.embedding, normalize: checked } }));
                onAutoSave();
              }}
            />
          </div>

          {showEmbeddingAdvanced ? (
            <>
              <div className="col-span-2">
                <Separator />
              </div>

              <div className="space-y-2">
                <Label>Attention</Label>
                <Input
                  value={editorState.embedding.attn_implementation}
                  onChange={(e) =>
                    setEditorState((s) => ({
                      ...s,
                      embedding: { ...s.embedding, attn_implementation: e.target.value },
                    }))
                  }
                  onBlur={onAutoSave}
                  placeholder="sdpa / eager"
                />
              </div>

              <div className="space-y-2">
                <Label>Min Image Tokens</Label>
                <Input
                  type="number"
                  value={editorState.embedding.min_image_tokens}
                  onChange={(e) =>
                    setEditorState((s) => ({
                      ...s,
                      embedding: { ...s.embedding, min_image_tokens: e.target.value },
                    }))
                  }
                  onBlur={onAutoSave}
                />
              </div>

              <div className="space-y-2">
                <Label>Max Image Tokens</Label>
                <Input
                  type="number"
                  value={editorState.embedding.max_image_tokens}
                  onChange={(e) =>
                    setEditorState((s) => ({
                      ...s,
                      embedding: { ...s.embedding, max_image_tokens: e.target.value },
                    }))
                  }
                  onBlur={onAutoSave}
                />
              </div>

              <div className="space-y-2 col-span-2">
                <Label>Default Instruction</Label>
                <Input
                  value={editorState.embedding.default_instruction}
                  onChange={(e) =>
                    setEditorState((s) => ({
                      ...s,
                      embedding: { ...s.embedding, default_instruction: e.target.value },
                    }))
                  }
                  onBlur={onAutoSave}
                  placeholder="Represent the user's input."
                />
              </div>

              <div className="flex items-center justify-between rounded-md border p-3 col-span-2">
                <div className="space-y-1">
                  <Label>Allow Image URLs</Label>
                  <div className="text-xs text-muted-foreground">Security risk: keep off unless trusted</div>
                </div>
                <Switch
                  checked={editorState.embedding.allow_image_urls}
                  onCheckedChange={(checked) => {
                    setEditorState((s) => ({
                      ...s,
                      embedding: { ...s.embedding, allow_image_urls: checked },
                    }));
                    onAutoSave();
                  }}
                />
              </div>
            </>
          ) : null}
        </div>
      </SettingsCard>

      {/* Vision Model */}
      <SettingsCard>
        <h4 className="text-sm font-medium">Vision Model</h4>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-2">
            <Label>Provider</Label>
            <Select
              value={editorState.vision.provider}
              onValueChange={(v) => {
                setEditorState((s) => ({ ...s, vision: { ...s.vision, provider: v } }));
                onAutoSave();
              }}
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
                setEditorState((s) => ({ ...s, vision: { ...s.vision, model_name: e.target.value } }))
              }
              onBlur={onAutoSave}
              placeholder="e.g. gpt-4o-mini"
            />
          </div>
          <div className="space-y-2 col-span-2">
            <Label>Base URL (optional)</Label>
            <Input
              value={editorState.vision.base_url}
              onChange={(e) =>
                setEditorState((s) => ({ ...s, vision: { ...s.vision, base_url: e.target.value } }))
              }
              onBlur={onAutoSave}
              placeholder="e.g. https://api.openai.com/v1"
            />
          </div>
          <div className="space-y-2 col-span-2">
            <Label>API Key (leave blank to keep)</Label>
            <Input
              type="password"
              value={editorState.vision.api_key}
              onChange={(e) =>
                setEditorState((s) => ({ ...s, vision: { ...s.vision, api_key: e.target.value } }))
              }
              onBlur={onAutoSave}
              placeholder="sk-..."
            />
          </div>
        </div>
      </SettingsCard>

      {/* Reranker */}
      <SettingsCard>
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-medium">Reranker</h4>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowRerankerAdvanced((v) => !v)}
          >
            {showRerankerAdvanced ? 'Hide Advanced' : 'Advanced'}
          </Button>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="flex items-center justify-between rounded-md border p-3 col-span-2">
            <div className="space-y-1">
              <Label>Enable Reranker</Label>
              <div className="text-xs text-muted-foreground">Applies to retrieval ranking</div>
            </div>
            <Switch
              checked={editorState.reranker.enabled}
              onCheckedChange={(checked) => {
                setEditorState((s) => ({ ...s, reranker: { ...s.reranker, enabled: checked } }));
                onAutoSave();
              }}
            />
          </div>

          <div className="space-y-2">
            <Label>Provider</Label>
            <Select
              value={editorState.reranker.provider}
              onValueChange={(v) => {
                setEditorState((s) => ({ ...s, reranker: { ...s.reranker, provider: v } }));
                onAutoSave();
              }}
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
                setEditorState((s) => ({ ...s, reranker: { ...s.reranker, model_name: e.target.value } }))
              }
              onBlur={onAutoSave}
              disabled={!editorState.reranker.enabled}
              placeholder="e.g. Qwen/Qwen3-VL-Reranker-2B"
            />
          </div>

          <div className="space-y-2">
            <Label>Device</Label>
            <Input
              value={editorState.reranker.device}
              onChange={(e) =>
                setEditorState((s) => ({ ...s, reranker: { ...s.reranker, device: e.target.value } }))
              }
              onBlur={onAutoSave}
              disabled={!editorState.reranker.enabled}
              placeholder="cuda:0 / cpu"
            />
          </div>

          <div className="space-y-2">
            <Label>Batch Size</Label>
            <Input
              type="number"
              value={editorState.reranker.batch_size}
              onChange={(e) =>
                setEditorState((s) => ({ ...s, reranker: { ...s.reranker, batch_size: e.target.value } }))
              }
              onBlur={onAutoSave}
              disabled={!editorState.reranker.enabled}
            />
          </div>

          <div className="space-y-2 col-span-2">
            <Label>Model Path (optional)</Label>
            <Input
              value={editorState.reranker.model_path}
              onChange={(e) =>
                setEditorState((s) => ({ ...s, reranker: { ...s.reranker, model_path: e.target.value } }))
              }
              onBlur={onAutoSave}
              disabled={!editorState.reranker.enabled}
              placeholder="/path/to/local/model (optional)"
            />
          </div>

          <div className="space-y-2 col-span-2">
            <Label>Base URL (optional)</Label>
            <Input
              value={editorState.reranker.base_url}
              onChange={(e) =>
                setEditorState((s) => ({ ...s, reranker: { ...s.reranker, base_url: e.target.value } }))
              }
              onBlur={onAutoSave}
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
                setEditorState((s) => ({ ...s, reranker: { ...s.reranker, api_key: e.target.value } }))
              }
              onBlur={onAutoSave}
              disabled={!editorState.reranker.enabled}
            />
          </div>

          <div className="space-y-2 col-span-2">
            <Label>Instruction (optional)</Label>
            <Textarea
              value={editorState.reranker.instruction}
              onChange={(e) =>
                setEditorState((s) => ({ ...s, reranker: { ...s.reranker, instruction: e.target.value } }))
              }
              onBlur={onAutoSave}
              disabled={!editorState.reranker.enabled}
              placeholder="(optional)"
              className="min-h-[60px]"
            />
          </div>

          {showRerankerAdvanced ? (
            <>
              <div className="col-span-2">
                <Separator />
              </div>

              <div className="space-y-2">
                <Label>DType</Label>
                <Input
                  value={editorState.reranker.dtype}
                  onChange={(e) =>
                    setEditorState((s) => ({ ...s, reranker: { ...s.reranker, dtype: e.target.value } }))
                  }
                  onBlur={onAutoSave}
                  disabled={!editorState.reranker.enabled}
                  placeholder="float16"
                />
              </div>

              <div className="space-y-2">
                <Label>Attention</Label>
                <Input
                  value={editorState.reranker.attn_implementation}
                  onChange={(e) =>
                    setEditorState((s) => ({
                      ...s,
                      reranker: { ...s.reranker, attn_implementation: e.target.value },
                    }))
                  }
                  onBlur={onAutoSave}
                  disabled={!editorState.reranker.enabled}
                  placeholder="sdpa / eager"
                />
              </div>

              <div className="space-y-2">
                <Label>Max Length</Label>
                <Input
                  type="number"
                  value={editorState.reranker.max_length}
                  onChange={(e) =>
                    setEditorState((s) => ({ ...s, reranker: { ...s.reranker, max_length: e.target.value } }))
                  }
                  onBlur={onAutoSave}
                  disabled={!editorState.reranker.enabled}
                />
              </div>

              <div className="space-y-2">
                <Label>Min Image Tokens</Label>
                <Input
                  type="number"
                  value={editorState.reranker.min_image_tokens}
                  onChange={(e) =>
                    setEditorState((s) => ({
                      ...s,
                      reranker: { ...s.reranker, min_image_tokens: e.target.value },
                    }))
                  }
                  onBlur={onAutoSave}
                  disabled={!editorState.reranker.enabled}
                />
              </div>

              <div className="space-y-2">
                <Label>Max Image Tokens</Label>
                <Input
                  type="number"
                  value={editorState.reranker.max_image_tokens}
                  onChange={(e) =>
                    setEditorState((s) => ({
                      ...s,
                      reranker: { ...s.reranker, max_image_tokens: e.target.value },
                    }))
                  }
                  onBlur={onAutoSave}
                  disabled={!editorState.reranker.enabled}
                />
              </div>

              <div className="space-y-2 col-span-2">
                <Label>System Prompt (optional)</Label>
                <Textarea
                  value={editorState.reranker.system_prompt}
                  onChange={(e) =>
                    setEditorState((s) => ({
                      ...s,
                      reranker: { ...s.reranker, system_prompt: e.target.value },
                    }))
                  }
                  onBlur={onAutoSave}
                  disabled={!editorState.reranker.enabled}
                  className="min-h-[80px]"
                  placeholder="(optional)"
                />
              </div>

              <div className="flex items-center justify-between rounded-md border p-3 col-span-2">
                <div className="space-y-1">
                  <Label>Allow Image URLs</Label>
                  <div className="text-xs text-muted-foreground">Security risk: keep off unless trusted</div>
                </div>
                <Switch
                  checked={editorState.reranker.allow_image_urls}
                  onCheckedChange={(checked) => {
                    setEditorState((s) => ({
                      ...s,
                      reranker: { ...s.reranker, allow_image_urls: checked },
                    }));
                    onAutoSave();
                  }}
                  disabled={!editorState.reranker.enabled}
                />
              </div>
            </>
          ) : null}
        </div>
      </SettingsCard>
    </div>
  );
}

// ============================================================================
// Indexing Tab Content
// ============================================================================

function IndexingTabContent() {
  const { config, isLoading: isLoadingConfig } = useIndexingConfig();
  const { updateConfig, isUpdating } = useUpdateIndexingConfig();

  const [autoIndexingEnabled, setAutoIndexingEnabled] = useState(true);
  const [scanInterval, setScanInterval] = useState('60');
  const [maxFilesPerBatch, setMaxFilesPerBatch] = useState('5');
  const [hasChanges, setHasChanges] = useState(false);

  // Sync local state with fetched config
  useEffect(() => {
    if (config) {
      setAutoIndexingEnabled(config.auto_indexing_enabled);
      setScanInterval(String(config.indexing_scan_interval));
      setMaxFilesPerBatch(String(config.indexing_max_files_per_batch));
      setHasChanges(false);
    }
  }, [config]);

  // Track changes
  useEffect(() => {
    if (!config) return;
    const changed =
      autoIndexingEnabled !== config.auto_indexing_enabled ||
      scanInterval !== String(config.indexing_scan_interval) ||
      maxFilesPerBatch !== String(config.indexing_max_files_per_batch);
    setHasChanges(changed);
  }, [autoIndexingEnabled, scanInterval, maxFilesPerBatch, config]);

  const handleSave = (
    overrides: Partial<{
      autoIndexingEnabled: boolean;
      scanInterval: string;
      maxFilesPerBatch: string;
    }> = {}
  ) => {
    if (!config) return;
    if (isUpdating) return;

    const enabled = overrides.autoIndexingEnabled ?? autoIndexingEnabled;
    const nextScanInterval = overrides.scanInterval ?? scanInterval;
    const nextMaxFilesPerBatch = overrides.maxFilesPerBatch ?? maxFilesPerBatch;

    const changed =
      enabled !== config.auto_indexing_enabled ||
      nextScanInterval !== String(config.indexing_scan_interval) ||
      nextMaxFilesPerBatch !== String(config.indexing_max_files_per_batch);
    if (!changed) return;

    const interval = parseInt(nextScanInterval, 10);
    const maxFiles = parseInt(nextMaxFilesPerBatch, 10);

    if (isNaN(interval) || interval < 1) {
      toast.error('Invalid Input', 'Scan interval must be at least 1 second');
      setScanInterval(String(config.indexing_scan_interval));
      return;
    }
    if (isNaN(maxFiles) || maxFiles < 1) {
      toast.error('Invalid Input', 'Max files per batch must be at least 1');
      setMaxFilesPerBatch(String(config.indexing_max_files_per_batch));
      return;
    }

    updateConfig({
      auto_indexing_enabled: enabled,
      indexing_scan_interval: interval,
      indexing_max_files_per_batch: maxFiles,
    });
  };

  if (isLoadingConfig) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          Configure automatic background indexing for new and modified documents. Changes are saved automatically.
        </p>
        {isUpdating ? (
          <Badge variant="secondary" className="gap-2">
            <Loader2 className="h-3 w-3 animate-spin" />
            Saving…
          </Badge>
        ) : hasChanges ? (
          <Badge variant="outline">Unsaved changes</Badge>
        ) : (
          <Badge variant="outline">All changes saved</Badge>
        )}
      </div>

      <SettingsCard>
        <div className="space-y-4">
          {/* Auto Indexing Enabled Switch */}
          <div className="flex items-center justify-between">
            <div className="space-y-1">
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
              onCheckedChange={(checked) => {
                setAutoIndexingEnabled(checked);
                handleSave({ autoIndexingEnabled: checked });
              }}
              disabled={isUpdating}
            />
          </div>

          <Separator />

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
              value={scanInterval}
              onChange={(e) => setScanInterval(e.target.value)}
              onBlur={() => handleSave()}
              disabled={isUpdating}
            />
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
              value={maxFilesPerBatch}
              onChange={(e) => setMaxFilesPerBatch(e.target.value)}
              onBlur={() => handleSave()}
              disabled={isUpdating}
            />
            <p className="text-xs text-muted-foreground">
              Maximum number of files to process per iteration (minimum: 1)
            </p>
          </div>
        </div>
      </SettingsCard>

    </div>
  );
}

// ============================================================================
// Chat Tab Content
// ============================================================================

function ChatTabContent() {
  const { config, isLoading: isLoadingConfig } = useChatConfig();
  const { updateConfig, isUpdating } = useUpdateChatConfig();

  const [autoAttachImages, setAutoAttachImages] = useState(true);
  const [maxRetrievedImages, setMaxRetrievedImages] = useState('4');
  const [hasChanges, setHasChanges] = useState(false);

  // Sync local state with fetched config
  useEffect(() => {
    if (config) {
      setAutoAttachImages(config.auto_attach_retrieved_images);
      setMaxRetrievedImages(String(config.max_retrieved_images));
      setHasChanges(false);
    }
  }, [config]);

  // Track changes
  useEffect(() => {
    if (!config) return;
    const changed =
      autoAttachImages !== config.auto_attach_retrieved_images ||
      maxRetrievedImages !== String(config.max_retrieved_images);
    setHasChanges(changed);
  }, [autoAttachImages, maxRetrievedImages, config]);

  const handleSave = (
    overrides: Partial<{
      autoAttachImages: boolean;
      maxRetrievedImages: string;
    }> = {}
  ) => {
    if (!config) return;
    if (isUpdating) return;

    const enabled = overrides.autoAttachImages ?? autoAttachImages;
    const nextMaxImages = overrides.maxRetrievedImages ?? maxRetrievedImages;

    const changed =
      enabled !== config.auto_attach_retrieved_images ||
      nextMaxImages !== String(config.max_retrieved_images);
    if (!changed) return;

    const maxImages = parseInt(nextMaxImages, 10);

    if (isNaN(maxImages) || maxImages < 0) {
      toast.error('Invalid Input', 'Max retrieved images must be at least 0');
      setMaxRetrievedImages(String(config.max_retrieved_images));
      return;
    }

    updateConfig({
      auto_attach_retrieved_images: enabled,
      max_retrieved_images: maxImages,
    });
  };

  if (isLoadingConfig) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          Configure chat settings for auto-attaching retrieved images to assistant responses.
        </p>
        {isUpdating ? (
          <Badge variant="secondary" className="gap-2">
            <Loader2 className="h-3 w-3 animate-spin" />
            Saving…
          </Badge>
        ) : hasChanges ? (
          <Badge variant="outline">Unsaved changes</Badge>
        ) : (
          <Badge variant="outline">All changes saved</Badge>
        )}
      </div>

      <SettingsCard>
        <div className="space-y-4">
          {/* Auto Attach Images Switch */}
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <Label htmlFor="auto_attach_images" className="text-sm font-medium">
                Auto-attach Retrieved Images
              </Label>
              <p className="text-xs text-muted-foreground">
                Automatically attach relevant images from RAG retrieval context to assistant responses
              </p>
            </div>
            <Switch
              id="auto_attach_images"
              checked={autoAttachImages}
              onCheckedChange={(checked) => {
                setAutoAttachImages(checked);
                handleSave({ autoAttachImages: checked });
              }}
              disabled={isUpdating}
            />
          </div>

          <Separator />

          {/* Max Retrieved Images Input */}
          <div className="space-y-2">
            <Label htmlFor="max_retrieved_images" className="text-sm font-medium">
              Maximum Retrieved Images
            </Label>
            <Input
              id="max_retrieved_images"
              type="number"
              min="0"
              step="1"
              value={maxRetrievedImages}
              onChange={(e) => setMaxRetrievedImages(e.target.value)}
              onBlur={() => handleSave()}
              disabled={isUpdating}
            />
            <p className="text-xs text-muted-foreground">
              Maximum number of images to attach per response (0 to disable)
            </p>
          </div>
        </div>
      </SettingsCard>

    </div>
  );
}

// ============================================================================
// System Tab Content
// ============================================================================

function SystemTabContent({
  configData,
  configLoading,
  configError,
  handleReloadConfig,
  reloadMutation,
  lastReloadResult,
}: {
  configData?: ConfigResponse;
  configLoading: boolean;
  configError: Error | null;
  handleReloadConfig: () => void;
  reloadMutation: { isPending: boolean };
  lastReloadResult?: ConfigReloadResponse | null;
}) {
  if (configError) {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
        <div className="text-sm text-destructive">Failed to load configuration</div>
      </div>
    );
  }

  if (configLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!configData) return null;

  return (
    <div className="space-y-4">
      {/* Reload Config Action */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">System configuration is read-only. Use Reload to refresh from files.</p>
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
      </div>

      {/* Last Reload Result */}
      {lastReloadResult && (
        <div
          className={`rounded-lg border p-3 text-sm ${
            lastReloadResult.status === 'success'
              ? 'border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/20'
              : lastReloadResult.status === 'partial'
                ? 'border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/20'
                : 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20'
          }`}
        >
          <div className="font-medium mb-1">
            {lastReloadResult.status === 'success'
              ? 'Reload Successful'
              : lastReloadResult.status === 'partial'
                ? 'Partial Reload'
                : 'Reload Failed'}
          </div>
          <p className="text-xs text-muted-foreground">{lastReloadResult.message}</p>
          {lastReloadResult.reloaded_files.length > 0 && (
            <div className="mt-2">
              <span className="text-xs font-medium">Reloaded files:</span>
              <ul className="text-xs text-muted-foreground ml-4 list-disc">
                {lastReloadResult.reloaded_files.map((file) => (
                  <li key={file}>{file}</li>
                ))}
              </ul>
            </div>
          )}
          {Object.keys(lastReloadResult.errors).length > 0 && (
            <div className="mt-2">
              <span className="text-xs font-medium text-destructive">Errors:</span>
              <ul className="text-xs text-destructive ml-4 list-disc">
                {Object.entries(lastReloadResult.errors).map(([file, error]) => (
                  <li key={file}>
                    {file}: {error}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Backend Server */}
      <SettingsCard>
        <h4 className="text-sm font-medium flex items-center gap-2">
          <Server className="h-4 w-4" />
          Backend Server
        </h4>
        <div className="grid grid-cols-2 gap-2">
          <ConfigRow label="Host" value={configData.backend.host} />
          <ConfigRow label="Port" value={String(configData.backend.port)} />
          <ConfigRow
            label="Env File"
            value={configData.backend.env_file_loaded || 'Not loaded from file'}
          />
          <ConfigRow label="CORS Origins" value={configData.backend.cors_origins.join(', ')} />
        </div>
      </SettingsCard>

      {/* Storage */}
      <SettingsCard>
        <h4 className="text-sm font-medium flex items-center gap-2">
          <Database className="h-4 w-4" />
          Storage
        </h4>
        <div className="grid grid-cols-2 gap-2">
          <ConfigRow label="Working Directory" value={configData.storage.working_dir} />
          <ConfigRow label="Upload Directory" value={configData.storage.upload_dir} />
        </div>
      </SettingsCard>

      {/* Processing */}
      <SettingsCard>
        <h4 className="text-sm font-medium flex items-center gap-2">
          <Cpu className="h-4 w-4" />
          Processing
        </h4>
        <div className="grid grid-cols-2 gap-2">
          <ConfigRow label="Parser" value={configData.processing.parser} />
          <ConfigRow
            label="Image Processing"
            value={<StatusIndicator ok={configData.processing.enable_image_processing} yesText="Enabled" noText="Disabled" />}
            mono={false}
          />
          <ConfigRow
            label="Table Processing"
            value={<StatusIndicator ok={configData.processing.enable_table_processing} yesText="Enabled" noText="Disabled" />}
            mono={false}
          />
          <ConfigRow
            label="Equation Processing"
            value={<StatusIndicator ok={configData.processing.enable_equation_processing} yesText="Enabled" noText="Disabled" />}
            mono={false}
          />
        </div>
      </SettingsCard>

      {/* Chat Settings */}
      {configData.chat && (
        <SettingsCard>
          <h4 className="text-sm font-medium flex items-center gap-2">
            <MessageSquare className="h-4 w-4" />
            Chat Settings
          </h4>
          <div className="grid grid-cols-2 gap-2">
            <ConfigRow
              label="Auto-attach Retrieved Images"
              value={<StatusIndicator ok={configData.chat.auto_attach_retrieved_images} yesText="Enabled" noText="Disabled" />}
              mono={false}
            />
            <ConfigRow
              label="Max Retrieved Images"
              value={String(configData.chat.max_retrieved_images)}
            />
          </div>
        </SettingsCard>
      )}
    </div>
  );
}

// ============================================================================
// Main Settings Modal Component
// ============================================================================

/**
 * Settings Modal Component
 *
 * Modal dialog for viewing and editing backend configuration.
 * Organized into tabs for better navigation:
 * - Status: Health and readiness information
 * - Appearance: Theme settings (light/dark/system)
 * - Models: Editable model configuration (LLM, Embedding, Vision, Reranker)
 * - Indexing: Background indexing settings
 * - System: Read-only backend, storage, and processing configuration
 */
export function SettingsModal() {
  const [open, setOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('status');
  const [editorState, setEditorState] = useState<ModelEditorState>(DEFAULT_EDITOR_STATE);
  const [lastReloadResult, setLastReloadResult] = useState<ConfigReloadResponse | null>(null);
  const baselineStateRef = useRef<ModelEditorState>(DEFAULT_EDITOR_STATE);
  const modelsAutoSaveTimerRef = useRef<number | null>(null);

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
    refetchInterval: open ? 5000 : false,
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
      setLastReloadResult(data);
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

  // Prefill editor state from backend config
  useEffect(() => {
    if (!open || !configData) return;

    setEditorState((prev) => {
      const next: ModelEditorState = {
        ...prev,
        llm: {
          provider: configData.models.llm.provider || prev.llm.provider,
          model_name: configData.models.llm.model_name || prev.llm.model_name,
          base_url: configData.models.llm.base_url ?? '',
          api_key: '',
          temperature:
            configData.models.llm.temperature !== undefined ? String(configData.models.llm.temperature) : '',
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
          embedding_dim:
            configData.models.embedding.embedding_dim !== undefined
              ? String(configData.models.embedding.embedding_dim)
              : '',
          device: configData.models.embedding.device ?? prev.embedding.device,
          dtype: configData.models.embedding.dtype ?? prev.embedding.dtype,
          attn_implementation: configData.models.embedding.attn_implementation ?? prev.embedding.attn_implementation,
          max_length:
            configData.models.embedding.max_length !== undefined
              ? String(configData.models.embedding.max_length)
              : prev.embedding.max_length,
          default_instruction: configData.models.embedding.default_instruction ?? '',
          normalize: configData.models.embedding.normalize ?? prev.embedding.normalize,
          allow_image_urls: configData.models.embedding.allow_image_urls ?? prev.embedding.allow_image_urls,
          min_image_tokens:
            configData.models.embedding.min_image_tokens !== undefined
              ? String(configData.models.embedding.min_image_tokens)
              : prev.embedding.min_image_tokens,
          max_image_tokens:
            configData.models.embedding.max_image_tokens !== undefined
              ? String(configData.models.embedding.max_image_tokens)
              : prev.embedding.max_image_tokens,
        },
        reranker: {
          enabled: configData.models.reranker?.enabled ?? false,
          provider: configData.models.reranker?.provider ?? prev.reranker.provider,
          model_name: configData.models.reranker?.model_name ?? '',
          model_path: configData.models.reranker?.model_path ?? '',
          device: configData.models.reranker?.device ?? prev.reranker.device,
          dtype: configData.models.reranker?.dtype ?? prev.reranker.dtype,
          attn_implementation: configData.models.reranker?.attn_implementation ?? prev.reranker.attn_implementation,
          batch_size:
            configData.models.reranker?.batch_size !== undefined
              ? String(configData.models.reranker.batch_size)
              : prev.reranker.batch_size,
          max_length:
            configData.models.reranker?.max_length !== undefined
              ? String(configData.models.reranker.max_length)
              : prev.reranker.max_length,
          instruction: '',
          system_prompt: '',
          api_key: '',
          base_url: configData.models.reranker?.base_url ?? '',
          min_image_tokens:
            configData.models.reranker?.min_image_tokens !== undefined
              ? String(configData.models.reranker.min_image_tokens)
              : prev.reranker.min_image_tokens,
          max_image_tokens:
            configData.models.reranker?.max_image_tokens !== undefined
              ? String(configData.models.reranker.max_image_tokens)
              : prev.reranker.max_image_tokens,
          allow_image_urls: configData.models.reranker?.allow_image_urls ?? prev.reranker.allow_image_urls,
        },
      };

      baselineStateRef.current = next;
      return next;
    });
  }, [open, configData]);

  // Check if there are changes to the model config
  const hasModelChanges = useCallback(() => {
    const baseline = baselineStateRef.current;
    // Check LLM changes
    if (editorState.llm.provider !== baseline.llm.provider) return true;
    if (editorState.llm.model_name !== baseline.llm.model_name) return true;
    if (editorState.llm.base_url !== baseline.llm.base_url) return true;
    if (editorState.llm.api_key.trim()) return true;
    if (editorState.llm.temperature.trim() !== baseline.llm.temperature.trim()) return true;
    if (editorState.llm.max_tokens.trim() !== baseline.llm.max_tokens.trim()) return true;
    // Check Vision changes
    if (editorState.vision.provider !== baseline.vision.provider) return true;
    if (editorState.vision.model_name !== baseline.vision.model_name) return true;
    if (editorState.vision.base_url !== baseline.vision.base_url) return true;
    if (editorState.vision.api_key.trim()) return true;
    // Check Embedding changes
    if (editorState.embedding.provider !== baseline.embedding.provider) return true;
    if (editorState.embedding.model_name !== baseline.embedding.model_name) return true;
    if (editorState.embedding.base_url !== baseline.embedding.base_url) return true;
    if (editorState.embedding.api_key.trim()) return true;
    if (editorState.embedding.embedding_dim.trim() !== baseline.embedding.embedding_dim.trim()) return true;
    if (editorState.embedding.device !== baseline.embedding.device) return true;
    if (editorState.embedding.dtype !== baseline.embedding.dtype) return true;
    if (editorState.embedding.attn_implementation !== baseline.embedding.attn_implementation) return true;
    if (editorState.embedding.max_length.trim() !== baseline.embedding.max_length.trim()) return true;
    if (editorState.embedding.default_instruction !== baseline.embedding.default_instruction) return true;
    if (editorState.embedding.normalize !== baseline.embedding.normalize) return true;
    if (editorState.embedding.allow_image_urls !== baseline.embedding.allow_image_urls) return true;
    if (editorState.embedding.min_image_tokens.trim() !== baseline.embedding.min_image_tokens.trim()) return true;
    if (editorState.embedding.max_image_tokens.trim() !== baseline.embedding.max_image_tokens.trim()) return true;
    // Check Reranker changes
    if (editorState.reranker.enabled !== baseline.reranker.enabled) return true;
    if (editorState.reranker.provider !== baseline.reranker.provider) return true;
    if (editorState.reranker.model_name !== baseline.reranker.model_name) return true;
    if (editorState.reranker.model_path !== baseline.reranker.model_path) return true;
    if (editorState.reranker.device !== baseline.reranker.device) return true;
    if (editorState.reranker.dtype !== baseline.reranker.dtype) return true;
    if (editorState.reranker.attn_implementation !== baseline.reranker.attn_implementation) return true;
    if (editorState.reranker.batch_size.trim() !== baseline.reranker.batch_size.trim()) return true;
    if (editorState.reranker.max_length.trim() !== baseline.reranker.max_length.trim()) return true;
    if (editorState.reranker.instruction.trim()) return true;
    if (editorState.reranker.system_prompt.trim()) return true;
    if (editorState.reranker.api_key.trim()) return true;
    if (editorState.reranker.base_url !== baseline.reranker.base_url) return true;
    if (editorState.reranker.min_image_tokens.trim() !== baseline.reranker.min_image_tokens.trim()) return true;
    if (editorState.reranker.max_image_tokens.trim() !== baseline.reranker.max_image_tokens.trim()) return true;
    if (editorState.reranker.allow_image_urls !== baseline.reranker.allow_image_urls) return true;
    return false;
  }, [editorState]);

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
    if (editorState.llm.temperature.trim() !== baseline.llm.temperature.trim())
      llmUpdate.temperature = toFloat(editorState.llm.temperature);
    if (editorState.llm.max_tokens.trim() !== baseline.llm.max_tokens.trim())
      llmUpdate.max_tokens = toInt(editorState.llm.max_tokens);
    if (Object.keys(llmUpdate).length > 0) {
      if (llmUpdate.model_name !== undefined && !llmUpdate.model_name.trim()) {
        toast.error('Missing LLM Model', 'Please fill LLM model_name');
        return;
      }
      requestBody.llm = llmUpdate;
    }

    const visionUpdate: NonNullable<ModelsUpdateRequest['vision']> = {};
    if (editorState.vision.provider !== baseline.vision.provider) visionUpdate.provider = editorState.vision.provider;
    if (editorState.vision.model_name !== baseline.vision.model_name)
      visionUpdate.model_name = editorState.vision.model_name;
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
    if (editorState.embedding.provider !== baseline.embedding.provider)
      embeddingUpdate.provider = editorState.embedding.provider;
    if (editorState.embedding.model_name !== baseline.embedding.model_name)
      embeddingUpdate.model_name = editorState.embedding.model_name;
    if (editorState.embedding.base_url !== baseline.embedding.base_url)
      embeddingUpdate.base_url = editorState.embedding.base_url;
    if (editorState.embedding.api_key.trim()) embeddingUpdate.api_key = editorState.embedding.api_key;
    if (editorState.embedding.embedding_dim.trim() !== baseline.embedding.embedding_dim.trim())
      embeddingUpdate.embedding_dim = toInt(editorState.embedding.embedding_dim);
    if (editorState.embedding.device !== baseline.embedding.device)
      embeddingUpdate.device = editorState.embedding.device;
    if (editorState.embedding.dtype !== baseline.embedding.dtype) embeddingUpdate.dtype = editorState.embedding.dtype;
    if (editorState.embedding.attn_implementation !== baseline.embedding.attn_implementation)
      embeddingUpdate.attn_implementation = editorState.embedding.attn_implementation;
    if (editorState.embedding.max_length.trim() !== baseline.embedding.max_length.trim())
      embeddingUpdate.max_length = toInt(editorState.embedding.max_length);
    if (editorState.embedding.default_instruction !== baseline.embedding.default_instruction)
      embeddingUpdate.default_instruction = editorState.embedding.default_instruction;
    if (editorState.embedding.normalize !== baseline.embedding.normalize)
      embeddingUpdate.normalize = editorState.embedding.normalize;
    if (editorState.embedding.allow_image_urls !== baseline.embedding.allow_image_urls)
      embeddingUpdate.allow_image_urls = editorState.embedding.allow_image_urls;
    if (editorState.embedding.min_image_tokens.trim() !== baseline.embedding.min_image_tokens.trim())
      embeddingUpdate.min_image_tokens = toInt(editorState.embedding.min_image_tokens);
    if (editorState.embedding.max_image_tokens.trim() !== baseline.embedding.max_image_tokens.trim())
      embeddingUpdate.max_image_tokens = toInt(editorState.embedding.max_image_tokens);
    if (Object.keys(embeddingUpdate).length > 0) {
      if (embeddingUpdate.model_name !== undefined && !embeddingUpdate.model_name.trim()) {
        toast.error('Missing Embedding Model', 'Please fill embedding model_name');
        return;
      }
      requestBody.embedding = embeddingUpdate;
    }

    const rerankerUpdate: NonNullable<ModelsUpdateRequest['reranker']> = {};
    if (editorState.reranker.enabled !== baseline.reranker.enabled)
      rerankerUpdate.enabled = editorState.reranker.enabled;
    if (editorState.reranker.provider !== baseline.reranker.provider)
      rerankerUpdate.provider = editorState.reranker.provider;
    if (editorState.reranker.model_name !== baseline.reranker.model_name)
      rerankerUpdate.model_name = editorState.reranker.model_name;
    if (editorState.reranker.model_path !== baseline.reranker.model_path)
      rerankerUpdate.model_path = editorState.reranker.model_path;
    if (editorState.reranker.device !== baseline.reranker.device) rerankerUpdate.device = editorState.reranker.device;
    if (editorState.reranker.dtype !== baseline.reranker.dtype) rerankerUpdate.dtype = editorState.reranker.dtype;
    if (editorState.reranker.attn_implementation !== baseline.reranker.attn_implementation)
      rerankerUpdate.attn_implementation = editorState.reranker.attn_implementation;
    if (editorState.reranker.batch_size.trim() !== baseline.reranker.batch_size.trim())
      rerankerUpdate.batch_size = toInt(editorState.reranker.batch_size);
    if (editorState.reranker.max_length.trim() !== baseline.reranker.max_length.trim())
      rerankerUpdate.max_length = toInt(editorState.reranker.max_length);
    if (editorState.reranker.instruction.trim()) rerankerUpdate.instruction = editorState.reranker.instruction;
    if (editorState.reranker.system_prompt.trim()) rerankerUpdate.system_prompt = editorState.reranker.system_prompt;
    if (editorState.reranker.api_key.trim()) rerankerUpdate.api_key = editorState.reranker.api_key;
    if (editorState.reranker.base_url !== baseline.reranker.base_url)
      rerankerUpdate.base_url = editorState.reranker.base_url;
    if (editorState.reranker.min_image_tokens.trim() !== baseline.reranker.min_image_tokens.trim())
      rerankerUpdate.min_image_tokens = toInt(editorState.reranker.min_image_tokens);
    if (editorState.reranker.max_image_tokens.trim() !== baseline.reranker.max_image_tokens.trim())
      rerankerUpdate.max_image_tokens = toInt(editorState.reranker.max_image_tokens);
    if (editorState.reranker.allow_image_urls !== baseline.reranker.allow_image_urls)
      rerankerUpdate.allow_image_urls = editorState.reranker.allow_image_urls;
    if (Object.keys(rerankerUpdate).length > 0) {
      requestBody.reranker = rerankerUpdate;
    }

    if (!requestBody.llm && !requestBody.vision && !requestBody.embedding && !requestBody.reranker) {
      toast.info('No Changes', 'No model settings were changed');
      return;
    }

    updateModelsMutation.mutate(requestBody);
  };

  const scheduleAutoSaveModels = useCallback(() => {
    if (modelsAutoSaveTimerRef.current) {
      window.clearTimeout(modelsAutoSaveTimerRef.current);
    }

    // Small debounce to avoid double-saves when focus moves quickly between fields.
    modelsAutoSaveTimerRef.current = window.setTimeout(() => {
      if (!open) return;
      if (updateModelsMutation.isPending) return;
      if (!hasModelChanges()) return;
      handleSaveModels();
    }, 250);
  }, [open, updateModelsMutation.isPending, hasModelChanges, handleSaveModels]);

  // Cleanup any pending auto-save timers on unmount.
  useEffect(() => {
    return () => {
      if (modelsAutoSaveTimerRef.current) {
        window.clearTimeout(modelsAutoSaveTimerRef.current);
        modelsAutoSaveTimerRef.current = null;
      }
    };
  }, []);

  const handleOpenChange = (nextOpen: boolean) => {
    // When closing, flush any pending model changes (best-effort).
    if (open && !nextOpen) {
      if (modelsAutoSaveTimerRef.current) {
        window.clearTimeout(modelsAutoSaveTimerRef.current);
        modelsAutoSaveTimerRef.current = null;
      }
      if (!updateModelsMutation.isPending && hasModelChanges()) {
        handleSaveModels();
      }
    }
    setOpen(nextOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" className="h-9 w-9">
          <Settings className="h-5 w-5" />
          <span className="sr-only">Settings</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Settings &amp; Configuration
          </DialogTitle>
          <DialogDescription>View backend status and manage configuration settings</DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col min-h-0">
          <TabsList className="grid w-full grid-cols-6">
            <TabsTrigger value="status" aria-label="Status" className="flex items-center gap-1">
              <Server className="h-4 w-4" />
              <span className="hidden sm:inline">Status</span>
            </TabsTrigger>
            <TabsTrigger value="appearance" aria-label="Appearance" className="flex items-center gap-1">
              <Palette className="h-4 w-4" />
              <span className="hidden sm:inline">Appearance</span>
            </TabsTrigger>
            <TabsTrigger value="models" aria-label="Models" className="flex items-center gap-1">
              <Cpu className="h-4 w-4" />
              <span className="hidden sm:inline">Models</span>
            </TabsTrigger>
            <TabsTrigger value="indexing" aria-label="Indexing" className="flex items-center gap-1">
              <FolderCog className="h-4 w-4" />
              <span className="hidden sm:inline">Indexing</span>
            </TabsTrigger>
            <TabsTrigger value="chat" aria-label="Chat" className="flex items-center gap-1">
              <MessageSquare className="h-4 w-4" />
              <span className="hidden sm:inline">Chat</span>
            </TabsTrigger>
            <TabsTrigger value="system" aria-label="System" className="flex items-center gap-1">
              <Database className="h-4 w-4" />
              <span className="hidden sm:inline">System</span>
            </TabsTrigger>
          </TabsList>

          <div className="flex-1 overflow-y-auto mt-4 pr-1">
            <TabsContent value="status" className="mt-0 h-full">
              <StatusTabContent
                healthData={healthData}
                healthLoading={healthLoading}
                healthError={healthError as Error | null}
                readyData={readyData}
                readyLoading={readyLoading}
                readyError={readyError as Error | null}
              />
            </TabsContent>

            <TabsContent value="appearance" className="mt-0 h-full">
              <AppearanceTabContent />
            </TabsContent>

            <TabsContent value="models" className="mt-0 h-full">
              <ModelsTabContent
                configData={configData}
                configLoading={configLoading}
                configError={configError as Error | null}
                editorState={editorState}
                setEditorState={setEditorState}
                onAutoSave={scheduleAutoSaveModels}
                updateModelsMutation={updateModelsMutation}
                hasChanges={hasModelChanges()}
              />
            </TabsContent>

            <TabsContent value="indexing" className="mt-0 h-full">
              <IndexingTabContent />
            </TabsContent>

            <TabsContent value="chat" className="mt-0 h-full">
              <ChatTabContent />
            </TabsContent>

            <TabsContent value="system" className="mt-0 h-full">
              <SystemTabContent
                configData={configData}
                configLoading={configLoading}
                configError={configError as Error | null}
                handleReloadConfig={handleReloadConfig}
                reloadMutation={reloadMutation}
                lastReloadResult={lastReloadResult}
              />
            </TabsContent>
          </div>
        </Tabs>

        {/* Footer */}
        <div className="flex justify-between items-center pt-4 border-t mt-4">
          <p className="text-xs text-muted-foreground">
            {reloadMutation.isPending
              ? 'Reloading configuration...'
              : updateModelsMutation.isPending
                ? 'Applying model configuration...'
                : ''}
          </p>
          <Button variant="default" size="sm" onClick={() => setOpen(false)}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

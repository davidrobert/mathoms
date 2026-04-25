"use client";

import { useCallback, useEffect, useState } from "react";
import {
  getLLMConfig,
  saveLLMConfig,
  deleteLLMConfig,
  testLLMConnection,
  getLLMTier,
  type LLMConfigResponse,
  type LLMTierResponse,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Spinner } from "@/components/Spinner";
import {
  Brain,
  Shield,
  Eye,
  EyeOff,
  Trash2,
  Zap,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";
import { useWorkspace } from "@/lib/WorkspaceProvider";
import type { UserWorkspace } from "@/lib/api";

const PROVIDERS = [
  { value: "anthropic", label: "Anthropic" },
  { value: "openai", label: "OpenAI" },
  { value: "google", label: "Google AI" },
  { value: "openrouter", label: "OpenRouter" },
  { value: "groq", label: "Groq" },
  { value: "ollama", label: "Ollama (local)" },
] as const;

const MODELS_BY_PROVIDER: Record<string, { value: string; label: string }[]> = {
  anthropic: [
    { value: "claude-opus-4-6", label: "Claude Opus 4.6" },
    { value: "claude-sonnet-4-6", label: "Claude Sonnet 4.6" },
    { value: "claude-haiku-4-5", label: "Claude Haiku 4.5" },
    { value: "claude-sonnet-4-5", label: "Claude Sonnet 4.5" },
    { value: "claude-opus-4-5", label: "Claude Opus 4.5" },
  ],
  openai: [
    { value: "gpt-4o", label: "GPT-4o" },
    { value: "gpt-4o-mini", label: "GPT-4o Mini" },
    { value: "gpt-4-turbo", label: "GPT-4 Turbo" },
    { value: "o3", label: "o3" },
    { value: "o3-mini", label: "o3 Mini" },
    { value: "o4-mini", label: "o4 Mini" },
  ],
  google: [
    { value: "gemini/gemini-2.5-pro", label: "Gemini 2.5 Pro" },
    { value: "gemini/gemini-2.5-flash", label: "Gemini 2.5 Flash" },
    { value: "gemini/gemini-2.0-flash", label: "Gemini 2.0 Flash" },
  ],
  groq: [
    { value: "llama-3.3-70b-versatile", label: "Llama 3.3 70B" },
    { value: "llama-3.1-8b-instant", label: "Llama 3.1 8B" },
    { value: "mixtral-8x7b-32768", label: "Mixtral 8x7B" },
  ],
  openrouter: [
    { value: "anthropic/claude-opus-4-6", label: "Claude Opus 4.6" },
    { value: "anthropic/claude-sonnet-4-6", label: "Claude Sonnet 4.6" },
    { value: "openai/gpt-4o", label: "GPT-4o" },
    { value: "google/gemini-2.5-pro", label: "Gemini 2.5 Pro" },
  ],
  ollama: [
    { value: "llama3.3", label: "Llama 3.3" },
    { value: "mistral", label: "Mistral" },
    { value: "codellama", label: "Code Llama" },
    { value: "qwen2.5-coder", label: "Qwen 2.5 Coder" },
  ],
};

export default function LLMTab() {
  const { workspace } = useWorkspace();
  if (!workspace) return null;
  return <LLMTabContent workspace={workspace} />;
}

function LLMTabContent({ workspace }: { workspace: UserWorkspace }) {

  const [config, setConfig] = useState<LLMConfigResponse | null>(null);
  const [tier, setTier] = useState<LLMTierResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const [provider, setProvider] = useState("anthropic");
  const [apiKey, setApiKey] = useState("");
  const [modelName, setModelName] = useState("");
  const [customModel, setCustomModel] = useState(false);
  const [showKey, setShowKey] = useState(false);

  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const availableModels = MODELS_BY_PROVIDER[provider] ?? [];

  const handleProviderChange = (v: string) => {
    setProvider(v);
    const models = MODELS_BY_PROVIDER[v] ?? [];
    const currentInList = models.some((m) => m.value === modelName);
    if (!currentInList) {
      setModelName(models[0]?.value ?? "");
      setCustomModel(models.length === 0);
    }
  };

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [cfg, t] = await Promise.all([getLLMConfig(workspace.id), getLLMTier(workspace.id)]);
      setConfig(cfg);
      setTier(t);
      if (cfg) {
        setProvider(cfg.provider);
        setModelName(cfg.model_name);
        const models = MODELS_BY_PROVIDER[cfg.provider] ?? [];
        const inList = models.some((m) => m.value === cfg.model_name);
        setCustomModel(!inList);
      }
    } catch {
      toast.error("Erro ao carregar configuração LLM");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSave = async () => {
    if (!provider || !apiKey || !modelName) {
      toast.error("Preencha todos os campos obrigatórios");
      return;
    }
    setSaving(true);
    try {
      const updated = await saveLLMConfig(workspace.id, {
        provider,
        api_key: apiKey,
        model_name: modelName,
      });
      setConfig(updated);
      setApiKey("");
      setShowKey(false);
      toast.success("Configuração LLM salva com sucesso");
      const t = await getLLMTier(workspace.id);
      setTier(t);
    } catch {
      toast.error("Erro ao salvar configuração");
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    try {
      const result = await testLLMConnection(workspace.id);
      if (result.success) {
        toast.success(result.message || "Conexão bem-sucedida");
      } else {
        toast.error(result.message || "Falha na conexão");
      }
    } catch {
      toast.error("Erro ao testar conexão");
    } finally {
      setTesting(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await deleteLLMConfig(workspace.id);
      setConfig(null);
      setProvider("anthropic");
      setApiKey("");
      setModelName(MODELS_BY_PROVIDER["anthropic"][0]?.value ?? "");
      setCustomModel(false);
      toast.success("Configuração LLM removida");
      const t = await getLLMTier(workspace.id);
      setTier(t);
    } catch {
      toast.error("Erro ao remover configuração");
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner size="lg" />
      </div>
    );
  }

  const tierLabel = tier?.tier === "premium" ? "Premium" : "Free";
  const tierVariant = tier?.tier === "premium" ? "default" : "secondary";
  const isKeyInvalid = config?.api_key_status === "invalid";

  return (
    <div className="space-y-6">
      {/* Tier indicator */}
      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0 pb-3">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
              <Shield className="h-4.5 w-4.5 text-primary" />
            </div>
            <div>
              <CardTitle className="text-base">Nível de acesso</CardTitle>
              <CardDescription className="text-xs">
                Determina quais etapas do pipeline ficam disponíveis
              </CardDescription>
            </div>
          </div>
          <Badge variant={tierVariant} className="text-xs">
            {tierLabel}
          </Badge>
        </CardHeader>
        <CardContent className="pt-0">
          <p className="text-sm text-muted-foreground">
            {tier?.tier === "premium"
              ? "Todas as etapas com IA (leitura de dados pessoais, IRPF, investimentos e revisão final) estão habilitadas."
              : isKeyInvalid
                ? "A chave salva não pôde ser descriptografada (FERNET_KEY rotacionada). Re-salve a API key para reativar Premium."
                : "Configure uma chave de API para desbloquear as etapas com IA do processamento."}
          </p>
        </CardContent>
      </Card>

      {/* LLM Config form */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
              <Brain className="h-4.5 w-4.5 text-primary" />
            </div>
            <div>
              <CardTitle className="text-base">Configuração LLM</CardTitle>
              <CardDescription className="text-xs">
                {config
                  ? isKeyInvalid
                    ? `Chave inválida: ${config.provider} / ${config.model_name} — re-salve para reativar`
                    : `Configurado: ${config.provider} / ${config.model_name}`
                  : "Nenhuma configuração ativa"}
              </CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-5">
          {isKeyInvalid && (
            <div
              role="alert"
              className="flex items-start gap-3 rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm"
            >
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
              <div className="space-y-1">
                <p className="font-medium text-destructive">Chave de API não pôde ser descriptografada</p>
                <p className="text-muted-foreground">
                  A FERNET_KEY do servidor foi rotacionada após a chave ser salva. O pipeline está
                  rodando em modo Free (sem etapas LLM). Insira a chave novamente abaixo e clique em
                  Salvar para reativar Premium.
                </p>
              </div>
            </div>
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="llm-provider">Provedor</Label>
              <Select value={provider} onValueChange={(v) => v && handleProviderChange(v)}>
                <SelectTrigger id="llm-provider">
                  <SelectValue placeholder="Selecionar provedor" />
                </SelectTrigger>
                <SelectContent>
                  {PROVIDERS.map((p) => (
                    <SelectItem key={p.value} value={p.value}>
                      {p.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="llm-model">Modelo</Label>
                {availableModels.length > 0 && (
                  <button
                    type="button"
                    className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                    onClick={() => {
                      setCustomModel(!customModel);
                      if (customModel && availableModels.length > 0) {
                        setModelName(availableModels[0].value);
                      }
                    }}
                  >
                    {customModel ? "← Voltar à lista" : "Digitar manualmente"}
                  </button>
                )}
              </div>
              {customModel || availableModels.length === 0 ? (
                <Input
                  id="llm-model"
                  placeholder="ex: claude-opus-4-6, gpt-4o"
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                />
              ) : (
                <Select value={modelName} onValueChange={(v) => v && setModelName(v)}>
                  <SelectTrigger id="llm-model">
                    <SelectValue placeholder="Selecionar modelo" />
                  </SelectTrigger>
                  <SelectContent>
                    {availableModels.map((m) => (
                      <SelectItem key={m.value} value={m.value}>
                        {m.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="llm-key">Chave de API</Label>
            <div className="relative">
              <Input
                id="llm-key"
                type={showKey ? "text" : "password"}
                placeholder={
                  config
                    ? isKeyInvalid
                      ? "Insira a chave novamente para reativar"
                      : "••••••••  (já configurada — insira nova para alterar)"
                    : "sk-..."
                }
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="pr-10"
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="absolute right-0 top-0 h-full w-10"
                onClick={() => setShowKey(!showKey)}
                aria-label={showKey ? "Ocultar chave" : "Mostrar chave"}
                tabIndex={-1}
              >
                {showKey ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>

          <Separator />

          <div className="flex flex-wrap gap-3">
            <Button onClick={handleSave} disabled={saving || !apiKey}>
              {saving ? (
                <Spinner className="mr-2 h-4 w-4" />
              ) : (
                <Zap className="mr-2 h-4 w-4" />
              )}
              Salvar
            </Button>

            {config && !isKeyInvalid && (
              <Button
                variant="outline"
                onClick={handleTest}
                disabled={testing}
              >
                {testing ? (
                  <Spinner className="mr-2 h-4 w-4" />
                ) : (
                  <CheckCircle2 className="mr-2 h-4 w-4" />
                )}
                Testar Conexão
              </Button>
            )}

            {config && (
              <Button
                variant="destructive"
                onClick={() => setConfirmOpen(true)}
                disabled={deleting}
              >
                {deleting ? (
                  <Spinner className="mr-2 h-4 w-4" />
                ) : (
                  <Trash2 className="mr-2 h-4 w-4" />
                )}
                Remover Configuração
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Remover configuração LLM?"
        description="Isso vai desativar todas as etapas LLM do pipeline e reverter o nível para Free."
        confirmLabel="Remover"
        variant="destructive"
        onConfirm={handleDelete}
      />
    </div>
  );
}

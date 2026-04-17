"use client";

import { useCallback, useEffect, useState } from "react";
import { getInstitutionsConfig, updateInstitutionsConfig, ApiError } from "@/lib/api";
import { bankLabel } from "@/lib/format";
import { Spinner } from "@/components/Spinner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Card, CardContent } from "@/components/ui/card";
import { ChevronDown, ChevronUp } from "lucide-react";
import { useWorkspace } from "@/lib/WorkspaceProvider";
import type { UserWorkspace } from "@/lib/api";

export default function InstitutionsTab() {
  const { workspace } = useWorkspace();
  if (!workspace) return null;
  return <InstitutionsTabContent workspace={workspace} />;
}

function InstitutionsTabContent({ workspace }: { workspace: UserWorkspace }) {

  const [config, setConfig] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [jsonMode, setJsonMode] = useState(false);
  const [jsonText, setJsonText] = useState("");
  const [saving, setSaving] = useState(false);

  const reload = useCallback(async () => {
    try {
      const data = await getInstitutionsConfig(workspace.id);
      setConfig(data.config_json);
      setJsonText(JSON.stringify(data.config_json, null, 2));
    } catch {
      setError("Erro ao carregar configuração de instituições");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { reload(); }, [reload]);

  const bankKeys = config ? Object.keys(config).filter((k) => typeof config[k] === "object") : [];

  async function handleSaveJson() {
    setError(""); setSaving(true);
    try {
      const parsed = JSON.parse(jsonText);
      const updated = await updateInstitutionsConfig(workspace.id, parsed);
      setConfig(updated.config_json);
      setJsonText(JSON.stringify(updated.config_json, null, 2));
      setSuccess("Salvo!");
      setTimeout(() => setSuccess(""), 2000);
    } catch (err) {
      if (err instanceof SyntaxError) {
        setError("JSON inválido: " + err.message);
      } else {
        setError(err instanceof ApiError ? err.detail : "Erro ao salvar");
      }
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div>
      {error && (
        <div className="mb-4 rounded-lg bg-loss/10 p-3 text-sm text-loss">
          {error} <button onClick={() => setError("")} className="ml-2 underline">fechar</button>
        </div>
      )}
      {success && <div className="mb-4 rounded-lg bg-gain/10 p-3 text-sm text-gain">{success}</div>}

      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{bankKeys.length} instituições configuradas</p>
        <Button variant="outline" size="sm" onClick={() => setJsonMode(!jsonMode)}>
          {jsonMode ? "Modo visual" : "Editor JSON"}
        </Button>
      </div>

      {jsonMode ? (
        <div className="space-y-3">
          <Textarea
            value={jsonText}
            onChange={(e) => setJsonText(e.target.value)}
            rows={24}
            spellCheck={false}
            className="font-mono text-xs"
          />
          <Button onClick={handleSaveJson} disabled={saving}>
            {saving ? "Salvando..." : "Salvar JSON"}
          </Button>
        </div>
      ) : (
        <div className="space-y-2">
          {bankKeys.map((key) => {
            const bank = config![key] as Record<string, unknown>;
            const isActive = bank.active !== false;
            return (
              <BankCard
                key={key}
                code={key}
                bank={bank}
                active={isActive}
                onToggle={async () => {
                  const newConfig = { ...config!, [key]: { ...bank, active: !isActive } };
                  setSaving(true);
                  try {
                    const updated = await updateInstitutionsConfig(workspace.id, newConfig);
                    setConfig(updated.config_json);
                    setJsonText(JSON.stringify(updated.config_json, null, 2));
                  } catch (err) {
                    setError(err instanceof ApiError ? err.detail : "Erro ao atualizar");
                  } finally {
                    setSaving(false);
                  }
                }}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

function BankCard({ code, bank, active, onToggle }: {
  code: string;
  bank: Record<string, unknown>;
  active: boolean;
  onToggle: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const tipoDoc = bank.tipo_documento as string | undefined;
  const cartoes = bank.cartoes as string[] | undefined;

  return (
    <Card className={`transition ${!active ? "opacity-60" : ""}`}>
      <CardContent className="p-0">
        <div className="flex items-center gap-3 px-4 py-3">
          <Switch checked={active} onCheckedChange={onToggle} aria-label={`Ativar ${bankLabel(code)}`} />
          <div className="flex-1">
            <span className="text-sm font-medium">{bankLabel(code)}</span>
            <span className="ml-2 text-xs text-muted-foreground">{code}</span>
            {tipoDoc && <span className="ml-2 text-xs text-muted-foreground">· {tipoDoc}</span>}
          </div>
          {cartoes && <span className="text-xs text-muted-foreground">{cartoes.length} cartões</span>}
          <Button variant="ghost" size="sm" onClick={() => setExpanded(!expanded)}>
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
        </div>
        {expanded && (
          <div className="border-t border-border px-4 py-3">
            <pre className="max-h-48 overflow-auto rounded-lg bg-muted p-2 text-xs font-mono">
              {JSON.stringify(bank, null, 2)}
            </pre>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

"use client";

import { useCallback, useEffect, useState } from "react";
import { getPipelineConfig, updatePipelineConfig, type PipelineConfigData, ApiError } from "@/lib/api";
import { Spinner } from "@/components/Spinner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

export default function PipelineTab() {
  const [config, setConfig] = useState<PipelineConfigData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const reload = useCallback(async () => {
    try {
      const data = await getPipelineConfig();
      setConfig(data);
    } catch {
      setError("Erro ao carregar configuração do pipeline");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { reload(); }, [reload]);

  async function handleSave(section: string, data: Record<string, unknown>) {
    setError(""); setSuccess(""); setSaving(true);
    try {
      const updated = await updatePipelineConfig({ [section]: data });
      setConfig(updated);
      setSuccess("Salvo!");
      setTimeout(() => setSuccess(""), 2000);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  }

  if (loading || !config) {
    return (
      <div className="flex justify-center py-12">
        <Spinner size="lg" />
      </div>
    );
  }

  const llm = (config.llm ?? {}) as Record<string, unknown>;
  const fileLimits = (config.file_limits ?? {}) as Record<string, unknown>;
  const qa = (config.qa_thresholds ?? {}) as Record<string, unknown>;

  return (
    <div className="space-y-6">
      {error && <div className="rounded-lg bg-loss/10 p-3 text-sm text-loss">{error}</div>}
      {success && <div className="rounded-lg bg-gain/10 p-3 text-sm text-gain">{success}</div>}

      <ConfigSection title="LLM" description="Configurações do modelo de linguagem" fields={[
        { key: "model", label: "Modelo", value: llm.model as string ?? "claude-sonnet-4-20250514", type: "text" },
        { key: "max_tokens", label: "Max Tokens", value: llm.max_tokens as number ?? 500, type: "number" },
        { key: "confidence_threshold", label: "Threshold de confiança", value: llm.confidence_threshold as number ?? 0.7, type: "number", step: "0.1" },
      ]} onSave={(data) => handleSave("llm", data)} saving={saving} />

      <ConfigSection title="Limites de Arquivo" description="Tamanhos mínimos e limites de preview" fields={[
        { key: "preview_max_chars", label: "Max chars preview", value: fileLimits.preview_max_chars as number ?? 2000, type: "number" },
        { key: "preview_max_rows", label: "Max linhas preview", value: fileLimits.preview_max_rows as number ?? 20, type: "number" },
        { key: "min_pdf_bytes", label: "Min bytes PDF", value: fileLimits.min_pdf_bytes as number ?? 1024, type: "number" },
        { key: "min_xls_bytes", label: "Min bytes XLS", value: fileLimits.min_xls_bytes as number ?? 40000, type: "number" },
        { key: "min_csv_bytes", label: "Min bytes CSV", value: fileLimits.min_csv_bytes as number ?? 500, type: "number" },
      ]} onSave={(data) => handleSave("file_limits", data)} saving={saving} />

      <ConfigSection title="QA Thresholds" description="Tolerâncias para a validação cruzada do relatório" fields={[
        { key: "score_diff_max", label: "Score diff max", value: qa.score_diff_max as number ?? 0.5, type: "number", step: "0.1" },
        { key: "patrimonio_composicao_diff_pct_max", label: "Composição patrim. diff % max", value: qa.patrimonio_composicao_diff_pct_max as number ?? 5, type: "number" },
        { key: "cv_fluxo_diff_max", label: "Fluxo diff max (R$)", value: qa.cv_fluxo_diff_max as number ?? 100, type: "number" },
        { key: "cv_taxa_poupanca_diff_pp_max", label: "Taxa poupança diff pp max", value: qa.cv_taxa_poupanca_diff_pp_max as number ?? 5, type: "number" },
        { key: "qa_unidentified_target_pct", label: "% target não-identificados", value: qa.qa_unidentified_target_pct as number ?? 10, type: "number", step: "0.1" },
      ]} onSave={(data) => handleSave("qa_thresholds", data)} saving={saving} />
    </div>
  );
}

function ConfigSection({ title, description, fields, onSave, saving }: {
  title: string;
  description: string;
  fields: { key: string; label: string; value: string | number; type: string; step?: string }[];
  onSave: (data: Record<string, unknown>) => void;
  saving: boolean;
}) {
  const [values, setValues] = useState<Record<string, string | number>>(
    Object.fromEntries(fields.map((f) => [f.key, f.value]))
  );
  const [dirty, setDirty] = useState(false);

  function handleChange(key: string, val: string) {
    const field = fields.find((f) => f.key === key);
    setValues((prev) => ({
      ...prev,
      [key]: field?.type === "number" ? (val === "" ? "" : Number(val)) : val,
    }));
    setDirty(true);
  }

  function handleSave() {
    const data: Record<string, unknown> = {};
    for (const f of fields) {
      data[f.key] = values[f.key];
    }
    onSave(data);
    setDirty(false);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
          {fields.map((f) => (
            <div key={f.key}>
              <Label className="mb-1 text-xs text-muted-foreground">{f.label}</Label>
              <Input
                type={f.type}
                step={f.step}
                value={values[f.key]}
                onChange={(e) => handleChange(f.key, e.target.value)}
              />
            </div>
          ))}
        </div>
        {dirty && (
          <Button className="mt-3" size="sm" onClick={handleSave} disabled={saving}>
            {saving ? "Salvando..." : "Salvar alterações"}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

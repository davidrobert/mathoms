"use client";

import { useCallback, useEffect, useState } from "react";
import { getReportLayout, updateReportLayout, ApiError } from "@/lib/api";
import { Spinner } from "@/components/Spinner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { ChevronUp, ChevronDown } from "lucide-react";

interface Section {
  key: string;
  title?: string;
  visible?: boolean;
  [k: string]: unknown;
}

export default function ReportLayoutTab() {
  const [config, setConfig] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [saving, setSaving] = useState(false);
  const [jsonMode, setJsonMode] = useState(false);
  const [jsonText, setJsonText] = useState("");

  const reload = useCallback(async () => {
    try {
      const data = await getReportLayout();
      setConfig(data.config_json);
      setJsonText(JSON.stringify(data.config_json, null, 2));
    } catch {
      setError("Erro ao carregar layout do relatório");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { reload(); }, [reload]);

  const sections: Section[] = (() => {
    if (!config) return [];
    const secs = config.sections;
    if (Array.isArray(secs)) {
      return secs.map((s: Record<string, unknown>, i: number) => ({
        ...s,
        key: (s.id as string) ?? (s.title as string) ?? `section_${i}`,
        visible: s.visible !== false,
      }));
    }
    if (secs && typeof secs === "object") {
      return Object.entries(secs as Record<string, unknown>).map(([key, val]) => ({
        ...(val && typeof val === "object" ? val : {}),
        key,
        visible: (val as Record<string, unknown>)?.visible !== false,
      }));
    }
    return Object.entries(config).map(([key, val]) => ({
      ...(val && typeof val === "object" ? (val as Record<string, unknown>) : {}),
      key,
      visible: true,
    }));
  })();

  async function handleToggle(section: Section) {
    if (!config) return;
    setSaving(true);
    try {
      const updated = toggleSection(config, section.key, !section.visible);
      const result = await updateReportLayout(updated);
      setConfig(result.config_json);
      setJsonText(JSON.stringify(result.config_json, null, 2));
      setSuccess("Visibilidade atualizada!");
      setTimeout(() => setSuccess(""), 1500);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao atualizar");
    } finally {
      setSaving(false);
    }
  }

  async function handleMoveSection(idx: number, dir: -1 | 1) {
    if (!config) return;
    const targetIdx = idx + dir;
    if (targetIdx < 0 || targetIdx >= sections.length) return;
    setSaving(true);
    try {
      const reordered = reorderSection(config, idx, targetIdx);
      const result = await updateReportLayout(reordered);
      setConfig(result.config_json);
      setJsonText(JSON.stringify(result.config_json, null, 2));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao reordenar");
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveJson() {
    setError(""); setSaving(true);
    try {
      const parsed = JSON.parse(jsonText);
      const result = await updateReportLayout(parsed);
      setConfig(result.config_json);
      setJsonText(JSON.stringify(result.config_json, null, 2));
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
      {error && <div className="mb-4 rounded-lg bg-loss/10 p-3 text-sm text-loss">{error}</div>}
      {success && <div className="mb-4 rounded-lg bg-gain/10 p-3 text-sm text-gain">{success}</div>}

      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{sections.length} seções no layout</p>
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
          {sections.map((sec, idx) => (
            <div
              key={sec.key}
              className={`flex items-center gap-3 rounded-lg border bg-card px-4 py-3 transition ${
                sec.visible ? "border-border" : "border-border opacity-50"
              }`}
            >
              {/* Reorder Arrows */}
              <div className="flex flex-col gap-0.5">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-5 w-5 p-0"
                  onClick={() => handleMoveSection(idx, -1)}
                  disabled={idx === 0 || saving}
                >
                  <ChevronUp className="h-3 w-3" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-5 w-5 p-0"
                  onClick={() => handleMoveSection(idx, 1)}
                  disabled={idx === sections.length - 1 || saving}
                >
                  <ChevronDown className="h-3 w-3" />
                </Button>
              </div>

              <Switch
                checked={sec.visible}
                onCheckedChange={() => handleToggle(sec)}
                disabled={saving}
                aria-label={`Visibilidade ${sec.title ?? sec.key}`}
              />

              <div className="flex-1">
                <span className="text-sm font-medium">{sec.title ?? sec.key}</span>
                <span className="ml-2 text-xs text-muted-foreground">{sec.key}</span>
              </div>
              <span className="text-xs text-muted-foreground">#{idx + 1}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function toggleSection(config: Record<string, unknown>, key: string, visible: boolean): Record<string, unknown> {
  const clone = JSON.parse(JSON.stringify(config));
  if (Array.isArray(clone.sections)) {
    const sec = clone.sections.find((s: Record<string, unknown>) => (s.id ?? s.title) === key);
    if (sec) sec.visible = visible;
  } else if (clone.sections && typeof clone.sections === "object") {
    if (clone.sections[key]) clone.sections[key].visible = visible;
  } else if (clone[key] && typeof clone[key] === "object") {
    clone[key].visible = visible;
  }
  return clone;
}

function reorderSection(config: Record<string, unknown>, fromIdx: number, toIdx: number): Record<string, unknown> {
  const clone = JSON.parse(JSON.stringify(config));
  if (Array.isArray(clone.sections)) {
    const [moved] = clone.sections.splice(fromIdx, 1);
    clone.sections.splice(toIdx, 0, moved);
  } else if (clone.sections && typeof clone.sections === "object") {
    const entries = Object.entries(clone.sections);
    const [moved] = entries.splice(fromIdx, 1);
    entries.splice(toIdx, 0, moved);
    clone.sections = Object.fromEntries(entries);
  }
  return clone;
}

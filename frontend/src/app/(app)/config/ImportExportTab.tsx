"use client";

import { useCallback, useRef, useState } from "react";
import { exportConfig, importConfig, type ConfigExport, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Download, Upload } from "lucide-react";
import { useWorkspace } from "@/lib/WorkspaceProvider";

const CONFIG_SECTIONS = [
  { key: "family_members", label: "Membros da família" },
  { key: "categorization", label: "Categorias (despesas/receitas)" },
  { key: "pipeline", label: "Parâmetros do pipeline" },
  { key: "institutions", label: "Instituições financeiras" },
  { key: "report_layout", label: "Layout do relatório" },
] as const;

type SectionKey = (typeof CONFIG_SECTIONS)[number]["key"];

export default function ImportExportTab() {
  const { workspace } = useWorkspace();
  if (!workspace) return null;

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [importing, setImporting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [preview, setPreview] = useState<ConfigExport | null>(null);
  const [selectedSections, setSelectedSections] = useState<Set<SectionKey>>(
    new Set(CONFIG_SECTIONS.map((s) => s.key))
  );
  const fileRef = useRef<HTMLInputElement>(null);

  const handleExport = useCallback(async () => {
    setError(""); setExporting(true);
    try {
      const data = await exportConfig(workspace!.id);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `fin-config-export-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      setSuccess("Configuração exportada!");
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao exportar");
    } finally {
      setExporting(false);
    }
  }, []);

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    setError(""); setPreview(null);
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const data = JSON.parse(ev.target?.result as string);
        setPreview(data);
      } catch {
        setError("Arquivo JSON inválido");
      }
    };
    reader.readAsText(file);
  }

  async function handleImport() {
    if (!preview) return;
    setError(""); setImporting(true);

    const importData: Partial<ConfigExport> = {};
    for (const key of selectedSections) {
      if (preview[key]) {
        (importData as Record<string, unknown>)[key] = preview[key];
      }
    }

    try {
      const result = await importConfig(workspace!.id, importData);
      setSuccess(`Importado com sucesso: ${result.imported.join(", ")} (${result.total} seções)`);
      setPreview(null);
      if (fileRef.current) fileRef.current.value = "";
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao importar");
    } finally {
      setImporting(false);
    }
  }

  function toggleSection(key: SectionKey) {
    setSelectedSections((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  return (
    <div className="space-y-8">
      {error && <div className="rounded-lg bg-loss/10 p-3 text-sm text-loss">{error}</div>}
      {success && <div className="rounded-lg bg-gain/10 p-3 text-sm text-gain">{success}</div>}

      {/* Export */}
      <Card>
        <CardHeader>
          <CardTitle>Exportar Configuração</CardTitle>
          <CardDescription>
            Baixe todas as configurações do workspace como arquivo JSON. Inclui membros, categorias, parâmetros, instituições e layout.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={handleExport} disabled={exporting}>
            <Download className="mr-2 h-4 w-4" />
            {exporting ? "Exportando..." : "Exportar JSON"}
          </Button>
        </CardContent>
      </Card>

      {/* Import */}
      <Card>
        <CardHeader>
          <CardTitle>Importar Configuração</CardTitle>
          <CardDescription>
            Importe configurações de um arquivo JSON. Você pode escolher quais seções importar.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm font-medium hover:bg-muted transition">
            <Upload className="h-4 w-4" />
            Selecionar arquivo JSON
            <input ref={fileRef} type="file" accept=".json,application/json" onChange={handleFileSelect} className="hidden" />
          </label>

          {/* Preview */}
          {preview && (
            <div className="mt-4 space-y-3">
              <h4 className="text-sm font-medium">Seções encontradas — selecione quais importar:</h4>
              <div className="space-y-2">
                {CONFIG_SECTIONS.map((sec) => {
                  const data = preview[sec.key];
                  const hasData = data != null && Object.keys(data).length > 0;
                  return (
                    <label
                      key={sec.key}
                      className={`flex items-center gap-3 rounded-lg border px-4 py-3 transition ${
                        hasData ? "border-border cursor-pointer hover:bg-accent" : "border-border opacity-40"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedSections.has(sec.key) && hasData}
                        disabled={!hasData}
                        onChange={() => toggleSection(sec.key)}
                        className="h-4 w-4 rounded border-input text-primary focus:ring-ring"
                      />
                      <div className="flex-1">
                        <span className="text-sm font-medium">{sec.label}</span>
                        {hasData ? (
                          <span className="ml-2 text-xs text-gain">
                            {Object.keys(data).length} chaves
                          </span>
                        ) : (
                          <span className="ml-2 text-xs text-muted-foreground">não encontrado no arquivo</span>
                        )}
                      </div>
                    </label>
                  );
                })}
              </div>

              <div className="flex gap-2 pt-2">
                <Button onClick={handleImport} disabled={importing || selectedSections.size === 0}>
                  {importing ? "Importando..." : `Importar ${selectedSections.size} seção(ões)`}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => { setPreview(null); if (fileRef.current) fileRef.current.value = ""; }}
                >
                  Cancelar
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

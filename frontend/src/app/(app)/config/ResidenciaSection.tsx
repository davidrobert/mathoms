"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/Spinner";
import {
  listProperties,
  setPropertyClassification,
  setResidenciaStatus,
  type Classification,
  type PropertyListResponse,
  type PropertyResponse,
  type ResidenciaStatus,
} from "@/lib/api/properties";

const CLASSIFICATION_LABELS: Record<Classification, string> = {
  residencia_principal: "Residência principal",
  uso_pessoal: "Uso pessoal (casa de praia, familiar)",
  locado: "Imóvel locado",
  comercial: "Imóvel comercial",
  especulacao: "Terreno / especulação",
  desconhecido: "Não classificado",
};

function classificationLabel(c: Classification | null): string {
  return c === null ? "Não classificado" : CLASSIFICATION_LABELS[c];
}

export function ResidenciaSection({ workspaceId }: { workspaceId: string }) {
  const [data, setData] = useState<PropertyListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setError("");
    try {
      const resp = await listProperties(workspaceId);
      setData(resp);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao listar imóveis");
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    reload();
  }, [reload]);

  async function handleStatus(status: ResidenciaStatus) {
    setSaving("status");
    try {
      await setResidenciaStatus(workspaceId, status);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao salvar status");
    } finally {
      setSaving(null);
    }
  }

  async function handleClassification(propertyId: string, classification: Classification) {
    setSaving(propertyId);
    try {
      await setPropertyClassification(workspaceId, propertyId, classification);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao salvar classificação");
    } finally {
      setSaving(null);
    }
  }

  if (loading) {
    return (
      <Card className="mb-4">
        <CardContent className="p-5">
          <Spinner size="sm" />
        </CardContent>
      </Card>
    );
  }

  if (data === null) {
    return null;
  }

  // Sem imóveis no IRPF → empty state com opção rented/undeclared.
  if (data.properties.length === 0) {
    return (
      <Card className="mb-4">
        <CardContent className="p-5">
          <h3 className="mb-1 text-sm font-medium text-foreground">Residência principal</h3>
          <p className="mb-3 text-xs text-muted-foreground">
            Ainda não identificamos imóveis no seu IRPF. Suba uma declaração ou marque seu status manualmente:
          </p>
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant={data.residencia_status === "rented" ? "default" : "outline"}
              disabled={saving === "status"}
              onClick={() => handleStatus("rented")}
            >
              Moro alugado
            </Button>
            <Button
              size="sm"
              variant={data.residencia_status === "undeclared" ? "default" : "outline"}
              disabled={saving === "status"}
              onClick={() => handleStatus("undeclared")}
            >
              Decidir depois
            </Button>
          </div>
          {error && <p className="mt-2 text-xs text-loss">{error}</p>}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="mb-4">
      <CardContent className="p-5">
        <h3 className="mb-1 text-sm font-medium text-foreground">Residência principal e imóveis</h3>
        <p className="mb-3 text-xs text-muted-foreground">
          Identificamos {data.properties.length} imóvel(is) no seu IRPF. Marque qual é a residência principal — afeta como o relatório separa &quot;Residência&quot; de &quot;Imóveis de Renda&quot;.
        </p>

        <div className="mb-3 flex flex-wrap items-center gap-2 text-xs">
          <span className="font-medium text-muted-foreground">Status:</span>
          <Button
            size="sm"
            variant={data.residencia_status === "owned" ? "default" : "outline"}
            disabled={saving === "status"}
            onClick={() => handleStatus("owned")}
          >
            Possui residência
          </Button>
          <Button
            size="sm"
            variant={data.residencia_status === "rented" ? "default" : "outline"}
            disabled={saving === "status"}
            onClick={() => handleStatus("rented")}
          >
            Moro alugado
          </Button>
          <Button
            size="sm"
            variant={data.residencia_status === "undeclared" ? "default" : "outline"}
            disabled={saving === "status"}
            onClick={() => handleStatus("undeclared")}
          >
            Decidir depois
          </Button>
        </div>

        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs text-muted-foreground">
              <th className="py-2 pr-3 font-medium">Tipo</th>
              <th className="py-2 pr-3 font-medium">Descrição</th>
              <th className="py-2 pr-3 font-medium">Classificação</th>
              <th className="py-2 text-right font-medium">Ação</th>
            </tr>
          </thead>
          <tbody>
            {data.properties.map((p) => (
              <PropertyRow
                key={p.property_id}
                property={p}
                saving={saving === p.property_id}
                onClassify={handleClassification}
              />
            ))}
          </tbody>
        </table>

        {error && <p className="mt-3 text-xs text-loss">{error}</p>}
      </CardContent>
    </Card>
  );
}

function PropertyRow({
  property,
  saving,
  onClassify,
}: {
  property: PropertyResponse;
  saving: boolean;
  onClassify: (id: string, c: Classification) => void;
}) {
  const codigoLabel = property.codigo_rfb === "12" ? "Casa" : property.codigo_rfb === "11" ? "Apto" : `Cód ${property.codigo_rfb}`;
  return (
    <tr className="border-b last:border-0">
      <td className="py-2 pr-3 text-xs">{codigoLabel}</td>
      <td className="py-2 pr-3">
        <span className="text-xs leading-tight">
          {property.descricao_sample ?? "—"}
        </span>
        {property.suggested_residencia_principal && (
          <span
            aria-describedby={`suggest-${property.property_id}`}
            className="ml-2 inline-flex items-center rounded-full bg-primary/15 px-2 py-0.5 text-[10px] font-medium text-primary"
          >
            sugerida pelo seu endereço no IRPF
          </span>
        )}
        {property.low_confidence && (
          <span className="ml-2 inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">
            sem endereço estruturado
          </span>
        )}
      </td>
      <td className="py-2 pr-3 text-xs">{classificationLabel(property.classification)}</td>
      <td className="py-2 text-right">
        <select
          className="rounded border bg-background px-2 py-1 text-xs"
          value={property.classification ?? ""}
          disabled={saving}
          onChange={(e) => {
            const v = e.target.value;
            if (v) onClassify(property.property_id, v as Classification);
          }}
        >
          <option value="" disabled>
            classificar...
          </option>
          <option value="residencia_principal">Residência principal</option>
          <option value="uso_pessoal">Uso pessoal</option>
          <option value="locado">Locado</option>
          <option value="comercial">Comercial</option>
          <option value="especulacao">Especulação</option>
          <option value="desconhecido">Não classificado</option>
        </select>
      </td>
    </tr>
  );
}

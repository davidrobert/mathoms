"use client";

/**
 * Seção em MembersTab que renderiza ``MarketValueInline`` por imóvel
 * classificado como locado/comercial (ADR-227 §D2 · Sprint A15 Onda 5b).
 *
 * Filtra ``listProperties`` por ``classification ∈ {locado, comercial}``
 * — imóveis residenciais/uso pessoal não precisam de declaração de
 * valor de mercado (não geram fluxo no IF).
 */

import { useCallback, useEffect, useState } from "react";

import { MarketValueInline } from "@/components/members/MarketValueInline";
import { Spinner } from "@/components/Spinner";
import { listProperties, type PropertyResponse } from "@/lib/api/properties";

function _label(p: PropertyResponse): string {
  return p.descricao_sample ?? p.endereco_canonical ?? `Imóvel ${p.codigo_rfb}`;
}

export function MarketValueSection({ workspaceId }: { workspaceId: string }) {
  const [properties, setProperties] = useState<PropertyResponse[]>([]);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await listProperties(workspaceId);
      setProperties(
        resp.properties.filter(
          (p) => p.classification === "locado" || p.classification === "comercial",
        ),
      );
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  if (loading) return <Spinner />;

  if (properties.length === 0) {
    return (
      <p
        className="text-sm"
        style={{ color: "var(--surface-muted-foreground)" }}
      >
        Nenhum imóvel locado ou comercial classificado. Para refletir valor de mercado, classifique
        o imóvel em &ldquo;Residência&rdquo; primeiro.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <h2 className="text-base font-medium">Valor de mercado dos imóveis de renda</h2>
        <p className="text-sm" style={{ color: "var(--surface-muted-foreground)" }}>
          Quando o valor de mercado mudou em relação ao IRPF, declare aqui — o
          relatório recalcula yield e patrimônio líquido econômico. Histórico preservado.
        </p>
      </div>
      {properties.map((p) => (
        <MarketValueInline
          key={p.property_id}
          workspaceId={workspaceId}
          propertyId={p.property_id}
          propertyLabel={_label(p)}
        />
      ))}
    </div>
  );
}

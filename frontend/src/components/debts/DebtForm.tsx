"use client";

/**
 * Form de criação/edição de Debt (ADR-227 §D1 · Sprint A15 Onda 5).
 *
 * `percentual_atribuicao_imovel` é exibido **apenas quando** a property
 * selecionada tem mais de 1 cotitular (co-propriedade familiar).
 */

import { useEffect, useState } from "react";

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
import { Textarea } from "@/components/ui/textarea";
import type {
  DebtCreate,
  DebtResponse,
  DebtTipo,
  DebtUpdate,
} from "@/lib/api/debts";

const DEBT_TIPOS: { value: DebtTipo; label: string }[] = [
  { value: "financiamento_imobiliario", label: "Financiamento imobiliário" },
  { value: "consignado", label: "Consignado" },
  { value: "cdc", label: "CDC" },
  { value: "cartao_rotativo", label: "Cartão rotativo" },
  { value: "rotativo", label: "Crédito rotativo" },
  { value: "outro", label: "Outro" },
];

export interface PropertyOption {
  id: string;
  label: string;
  /** Número de cotitulares (≥ 1). Quando > 1, exibe percentual_atribuicao_imovel. */
  cotitulares_count: number;
}

export interface MemberOption {
  id: string;
  label: string;
}

export interface DebtFormProps {
  initial?: DebtResponse;
  properties: PropertyOption[];
  members: MemberOption[];
  onSubmit: (body: DebtCreate | DebtUpdate) => Promise<void>;
  onCancel?: () => void;
}

interface FormState {
  tipo: DebtTipo;
  descricao: string;
  saldo_devedor_brl: string;
  parcela_mensal_brl: string;
  taxa_juros_aa: string;
  prazo_meses_restantes: string;
  data_contratacao: string;
  family_member_id: string;
  property_id: string;
  percentual_atribuicao_imovel: string;
}

function _initialState(initial: DebtResponse | undefined): FormState {
  return {
    tipo: initial?.tipo ?? "outro",
    descricao: initial?.descricao ?? "",
    saldo_devedor_brl: initial?.saldo_devedor_brl ?? "",
    parcela_mensal_brl: initial?.parcela_mensal_brl ?? "",
    taxa_juros_aa: initial?.taxa_juros_aa ?? "",
    prazo_meses_restantes: initial?.prazo_meses_restantes?.toString() ?? "",
    data_contratacao: initial?.data_contratacao ?? "",
    family_member_id: initial?.family_member_id ?? "",
    property_id: initial?.property_id ?? "",
    percentual_atribuicao_imovel: initial?.percentual_atribuicao_imovel ?? "100",
  };
}

function _buildBody(state: FormState, showPct: boolean): DebtCreate {
  return {
    tipo: state.tipo,
    descricao: state.descricao || null,
    saldo_devedor_brl: state.saldo_devedor_brl,
    parcela_mensal_brl: state.parcela_mensal_brl || null,
    taxa_juros_aa: state.taxa_juros_aa || null,
    prazo_meses_restantes: state.prazo_meses_restantes
      ? Number.parseInt(state.prazo_meses_restantes, 10)
      : null,
    data_contratacao: state.data_contratacao || null,
    family_member_id: state.family_member_id || null,
    property_id: state.property_id || null,
    percentual_atribuicao_imovel:
      showPct && state.property_id ? state.percentual_atribuicao_imovel : null,
  };
}

export function DebtForm({ initial, properties, members, onSubmit, onCancel }: DebtFormProps) {
  const [state, setState] = useState<FormState>(() => _initialState(initial));
  const [submitting, setSubmitting] = useState(false);
  const selectedProperty = properties.find((p) => p.id === state.property_id);
  const showPct = !!selectedProperty && selectedProperty.cotitulares_count > 1;

  useEffect(() => {
    if (!showPct) {
      setState((s) => ({ ...s, percentual_atribuicao_imovel: "100" }));
    }
  }, [showPct]);

  const update = <K extends keyof FormState>(key: K) => (value: FormState[K]) =>
    setState((s) => ({ ...s, [key]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await onSubmit(_buildBody(state, showPct));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid gap-2">
        <Label htmlFor="debt-tipo">Tipo</Label>
        <Select value={state.tipo} onValueChange={(v) => update("tipo")(v as DebtTipo)}>
          <SelectTrigger id="debt-tipo">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {DEBT_TIPOS.map((t) => (
              <SelectItem key={t.value} value={t.value}>
                {t.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid gap-2">
        <Label htmlFor="debt-descricao">Descrição</Label>
        <Textarea
          id="debt-descricao"
          value={state.descricao}
          onChange={(e) => update("descricao")(e.target.value)}
          placeholder="Ex.: Financiamento Itaú — apto. residencial"
          rows={2}
        />
      </div>

      <div className="grid gap-2 md:grid-cols-2 md:gap-4">
        <div className="grid gap-2">
          <Label htmlFor="debt-saldo">Saldo devedor (BRL)</Label>
          <Input
            id="debt-saldo"
            inputMode="decimal"
            value={state.saldo_devedor_brl}
            onChange={(e) => update("saldo_devedor_brl")(e.target.value)}
            placeholder="0.00"
            required
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="debt-parcela">Parcela mensal (BRL)</Label>
          <Input
            id="debt-parcela"
            inputMode="decimal"
            value={state.parcela_mensal_brl}
            onChange={(e) => update("parcela_mensal_brl")(e.target.value)}
            placeholder="0.00"
          />
        </div>
      </div>

      <div className="grid gap-2 md:grid-cols-2 md:gap-4">
        <div className="grid gap-2">
          <Label htmlFor="debt-taxa">Taxa a.a. (%)</Label>
          <Input
            id="debt-taxa"
            inputMode="decimal"
            value={state.taxa_juros_aa}
            onChange={(e) => update("taxa_juros_aa")(e.target.value)}
            placeholder="12.50"
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="debt-prazo">Prazo restante (meses)</Label>
          <Input
            id="debt-prazo"
            inputMode="numeric"
            value={state.prazo_meses_restantes}
            onChange={(e) => update("prazo_meses_restantes")(e.target.value)}
            placeholder="180"
          />
        </div>
      </div>

      <div className="grid gap-2 md:grid-cols-2 md:gap-4">
        <div className="grid gap-2">
          <Label htmlFor="debt-member">Membro vinculado</Label>
          <Select
            value={state.family_member_id || "__none__"}
            onValueChange={(v) => update("family_member_id")(v && v !== "__none__" ? v : "")}
          >
            <SelectTrigger id="debt-member">
              <SelectValue placeholder="Sem vínculo" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__none__">Sem vínculo</SelectItem>
              {members.map((m) => (
                <SelectItem key={m.id} value={m.id}>
                  {m.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-2">
          <Label htmlFor="debt-property">Imóvel vinculado</Label>
          <Select
            value={state.property_id || "__none__"}
            onValueChange={(v) => update("property_id")(v && v !== "__none__" ? v : "")}
          >
            <SelectTrigger id="debt-property">
              <SelectValue placeholder="Sem vínculo" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__none__">Sem vínculo</SelectItem>
              {properties.map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {showPct && (
        <div className="grid gap-2">
          <Label htmlFor="debt-pct">Percentual de atribuição (%)</Label>
          <Input
            id="debt-pct"
            inputMode="decimal"
            value={state.percentual_atribuicao_imovel}
            onChange={(e) => update("percentual_atribuicao_imovel")(e.target.value)}
            placeholder="100"
            aria-describedby="debt-pct-hint"
          />
          <p id="debt-pct-hint" className="text-sm" style={{ color: "var(--surface-muted-foreground)" }}>
            Imóvel com mais de 1 cotitular — informe o % deste débito vinculado a este imóvel.
            Para rateio complexo, edite manualmente.
          </p>
        </div>
      )}

      <div className="flex justify-end gap-2">
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel} disabled={submitting}>
            Cancelar
          </Button>
        )}
        <Button type="submit" disabled={submitting || !state.saldo_devedor_brl}>
          {submitting ? "Salvando…" : "Salvar"}
        </Button>
      </div>
    </form>
  );
}

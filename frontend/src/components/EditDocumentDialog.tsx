"use client";

import { useEffect, useState } from "react";
import { Save } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
  ApiError,
  updateDocumentClassification,
  type DocumentResponse,
  type DocumentType,
} from "@/lib/api";

// Tipos user-facing. "e1_members_json" / "e1_5_baseline_json" ficam de
// fora — vêm do detector de JSON, não devem ser escolhidos à mão.
const DOC_TYPE_OPTIONS: { value: DocumentType; label: string }[] = [
  { value: "bank_statement", label: "Extrato" },
  { value: "credit_card_bill", label: "Fatura de cartão" },
  { value: "investment_report", label: "Investimentos" },
  { value: "irpf", label: "IRPF / Receita Federal" },
  // ADR-238 (A17 L1) — informe anual avulso (PGBL/VGBL em L1; financeiro
  // PF/PJ e proventos em L2-L4). Distinto de "irpf" (declaração entregue).
  { value: "informe_rendimentos_anuais", label: "Informe de Rendimentos (PGBL/VGBL)" },
  // ADR-239 (A18 L1) — comprovante de bem (CRLV em L1; V2 imóveis).
  { value: "comprovante_bem", label: "Comprovante de Bem (CRLV)" },
  { value: "other", label: "Outro" },
];

// Instituições canônicas (espelha BANK_NAMES em frontend/src/lib/format.ts
// e config/institutions.json → banco_canonical).
const INSTITUTION_OPTIONS: { value: string; label: string }[] = [
  { value: "itau", label: "Itaú" },
  { value: "bradesco", label: "Bradesco" },
  { value: "santander", label: "Santander" },
  { value: "c6bank", label: "C6 Bank" },
  { value: "btgpactual", label: "BTG Pactual" },
  { value: "rico", label: "Rico" },
  { value: "picpay", label: "PicPay" },
  { value: "wise", label: "Wise" },
  { value: "bankofamerica", label: "Bank of America" },
  { value: "quintoandar", label: "QuintoAndar" },
  { value: "binance", label: "Binance" },
  { value: "caixa", label: "Caixa Econômica Federal" },
  { value: "nubank", label: "Nubank" },
  { value: "inter", label: "Inter" },
  { value: "stone", label: "Stone" },
  { value: "receitafederal", label: "Receita Federal" },
  // ADR-238 A17 L1 — seguradora previdência privada.
  { value: "brasilprev", label: "BrasilPrev" },
];

const NONE = "__none__";

interface EditDocumentDialogProps {
  workspaceId: string;
  doc: DocumentResponse | null;
  open: boolean;
  onClose: () => void;
  onSaved: (updated: DocumentResponse) => void;
}

export function EditDocumentDialog({
  workspaceId,
  doc,
  open,
  onClose,
  onSaved,
}: EditDocumentDialogProps) {
  const [docType, setDocType] = useState<DocumentType | typeof NONE>(NONE);
  const [bankCode, setBankCode] = useState<string>(NONE);
  const [period, setPeriod] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !doc) return;
    setDocType(doc.doc_type ?? NONE);
    setBankCode(doc.bank_code ?? NONE);
    setPeriod(doc.period ?? "");
    setError(null);
  }, [open, doc]);

  async function handleSave() {
    if (!doc) return;
    setSaving(true);
    setError(null);
    try {
      const payload: Parameters<typeof updateDocumentClassification>[2] = {
        doc_type: docType === NONE ? null : docType,
        bank_code: bankCode === NONE ? null : bankCode,
        period: period.trim() === "" ? null : period.trim(),
      };
      const updated = await updateDocumentClassification(workspaceId, doc.id, payload);
      onSaved(updated);
      onClose();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : "Erro ao salvar classificação. Tente novamente.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Editar classificação</DialogTitle>
          <DialogDescription>
            {doc?.original_name ?? "Documento"}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4 py-2">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="doc-type">Tipo</Label>
            <Select
              value={docType}
              onValueChange={(v) => v && setDocType(v as DocumentType | typeof NONE)}
            >
              <SelectTrigger id="doc-type" className="w-full">
                <SelectValue placeholder="Selecionar tipo" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NONE}>—</SelectItem>
                {DOC_TYPE_OPTIONS.map((o) => (
                  <SelectItem key={o.value} value={o.value}>
                    {o.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="bank-code">Instituição</Label>
            <Select value={bankCode} onValueChange={(v) => v && setBankCode(v)}>
              <SelectTrigger id="bank-code" className="w-full">
                <SelectValue placeholder="Selecionar instituição" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NONE}>—</SelectItem>
                {INSTITUTION_OPTIONS.map((o) => (
                  <SelectItem key={o.value} value={o.value}>
                    {o.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="period">Período</Label>
            <Input
              id="period"
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              placeholder="AAAAMM ou AAAAMM_AAAAMM (ex: 202406 ou 202401_202412)"
            />
            <p className="text-xs text-muted-foreground">
              Use <code>999999</code> para período indeterminado (ex: faturas sem competência).
            </p>
          </div>

          {error && (
            <div className="rounded-md bg-loss/10 p-2 text-sm text-loss">{error}</div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>
            Cancelar
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            <Save className="mr-1.5 h-4 w-4" />
            {saving ? "Salvando..." : "Salvar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

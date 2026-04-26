"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/Spinner";
import { useWorkspace } from "@/lib/WorkspaceProvider";
import { useTransferConfig } from "@/hooks/useTransferConfig";
import type { TransferConfigData } from "@/lib/api";

const EMPTY_DRAFT: TransferConfigData = {
  patterns_pix: [],
  patterns_global: [],
  patterns_bank_specific: {},
  recipients: [],
};

function cloneDraft(data: TransferConfigData): TransferConfigData {
  return {
    patterns_pix: [...data.patterns_pix],
    patterns_global: [...data.patterns_global],
    patterns_bank_specific: Object.fromEntries(
      Object.entries(data.patterns_bank_specific).map(([k, v]) => [k, [...v]]),
    ),
    recipients: [...data.recipients],
  };
}

function draftsEqual(a: TransferConfigData, b: TransferConfigData): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

export default function TransferConfigEditor() {
  const { workspace } = useWorkspace();
  const workspaceId = workspace?.id;
  const { data, loading, saving, error, success, save, clearMessages } = useTransferConfig(workspaceId);
  const [draft, setDraft] = useState<TransferConfigData>(EMPTY_DRAFT);

  useEffect(() => {
    if (data) setDraft(cloneDraft(data));
  }, [data]);

  const dirty = useMemo(() => (data ? !draftsEqual(draft, data) : false), [draft, data]);

  const updateList = useCallback(
    (key: "patterns_pix" | "patterns_global" | "recipients", values: string[]) => {
      setDraft((prev) => ({ ...prev, [key]: values }));
      clearMessages();
    },
    [clearMessages],
  );

  const updateBankSpecific = useCallback(
    (next: Record<string, string[]>) => {
      setDraft((prev) => ({ ...prev, patterns_bank_specific: next }));
      clearMessages();
    },
    [clearMessages],
  );

  async function handleSave() {
    if (!workspaceId) return;
    try {
      await save(draft);
    } catch {
      // mensagem já foi setada pelo hook
    }
  }

  if (!workspaceId) {
    return null;
  }

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {error ? (
        <div role="alert" className="rounded-lg bg-loss/10 p-3 text-sm text-loss">
          {error}
        </div>
      ) : null}
      {success ? (
        <div role="status" className="rounded-lg bg-gain/10 p-3 text-sm text-gain">
          {success}
        </div>
      ) : null}

      <p className="text-sm text-muted-foreground">
        Configure os nomes de pessoas e contas próprias da família para que transferências entre elas não apareçam como gastos.
      </p>

      <StringListSection
        title="Recipients"
        description="Nomes ou identificadores de contas próprias. Transações cuja descrição contiver qualquer um destes nomes serão classificadas como transferência interna (não como gasto)."
        placeholder="Ex: DAVID ROBERT CAMARGO"
        items={draft.recipients}
        onChange={(next) => updateList("recipients", next)}
        addLabel="Adicionar recipient"
        testId="recipients"
      />

      <StringListSection
        title="Padrões PIX"
        description="Trechos de descrição de PIX que indicam transferência entre contas próprias (ex.: PIX TRANSF DAVID)."
        placeholder="Ex: PIX TRANSF DAVID"
        items={draft.patterns_pix}
        onChange={(next) => updateList("patterns_pix", next)}
        addLabel="Adicionar padrão PIX"
        testId="patterns-pix"
      />

      <StringListSection
        title="Padrões globais"
        description="Trechos que valem em qualquer banco (ex.: TED D HBANK)."
        placeholder="Ex: TED D HBANK"
        items={draft.patterns_global}
        onChange={(next) => updateList("patterns_global", next)}
        addLabel="Adicionar padrão global"
        testId="patterns-global"
      />

      <BankSpecificSection
        bankPatterns={draft.patterns_bank_specific}
        onChange={updateBankSpecific}
      />

      <div className="flex items-center justify-end gap-3 pt-2">
        <Button onClick={handleSave} disabled={!dirty || saving} data-testid="save-transfer-config">
          {saving ? "Salvando..." : "Salvar alterações"}
        </Button>
      </div>
    </div>
  );
}

interface StringListSectionProps {
  title: string;
  description: string;
  placeholder: string;
  items: string[];
  onChange: (next: string[]) => void;
  addLabel: string;
  testId: string;
}

function StringListSection({ title, description, placeholder, items, onChange, addLabel, testId }: StringListSectionProps) {
  const [draftItem, setDraftItem] = useState("");

  function handleAdd() {
    const value = draftItem.trim();
    if (!value) return;
    if (items.includes(value)) {
      setDraftItem("");
      return;
    }
    onChange([...items, value]);
    setDraftItem("");
  }

  function handleEdit(index: number, value: string) {
    const next = [...items];
    next[index] = value;
    onChange(next);
  }

  function handleRemove(index: number) {
    onChange(items.filter((_, i) => i !== index));
  }

  return (
    <Card data-testid={`section-${testId}`}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {items.map((item, index) => (
            <li key={`${testId}-${index}`} className="flex items-center gap-2">
              <Label htmlFor={`${testId}-item-${index}`} className="sr-only">
                {`${title} ${index + 1}`}
              </Label>
              <Input
                id={`${testId}-item-${index}`}
                value={item}
                onChange={(event) => handleEdit(index, event.target.value)}
                data-testid={`${testId}-item-${index}`}
              />
              <Button
                variant="ghost"
                size="sm"
                aria-label={`Remover ${title.toLowerCase()} ${index + 1}`}
                onClick={() => handleRemove(index)}
                className="text-muted-foreground hover:text-destructive"
                data-testid={`${testId}-remove-${index}`}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </li>
          ))}
          {items.length === 0 ? (
            <li className="text-xs italic text-muted-foreground">Nenhum item cadastrado.</li>
          ) : null}
        </ul>

        <div className="mt-4 flex items-center gap-2">
          <Label htmlFor={`${testId}-add-input`} className="sr-only">
            {addLabel}
          </Label>
          <Input
            id={`${testId}-add-input`}
            placeholder={placeholder}
            value={draftItem}
            onChange={(event) => setDraftItem(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                handleAdd();
              }
            }}
            data-testid={`${testId}-new-input`}
          />
          <Button
            variant="outline"
            onClick={handleAdd}
            disabled={!draftItem.trim()}
            data-testid={`${testId}-add`}
          >
            <Plus className="mr-1 h-4 w-4" />
            {addLabel}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

interface BankSpecificSectionProps {
  bankPatterns: Record<string, string[]>;
  onChange: (next: Record<string, string[]>) => void;
}

function BankSpecificSection({ bankPatterns, onChange }: BankSpecificSectionProps) {
  const [newBankCode, setNewBankCode] = useState("");
  const banks = Object.keys(bankPatterns).sort();

  function addBank() {
    const code = newBankCode.trim().toLowerCase();
    if (!code) return;
    if (bankPatterns[code]) {
      setNewBankCode("");
      return;
    }
    onChange({ ...bankPatterns, [code]: [] });
    setNewBankCode("");
  }

  function removeBank(code: string) {
    const next = { ...bankPatterns };
    delete next[code];
    onChange(next);
  }

  function setPatterns(code: string, patterns: string[]) {
    onChange({ ...bankPatterns, [code]: patterns });
  }

  return (
    <Card data-testid="section-patterns-bank">
      <CardHeader>
        <CardTitle>Padrões por banco</CardTitle>
        <CardDescription>
          Trechos que <strong>só</strong> marcam transferência interna em extratos do banco específico (ex.: a palavra Pagamento no C6 Bank).
        </CardDescription>
      </CardHeader>
      <CardContent>
        {banks.length === 0 ? (
          <p className="text-xs italic text-muted-foreground">Nenhum banco com padrão específico.</p>
        ) : (
          <ul className="space-y-4">
            {banks.map((code) => (
              <BankBlock
                key={code}
                code={code}
                patterns={bankPatterns[code] ?? []}
                onPatternsChange={(next) => setPatterns(code, next)}
                onRemoveBank={() => removeBank(code)}
              />
            ))}
          </ul>
        )}

        <div className="mt-4 flex items-center gap-2">
          <Label htmlFor="bank-new-code" className="sr-only">
            Código do banco
          </Label>
          <Input
            id="bank-new-code"
            placeholder="Código do banco (ex: c6bank, itau)"
            value={newBankCode}
            onChange={(event) => setNewBankCode(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                addBank();
              }
            }}
            data-testid="bank-new-input"
          />
          <Button variant="outline" onClick={addBank} disabled={!newBankCode.trim()} data-testid="bank-add">
            <Plus className="mr-1 h-4 w-4" />
            Adicionar banco
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

interface BankBlockProps {
  code: string;
  patterns: string[];
  onPatternsChange: (next: string[]) => void;
  onRemoveBank: () => void;
}

function BankBlock({ code, patterns, onPatternsChange, onRemoveBank }: BankBlockProps) {
  const [draftPattern, setDraftPattern] = useState("");

  function addPattern() {
    const value = draftPattern.trim();
    if (!value) return;
    if (patterns.includes(value)) {
      setDraftPattern("");
      return;
    }
    onPatternsChange([...patterns, value]);
    setDraftPattern("");
  }

  function editPattern(index: number, value: string) {
    const next = [...patterns];
    next[index] = value;
    onPatternsChange(next);
  }

  function removePattern(index: number) {
    onPatternsChange(patterns.filter((_, i) => i !== index));
  }

  return (
    <li className="rounded-md border border-border bg-muted/30 p-3" data-testid={`bank-${code}`}>
      <div className="mb-2 flex items-center justify-between gap-2">
        <h4 className="text-sm font-semibold">{code}</h4>
        <Button
          variant="ghost"
          size="sm"
          aria-label={`Remover banco ${code}`}
          onClick={onRemoveBank}
          className="text-muted-foreground hover:text-destructive"
          data-testid={`bank-${code}-remove`}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
      <ul className="space-y-2">
        {patterns.map((pattern, index) => (
          <li key={`${code}-pattern-${index}`} className="flex items-center gap-2">
            <Label htmlFor={`${code}-pattern-${index}`} className="sr-only">
              {`Padrão ${index + 1} de ${code}`}
            </Label>
            <Input
              id={`${code}-pattern-${index}`}
              value={pattern}
              onChange={(event) => editPattern(index, event.target.value)}
              data-testid={`bank-${code}-pattern-${index}`}
            />
            <Button
              variant="ghost"
              size="sm"
              aria-label={`Remover padrão ${index + 1} de ${code}`}
              onClick={() => removePattern(index)}
              className="text-muted-foreground hover:text-destructive"
              data-testid={`bank-${code}-pattern-remove-${index}`}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </li>
        ))}
        {patterns.length === 0 ? (
          <li className="text-xs italic text-muted-foreground">Nenhum padrão para este banco.</li>
        ) : null}
      </ul>

      <div className="mt-3 flex items-center gap-2">
        <Label htmlFor={`${code}-add-pattern`} className="sr-only">
          Novo padrão para {code}
        </Label>
        <Input
          id={`${code}-add-pattern`}
          placeholder="Ex: Pagamento"
          value={draftPattern}
          onChange={(event) => setDraftPattern(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              addPattern();
            }
          }}
          data-testid={`bank-${code}-new-input`}
        />
        <Button
          variant="outline"
          size="sm"
          onClick={addPattern}
          disabled={!draftPattern.trim()}
          data-testid={`bank-${code}-add`}
        >
          <Plus className="mr-1 h-4 w-4" />
          Adicionar padrão
        </Button>
      </div>
    </li>
  );
}

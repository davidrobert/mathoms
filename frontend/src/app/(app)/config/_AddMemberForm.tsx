"use client";

import type { FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Plus } from "lucide-react";

const ROLES = [
  { value: "titular", label: "Titular" },
  { value: "conjuge", label: "Cônjuge" },
  { value: "filho", label: "Filho(a)" },
  { value: "dependente", label: "Dependente" },
];

export function AddMemberForm({
  open,
  onOpen,
  onCancel,
  onSubmit,
}: {
  open: boolean;
  onOpen: () => void;
  onCancel: () => void;
  onSubmit: (e: FormEvent<HTMLFormElement>) => void;
}) {
  if (!open) {
    return (
      <Button variant="outline" className="mt-4 w-full border-dashed" onClick={onOpen}>
        <Plus className="mr-2 h-4 w-4" />
        Adicionar membro
      </Button>
    );
  }

  return (
    <form onSubmit={onSubmit} className="mt-4 rounded-xl border border-primary/30 bg-primary/5 p-5 space-y-4">
      <div>
        <h3 className="font-medium">Novo membro</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          Não é preciso preencher um &quot;código&quot; técnico: o sistema cria um identificador interno a partir do nome.
          Depois de salvar, o cartão abre para você vincular contas bancárias.
        </p>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <Label className="mb-1 block text-xs text-muted-foreground">Nome completo (civil atual)</Label>
          <Input name="full_name" placeholder="Como nos documentos oficiais" required />
        </div>
        <div>
          <Label className="mb-1 block text-xs text-muted-foreground">Como prefere ser chamado(a)</Label>
          <Input name="short_name" placeholder="Ex.: Maria, David" required />
        </div>
        <div className="sm:col-span-2">
          <Label className="mb-1 block text-xs text-muted-foreground">Nome civil anterior (opcional)</Label>
          <Input name="birth_name" placeholder="Se ainda aparece em extratos ou contratos antigos" />
        </div>
        <div>
          <Label className="mb-1 block text-xs text-muted-foreground">CPF</Label>
          <Input name="cpf" placeholder="11 dígitos" />
        </div>
        <div>
          <Label className="mb-1 block text-xs text-muted-foreground">Nascimento</Label>
          <Input name="birth_date" type="date" />
        </div>
        <div>
          <Label className="mb-1 block text-xs text-muted-foreground">Papel</Label>
          <select name="role" required className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring">
            {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
        </div>
        <details className="sm:col-span-2 rounded-lg border border-border/60 bg-background/50 p-3 text-xs">
          <summary className="cursor-pointer font-medium text-foreground">Identificador interno (opcional)</summary>
          <p className="mt-2 text-muted-foreground">
            Só altere se estiver importando dados que já usam uma chave fixa (ex.: <code className="rounded bg-muted px-1">david</code>).
            Requisitos: letras minúsculas, números e underscore; único neste workspace.
          </p>
          <Input name="key" className="mt-2 font-mono text-sm" placeholder="ex.: maria_silva" />
        </details>
      </div>
      <div className="flex gap-2">
        <Button type="submit">Salvar e abrir edição</Button>
        <Button type="button" variant="outline" onClick={onCancel}>Cancelar</Button>
      </div>
    </form>
  );
}

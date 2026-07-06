"use client";

// Escrita de CPF é write-only e nunca pré-preenchida com o valor atual (nem
// mascarado, nem completo) — evita o foot-gun de salvar a máscara
// "***.***.789-00" como se fosse o CPF real ao confirmar sem digitar nada.

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function ChangeCpfButton({ onSave }: { onSave: (cpf: string) => void }) {
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState("");

  if (!editing) {
    return (
      <button
        type="button"
        onClick={() => setEditing(true)}
        className="text-xs font-semibold text-primary hover:underline"
      >
        Alterar CPF
      </button>
    );
  }

  function cancel() {
    setVal("");
    setEditing(false);
  }

  function save() {
    const trimmed = val.trim();
    if (!trimmed) return;
    onSave(trimmed);
    cancel();
  }

  return (
    <div className="flex items-center gap-1">
      <Input
        value={val}
        onChange={(e) => setVal(e.target.value)}
        placeholder="Novo CPF (11 dígitos)"
        autoFocus
        className="h-8 w-40 text-sm"
      />
      <Button size="sm" disabled={!val.trim()} onClick={save}>
        Salvar
      </Button>
      <Button size="sm" variant="outline" onClick={cancel}>
        Cancelar
      </Button>
    </div>
  );
}

"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { bankLabel } from "@/lib/format";
import type { BankAccountConfig, IrpfSuggestion } from "@/lib/api";

export type DiffResolution = "merge" | "create_separate";

interface Props {
  open: boolean;
  suggestion: IrpfSuggestion | null;
  collisionAccount: BankAccountConfig | null;
  onResolve: (resolution: DiffResolution) => void;
  onCancel: () => void;
}

function _accountLine(label: string, agency?: string | null, number?: string | null) {
  return (
    <p className="text-sm text-muted-foreground">
      {label}
      {agency && <span className="ml-2">Ag: {agency}</span>}
      {number && <span className="ml-2">Cc: {number}</span>}
    </p>
  );
}

export function IrpfDiffModal({
  open,
  suggestion,
  collisionAccount,
  onResolve,
  onCancel,
}: Props) {
  if (!suggestion || !collisionAccount) return null;
  const inst = bankLabel(suggestion.institution_code);
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onCancel()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Estas são a mesma conta?</DialogTitle>
          <DialogDescription>
            Encontramos {inst} cadastrado com um número diferente. Confirme antes
            de adicionar para não duplicar.
          </DialogDescription>
        </DialogHeader>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2" data-testid="irpf-diff-modal-grid">
          <div className="rounded-lg border border-border/60 bg-muted/30 p-3">
            <p className="mb-1 text-xs font-medium uppercase text-muted-foreground">
              IRPF {suggestion.irpf_year} declara
            </p>
            <p className="font-medium">{inst}</p>
            {_accountLine("Conta", suggestion.agency, suggestion.account_number_raw)}
          </div>
          <div className="rounded-lg border border-border/60 bg-muted/30 p-3">
            <p className="mb-1 text-xs font-medium uppercase text-muted-foreground">
              Você cadastrou
            </p>
            <p className="font-medium">{bankLabel(collisionAccount.institution_code)}</p>
            {_accountLine("Conta", collisionAccount.agency, collisionAccount.account_number)}
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onResolve("merge")}>
            Mesma conta — manter cadastrado
          </Button>
          <Button onClick={() => onResolve("create_separate")}>
            Contas diferentes — criar as duas
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

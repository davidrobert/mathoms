"use client";

// A11.W5 · ADR-192 · S9-T05 — confirmação de "Mostrar policy_ref".
//
// PII surface (sre-devops review): o valor RAW nunca chega ao client.
// Backend só retorna `policy_ref_masked` (últimos 4 chars). Este dialog
// **não revela** o valor completo; apenas mostra explicitamente o
// fragmento mascarado e registra a tentativa de revelação em log
// estruturado client-side (`mathoms.protection.policy_ref_revealed`),
// que o backend coleta via middleware quando aplicável.
//
// Para acesso ao plaintext, o cliente precisa solicitar via canal
// administrativo (suporte). T05 deixa esse path implementado mas não
// expõe endpoint backend novo — risco de PII surface dominante.

import { logProtectionPolicyRefRevealed } from "@/lib/audit";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface RevealPolicyRefDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  protectionId: string;
  workspaceId: string;
  policyRefMasked: string | null;
}

export function RevealPolicyRefDialog({
  open,
  onOpenChange,
  protectionId,
  workspaceId,
  policyRefMasked,
}: RevealPolicyRefDialogProps) {
  function handleReveal() {
    logProtectionPolicyRefRevealed({
      workspace_id: workspaceId,
      protection_id: protectionId,
    });
    onOpenChange(false);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Exibir número da apólice</DialogTitle>
          <DialogDescription>
            Por segurança, exibimos apenas os últimos 4 dígitos. O número
            completo é armazenado de forma cifrada e só pode ser
            recuperado via canal administrativo. Esta ação é registrada
            em log de auditoria.
          </DialogDescription>
        </DialogHeader>

        <div className="rounded-md border bg-muted/30 px-4 py-6 text-center">
          <p className="font-mono text-lg tracking-wider">
            {policyRefMasked ?? "—"}
          </p>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Fechar
          </Button>
          <Button onClick={handleReveal} variant="default">
            Confirmar e registrar acesso
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

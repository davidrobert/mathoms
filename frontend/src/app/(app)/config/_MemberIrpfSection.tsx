"use client";

import type { BankAccountConfig, IrpfSuggestion } from "@/lib/api";
import { IrpfSuggestionCard } from "./_IrpfSuggestionCard";
import { bankLabel } from "@/lib/format";

interface Props {
  suggestions: IrpfSuggestion[];
  memberAccounts: BankAccountConfig[];
  onAccept: (suggestion: IrpfSuggestion) => void;
  onDismiss: (suggestion: IrpfSuggestion) => void;
  isBusy?: boolean;
}

function _findCollisionAccount(
  suggestion: IrpfSuggestion,
  accounts: BankAccountConfig[],
): BankAccountConfig | undefined {
  if (!suggestion.collision_with_account_id) return undefined;
  return accounts.find((acc) => acc.id === suggestion.collision_with_account_id);
}

function _formatCollisionLabel(acc: BankAccountConfig): string {
  const inst = bankLabel(acc.institution_code);
  return acc.account_number ? `${inst} ${acc.account_number}` : inst;
}

export function MemberIrpfSection({
  suggestions,
  memberAccounts,
  onAccept,
  onDismiss,
  isBusy = false,
}: Props) {
  if (suggestions.length === 0) return null;
  const firstYear = suggestions[0]?.irpf_year ?? 0;
  return (
    <div
      className="border-t border-border/40 pt-3 space-y-2"
      data-testid="member-irpf-section"
    >
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Encontradas no seu IRPF {firstYear}
        <span className="ml-2 normal-case text-muted-foreground/80 font-normal">
          · você declarou estas contas
        </span>
      </p>
      <div className="space-y-2">
        {suggestions.map((s) => {
          const collision = _findCollisionAccount(s, memberAccounts);
          return (
            <IrpfSuggestionCard
              key={`${s.institution_code}-${s.account_number_norm ?? "nonum"}-${s.member_key}`}
              suggestion={s}
              collisionAccountLabel={collision ? _formatCollisionLabel(collision) : undefined}
              onAccept={onAccept}
              onDismiss={onDismiss}
              isBusy={isBusy}
            />
          );
        })}
      </div>
    </div>
  );
}

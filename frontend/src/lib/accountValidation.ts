/**
 * Validação de conta bancária na UI (ADR-226 PR1).
 *
 * Espelha `pipeline/domain/services/account_normalization.py` no formato
 * canônico digits-only — usado pelo MembersTab para detectar colisão
 * (banco + número) entre membros antes do POST.
 */

import type { BankAccountConfig, FamilyMemberConfig } from "./api";

export function normalizeAccountNumber(raw: string | null | undefined): string | null {
  if (!raw) return null;
  const digits = raw.replace(/\D/g, "");
  return digits || null;
}

export interface AccountCollision {
  ownerName: string;
}

export function findAccountCollision(
  members: FamilyMemberConfig[],
  ownerMemberId: string,
  institution_code: string,
  account_number: string | null | undefined,
): AccountCollision | null {
  const norm = normalizeAccountNumber(account_number);
  if (norm === null) return null;
  for (const m of members) {
    if (m.id === ownerMemberId) continue;
    const hit = m.accounts.find(
      (acc: BankAccountConfig) =>
        acc.institution_code === institution_code &&
        normalizeAccountNumber(acc.account_number) === norm,
    );
    if (hit) return { ownerName: m.full_name };
  }
  return null;
}

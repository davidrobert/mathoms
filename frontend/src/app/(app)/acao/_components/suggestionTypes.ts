// Direção E · Onda 5 — handler types compartilhados entre InboxTab e
// SuggestionCard. Mantém o card desacoplado do hook (testável em
// isolamento via vitest).

import type {
  AcceptSuggestionPayload,
  DismissSuggestionPayload,
  ModifySuggestionPayload,
  Suggestion,
} from "@/lib/api";

export type AcceptHandler = (
  id: string,
  payload: AcceptSuggestionPayload,
) => Promise<Suggestion>;

export type ModifyHandler = (
  id: string,
  payload: ModifySuggestionPayload,
) => Promise<Suggestion>;

export type DismissHandler = (
  id: string,
  payload: DismissSuggestionPayload,
) => Promise<Suggestion>;

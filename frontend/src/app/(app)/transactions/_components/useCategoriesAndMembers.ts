"use client";

import { useEffect, useState } from "react";
import {
  listCategoriesResolved,
  listMembers,
  type CategoryConfig,
  type FamilyMemberConfig,
} from "@/lib/api";

/** Hook compartilhado entre transactions e config — read-path moderno
 * (A7.3 · ADR-137). Antes consumia `/config/categories` (legacy) — workspace
 * novo abria lista vazia porque o endpoint legado não conhece o template
 * global v1.
 */
export function useCategoriesAndMembers(workspaceId: string | undefined) {
  const [categories, setCategories] = useState<CategoryConfig[]>([]);
  const [members, setMembers] = useState<FamilyMemberConfig[]>([]);

  useEffect(() => {
    if (!workspaceId) return;
    listCategoriesResolved(workspaceId)
      .then((r) => setCategories(r.categories))
      .catch(() => {});
    listMembers(workspaceId).then((r) => setMembers(r.members)).catch(() => {});
  }, [workspaceId]);

  return { categories, members };
}

"use client";

import { useEffect, useState } from "react";
import {
  listCategories,
  listMembers,
  type CategoryConfig,
  type FamilyMemberConfig,
} from "@/lib/api";

export function useCategoriesAndMembers(workspaceId: string | undefined) {
  const [categories, setCategories] = useState<CategoryConfig[]>([]);
  const [members, setMembers] = useState<FamilyMemberConfig[]>([]);

  useEffect(() => {
    if (!workspaceId) return;
    listCategories(workspaceId).then((r) => setCategories(r.categories)).catch(() => {});
    listMembers(workspaceId).then((r) => setMembers(r.members)).catch(() => {});
  }, [workspaceId]);

  return { categories, members };
}

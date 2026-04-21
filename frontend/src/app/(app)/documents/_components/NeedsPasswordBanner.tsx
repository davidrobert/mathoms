"use client";

import Link from "next/link";
import { KeyRound } from "lucide-react";
import { Button } from "@/components/ui/button";

export function NeedsPasswordBanner({
  count,
  onRetry,
}: {
  count: number;
  onRetry: () => void;
}) {
  if (count === 0) return null;
  return (
    <div className="mb-4 flex items-center justify-between rounded-lg bg-alert/10 px-4 py-3">
      <p className="text-sm text-alert">
        <KeyRound className="mr-1.5 inline-block h-4 w-4" />
        <span className="font-medium">{count}</span> documento(s) protegido(s) por senha.{" "}
        <Link href="/vault" className="underline">
          Adicione senhas no vault
        </Link>{" "}
        e tente novamente.
      </p>
      <Button variant="outline" size="sm" onClick={onRetry}>
        Tentar desbloquear
      </Button>
    </div>
  );
}

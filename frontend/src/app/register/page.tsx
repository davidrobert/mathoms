"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { resolveNext } from "@/lib/nextUrl";
import { Spinner } from "@/components/Spinner";
import { StatusPageFooter } from "@/components/StatusPageFooter";
import { RegisterForm } from "./RegisterForm";

function RegisterPageInner() {
  const nextUrl = resolveNext(useSearchParams().get("next"));

  return (
    <div className="flex min-h-screen flex-col px-4">
      <div className="flex flex-1 items-center justify-center">
        <div className="w-full max-w-md">
          <div className="mb-8 text-center">
            <h1 className="text-3xl font-bold tracking-tight">Mathoms AI</h1>
            <p className="mt-2 text-sm text-muted-foreground">Crie sua conta de acesso</p>
            <p className="mx-auto mt-3 max-w-md text-xs leading-relaxed text-muted-foreground">
              Isto é só o <span className="text-foreground/90">login</span> (quem usa o app). Depois de entrar, seu nome e
              email aparecem em <span className="font-medium text-foreground">Configurações → Acessos</span>. As pessoas
              que entram no relatório e no pipeline são cadastradas em{" "}
              <span className="font-medium text-foreground">Configurações → Membros</span>.
            </p>
          </div>
          <RegisterForm nextUrl={nextUrl} />
        </div>
      </div>
      <StatusPageFooter variant="auth" />
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Spinner size="lg" />
        </div>
      }
    >
      <RegisterPageInner />
    </Suspense>
  );
}

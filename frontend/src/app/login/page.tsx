"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { resolveNext } from "@/lib/nextUrl";
import { Spinner } from "@/components/Spinner";
import { StatusPageFooter } from "@/components/StatusPageFooter";
import { LoginForm } from "./LoginForm";

function LoginPageInner() {
  const nextUrl = resolveNext(useSearchParams().get("next"));

  return (
    <div className="flex min-h-screen flex-col px-4">
      <div className="flex flex-1 items-center justify-center">
        <div className="w-full max-w-md">
          <div className="mb-8 text-center">
            <h1 className="text-3xl font-bold tracking-tight">Mathoms AI</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Relatório Financeiro Familiar
            </p>
          </div>
          <LoginForm nextUrl={nextUrl} />
        </div>
      </div>
      <StatusPageFooter variant="auth" />
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Spinner size="lg" />
        </div>
      }
    >
      <LoginPageInner />
    </Suspense>
  );
}

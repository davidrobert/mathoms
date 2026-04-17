"use client";

import { FormEvent, Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { login, setToken, ApiError } from "@/lib/api";
import { resolveNext } from "@/lib/nextUrl";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/Spinner";
import { StatusPageFooter } from "@/components/StatusPageFooter";

function LoginPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextUrl = resolveNext(searchParams.get("next"));
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await login(email, password);
      setToken(data.access_token);
      router.push(nextUrl);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(
          err.status === 401
            ? "Email ou senha incorretos"
            : err.detail
        );
      } else {
        setError("Erro de conexão. Tente novamente.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col px-4">
      <div className="flex flex-1 items-center justify-center">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold tracking-tight">Fin</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Relatório Financeiro Familiar
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Entrar</CardTitle>
          </CardHeader>
          <CardContent>
            {error && (
              <div className="mb-4 rounded-lg bg-loss/10 p-3 text-sm text-loss">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="seu@email.com"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Senha</Label>
                <Input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                />
              </div>

              <Button type="submit" disabled={loading} className="w-full">
                {loading ? (
                  <span className="inline-flex items-center gap-2">
                    <Spinner size="sm" className="text-primary-foreground" />
                    Entrando...
                  </span>
                ) : (
                  "Entrar"
                )}
              </Button>
            </form>

            <p className="mt-4 text-center text-sm text-muted-foreground">
              Não tem conta?{" "}
              <Link
                href={`/register${nextUrl !== "/documents" ? `?next=${encodeURIComponent(nextUrl)}` : ""}`}
                className="font-medium text-primary hover:underline"
              >
                Criar conta
              </Link>
            </p>
          </CardContent>
        </Card>
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

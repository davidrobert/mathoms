"use client";

import { FormEvent, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { register, setToken, ApiError } from "@/lib/api";
import { resolveNext } from "@/lib/nextUrl";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/Spinner";
import { StatusPageFooter } from "@/components/StatusPageFooter";

export default function RegisterPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextUrl = resolveNext(searchParams.get("next"));
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await register(email, password, fullName);
      setToken(data.access_token);
      router.push(nextUrl);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(
          err.status === 409
            ? "Este email já está cadastrado"
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
          <p className="mt-2 text-sm text-muted-foreground">Crie sua conta de acesso</p>
          <p className="mx-auto mt-3 max-w-md text-xs leading-relaxed text-muted-foreground">
            Isto é só o <span className="text-foreground/90">login</span> (quem usa o app). Depois de entrar, seu nome e
            email aparecem em <span className="font-medium text-foreground">Configurações → Acessos</span>. As pessoas
            que entram no relatório e no pipeline são cadastradas em{" "}
            <span className="font-medium text-foreground">Configurações → Membros</span>.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Criar conta</CardTitle>
          </CardHeader>
          <CardContent>
            {error && (
              <div className="mb-4 rounded-lg bg-loss/10 p-3 text-sm text-loss">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="fullName">Seu nome</Label>
                <Input
                  id="fullName"
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Como deve aparecer na sua conta"
                  autoComplete="name"
                />
                <p className="text-xs text-muted-foreground">
                  Independente dos membros da família que você configurará no relatório.
                </p>
              </div>

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
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Mínimo 6 caracteres"
                />
              </div>

              <Button type="submit" disabled={loading} className="w-full">
                {loading ? (
                  <span className="inline-flex items-center gap-2">
                    <Spinner size="sm" className="text-primary-foreground" />
                    Criando conta...
                  </span>
                ) : (
                  "Criar conta"
                )}
              </Button>
            </form>

            <p className="mt-4 text-center text-sm text-muted-foreground">
              Já tem conta?{" "}
              <Link
                href={`/login${nextUrl !== "/documents" ? `?next=${encodeURIComponent(nextUrl)}` : ""}`}
                className="font-medium text-primary hover:underline"
              >
                Entrar
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

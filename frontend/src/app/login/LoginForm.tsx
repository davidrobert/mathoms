"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { login, setToken, loginErrorMessage, type AuthErrorMessage } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/Spinner";

function registerHref(nextUrl: string): string {
  return `/register${nextUrl !== "/documents" ? `?next=${encodeURIComponent(nextUrl)}` : ""}`;
}

export function LoginForm({ nextUrl }: { nextUrl: string }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<AuthErrorMessage | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = await login(email, password);
      setToken(data.access_token);
      router.push(nextUrl);
    } catch (err) {
      // Mantém o erro técnico no console p/ debug local; o usuário vê
      // a mensagem amigável montada por loginErrorMessage().
      console.error("[login] failed", err);
      setError(loginErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Entrar</CardTitle>
      </CardHeader>
      <CardContent>
        {error && (
          <div
            role="alert"
            aria-live="polite"
            className="mb-4 rounded-lg border border-loss/30 bg-loss/10 p-3 text-sm"
          >
            <p className="font-medium text-loss">{error.headline}</p>
            {error.hint && (
              <p className="mt-1 text-muted-foreground">{error.hint}</p>
            )}
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
              suppressHydrationWarning
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
              suppressHydrationWarning
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
          <Link href={registerHref(nextUrl)} className="font-medium text-primary hover:underline">
            Criar conta
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}

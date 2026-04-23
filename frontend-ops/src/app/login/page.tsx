"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { api, AdminApiError } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.login(username, password);
      router.replace("/users");
    } catch (err) {
      if (err instanceof AdminApiError && err.status === 401) {
        setError("Usuário ou senha inválidos.");
      } else if (err instanceof AdminApiError && err.status === 503) {
        setError("Configuração indisponível. Verifique internal_operators.yaml.");
      } else {
        setError("Falha ao autenticar. Tente novamente.");
      }
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-surface-bg px-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm bg-surface-card border border-surface-border rounded-card p-8 shadow-md"
      >
        <h1 className="font-display text-2xl font-semibold text-brand-primary mb-1">
          Console interno
        </h1>
        <p className="text-sm text-surface-muted-fg mb-6">
          Acesso restrito a operadores. Sessão registrada em audit.
        </p>

        <label className="block mb-4">
          <span className="text-sm font-medium text-surface-fg">Usuário</span>
          <input
            type="text"
            autoComplete="username"
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="mt-1 w-full rounded-md border border-surface-border bg-surface-bg px-3 py-2 text-surface-fg focus:outline-none focus:ring-2 focus:ring-brand-primary"
          />
        </label>

        <label className="block mb-6">
          <span className="text-sm font-medium text-surface-fg">Senha</span>
          <input
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-md border border-surface-border bg-surface-bg px-3 py-2 text-surface-fg focus:outline-none focus:ring-2 focus:ring-brand-primary"
          />
        </label>

        {error && (
          <p
            role="alert"
            className="mb-4 text-sm text-brand-danger bg-brand-danger/10 border border-brand-danger/30 rounded-md px-3 py-2"
          >
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-md bg-brand-primary text-brand-primary-fg font-medium py-2 hover:opacity-90 disabled:opacity-50"
        >
          {loading ? "Autenticando…" : "Entrar"}
        </button>
      </form>
    </main>
  );
}

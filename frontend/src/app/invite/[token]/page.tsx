"use client";

/**
 * Página pública de aceite de convite (F9).
 *
 * Fluxo:
 *   1. Pega `token` do path, busca preview via `GET /invitations/{token}`
 *      (rota pública — não precisa de auth).
 *   2. Se ok, mostra contexto (workspace, quem convidou, role).
 *   3. Se user NÃO está logado: botão "Entrar/Criar conta" → login?next=/invite/{token}
 *      (precisamos login com o email específico do convite, então melhor
 *      pedir login explícito do que tentar auto).
 *   4. Se user está logado: botão "Aceitar" → `POST /invitations/{token}/accept`
 *   5. Sucesso: localStorage currentWorkspaceId = ws.id, redirect /plano
 *
 * Erros tratados:
 *   - 404 → link inválido/digitado errado
 *   - 410 (expired/revoked) → estado "convite não vale mais"
 *   - 403 email_mismatch → user logado é outro; orienta trocar de conta
 *   - 409 already_accepted → manda pro workspace direto
 */

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";

import {
  ApiError,
  acceptInvitation,
  getToken,
  previewInvitation,
} from "@/lib/api";
import type { InvitationPreviewResponse } from "@/lib/api";
import { roleDescription, roleLabel } from "@/lib/roleLabels";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/Spinner";

const WORKSPACE_STORAGE_KEY = "fin.currentWorkspaceId";

export default function AcceptInvitePage() {
  const router = useRouter();
  const params = useParams<{ token: string }>();
  const token = params?.token ?? "";

  const [preview, setPreview] = useState<InvitationPreviewResponse | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [accepting, setAccepting] = useState(false);

  const isLoggedIn =
    typeof window !== "undefined" ? Boolean(getToken()) : false;
  const returnUrl = `/invite/${encodeURIComponent(token)}`;

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await previewInvitation(token);
        if (!cancelled) setPreview(data);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError && err.status === 404
              ? "Este link de convite não existe. Verifique se copiou corretamente."
              : err instanceof Error
                ? err.message
                : "Erro ao carregar convite."
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function handleAccept() {
    setAccepting(true);
    setError(null);
    try {
      const result = await acceptInvitation(token);
      if (typeof window !== "undefined") {
        window.localStorage.setItem(WORKSPACE_STORAGE_KEY, result.workspace_id);
      }
      router.push("/plano");
    } catch (err) {
      if (err instanceof ApiError) {
        // O detail do backend pode ser {code, message} ou string
        const detail = err.detail as unknown;
        const code =
          typeof detail === "object" && detail && "code" in detail
            ? (detail as { code: string }).code
            : undefined;

        if (code === "email_mismatch") {
          setError(
            "Este convite é para outro email. Saia da conta atual e entre " +
              "com o email correto."
          );
        } else if (code === "expired") {
          setError("Este convite expirou. Peça um novo ao responsável.");
        } else if (code === "revoked") {
          setError("Este convite foi cancelado pelo responsável.");
        } else if (code === "already_accepted") {
          // Já aceitou antes — só redireciona
          router.push("/plano");
          return;
        } else {
          setError(err.message);
        }
      } else {
        setError("Erro ao aceitar convite. Tente novamente.");
      }
      setAccepting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner />
      </div>
    );
  }

  if (error && !preview) {
    return (
      <div className="mx-auto flex min-h-screen max-w-md items-center px-6">
        <Card className="w-full">
          <CardHeader>
            <CardTitle>Convite inválido</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">{error}</p>
            <Link href="/login" className="mt-6 inline-block">
              <Button variant="outline">Ir para login</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!preview) return null;

  const inviterLabel = preview.invited_by_name ?? preview.invited_by_email;
  const isTerminal = preview.status !== "pending";

  return (
    <div className="mx-auto flex min-h-screen max-w-md items-center px-6">
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="text-lg">
            Você foi convidado para{" "}
            <span className="font-semibold">{preview.workspace_name}</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="rounded-md border bg-muted/30 p-4 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Convidado como</span>
              <span className="font-medium">{roleLabel(preview.role)}</span>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              {roleDescription(preview.role)}
            </p>
            {inviterLabel && (
              <div className="mt-3 flex justify-between border-t pt-3">
                <span className="text-muted-foreground">Convidado por</span>
                <span className="font-medium">{inviterLabel}</span>
              </div>
            )}
            <div className="mt-2 flex justify-between">
              <span className="text-muted-foreground">Para o email</span>
              <span className="font-medium">{preview.email}</span>
            </div>
          </div>

          {isTerminal && (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm dark:border-amber-900 dark:bg-amber-950">
              {preview.status === "accepted" && (
                <p>Este convite já foi aceito.</p>
              )}
              {preview.status === "revoked" && (
                <p>Este convite foi cancelado pelo responsável.</p>
              )}
              {preview.status === "expired" && (
                <p>
                  Este convite expirou. Peça um novo ao responsável do
                  workspace.
                </p>
              )}
            </div>
          )}

          {error && (
            <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
              {error}
            </div>
          )}

          {!isTerminal && (
            <>
              {isLoggedIn ? (
                <Button
                  className="w-full"
                  onClick={handleAccept}
                  disabled={accepting}
                >
                  {accepting ? "Processando..." : "Aceitar convite"}
                </Button>
              ) : (
                <div className="space-y-2">
                  <p className="text-xs text-muted-foreground">
                    Para aceitar, entre com a conta do email{" "}
                    <strong>{preview.email}</strong>. Se ainda não tem conta,
                    crie uma usando esse email.
                  </p>
                  <Link
                    href={`/login?next=${encodeURIComponent(returnUrl)}`}
                    className="block"
                  >
                    <Button className="w-full">Entrar</Button>
                  </Link>
                  <Link
                    href={`/register?next=${encodeURIComponent(returnUrl)}`}
                    className="block"
                  >
                    <Button variant="outline" className="w-full">
                      Criar conta
                    </Button>
                  </Link>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

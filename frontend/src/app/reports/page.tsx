"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  listReports,
  getMe,
  clearToken,
  type ReportResponse,
  type UserResponse,
} from "@/lib/api";

export default function ReportsPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserResponse | null>(null);
  const [reports, setReports] = useState<ReportResponse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [me, data] = await Promise.all([getMe(), listReports()]);
        setUser(me);
        setReports(data.reports);
      } catch {
        clearToken();
        router.replace("/login");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [router]);

  function handleLogout() {
    clearToken();
    router.replace("/login");
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <h1 className="text-xl font-bold text-gray-900">Fin</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-500">{user?.full_name}</span>
            <button
              onClick={handleLogout}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
            >
              Sair
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        <h2 className="mb-6 text-2xl font-semibold text-gray-900">
          Meus Relatórios
        </h2>

        {reports.length === 0 ? (
          <div className="rounded-xl border border-dashed border-gray-300 p-12 text-center">
            <p className="text-gray-500">Nenhum relatório disponível.</p>
            <p className="mt-2 text-sm text-gray-400">
              Execute o pipeline para gerar seu primeiro relatório.
            </p>
          </div>
        ) : (
          <div className="grid gap-4">
            {reports.map((report) => (
              <Link
                key={report.id}
                href={`/reports/${report.id}`}
                className="group flex items-center justify-between rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition hover:border-blue-300 hover:shadow-md"
              >
                <div>
                  <h3 className="font-medium text-gray-900 group-hover:text-blue-600">
                    {report.title}
                  </h3>
                  <p className="mt-1 text-sm text-gray-500">
                    {report.period && `Período: ${report.period}`}
                    {report.size_bytes &&
                      ` · ${(report.size_bytes / 1024).toFixed(0)}KB`}
                  </p>
                </div>
                <div className="text-sm text-gray-400">
                  {new Date(report.created_at).toLocaleDateString("pt-BR")}
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

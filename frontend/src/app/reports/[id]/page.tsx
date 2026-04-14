"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { getReportHtmlUrl, clearToken } from "@/lib/api";

export default function ReportViewPage() {
  const router = useRouter();
  const params = useParams();
  const reportId = params.id as string;
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("fin_token");
    if (!token) {
      router.replace("/login");
      return;
    }

    const url = getReportHtmlUrl(reportId);
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.text();
      })
      .then((html) => {
        if (iframeRef.current) {
          const doc = iframeRef.current.contentDocument;
          if (doc) {
            doc.open();
            doc.write(html);
            doc.close();
          }
        }
        setLoading(false);
      })
      .catch((err) => {
        if (err.message.includes("401") || err.message.includes("403")) {
          clearToken();
          router.replace("/login");
        } else {
          setError("Erro ao carregar relatório");
          setLoading(false);
        }
      });
  }, [reportId, router]);

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-6 py-3">
          <Link
            href="/reports"
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
          >
            ← Voltar
          </Link>
          <h1 className="text-lg font-semibold text-gray-900">
            Visualizar Relatório
          </h1>
        </div>
      </header>

      {loading && (
        <div className="flex flex-1 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
        </div>
      )}

      {error && (
        <div className="flex flex-1 items-center justify-center">
          <div className="rounded-lg bg-red-50 p-6 text-red-700">{error}</div>
        </div>
      )}

      <iframe
        ref={iframeRef}
        className={`flex-1 border-0 ${loading ? "hidden" : ""}`}
        title="Relatório Financeiro"
        sandbox="allow-scripts allow-same-origin"
      />
    </div>
  );
}

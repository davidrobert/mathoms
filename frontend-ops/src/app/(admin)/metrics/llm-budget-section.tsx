"use client";

// Editor de budget LLM por workspace (A30.l1 · ADR-173). Janela = mês-calendário
// UTC (mesma do hard-stop) — NÃO usar a janela rolling do /llm-cost-by-workspace.

import { useCallback, useEffect, useState } from "react";
import { Modal } from "@/components/Modal";
import { Badge, Button, TextInput } from "@/components/ui";
import { api, AdminApiError } from "@/lib/api";
import type { LLMBudgetMonthResponse, WorkspaceLLMBudgetMonth } from "@/lib/types";

const STATUS_LABEL: Record<WorkspaceLLMBudgetMonth["status"], string> = {
  ok: "OK",
  warn: "Warn",
  hard_stop: "Hard-stop",
  uncapped: "Sem cap",
};

const STATUS_TONE: Record<WorkspaceLLMBudgetMonth["status"], "success" | "warning" | "danger" | "neutral"> = {
  ok: "success",
  warn: "warning",
  hard_stop: "danger",
  uncapped: "neutral",
};

function usd(value: string | null): string {
  return value == null ? "—" : `US$ ${value}`;
}

function resultingStatus(
  spent: number,
  cap: number,
  warnRatio: number,
  hardStopRatio: number,
): WorkspaceLLMBudgetMonth["status"] {
  if (cap <= 0) return "uncapped";
  if (spent >= cap * hardStopRatio) return "hard_stop";
  if (spent >= cap * warnRatio) return "warn";
  return "ok";
}

function useLlmBudget() {
  const [data, setData] = useState<LLMBudgetMonthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (): Promise<void> => {
    setError(null);
    try {
      setData(await api.getLlmBudgetByWorkspace());
    } catch (err) {
      setError(err instanceof AdminApiError ? `${err.status} · ${err.code}` : "Falha ao carregar budget LLM.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return { data, error, load };
}

function SectionIntro({ data }: { data: LLMBudgetMonthResponse | null }) {
  return (
    <>
      <h2 className="font-display text-lg font-semibold text-surface-fg mb-1">
        Custo LLM por workspace {data ? `— ${data.month}` : ""}
      </h2>
      <p className="text-xs text-surface-muted-fg mb-3">
        Gasto do mês-calendário UTC corrente — mesma janela do hard-stop (warn ≥
        {data ? ` ${Math.round(data.warn_ratio * 100)}%` : " 80%"}, hard-stop ≥
        {data ? ` ${Math.round(data.hard_stop_ratio * 100)}%` : " 110%"}).
      </p>
    </>
  );
}

function ErrorBanner({ msg }: { msg: string }) {
  return (
    <div className="mb-3 rounded-md border border-brand-danger/30 bg-brand-danger/10 text-brand-danger text-sm px-3 py-2">
      {msg}
    </div>
  );
}

function BudgetEditor({ data, reload }: { data: LLMBudgetMonthResponse; reload: () => void }) {
  const [editing, setEditing] = useState<WorkspaceLLMBudgetMonth | null>(null);
  return (
    <>
      <BudgetTable items={data.items} onEdit={setEditing} />
      {editing && (
        <EditBudgetModal
          item={editing}
          warnRatio={data.warn_ratio}
          hardStopRatio={data.hard_stop_ratio}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            reload();
          }}
        />
      )}
    </>
  );
}

export function LlmBudgetSection() {
  const { data, error, load } = useLlmBudget();
  return (
    <div className="mt-8">
      <SectionIntro data={data} />
      {error && <ErrorBanner msg={error} />}
      {data && <BudgetEditor data={data} reload={() => void load()} />}
    </div>
  );
}

function BudgetTable({
  items,
  onEdit,
}: {
  items: WorkspaceLLMBudgetMonth[];
  onEdit: (item: WorkspaceLLMBudgetMonth) => void;
}) {
  if (items.length === 0) {
    return <p className="text-sm text-surface-muted-fg">Nenhum workspace.</p>;
  }
  return (
    <div className="overflow-x-auto rounded-card border border-surface-border">
      <table className="w-full text-sm">
        <thead className="bg-surface-muted text-surface-muted-fg text-left">
          <tr>
            <th className="px-3 py-2 font-medium">Workspace</th>
            <th className="px-3 py-2 font-medium">Gasto (mês)</th>
            <th className="px-3 py-2 font-medium">Cap</th>
            <th className="px-3 py-2 font-medium">% do cap</th>
            <th className="px-3 py-2 font-medium">Status</th>
            <th className="px-3 py-2 font-medium">Calls</th>
            <th className="px-3 py-2 font-medium" title="Calls sem custo conhecido">
              Custo ?
            </th>
            <th className="px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.workspace_id} className="border-t border-surface-border">
              <td className="px-3 py-2">
                <div className="text-surface-fg">{item.workspace_name ?? "—"}</div>
                <div className="text-xs text-surface-muted-fg mono-num">{item.workspace_id}</div>
              </td>
              <td className="px-3 py-2 mono-num">{usd(item.spent_month_usd)}</td>
              <td className="px-3 py-2 mono-num">{usd(item.cap_usd)}</td>
              <td className="px-3 py-2 mono-num">
                {item.pct_of_cap == null ? "—" : `${Math.round(item.pct_of_cap * 100)}%`}
              </td>
              <td className="px-3 py-2">
                <Badge tone={STATUS_TONE[item.status]}>{STATUS_LABEL[item.status]}</Badge>
              </td>
              <td className="px-3 py-2 mono-num">{item.call_count}</td>
              <td className="px-3 py-2 mono-num">{item.unknown_cost_calls}</td>
              <td className="px-3 py-2 text-right">
                <Button variant="secondary" onClick={() => onEdit(item)}>
                  Editar cap
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function EditBudgetModal({
  item,
  warnRatio,
  hardStopRatio,
  onClose,
  onSaved,
}: {
  item: WorkspaceLLMBudgetMonth;
  warnRatio: number;
  hardStopRatio: number;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [capInput, setCapInput] = useState(item.cap_usd ?? "");
  const [confirmUncap, setConfirmUncap] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const spent = Number(item.spent_month_usd);
  const capValue = Number(capInput);
  const capValid = capInput.trim() !== "" && Number.isFinite(capValue) && capValue >= 0;
  const preview = capValid ? resultingStatus(spent, capValue, warnRatio, hardStopRatio) : null;

  const save = async (body: { cap_usd: string } | { remove_cap: true }): Promise<void> => {
    setSaving(true);
    setError(null);
    try {
      await api.updateWorkspaceLlmBudget(item.workspace_id, body);
      onSaved();
    } catch (err) {
      setError(err instanceof AdminApiError ? `${err.status} · ${err.code}` : "Falha ao salvar.");
      setSaving(false);
    }
  };

  return (
    <Modal
      open
      title={`Budget LLM — ${item.workspace_name ?? item.workspace_id}`}
      onClose={onClose}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={saving}>
            Cancelar
          </Button>
          <Button
            variant="danger"
            onClick={() => setConfirmUncap(true)}
            disabled={saving || item.cap_usd == null}
          >
            Remover cap
          </Button>
          <Button
            onClick={() => void save({ cap_usd: capInput.trim() })}
            disabled={saving || !capValid}
          >
            Salvar cap
          </Button>
        </>
      }
    >
      <p>
        Gasto do mês corrente: <strong className="mono-num">{usd(item.spent_month_usd)}</strong> ·
        cap atual: <strong className="mono-num">{usd(item.cap_usd)}</strong>
      </p>
      <label className="block">
        <span className="text-xs text-surface-muted-fg">Novo cap mensal (USD)</span>
        <TextInput
          type="number"
          min="0"
          step="0.01"
          value={capInput}
          onChange={(e) => setCapInput(e.target.value)}
          className="mt-1 w-full"
        />
      </label>
      {preview && (
        <p>
          Status resultante:{" "}
          <Badge tone={STATUS_TONE[preview]}>{STATUS_LABEL[preview]}</Badge>{" "}
          {preview === "hard_stop" && (
            <span className="text-brand-danger">— o pipeline continua bloqueado com esse cap.</span>
          )}
          {preview === "warn" && (
            <span className="text-surface-muted-fg">— acima do warn; folga real exige cap maior.</span>
          )}
        </p>
      )}
      {error && <p className="text-brand-danger">{error}</p>}
      {confirmUncap && (
        <div className="rounded-md border border-brand-danger/30 bg-brand-danger/10 px-3 py-2">
          <p className="text-brand-danger">
            Remover o teto deixa o workspace <strong>sem freio de custo LLM</strong>. Confirmar?
          </p>
          <div className="mt-2 flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setConfirmUncap(false)} disabled={saving}>
              Manter cap
            </Button>
            <Button variant="danger" onClick={() => void save({ remove_cap: true })} disabled={saving}>
              Remover mesmo assim
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}

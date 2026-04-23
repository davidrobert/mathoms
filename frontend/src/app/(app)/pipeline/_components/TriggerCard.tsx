"use client";

import Link from "next/link";
import { stageName } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/Spinner";

function TriggeringLabel({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-2">
      <Spinner size="sm" className="text-primary-foreground" />
      {label}
    </span>
  );
}

function NewDocsButtons({
  newCount,
  readyCount,
  triggering,
  onTrigger,
}: {
  newCount: number;
  readyCount: number;
  triggering: boolean;
  onTrigger: (fromStage?: string, incremental?: boolean) => void;
}) {
  return (
    <>
      <Button onClick={() => onTrigger(undefined, true)} disabled={triggering}>
        {triggering ? <TriggeringLabel label="Iniciando..." /> : `Processar ${newCount} novo(s)`}
      </Button>
      <Button variant="outline" onClick={() => onTrigger()} disabled={triggering}>
        Processar todos ({readyCount})
      </Button>
    </>
  );
}

function EmptyReadyState({ onReload, title }: { onReload?: () => void; title: string }) {
  return (
    <Card className="mb-8">
      <CardContent>
        <h2 className="mb-2 font-medium">Gerar Relatório</h2>
        <div className="text-sm text-muted-foreground">
          {title === "loadError" ? (
            <>
              <p>Não foi possível carregar o status dos documentos e da fila.</p>
              <Button type="button" variant="outline" size="sm" className="mt-3" onClick={onReload}>
                Tentar novamente
              </Button>
            </>
          ) : (
            <>
              <p>Nenhum documento pronto para processar.</p>
              <Link href="/documents" className="mt-2 inline-block text-primary hover:underline">
                Enviar documentos →
              </Link>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function MissingIfGoalState() {
  return (
    <Card className="mb-8">
      <CardContent>
        <h2 className="mb-2 font-medium">Gerar Relatório</h2>
        <p className="text-sm text-muted-foreground">
          Antes de processar documentos, defina sua meta de Independência Financeira — ela é
          usada no cálculo de progresso e cenários do relatório.
        </p>
        <Link
          href="/plano/meta-if"
          className="mt-3 inline-block text-primary hover:underline"
        >
          Definir Meta IF →
        </Link>
      </CardContent>
    </Card>
  );
}

export function TriggerCard({
  readyCount,
  newCount,
  triggering,
  listDataOk,
  hasIfGoal,
  onReload,
  onTrigger,
}: {
  readyCount: number;
  newCount: number;
  triggering: boolean;
  listDataOk: boolean;
  /** `null` enquanto carrega, `false` bloqueia o trigger, `true` libera. */
  hasIfGoal: boolean | null;
  onReload: () => void;
  onTrigger: (fromStage?: string, incremental?: boolean) => void;
}) {
  if (!listDataOk) return <EmptyReadyState title="loadError" onReload={onReload} />;
  if (readyCount === 0) return <EmptyReadyState title="noDocs" />;
  if (hasIfGoal === false) return <MissingIfGoalState />;

  const blockedByIfGoal = hasIfGoal !== true;
  const hasNew = newCount > 0 && newCount < readyCount;
  return (
    <Card className="mb-8">
      <CardContent>
        <h2 className="mb-2 font-medium">Gerar Relatório</h2>
        <p className="mb-4 text-sm text-muted-foreground">
          <span className="font-medium text-foreground">{readyCount}</span>{" "}
          documento(s) pronto(s) para processamento
          {hasNew && (
            <> · <span className="font-medium text-primary">{newCount}</span> novo(s) desde última execução</>
          )}
          .
        </p>
        <div className="flex flex-wrap gap-3">
          {hasNew ? (
            <NewDocsButtons
              newCount={newCount}
              readyCount={readyCount}
              triggering={triggering || blockedByIfGoal}
              onTrigger={onTrigger}
            />
          ) : (
            <Button onClick={() => onTrigger()} disabled={triggering || blockedByIfGoal}>
              {triggering ? <TriggeringLabel label="Iniciando..." /> : "Processar documentos"}
            </Button>
          )}
          <Button
            variant="ghost"
            onClick={() => onTrigger("E3")}
            disabled={triggering || blockedByIfGoal}
          >
            Reprocessar a partir de {stageName("E3")}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

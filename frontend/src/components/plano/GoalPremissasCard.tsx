"use client";

import { ClipboardList } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type {
  AlocacaoGoalResponse,
  AporteGoalResponse,
  DolarGoalResponse,
  IFGoalResponse,
} from "@/lib/api";
import {
  buildAlocacaoPremissasRows,
  buildAportePremissasRows,
  buildDolarPremissasRows,
  buildIFPremissasRows,
  formatGoalVigenciaDate,
  type PremissaRow,
} from "@/lib/goalPremissas";
import type {
  AlocacaoGoalInputs,
  AlocacaoGoalDerived,
  AporteGoalInputs,
  AporteGoalDerived,
  DolarGoalInputs,
  DolarGoalDerived,
  IFGoalInputs,
  IFGoalDerived,
} from "@/lib/api";
import { cn } from "@/lib/cn";

export type GoalPremissasCardProps = {
  className?: string;
  /**
   * Em modo `draft`, se já existe meta no workspace: data ISO (YYYY-MM-DD)
   * da versão vigente — mostra contexto sem confundir com o rascunho atual.
   */
  existingEffectiveFrom?: string | null;
} & (
  | {
      kind: "if";
      mode: "draft";
      inputs: IFGoalInputs;
      derived: IFGoalDerived | null;
    }
  | {
      kind: "if";
      mode: "saved";
      goal: IFGoalResponse;
    }
  | {
      kind: "aporte";
      mode: "draft";
      inputs: AporteGoalInputs;
      derived: AporteGoalDerived | null;
    }
  | {
      kind: "aporte";
      mode: "saved";
      goal: AporteGoalResponse;
    }
  | {
      kind: "dolar";
      mode: "draft";
      inputs: DolarGoalInputs;
      derived: DolarGoalDerived | null;
      cambioUtilizado?: number | null;
    }
  | {
      kind: "dolar";
      mode: "saved";
      goal: DolarGoalResponse;
    }
  | {
      kind: "alocacao";
      mode: "draft";
      inputs: AlocacaoGoalInputs;
      derived: AlocacaoGoalDerived | null;
    }
  | {
      kind: "alocacao";
      mode: "saved";
      goal: AlocacaoGoalResponse;
    }
);

function rowsForProps(props: GoalPremissasCardProps): PremissaRow[] {
  if (props.kind === "if") {
    if (props.mode === "draft") {
      return buildIFPremissasRows(props.inputs, props.derived);
    }
    return buildIFPremissasRows(props.goal.inputs, props.goal.derived);
  }
  if (props.kind === "aporte") {
    if (props.mode === "draft") {
      return buildAportePremissasRows(props.inputs, props.derived);
    }
    return buildAportePremissasRows(props.goal.inputs, props.goal.derived);
  }
  if (props.kind === "dolar") {
    if (props.mode === "draft") {
      return buildDolarPremissasRows(
        props.inputs,
        props.derived,
        props.cambioUtilizado
      );
    }
    return buildDolarPremissasRows(
      props.goal.inputs,
      props.goal.derived,
      null
    );
  }
  if (props.mode === "draft") {
    return buildAlocacaoPremissasRows(props.inputs, props.derived);
  }
  return buildAlocacaoPremissasRows(props.goal.inputs, props.goal.derived);
}

function metaAndVigencia(props: GoalPremissasCardProps): {
  metaVersion: number;
  vigenciaLine: string;
} {
  if (props.mode === "saved") {
    const g = props.goal;
    const iso =
      typeof g.effective_from === "string"
        ? g.effective_from
        : String(g.effective_from);
    return {
      metaVersion: g.meta_version ?? 1,
      vigenciaLine: `Vigente desde ${formatGoalVigenciaDate(iso)}.`,
    };
  }
  const ex = props.existingEffectiveFrom;
  if (ex) {
    return {
      metaVersion: 1,
      vigenciaLine: `Rascunho — valores abaixo seguem o formulário. Versão salva vigente desde ${formatGoalVigenciaDate(ex)}.`,
    };
  }
  return {
    metaVersion: 1,
    vigenciaLine:
      "Ao salvar, esta versão passa a valer a partir da data de hoje.",
  };
}

function PremissasHeader({
  metaVersion,
  vigenciaLine,
}: {
  metaVersion: number;
  vigenciaLine: string;
}) {
  return (
    <CardHeader className="space-y-1 pb-2">
      <CardTitle className="flex items-center gap-2 text-base font-semibold">
        <ClipboardList className="h-4 w-4 text-muted-foreground" />
        Premissas desta meta
      </CardTitle>
      <p className="text-xs text-muted-foreground">{vigenciaLine}</p>
      <p className="text-xs text-muted-foreground">Versão do schema: {metaVersion}</p>
    </CardHeader>
  );
}

function PremissasRows({ rows }: { rows: PremissaRow[] }) {
  return (
    <CardContent className="pt-0">
      <dl className="space-y-2">
        {rows.map((row) => (
          <div
            key={row.label}
            className="flex flex-col gap-0.5 sm:flex-row sm:justify-between sm:gap-4"
          >
            <dt className="text-muted-foreground shrink-0">{row.label}</dt>
            <dd className="font-mono text-xs tabular-nums text-right sm:max-w-[70%] sm:text-sm">
              {row.value}
            </dd>
          </div>
        ))}
      </dl>
    </CardContent>
  );
}

export function GoalPremissasCard(props: GoalPremissasCardProps) {
  const { className, existingEffectiveFrom, ...rest } = props;
  const rows = rowsForProps(rest as GoalPremissasCardProps);
  const { metaVersion, vigenciaLine } = metaAndVigencia({
    ...rest,
    existingEffectiveFrom,
  } as GoalPremissasCardProps);

  return (
    <Card className={cn("border-dashed bg-muted/30 text-sm shadow-none", className)}>
      <PremissasHeader metaVersion={metaVersion} vigenciaLine={vigenciaLine} />
      <PremissasRows rows={rows} />
    </Card>
  );
}

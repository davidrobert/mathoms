import { Info } from "lucide-react";

import { Alert } from "../ui/Alert";
import type { RecalibracaoMcData } from "@/lib/api";

const MESES = [
  "janeiro",
  "fevereiro",
  "março",
  "abril",
  "maio",
  "junho",
  "julho",
  "agosto",
  "setembro",
  "outubro",
  "novembro",
  "dezembro",
];

/** "202512" → "dezembro de 2025". */
function competenciaPorExtenso(yyyymm: string | null): string | null {
  if (!yyyymm || yyyymm.length !== 6) return null;
  const mes = Number(yyyymm.slice(4, 6));
  if (!Number.isInteger(mes) || mes < 1 || mes > 12) return null;
  return `${MESES[mes - 1]} de ${yyyymm.slice(0, 4)}`;
}

/** Faceta comparável — par explícito, sem seta (lê mal em leitor de tela e PDF). */
function FacetaAnoCone({
  anoAnterior,
  anoNovo,
  competenciaMudou,
}: {
  anoAnterior: number;
  anoNovo: number;
  competenciaMudou: boolean;
}) {
  return (
    <p className="mt-3">
      <strong>
        Ano da meta no cenário central: de {anoAnterior} para {anoNovo}.
      </strong>{" "}
      Esse ano passou a sair de todos os cenários simulados, inclusive os que não
      alcançam a meta dentro do período projetado — antes, saía só dos que
      alcançavam.
      {competenciaMudou && (
        <>
          {" "}
          A diferença entre os dois anos mistura essa revisão e a evolução dos
          seus próprios números no período.
        </>
      )}
    </p>
  );
}

/** Faceta incomparável — sem par, e a probabilidade anterior nunca é impressa. */
function FacetaProbabilidadeAlvo({
  prazoAnos,
  anoAlvo,
}: {
  prazoAnos: number | null;
  anoAlvo: number | null;
}) {
  return (
    <p className="mt-3">
      <strong>A probabilidade agora mede o prazo que você declarou.</strong>{" "}
      Antes, ela media a chance de alcançar a data que o próprio modelo havia
      projetado. Agora mede a chance de você alcançar a meta dentro do prazo que
      declarou
      {prazoAnos != null && (
        <>
          {" "}— {prazoAnos} anos{anoAlvo != null && <>, até {anoAlvo}</>}
        </>
      )}
      . A pergunta mudou, então o número novo não se compara com o anterior. Ele
      pode ser maior ou menor, conforme a folga entre o seu prazo e o ritmo dos
      seus aportes.
    </p>
  );
}

/** Nota one-shot de recalibração do bloco de IF (ADR-360 §Nota one-shot · A40.l25). */
// Posição FIXA na S7, acima do primeiro card numérico e nunca ancorada a um
// card: as duas facetas moram em cards diferentes (o ano na prosa da projeção,
// a probabilidade na legenda do cone), e ressalva que SEGUE o número é lida
// depois de a inferência errada já ter se formado — em PDF, com quebra de
// página no meio, pode nem ser lida.
//
// Tom `info`, nunca `warning`: âmbar é o tratamento do PremissasFallbackAlert
// logo abaixo, que sinaliza DEGRADAÇÃO de dado. Equiparar "revisamos o modelo"
// a "suas premissas estão em fallback" diria que o relatório está pior do que
// está. O fecho "não pede nenhuma ação sua" é o que separa informativo de
// alarme. Nunca "sua carteira mudou" — nem a negação disso, que em relatório
// mensal seria falsa.
export function RecalibracaoMcNote({ nota }: { nota: RecalibracaoMcData | null }) {
  if (!nota || nota.facetas.length === 0) return null;

  const desde = competenciaPorExtenso(nota.periodo_anterior);

  return (
    <Alert
      severity="info"
      icon={<Info className="h-4 w-4" />}
      className="md:col-span-2 break-inside-avoid"
    >
      <p className="font-semibold">Revisamos o modelo desta projeção</p>
      <p className="mt-1">
        {desde ? <>Desde o seu relatório de {desde}, revisamos</> : <>Revisamos</>}{" "}
        como calculamos a projeção de independência financeira. Parte do que
        mudou nesta seção vem dessa revisão — não do seu patrimônio nem dos seus
        aportes.
      </p>

      {nota.facetas.map((f) =>
        f.faceta === "ano_cone" ? (
          <FacetaAnoCone
            key={f.faceta}
            anoAnterior={f.ano_anterior}
            anoNovo={f.ano_novo}
            competenciaMudou={nota.competencia_mudou}
          />
        ) : (
          <FacetaProbabilidadeAlvo
            key={f.faceta}
            prazoAnos={f.prazo_declarado_anos}
            anoAlvo={f.ano_alvo_declarado}
          />
        ),
      )}

      <p className="mt-3">
        A revisão em si não pede nenhuma ação sua. Este aviso aparece só neste
        relatório.
      </p>
    </Alert>
  );
}

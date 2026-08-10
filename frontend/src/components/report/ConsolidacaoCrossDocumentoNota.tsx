/** A40.l2 — declara à família que lançamentos repetidos entre documentos foram
 * contados uma vez só.
 *
 * Salvaguarda nº 1 da lane: sem esta linha o agregado fica irreconciliável
 * contra o extrato do banco, e para o planejador B2B2C — que responde
 * profissionalmente pelo número — ledger irreconciliável é veto de adoção.
 *
 * **Duas frases, uma base por frase.** A primeira é o fato completo (corpus),
 * que é a unidade contra a qual a família reconcilia: ela envia *documentos*,
 * não janelas. A segunda declara quanto disso caiu na janela de mensalização,
 * que é a base das médias exibidas ao lado. É o mesmo padrão de
 * `FluxoMensalChart.buildContext` (`describeRenderizada` + `describeAgregado`),
 * e satisfaz o invariante da [[ADR-306]] D1 mais fortemente que base única:
 * cada contagem sai do mesmo objeto que fornece seu rótulo.
 *
 * Vocabulário deliberado (ver COPY_GUIDELINES §2.2): **não** "consolidados" —
 * PRODUCT.md §1 já usa "consolida extratos, faturas" no sentido de *juntar*, e
 * o leitor entenderia o oposto do que houve. **Não** "removemos/excluímos" — a
 * linha não sumiu do extrato dela; deixou de contar duas vezes.
 */
import { Layers } from "lucide-react";

import { Alert } from "@/components/report/ui/Alert";
import {
  resolveConsolidacaoCrossDoc,
  type ConsolidacaoComJanela,
} from "@/components/report/utils/fluxoJanela";
import { describeJanelaEm } from "@/components/report/utils/janelaLabel";

/** Frase A — o fato, base corpus. Só a cláusula-fato vai em negrito; o fecho
 * fica em peso normal, como em `AcumuladoresBanner`. `M === 1` vira "todos no
 * mesmo mês": o "em M meses" da salvaguarda está preservado, só que "em 1 mês"
 * é agramatical em leitura corrida. */
function fraseDoCorpus({ count, meses }: ConsolidacaoComJanela): {
  fato: string;
  fecho: string;
} {
  if (count === 1) {
    return {
      fato: "1 lançamento aparecia em mais de um documento do mesmo banco.",
      fecho: "Contamos uma vez só.",
    };
  }
  const onde =
    meses === 1 ? ", todos no mesmo mês" : `, em ${meses} meses do período analisado`;
  return {
    fato: `${count} lançamentos apareciam em mais de um documento do mesmo banco${onde}.`,
    fecho: "Contamos cada um uma vez só.",
  };
}

/** Frase B — a janela das médias. `count === 0` é o caso mais valioso: corpus
 * com consolidação e janela sem ela significa que os headlines mensais **não**
 * mudaram por isso, e sem dizê-lo a família atribui à consolidação uma queda
 * que ela não causou. */
function fraseDaJanela(
  janela: ConsolidacaoComJanela,
  totalCorpus: number,
): string {
  const onde = describeJanelaEm(janela.rotulo);
  const base = `que é a base das médias mensais desta seção.`;
  if (janela.count === 0) {
    return `Nenhum deles está ${onde} — as médias mensais desta seção não mudaram por causa disso.`;
  }
  if (janela.count === totalCorpus) {
    return totalCorpus === 1
      ? `Ele está ${onde}, ${base}`
      : `Todos estão ${onde}, ${base}`;
  }
  const verbo = janela.count === 1 ? "está" : "estão";
  return `Destes, ${janela.count} ${verbo} ${onde}, ${base}`;
}

export function ConsolidacaoCrossDocumentoNota({
  fluxo,
  className,
}: {
  readonly fluxo: unknown;
  readonly className?: string;
}) {
  const bases = resolveConsolidacaoCrossDoc(fluxo);
  // Ausência é ausência: nenhum nó. Um Alert vazio ou "0 lançamentos"
  // afirmaria um fato que ninguém mediu naquele run.
  if (!bases) return null;

  const { fato, fecho } = fraseDoCorpus(bases.corpus);

  return (
    <Alert severity="info" icon={<Layers size={16} aria-hidden />} className={className}>
      <span data-testid="s2-consolidacao-corpus">
        <strong>{fato}</strong> {fecho}
      </span>
      {bases.janela && (
        <>
          {" "}
          <span data-testid="s2-consolidacao-janela">
            {fraseDaJanela(bases.janela, bases.corpus.count)}
          </span>
        </>
      )}
    </Alert>
  );
}

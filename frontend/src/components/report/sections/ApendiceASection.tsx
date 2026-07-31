import { ReportSection } from "../ReportSection";
import { ReportCard } from "../ReportCard";
import { SectionSummary } from "../SectionSummary";
import type { ReportAnalysisData } from "@/lib/api";

const GLOSSARIO: Array<{ termo: string; definicao: string }> = [
  { termo: "IF", definicao: "Independência Financeira — patrimônio suficiente para gerar renda passiva que cubra todas as despesas da família sem depender de trabalho ativo." },
  { termo: "TRS", definicao: "Taxa de Retirada Segura — percentual anual que pode ser sacado do patrimônio investido sem exauri-lo ao longo do tempo. Referência: 4–5% a.a. para carteira diversificada." },
  { termo: "CDI", definicao: "Certificado de Depósito Interbancário — taxa de referência para investimentos de renda fixa no Brasil. Acompanha de perto a taxa Selic." },
  { termo: "Selic", definicao: "Taxa básica de juros da economia brasileira, definida pelo COPOM (Comitê de Política Monetária do Banco Central)." },
  { termo: "IPCA", definicao: "Índice Nacional de Preços ao Consumidor Amplo — indicador oficial de inflação no Brasil, medido pelo IBGE." },
  { termo: "IPCA+", definicao: "Título público (Tesouro Direto) ou indexador que paga inflação IPCA mais um juro real prefixado." },
  { termo: "IGPM", definicao: "Índice Geral de Preços – Mercado. Índice de inflação medido pela FGV, frequentemente usado em contratos de aluguel." },
  { termo: "DAS", definicao: "Documento de Arrecadação do Simples Nacional — guia mensal de impostos para empresas optantes pelo Simples Nacional." },
  { termo: "Simples Nacional", definicao: "Regime tributário simplificado para micro e pequenas empresas com faturamento até R$4,8M/ano. Unifica diversos impostos em uma guia (DAS)." },
  { termo: "Lucro Presumido", definicao: "Regime tributário alternativo ao Simples onde a base de cálculo do IR é um percentual presumido do faturamento (32% para serviços)." },
  { termo: "PGBL", definicao: "Plano Gerador de Benefício Livre — modalidade de previdência privada que permite deduzir até 12% da renda bruta tributável no IRPF." },
  { termo: "VGBL", definicao: "Vida Gerador de Benefício Livre — previdência privada sem dedução fiscal, tributada apenas sobre os rendimentos no resgate." },
  { termo: "CDB", definicao: "Certificado de Depósito Bancário — título de renda fixa emitido por bancos. Pode ser prefixado, pós-fixado (CDI) ou indexado (IPCA+)." },
  { termo: "LCI / LCA", definicao: "Letras de Crédito Imobiliário / Agrícola — títulos de renda fixa isentos de IR para pessoa física." },
  { termo: "FII", definicao: "Fundo de Investimento Imobiliário — fundo negociado em bolsa que investe em imóveis ou ativos imobiliários, distribuindo rendimentos mensais." },
  { termo: "ETF", definicao: "Exchange Traded Fund — fundo de índice negociado em bolsa. Ex: IVVB11 (replica S&P 500 em BRL)." },
  { termo: "IVVB11", definicao: "ETF listado na B3 que replica o índice S&P 500, proporcionando exposição ao mercado americano em reais." },
  { termo: "DY", definicao: "Dividend Yield — rendimento de dividendos/rendimentos de um ativo, expresso como percentual anual sobre o preço." },
  { termo: "P/L", definicao: "Preço/Lucro — múltiplo que relaciona o preço de uma ação ao lucro por ação. Indica quantos anos de lucro o mercado está pagando." },
  { termo: "PM", definicao: "Preço Médio — custo médio de aquisição de um ativo, usado para cálculo de IR sobre ganho de capital." },
  { termo: "Alocação contracíclica", definicao: "Estratégia de investimento que prioriza o indexador de renda fixa fora do ciclo aquecido (ex.: IPCA+ longos quando a Selic está alta), capturando prêmio de marcação a mercado quando o ciclo inverte." },
  { termo: "IRPF", definicao: "Imposto de Renda Pessoa Física — imposto federal sobre a renda de pessoas físicas no Brasil." },
  { termo: "IOF", definicao: "Imposto sobre Operações Financeiras — imposto federal sobre câmbio, crédito, seguros e títulos." },
  { termo: "Carnê-Leão", definicao: "Recolhimento mensal obrigatório de IR sobre rendimentos recebidos de pessoas físicas ou do exterior, via DARF." },
];

const CATEGORIAS_PATRIMONIAIS: Array<{ categoria: string; descricao: string }> = [
  { categoria: "Patrimônio Bruto", descricao: "Soma de todos os ativos: imóveis, veículos, investimentos, criptos, caixa, empresas." },
  { categoria: "Patrimônio Investível", descricao: "Patrimônio Bruto − imóvel de residência − veículos. São os ativos que geram ou podem gerar renda passiva." },
  { categoria: "Renda Fixa", descricao: "CDBs, RDBs, Tesouro Direto, LCIs, LCAs, debêntures, CRI/CRA, poupança." },
  { categoria: "Ações BR", descricao: "Ações domésticas, ETFs BR, participação societária listada." },
  { categoria: "FIIs", descricao: "Fundos imobiliários (tijolo e papel) — geram renda passiva isenta de IR para PF." },
  { categoria: "Fundos", descricao: "FIC, FIM, FIA, fundos multimercado e fundos de ações abertos." },
  { categoria: "Internacional", descricao: "ETFs globais (IVVB11, S&P500), ações em USD, contas em moeda estrangeira (Wise, BofA)." },
  { categoria: "Previdência", descricao: "PGBL e VGBL — veículos de aposentadoria com benefício tributário." },
  { categoria: "Cripto", descricao: "Bitcoin, Ethereum e demais ativos digitais." },
  { categoria: "Caixa", descricao: "Saldos em contas correntes, contas digitais (PicPay, Nubank) e liquidez operacional em BRL." },
  { categoria: "Imóveis (investimento)", descricao: "Imóveis não-residenciais que geram aluguel ou valorização." },
  { categoria: "Reserva de Emergência", descricao: "Parcela líquida (resgate D+0 a D+2) destinada a cobrir 6–12 meses de despesas." },
];

function DefinitionTable({
  title,
  header,
  keyWidth,
  rows,
}: {
  title: string;
  header: string;
  keyWidth: string;
  rows: Array<{ key: string; value: string }>;
}) {
  return (
    <div className="md:col-span-2">
      <ReportCard variant="neutral" title={title}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--surface-border)] text-left text-xs uppercase tracking-wider text-[var(--surface-muted-foreground)]">
                <th scope="col" className="pb-2 font-semibold" style={{ width: keyWidth }}>{header}</th>
                <th scope="col" className="pb-2 font-semibold">Definição</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(({ key, value }) => (
                <tr key={key} className="border-b border-[var(--surface-border)]/40 last:border-0">
                  <td className="py-2 pr-4 font-semibold text-[var(--surface-foreground)]">{key}</td>
                  <td className="py-2 text-[var(--surface-muted-foreground)]">{value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ReportCard>
    </div>
  );
}

/** F9 · Fase D · Fase 10 — Apêndice A: Definições e Siglas.
 *  Glossário de termos financeiros + categorias patrimoniais.
 *  Conteúdo estático — válido para qualquer workspace.
 */
// `data` era opcional só porque um teste montava `<ApendiceASection />`; em
// produção o `MigratedSection` sempre passa. O `{data && …}` que isso obrigava
// é render site CONDICIONAL — a forma que a regra 7 de
// `dev/check_chart_conclusion_parity.py` usa para detectar parágrafo suprimido
// (A40.l4). Prop obrigatória mantém o render site incondicional, que é o que
// produção faz.
export function ApendiceASection({ data }: { data: ReportAnalysisData }) {
  return (
    <ReportSection id="APP_A" title="Apêndice A — Definições e Siglas">
      <SectionSummary data={data} sectionId="APP_A" />
      <DefinitionTable
        title="Glossário de Termos Financeiros"
        header="Sigla / Termo"
        keyWidth="20%"
        rows={GLOSSARIO.map((g) => ({ key: g.termo, value: g.definicao }))}
      />
      <DefinitionTable
        title="Categorias Patrimoniais"
        header="Categoria"
        keyWidth="30%"
        rows={CATEGORIAS_PATRIMONIAIS.map((c) => ({ key: c.categoria, value: c.descricao }))}
      />
    </ReportSection>
  );
}

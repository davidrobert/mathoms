# Track — A8 TRS real (renda passiva observada + Taxa de Retirada Sustentável efetiva)

> **Status:** ☐ aberta · independente · pode rodar paralelo a Onda 8/9
>
> **Contexto:** prompt self-contained para nova sessão Claude Code.
> Branch: `agent/a8-trs-real/<ts>`, partindo de `origin/main`.
>
> **Esforço estimado:** 5-6 dias (1 service novo, fix em IRPFAnalyzer
> bucket capital, wiring no E5 adapter, mitigações UX
> obrigatórias no S7, ADR canônica).
> **Prioridade:** P1 — destrava regra `rule_trs_desalinhada` dormente,
> dá honestidade metodológica ao S7, é demo-able em 1 sprint.
>
> **Validação metodológica:** financial-planner subagent revisou e
> confirmou framing geral, com 5 ajustes obrigatórios já incorporados
> aqui. Veredictos por decisão em §"Decisões metodológicas".
>
> **Validação UX/copy:** product-designer subagent revisou copy e
> hierarquia visual. 10 ajustes obrigatórios já incorporados em §Item
> 6 (ordem dos KPIs, copy de empty states, banners, tooltip, padrão de
> acessibilidade WCAG 2.1.1 + 1.4.13). Tooltip migrou de hover-on-value
> para `Info` icon next to label + caption permanente em acumulação.

---

## Briefing

A Independência Financeira do Perini só fecha quando você confronta
**TRS meta** (5%/4% — decisão do plano) com **TRS efetiva** (yield real
do patrimônio investido — observação dos fatos). Hoje o produto mostra
só projeção; não mostra "estado atual da carteira como geradora de
renda".

Três sintomas concretos no código:

1. **TRS efetiva nunca é calculada.**
   [`ratios_calculator.py:49-50`](../../pipeline/domain/services/ratios_calculator.py#L49)
   tem `rentabilidade_pct: str = "N/D"` e
   `aliquota_efetiva_ir_pct: str = "N/D"` como placeholders desde A5a.
   Comentário diz "preenchidas em A5c+". A5c passou.

2. **Renda passiva exibida é teórica, não observada.**
   [`if_projector.py:269`](../../pipeline/domain/services/if_projector.py#L269)
   computa `renda_passiva_estimada_4pct = investivel * 4% / 12` —
   estimativa Trinity sobre o investível total, sem olhar dividendos
   reais.

3. **Regra `rule_trs_desalinhada` está dormente.**
   [`suggestion_rules.py:86-112`](../../pipeline/domain/services/suggestion_rules.py#L86)
   espera `goals.taxa_retirada_efetiva_pct` populado. Ninguém popula.
   Logo a regra nunca dispara — desperdício de detector pronto.

**A boa notícia:** os dados já existem em parte.
[`irpf_analyzer.py:215-225`](../../pipeline/domain/services/irpf_analyzer.py#L215)
já decompõe rendimentos isentos (cod 09 lucros/dividendos), exclusiva
(cod 10 JCP, 12 aplicações, 06 ganho capital) e exterior. E
[`patrimonio_calculator.py`](../../pipeline/domain/services/patrimonio_calculator.py)
já segrega `imoveis_investimento`, `investimentos_titular`,
`investimentos_conjuge`, `residencia`. Falta:
- agregar com aluguéis (hoje em bucket trabalho — fix necessário)
- filtrar patrimônio investido (carteira de renda)
- dividir, expor com mitigações de UX que não induzam erro de iniciante

Esta lane fecha esse último mile.

## Riscos metodológicos a respeitar

O financial-planner foi explícito que TRS efetiva exibida sem contexto
**induz o erro #1 do iniciante** (Perini): vender growth para
perseguir DY, sacrificando retorno total. **Mitigações abaixo não são
opcionais.**

1. **Renda passiva absoluta em R$/mês visível ao lado do %** — "R$
   3.200/mês" ancora decisão familiar melhor que "2,3%" (Cerbasi).
2. **Tooltip + caption permanente em acumulação** — tooltip via `Info`
   icon ao lado do label TRS efetiva (WCAG-compliant); quando
   `progresso < 50` há **caption inline permanente** abaixo dos KPIs
   substituindo o tooltip como veículo principal (a maioria do dogfood
   estará em acumulação).
3. **Tom condicionado à fase de vida**, não a threshold fixo. Em
   acumulação (`progresso < 50%`), yield baixo é esperado e não vira
   warning.
4. **Detecção de ativos acumuladores** (IVVB11, BOVA11, IVV, fundos
   acumulação) > 40% do gerador → banner explicativo de que TRS
   efetiva subestima nesse cenário **+ tom warning também no card "Em
   acumuladores"** (fecha o loop visual entre KPI e banner).
5. **Aluguéis no bucket capital** (não trabalho) — coerência: se
   imóvel investimento está no denominador, aluguel está no numerador.

---

## Atualização da metodologia

`config/methodology.md` (§Métricas core) deve registrar:

> **TRS efetiva** = renda passiva anual observada / patrimônio
> investido (carteira de renda) × 100. Renda passiva agrega dividendos
> isentos (cod RFB 09), JCP exclusiva (10), aplicações exclusiva (12),
> ganho de capital exclusiva (06), rendimentos exterior e aluguéis
> (rendimentos PF/PJ classificados como aluguel) — fonte: IRPF
> analyzer (último ano-base disponível). **Aluguéis foram realocados
> de trabalho para capital nesta sprint** para coerência metodológica
> (Perini classifica aluguel como capital imobiliário) — ver ADR-NNN
> §Re-classificação.
>
> **Carteira de renda** (chave interna `patrimonio_gerador_brl`)
> exclui residência principal, veículos, derivativos e parcela de
> caixa correspondente à reserva de emergência. Inclui (mesmo com
> yield observado zero): cripto, ações growth e PGBL/VGBL em
> acumulação — yield 0% explícito é o sinal pedagógico, não erro.
>
> Confronto com TRS meta (5% Perini realista / 4% Trinity pessimista —
> decisão D15) sinaliza adequação da carteira como geradora de renda
> **na fase atual**: warning visual condicionado a `progresso ≥ 50%`
> (em acumulação, yield baixo é esperado).

ADR registrável: **ADR-NNN — Carteira de renda e taxa de retirada
efetiva**. Nome canônico usa "Carteira de renda" (terminologia UI),
corpo da ADR explicita correspondência com label interno "patrimônio
gerador". Estimativa: 80-120 linhas (ADR média; segue
`dev/validate_adr_format.py`). Cobre:
- Definição de carteira de renda + carteira de capital
- Buckets IRPF que compõem renda passiva
- Re-classificação aluguel (trabalho → capital) com paridade
- Por que cripto/growth/PGBL entram com yield 0%
- Por que warning é condicionado à fase
- Por que terminologia UI ≠ chave JSON

---

## Itens (6 entregáveis)

### 1. `PassiveIncomeCalculator` — service novo

**Arquivo:** `pipeline/domain/services/passive_income_calculator.py` (novo, ~200 LOC)

Service puro (R9/ISP). Recebe value object de config, retorna dataclass
frozen. Sem I/O.

```python
@dataclass(frozen=True)
class PassiveIncomeConfig:
    """Parâmetros do cálculo TRS efetiva.

    - ``trs_meta_pct``: 5,0 (D15 — Perini realista).
    - ``trs_trinity_pct``: 4,0 (Trinity clássico — fallback pessimista).
    - ``incluir_imoveis_investimento``: True (yield via aluguéis declarados).
    - ``excluir_residencia``: True (gera fluxo neutro/negativo).
    - ``excluir_veiculos``: True.
    - ``excluir_derivativos``: True (alavancagem ≠ estoque gerador).
    - ``reserva_emergencia_meses``: vem de ReservaConfig (escapa do caixa).
    - ``acumulador_tickers``: tuple de tickers conhecidos como
      acumuladores (BOVA11, IVVB11, IVV, SPY, etc.) — usado para
      heurística de banner explicativo.
    """
    trs_meta_pct: Decimal = Decimal("5.0")
    trs_trinity_pct: Decimal = Decimal("4.0")
    incluir_imoveis_investimento: bool = True
    excluir_residencia: bool = True
    excluir_veiculos: bool = True
    excluir_derivativos: bool = True
    reserva_emergencia_meses: int = 6
    acumulador_tickers: tuple[str, ...] = (
        "BOVA11", "IVVB11", "IVV", "SPY",
        "VOO", "WRLD11",  # ampliar conforme dogfood
    )


@dataclass(frozen=True)
class PassiveIncomeResult:
    """Output do PassiveIncomeCalculator.

    - ``renda_passiva_anual_brl``: soma observada IRPF (último ano-base).
    - ``renda_passiva_mensal_brl``: anual / 12 (UI ancora R$/mês).
    - ``renda_passiva_por_fonte_brl``: dict tipado (dividendos, jcp,
      aplicacoes, ganho_capital, exterior, alugueis).
    - ``patrimonio_gerador_brl``: subset filtrado.
    - ``trs_efetiva_pct``: renda / gerador × 100. Decimal('0') quando
      gerador == 0 (caso de empty workspace).
    - ``ano_referencia_irpf``: int (ex. 2025).
    - ``defasagem_meses``: meses entre ano-base IRPF + 1 e reference_date.
    - ``acumuladores_pct_gerador``: % do gerador em ativos acumuladores
      (heurística por ticker). >40% dispara banner UI.
    - ``status``: literal["ok", "sem_irpf", "gerador_zero"] —
      controla render do S7 (KPIs vs empty state).
    """
    renda_passiva_anual_brl: Decimal
    renda_passiva_mensal_brl: Decimal
    renda_passiva_por_fonte_brl: dict[str, Decimal]
    patrimonio_gerador_brl: Decimal
    trs_efetiva_pct: Decimal
    ano_referencia_irpf: int | None
    defasagem_meses: int | None
    acumuladores_pct_gerador: Decimal
    status: Literal["ok", "sem_irpf", "gerador_zero"]


class PassiveIncomeCalculator:
    def __init__(self, config: PassiveIncomeConfig) -> None: ...

    def calculate(
        self,
        *,
        irpf: IRPFAnalyzer | None,
        patrimonio: dict[str, Any],
        investimentos_atuais: dict[str, Any] | None,  # para detecção acumuladores
        reference_date: date,
        despesa_mensal_media_brl: Decimal,
    ) -> PassiveIncomeResult: ...
```

**Lógica `_renda_passiva_observada`** (a partir de IRPF último ano):
```
dividendos     = soma cod 09 dos isentos
jcp            = soma cod 10 da exclusiva
aplicacoes     = soma cod 12 (isentos + exclusiva)
ganho_capital  = soma cod 06 da exclusiva
exterior       = soma rendimentos_exterior
alugueis       = soma rendimentos_pf/pj filtrado por código RFB de
                 aluguel (cod 03/07) ou por flag tipo_rendimento
total = sum(...)
```

> ⚠️ **Aluguéis hoje vivem em `_bucket_trabalho` no IRPFAnalyzer.** O
> Item 2 abaixo move-os para `_bucket_capital`. O calculator novo
> consome o bucket capital atualizado via API pública do
> IRPFAnalyzer; não duplica lógica de filtro.

**Lógica `_patrimonio_gerador`** (a partir do `patrimonio_full`):
```
gerador =
    investimentos_titular           (sempre)
  + investimentos_conjuge           (sempre)
  + imoveis_investimento            (config flag, default True)
  + max(0, caixa − reserva_alvo)    (excedente acima da reserva)
  − derivativos_brl                 (subset excluído de investimentos)
```
**Inclui (mesmo yield 0%):** cripto sem staking, ações growth sem
dividendo, PGBL/VGBL em acumulação. Excluir mascararia concentração.

**Excluído sempre:** residência, veículos, derivativos, parcela de caixa
= reserva_alvo.

**Lógica `_pct_acumuladores`** (heurística para banner UI):
```
total_em_acumuladores = soma de holdings cujo ticker ∈ config.acumulador_tickers
pct = total_em_acumuladores / patrimonio_gerador × 100
```
Se >40%, UI mostra banner explicativo "ativos acumuladores subestimam
TRS efetiva — sinal correto é alocação alvo (S3)".

**Decimal everywhere.** Coerção via `Money.brl()` no boundary se algum
input vier float.

**Critério de aceite:**
- Service puro testável sem rede/DB.
- Decisões `incluir_imoveis_investimento` e `excluir_derivativos`
  configuráveis (config object).
- Status `"sem_irpf"` quando `irpf is None` ou `last_year is None`.
- Status `"gerador_zero"` quando patrimônio gerador é 0.
- 15+ unit tests em `tests/unit/pipeline/test_passive_income_calculator.py`:
  cada bucket IRPF (incluindo aluguéis), cada exclusão de patrimônio,
  ano sem declaração, workspace vazio, workspace só com residência,
  multi-membro titular+cônjuge, **detecção de acumuladores em 3
  cenários (0%, 25%, 60%)**, derivativos no patrimônio (devem ser
  subtraídos), PGBL em acumulação (deve entrar com yield 0%).

### 2. Fix `_bucket_capital` no IRPFAnalyzer + ADR de re-classificação

**Arquivo:** `pipeline/domain/services/irpf_analyzer.py`

Hoje [linha 204-212](../../pipeline/domain/services/irpf_analyzer.py#L204):
```python
def _bucket_trabalho(d: IRPFFullOutput) -> Decimal:
    pj = _sum(fp.rendimentos_tributaveis_brl for fp in d.rendimentos_pj)
    pf_servico = _sum(fp.valor_brl for fp in d.rendimentos_pf)  # ← inclui aluguel
    ...
```

**Mudança:**
- Separar `rendimentos_pf` em "trabalho" (serviço prestado, autônomo,
  carnê-leão sem aluguel) e "capital" (aluguéis recebidos PF) por
  código RFB ou flag tipo. Aluguel típico tem código 03/07 RFB
  (verificar com schema E1.6 atual).
- `_bucket_capital(d)` ganha `+ alugueis_pf + alugueis_pj`.
- `_bucket_trabalho(d)` perde aluguéis.
- `split_trabalho_vs_capital` agora reflete coerentemente.

**Impacto colateral importante:** S8 IRPF e chart `irpf_renda` em
Renda Anual Familiar usam `split_trabalho_vs_capital`. Os números
**vão mudar para todo workspace com aluguel declarado**. Test de
paridade obrigatório:
- `tests/unit/pipeline/test_irpf_analyzer_bucket_capital.py` — fixture
  com aluguel deve ir para capital, fixture sem aluguel não muda.
- Teste explícito que valida o **delta** entre antes/depois para
  workspace dogfood (informativo, não regression — comentado com
  número esperado).

**ADR § Re-classificação aluguel (parte da ADR principal):**
- Justificativa: Perini classifica aluguel como capital imobiliário;
  AUVP idem. Cerbasi neutro. Manter aluguel em trabalho era artefato
  de implementação inicial, não decisão metodológica.
- Quem é afetado: S8, chart `irpf_renda`, Renda Anual Familiar.
- Migração: nenhuma (recomputação automática do E5 next run).

**Critério de aceite:**
- 4+ unit tests cobrindo: aluguel PF, aluguel PJ, sem aluguel
  (idempotente), aluguel + serviço autônomo no mesmo declarante.
- Delta documentado em commit body ("workspace dogfood: trabalho R$
  X→Y, capital R$ Z→W").
- ADR registra a re-classificação como decisão consciente.

### 3. Wire IRPFAnalyzer + PassiveIncomeCalculator no E5AnalyzerAdapter

**Arquivo:** `pipeline/domain/services/e5_analyzer_adapter.py`

IRPFAnalyzer hoje só vive em `scripts/e5_analyze.py:3065`. Adapter novo
não o instancia. Esta lane wire-a.

**Mudanças:**
- Importar `IRPFAnalyzer` + `PassiveIncomeCalculator` no topo.
- Adicionar `passive_income_calculator: PassiveIncomeCalculator | None` à
  classe (parâmetro opcional injetável; default = None).
- Em `from_configs(...)`: instanciar passing `PassiveIncomeConfig.default()`
  ou montar a partir de `goals.json::independencia_financeira`.
- Em `analyze_via_store(store)`: ler artifact `extract_irpf_full` se existe
  (via `store.read("extract_irpf_full", key)`); compor `IRPFAnalyzer.from_payloads`
  ou `None` se ausente.
- Adicionar campo `passive_income: PassiveIncomeResult | None` no
  `E5AnalysisResult`.

**Cuidado de paridade:** o E5 legacy roda IRPFAnalyzer já — golden
tests podem mudar bytes em `goals` (vamos popular
`taxa_retirada_efetiva_pct`, `renda_passiva_anual_observada`,
`patrimonio_gerador_brl`, `acumuladores_pct_gerador`). Atualizar
goldens **no mesmo PR** com justificativa em commit body.

**⚠️ Aprovação humana dogfood antes do merge:** atualizar golden
mecanicamente é proibido nesta lane. PR precisa de checkpoint manual
do operador dogfood validando que TRS efetiva é sensata (entre 0,5% e
6,0% para o workspace de referência). Anotar no PR description que
checkpoint foi feito + número.

**Critério de aceite:**
- 2 unit tests do adapter com IRPF mock confirmando passive_income
  populado (com e sem acumuladores).
- 1 unit test do adapter SEM IRPF artifact confirmando
  `passive_income.status == "sem_irpf"`.
- Goldens E5 atualizados com aprovação dogfood.
- `pytest tests/unit/pipeline/test_e5_analyzer_adapter.py` verde.
- `pytest tests/test_e5_golden_execution.py` verde.

### 4. Update `RatiosCalculator` — sair do placeholder

**Arquivo:** `pipeline/domain/services/ratios_calculator.py`

Hoje retorna `"N/D"` como string. Quando o adapter populates o
PassiveIncomeResult, o ratios deve refletir.

**Design escolhido (DRY):** ratios consome `PassiveIncomeResult` pronto
do adapter — não duplica lógica.

**Mudanças:**
- `FinancialRatios.rentabilidade_pct: Decimal | None = None` (em vez de
  string `"N/D"`).
- `FinancialRatios.aliquota_efetiva_ir_pct: Decimal | None = None`.
- `to_legacy_dict()` mantém `"N/D"` para compatibilidade serialização
  legado quando `None`:
  ```python
  "rentabilidade_pct": (
      f"{self.rentabilidade_pct:.2f}"
      if self.rentabilidade_pct is not None
      else "N/D"
  )
  ```
- `calculate(...)` ganha parâmetro opcional `passive_income:
  PassiveIncomeResult | None = None`.
  Quando presente e `status == "ok"`, popula `rentabilidade_pct` com
  `trs_efetiva_pct`.
- `aliquota_efetiva_ir_pct`: derivar de IRPFAnalyzer já existente
  (`ir_pago_total / renda_total_brl`). Se IRPF ausente, mantém `None`.

**Critério de aceite:**
- Tests em `tests/unit/pipeline/test_ratios_calculator.py`: caso com
  passive_income, sem passive_income, mantém `"N/D"` no
  `to_legacy_dict()` para back-compat de fixtures.

### 5. Popular `goals.taxa_retirada_efetiva_pct` + filtro de fase na regra

**Arquivos:**
- `pipeline/domain/services/e5_serialization.py` (popular goals)
- `pipeline/domain/services/suggestion_rules.py` (filtro de fase)

**Em `e5_serialization.py`:** quando `passive_income.status == "ok"`,
o serializer adiciona ao bloco `goals.independencia_financeira`:
```json
{
  "taxa_retirada_efetiva_pct": 2.31,
  "renda_passiva_anual_observada_brl": 38420.50,
  "renda_passiva_mensal_observada_brl": 3201.71,
  "patrimonio_gerador_brl": 1664567.89,
  "acumuladores_pct_gerador": 12.4,
  "ano_referencia_irpf": 2025,
  "defasagem_meses": 16
}
```

**Em `suggestion_rules.py:rule_trs_desalinhada` (linha 86):** adicionar
filtro de fase para evitar ruído em acumulação. Hoje a regra dispara
quando `trs_efetiva > meta * 1.15` (sinal de retirada acima do
sustentável). **Adicional:** só dispara se `progresso_if_pct ≥ 50`.

```python
def rule_trs_desalinhada(...):
    """TRS efetiva > alvo + 15% E progresso ≥ 50% (Perini/AUVP).

    Filtro de fase evita ruído em acumulação onde TRS efetiva alta
    pode ser artefato de patrimônio investido pequeno (denominador
    baixo) — não sinal real de retirada acima do sustentável.
    """
    trs_atual = _as_float(goals.get("taxa_retirada_efetiva_pct"))
    if trs_atual is None:
        return None
    progresso = _as_float(goals.get("if_pct")) or 0.0
    if progresso < 50.0:
        return None
    target = cfg.trs_target_pct
    threshold = target * (1 + cfg.trs_drift_tolerance_pct)
    if trs_atual <= threshold:
        return None
    ...
```

**Não adicionar regra oposta (TRS << meta) nesta lane.** Risco de
falsos positivos em acumulação inviabiliza — fica para M3 (yield-on-cost
por classe, com contexto suficiente para recomendação correta).

**Critério de aceite:**
- 1 test em `tests/test_suggestion_generator.py` mostrando
  `rule_trs_desalinhada` ativa com goals populado E `if_pct >= 50`.
- 1 test mostrando regra **silenciosa** com `if_pct < 50` (mesmo
  quando TRS efetiva passa do threshold) — sinal de fase de
  acumulação.
- ADR registra: regra antes dormente, agora disparando com filtro de
  fase.

### 6. UI — S7 ganha 4 KPIs + tooltip-info-icon + caption-acumulação + 2 banners + empty states

**Arquivo:** `frontend/src/components/report/sections/S7IndependenciaSection.tsx`

Hoje tem 4 stats (Meta IF, Progresso, Ano IF, Gap). Adicionar **antes**
da projeção. Hierarquia validada por product-designer:

**Ordem dos 4 KPIs:** `Renda passiva | Carteira de renda | TRS efetiva | Em acumuladores`

Razão: numerador (R$/mês) → denominador (R$ patrimônio) → razão (%) →
nota explicativa. Espelha a leitura mental "R$ 3.200/mês de R$ 1,66 mi
→ ~2,3%". Princípio "decisão → contexto → detalhe".

```tsx
{passiveIncome && passiveIncome.status === "ok" && (
  <>
    <div className="md:col-span-2 grid grid-cols-1 gap-4 md:grid-cols-4">
      {/* 1. Renda passiva — âncora monetária do Cerbasi */}
      <Stat
        label="Renda passiva"
        value={
          <>
            <MonetaryValue value={passiveIncome.renda_passiva_mensal_brl} compact />
            <span className="text-xs text-muted-foreground">/mês</span>
          </>
        }
        sublabel={
          // text-sm (não text-xs) — alta renda lê fluxo anual também
          <span className="text-sm">
            R$ {formatBRL(passiveIncome.renda_passiva_anual_brl)} / ano
          </span>
        }
      />

      {/* 2. Carteira de renda — denominador */}
      <Stat
        label="Patrimônio investido"
        value={<MonetaryValue value={passiveIncome.patrimonio_gerador_brl} compact />}
        sublabel={`${pctOfTotal(passiveIncome.patrimonio_gerador_brl, patrimonio_total)}% do patrimônio`}
      />

      {/* 3. TRS efetiva — razão derivada, com Info icon WCAG-compliant */}
      <Stat
        label={
          <span className="inline-flex items-center gap-1">
            TRS efetiva
            <InfoTooltip
              ariaLabel="Sobre TRS efetiva"
              content="Yield observado vs. meta de retirada sustentável (5% Perini; piso conservador 4% Trinity Study)."
            />
          </span>
        }
        value={`${passiveIncome.trs_efetiva_pct.toFixed(1)}%`}
        tone={trsTone(
          passiveIncome.trs_efetiva_pct,
          goals.trs_pct ?? 5.0,
          goals.if_pct ?? 0,
        )}
        sublabel={
          <>
            Meta {(goals.trs_pct ?? 5).toFixed(1).replace(".", ",")}%
            {passiveIncome.defasagem_meses && passiveIncome.defasagem_meses >= 6 && (
              <span className="block text-xs text-muted-foreground mt-1">
                IRPF {passiveIncome.ano_referencia_irpf} ·
                {" "}{passiveIncome.defasagem_meses}m de defasagem
              </span>
            )}
          </>
        }
      />

      {/* 4. Em acumuladores — sempre presente (consistência > economia
          de espaço); tom condicional fecha loop visual com banner */}
      <Stat
        label="Em acumuladores"
        value={
          <span className={passiveIncome.acumuladores_pct_gerador === 0 ? "text-muted-foreground" : undefined}>
            {`${passiveIncome.acumuladores_pct_gerador.toFixed(0)}%`}
          </span>
        }
        tone={passiveIncome.acumuladores_pct_gerador > 40 ? "warning" : "neutral"}
        sublabel={
          passiveIncome.acumuladores_pct_gerador === 0
            ? "Sem ETFs/fundos acumuladores"
            : passiveIncome.acumuladores_pct_gerador > 40
              ? <span className="text-[var(--semantic-warning)]">&gt;40% subestima TRS</span>
              : "ETFs/fundos sem distribuição"
        }
      />
    </div>

    {/* Caption permanente em acumulação — substitui tooltip como veículo
        principal (WCAG 1.4.13). Some quando progresso ≥ 50. */}
    {(goals.if_pct ?? 0) < 50 && (
      <p className="text-xs text-muted-foreground mt-2">
        Carteira em acumulação — yield baixo é esperado nesta fase. Retorno
        total inclui valorização, não só dividendo.
      </p>
    )}

    {passiveIncome.acumuladores_pct_gerador > 40 && (
      <AcumuladoresBanner pct={passiveIncome.acumuladores_pct_gerador} />
    )}
    {passiveIncome.defasagem_meses && passiveIncome.defasagem_meses >= 15 && (
      <DefasagemWarningBanner
        ano={passiveIncome.ano_referencia_irpf}
        meses={passiveIncome.defasagem_meses}
      />
    )}
  </>
)}
{passiveIncome?.status === "sem_irpf" && (
  <EmptyState
    title="Importe seu IRPF para calcular a TRS efetiva"
    body="Sem a declaração, exibimos só a projeção. Com IRPF importado, calculamos sua renda passiva real (dividendos, JCP, aluguéis) sobre a carteira atual."
    cta={{ href: "/documents", label: "Importar IRPF" }}
    ctaSublabel="Aceita PDF da Receita ou .DEC"
  />
)}
{passiveIncome?.status === "gerador_zero" && (
  <EmptyState
    title="TRS efetiva começa quando há patrimônio investido"
    body="Ainda não identificamos ativos geradores de renda na sua carteira. Esta métrica passa a fazer sentido com os primeiros aportes — até lá, foque na meta de aporte mensal e na reserva de emergência."
  />
)}
```

**Copy final dos banners:**

`AcumuladoresBanner` (`pct > 40`):
> **{N}% da sua carteira de renda está em ativos sem distribuição** (BOVA11, IVVB11, IVV e similares). Esses ativos geram retorno por valorização, não dividendo — a TRS efetiva os subestima como geradores de renda. O sinal correto está na alocação alvo (S3), não nesta métrica.

`DefasagemWarningBanner` (`defasagem ≥ 15m`):
> **IRPF de {ano} desatualizado.** A TRS efetiva usa rendimentos declarados há {N} meses; mudanças recentes na carteira não estão refletidas. Importe a declaração mais recente para recalcular.
>
> CTA secundário: "Importar IRPF mais recente" → `/documents`

**Tooltip do `InfoTooltip` ao lado do label "TRS efetiva":**
> Yield observado vs. meta de retirada sustentável (5% Perini; piso
> conservador 4% Trinity Study).

**Caption permanente em acumulação** (`progresso < 50`):
> Carteira em acumulação — yield baixo é esperado nesta fase. Retorno
> total inclui valorização, não só dividendo.

**Helper `trsTone(efetiva, meta, progresso)` — tom condicionado à fase:**

| Fase | Critério | Tom |
|---|---|---|
| Acumulação | `progresso < 50` | **Sempre neutro/info** — yield baixo é esperado, sem warning |
| Aproximação | `50 ≤ progresso < 95`, `efetiva ≥ 0,7 × meta` | Neutro |
| Aproximação | `50 ≤ progresso < 95`, `efetiva < 0,7 × meta` | **Warning** — carteira deveria estar girando p/ yield |
| Independência | `progresso ≥ 95`, `efetiva ≥ meta` | **Positivo** — sustenta retiradas |
| Independência | `progresso ≥ 95`, `efetiva < meta` | **Warning** — não sustenta retiradas |

```ts
function trsTone(
  efetiva: number,
  meta: number,
  progresso: number,
): "neutral" | "positive" | "warning" {
  if (progresso < 50) return "neutral";
  if (progresso < 95) return efetiva >= meta * 0.7 ? "neutral" : "warning";
  // progresso ≥ 95 — IF próxima ou atingida
  return efetiva >= meta ? "positive" : "warning";
}
```

**Sem hex literal.** Usar `var(--semantic-success)`, `var(--semantic-warning)`,
`var(--surface-muted)` (ADR-076 + ADR-129).

**Tipos no `frontend/src/lib/api/reports.ts`:** adicionar
```ts
export interface PassiveIncomeData {
  status: "ok" | "sem_irpf" | "gerador_zero";
  renda_passiva_anual_brl: number;
  renda_passiva_mensal_brl: number;
  renda_passiva_por_fonte_brl: {
    dividendos: number; jcp: number; aplicacoes: number;
    ganho_capital: number; exterior: number; alugueis: number;
  };
  patrimonio_gerador_brl: number;
  trs_efetiva_pct: number;
  ano_referencia_irpf: number | null;
  defasagem_meses: number | null;
  acumuladores_pct_gerador: number;
}

// E em ReportAnalysisData:
passive_income?: PassiveIncomeData;
```

**Critério de aceite (validado por product-designer):**

- **Vitest matrix:** snapshot dos 4 KPIs em **3 fases × 2 acumuladores
  (low/high) × 3 defasagens (none/info/warning)** = 18 cenários
  testados. Renders adicionais: `sem_irpf`, `gerador_zero`.
- **Caption de acumulação aparece quando `progresso < 50`** e some quando
  `≥ 50` (teste explícito).
- **Loop visual KPI↔banner:** card "Em acumuladores" tem tom warning E
  sublabel `>40% subestima TRS` quando `pct > 40`. Idempotente quando
  ≤40.
- **WCAG 2.1 AA:** axe-core no S7 com tooltip aberto e fechado, screen
  reader (NVDA/VoiceOver) lê info crítica **sem ativar tooltip** (via
  caption permanente em acumulação + `Info` icon com `aria-label`).
- **WCAG 1.4.13** (Content on Hover): `InfoTooltip` é dismissable +
  hoverable + persistent. Conteúdo crítico de mitigação NÃO depende
  exclusivamente do tooltip — caption permanente cobre o caminho de
  acumulação.
- **WCAG 1.4.1** (Use of Color): tom warning no card acumuladores tem
  sublabel textual `>40% subestima TRS`, não apenas cor.
- **Mobile 360px:** todos os 4 KPIs legíveis em 1 coluna; sublabel
  "R$ X / ano" mantém `text-sm` (não `text-xs`); NBSP no `R$`.
- Playwright (extender `tests/e2e/reports.@critical.spec.ts`): tab por
  todos os cards via teclado, foca o `Info` icon, abre tooltip via
  Enter/Space, fecha via Escape.
- `make update-openapi-snapshot` (ADR-109) — `passive_income` no
  schema de `/v1/reports/{id}`.
- **Test usabilidade dogfood (5min):** mostre o card a 3 usuários
  AUVP-leitor; pergunte (i) "o que essa seção te diz?" e (ii) "você
  venderia growth para subir esse número?". Resposta correta esperada:
  (i) "yield observado vs. meta" / "carteira gerando R$X/mês"; (ii)
  "não". Falha de qualquer leitor = travar PR.
- 18 hex hardcoded de Onda 9 não é escopo desta lane; só **não
  introduzir novos**.

---

## Decisões metodológicas (validadas pelo financial-planner)

Estas estavam pendentes; agora consolidadas. Não alterar sem nova
consulta ao financial-planner.

### D1 — Patrimônio gerador (carteira de renda) ✅

**Inclusos sempre:** investimentos titular + cônjuge.

**Inclusos por config (default ON):** imóveis investimento.

**Inclusos com yield 0% explícito (sinal pedagógico):**
- Cripto sem staking (BTC hold puro)
- Ações growth sem dividendo (Tesla, NVDA, Amazon)
- PGBL/VGBL em acumulação (com nota: "Renda passiva PGBL = R$0/ano
  hoje; previsto na fase de usufruto")

**Inclusos como excedente:** caixa acima de `reserva_alvo` (parcela
até `reserva_alvo` é reserva de emergência, não gerador).

**Excluídos sempre:** residência principal, veículos, derivativos
(alavancagem ≠ estoque), parcela de caixa = `reserva_alvo`.

**Edge cases v1 (binário, sem pro-rata):**
- Imóvel uso misto: trata como o `descricao` atual indicar (residência
  ou investimento). Heurística leve no E5 narrativa quando detectar
  termos "uso misto", "loja", "comercial parcial".
- Ouro físico: incluso como gerador (yield 0%, igual cripto).
- USD em conta exterior: incluso como gerador em v1; refinamento em
  M2.

### D2 — Workspace sem IRPF ✅

Status `"sem_irpf"` → empty state com CTA "Importar IRPF". **Nunca**
estimar via categorização de transações.

### D3 — Defasagem IRPF — banner em 2 níveis ✅

| Defasagem | Nível | Localização |
|---|---|---|
| < 6 meses | nada | — |
| 6-14 meses | **info** discreto | sublabel inline no card TRS efetiva |
| ≥ 15 meses | **warning** | banner próprio abaixo dos KPIs |

Justificativa: ano-base AAAA declarado em abril/AAAA+1 = defasagem
natural de 4-5 meses. Sinal real de "desatualizado" começa por 12-15m.

### D4 — Tom semantic-warning condicionado à fase ✅

Threshold fixo seria erro metodológico. Ver helper `trsTone` no Item 6
acima — depende de `progresso_if_pct`.

**Em acumulação (progresso < 50): NUNCA warning.** Yield baixo é
esperado.

### D5 — Regra oposta (TRS << meta) — fora de escopo M1 ✅

Falsos positivos em acumulação inviabilizam. Vai para M3 com contexto
de yield-on-cost por classe.

---

## Riscos & mitigations

| Risco | Mitigação |
|---|---|
| Quebrar paridade goldens E5 (`"N/D"` → número, mudança bucket aluguéis) | Atualizar goldens **no mesmo PR**; **aprovação humana dogfood** explícita; `to_legacy_dict()` mantém `"N/D"` quando `passive_income is None` |
| Mudança de `_bucket_capital` afeta S8 e chart `irpf_renda` (cascata) | Item 2 inclui paridade test + ADR §Re-classificação documenta impacto; commit body cita delta |
| IRPF analyzer não plugado em adapter (só em legacy `e5_analyze.py`) | Item 3 wire-a explicitamente; testar caminho com e sem IRPF artifact |
| Rule `rule_trs_desalinhada` dispara em massa após ligar (ruído) | Item 5 adiciona filtro `progresso ≥ 50%`; já tem `dedup_key` por bucket de 0.5pp |
| Decimal vs float em chart libs | Coerção `Number(decimal.toString())` na boundary do front, manter Decimal no backend |
| Workspace sem IRPF importado = empty state (não regression) | Status `"sem_irpf"` é caminho explícito; teste cobre |
| Defasagem grande (16m) gera UX confuso | Banner em 2 níveis (D3) |
| **Usuário induzido ao erro #1 do iniciante** (vender growth para perseguir DY) | Caption permanente em acumulação + tooltip `Info` icon ao lado do label TRS efetiva (WCAG-compliant) + tom condicionado à fase + banner acumuladores + R$/mês visível antes do % |
| **Família com IVVB11/BOVA11 dominante vê TRS efetiva artificialmente baixa** | Banner explicativo quando acumuladores > 40% do gerador + tom warning + sublabel "&gt;40% subestima TRS" no card "Em acumuladores" (loop visual KPI↔banner) |
| **Conteúdo crítico de mitigação invisível em mobile/screen-reader** | Caption permanente em acumulação substitui tooltip como veículo principal; `InfoTooltip` segue WCAG 2.1.1 + 1.4.13 (dismissable + hoverable + persistent) |
| ADR-109 OpenAPI snapshot precisa atualizar | `make update-openapi-snapshot` no commit final |

---

## Sequência de execução (5-6 dias)

| Dia | Foco | Entregáveis |
|---|---|---|
| **D1** | Service puro (Item 1) | `PassiveIncomeCalculator` + 15 unit tests. Standalone, testável sem IRPF wire. |
| **D2** | Fix bucket capital (Item 2) | Aluguéis trabalho→capital + paridade test + ADR §Re-classificação rascunho. |
| **D3** | Wire E5 + ratios (Items 3, 4) | Adapter wire, ratios sai de placeholder. Goldens atualizados (rascunho — sem aprovação dogfood ainda). |
| **D4** | Serialization + suggestion (Item 5) | Popular goals + filtro de fase. Test da regra (silenciosa em acumulação). |
| **D5** | UI completa (Item 6) | S7 com 4 KPIs + tooltip + 2 banners + 2 empty states + helper `trsTone` + Vitest + Playwright. |
| **D6** | ADR + checkpoint dogfood + OpenAPI + a11y polish | ADR finalizada, dogfood validation manual (TRS efetiva sensata 0,5-6%), `make update-openapi-snapshot`, axe-core no S7, test usabilidade 3 leitores AUVP. **Copy review com product-designer já feito** (incorporado no Item 6). |

PR único atomicidade. Mudança coesa, mais fácil revisar holisticamente.

---

## Checklist final (antes de abrir PR)

Antes de abrir PR contra `main`:

- [ ] `pre-commit run --all-files` verde
- [ ] `pytest backend/tests -q` verde
- [ ] `pytest tests -q` verde (incluindo goldens E5 + paridade IRPF)
- [ ] `cd frontend && npm test -- --run` verde
- [ ] `cd frontend && npm run test:e2e` verde nos `@critical` que tocam S7
- [ ] **Checkpoint manual dogfood:** TRS efetiva calculada em workspace
  de referência está entre 0,5% e 6,0% (sanidade). Operador anotou no
  PR description o número observado.
- [ ] `make update-openapi-snapshot` rodado e diff comitado
- [ ] ADR-NNN escrita em `docs/DECISIONS.md` + ToC regenerada
  (`python3 dev/build_adr_toc.py --inline`)
- [ ] `python3 dev/check_adr_anchors.py` verde
- [ ] `python3 dev/validate_adr_format.py` verde
- [ ] `config/methodology.md` atualizado com §TRS efetiva +
  §Re-classificação aluguel
- [ ] `docs/CHANGELOG.md` atualizado (entry de hoje)
- [ ] Entry em `docs/agent_prompts/README.md` (esta tabela)
- [ ] Branch `agent/a8-trs-real/<ts>` rebased contra `origin/main` e
  pushada
- [ ] PR com template completo, label `feat`, escopo declarado
- [ ] **axe-core verde no S7** com tooltip aberto e fechado (WCAG 2.1 AA)
- [ ] **Test usabilidade 3 leitores AUVP** validando (i) leitura
  correta da seção, (ii) não-indução ao erro #1 do iniciante
- [ ] CI verde antes de habilitar auto-merge

---

## Notas para quem pegar a lane

- **Não invente regra de domínio.** Bater em [config/methodology.md](../../config/methodology.md)
  e nas docstrings de `irpf_analyzer.py` antes de decidir o que entra
  no bucket de capital.
- **Decimal everywhere no backend.** Float quebra TRS = renda/gerador
  com erro acumulado. Money.brl() para todas as agregações.
- **Teste com workspace dogfood** antes de abrir PR — o número precisa
  ser sensato. Se TRS efetiva sair 47%, tem bug; se sair 0,3%, conferir
  se o IRPF mais recente foi importado.
- **Não adicionar yield-on-cost por classe nesta lane.** Esse é M3
  (premium); inflate scope é receita para PR não fechar. Escopo
  fechado: agregado total + 6 fontes para chart de v2 (não v1).
- **Empty states são feature, não fallback.** Trate "sem_irpf" e
  "gerador_zero" como caminhos de primeira-classe, com copy específica
  e CTA quando aplicável. Métrica errada > sem métrica.
- **Terminologia UI ≠ chave JSON.** Backend usa `patrimonio_gerador_brl`
  (estável); UI usa "Carteira de renda" ou "Patrimônio investido".
  Não cruzar. ADR documenta correspondência.
- **Renda passiva R$/mês vem antes do %** na hierarquia visual. Cerbasi:
  âncora monetária bate âncora percentual em decisão familiar.
- **Tooltip + caption permanente não são opcionais.** São mitigação
  metodológica obrigatória — sem elas, M1 induz erro do iniciante. Em
  acumulação (`progresso < 50%`), a **caption** é o veículo principal
  (a maioria do dogfood estará em acumulação); o tooltip via `Info`
  icon é complementar.
- **Tom condicional no card "Em acumuladores" fecha loop visual com o
  banner.** Sem ele, usuário só descobre que importa quando estoura
  40%; com ele, o card sinaliza proximidade do threshold.
- **Não esconder o card "Em acumuladores" quando = 0%.** Consistência
  visual entre workspaces > economia de espaço — o conceito precisa
  existir na primeira leitura mesmo quando não se aplica.
- **`split_trabalho_vs_capital` muda valores em produção** com Item 2.
  Se isso quebrar algum chart inesperado, **pause e abra issue** —
  não improvise correção. ADR documenta o impacto esperado; impactos
  imprevistos exigem nova decisão.
- Se aparecer dúvida sobre se algo é "carteira de renda" durante
  implementação (ex.: ouro físico, USD em conta exterior, posição em
  derivativos), **pause e pergunte** — adicione ao §Decisões com
  default proposto, não invente sozinho.

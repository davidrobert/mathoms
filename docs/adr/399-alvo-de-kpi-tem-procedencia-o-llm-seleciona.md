---
id: ADR-399
type: adr
title: "Alvo de KPI tem procedência declarada; o LLM seleciona identidade, não autora número"
status: Proposto
phase: §r7 PE-2/FP-6
date: "2026-08-19"
relates_to:
  - "[[ADR-081]]"
  - "[[ADR-134]]"
  - "[[ADR-143]]"
  - "[[ADR-191]]"
  - "[[ADR-202]]"
  - "[[ADR-294]]"
  - "[[ADR-296]]"
  - "[[ADR-340]]"
  - "[[ADR-387]]"
  - "[[ADR-396]]"
tags:
  - type/adr
  - area/llm
  - area/dominio
---

## Contexto

`metricas[].target` do parecer — o valor-alvo que a família deve perseguir — era
string livre autorada pelo LLM. Dois defeitos medidos em runs armazenados:

**PE-2 — o alvo migra sobre dado byte-idêntico.** `ratios.concentracao_imobiliaria`
= 34,86 nos dois runs; o alvo publicado foi `< 30%` e depois `< 35%`,
**atravessando o valor observado**. Violação virou conformidade sem nada ter
mudado no patrimônio. O limiar canônico do repo é **50%** ([[ADR-340]]): os dois
números do LLM estavam errados, em direções opostas — não é viés, é ruído. E no
run em que disse `< 30%`, o produto afirmou violação a uma família que, pelo
próprio canon, estava conforme.

**FP-6 — o alvo é mais frouxo que a meta declarada.** Para renda fixa, a família
declarou `alvo_pct = 51,55`; o parecer publicou `≤ 55%`. Pior, o `valor_atual`
publicado (76,0%, base carteira financeira) vinha de base diferente do alvo
(82,30%, base carteira líquida): **dois denominadores para o mesmo conceito no
mesmo payload**. O desvio implícito saía ~21pp contra os 30,75pp que o motor já
havia calculado em `desvio_pp`.

A causa não é instrução ruim de prompt. A persona **já** diz "não invente
números" (R1) e o modelo violou em 8 dos 10 casos, porque o schema declarava
`target` **obrigatório, string livre**: um campo required cujo valor não existe no
payload é uma máquina de fabricação. A prova pelo contrário está na única métrica
cujo alvo bate com o canon ao dígito — reserva de emergência, o único cujo valor
**já é publicado no E5**. Quando o número existe no payload, o modelo copia.

Instrução não é gate. E `seed` também não resolve: [[ADR-396]] registra que ele é
descartado em `anthropic/*`.

## Decisão

**D1 — `target` e `valor_atual` são derivados; o LLM emite `metrica_key`.** O
trabalho do modelo muda de *autorar o alvo* para *selecionar a identidade do KPI*
num vocabulário fechado (`METRICA_KEYS`). KPI fora do enum não pode ser emitido —
é o cap estrutural na fabricação. Padrão [[ADR-081]] (determinístico primeiro) e
mesma forma do `valor_renderizado` de [[ADR-296]], escrito pelo finalize.

`valor_atual` entra junto e **não** é escopo extra: derivar só o alvo deixaria o
par incoerente (alvo de uma base ao lado de observado de outra) e fecharia o FP-6
apenas pela metade — o desvio seguiria subestimado. Cada KPI declara `base`, e as
duas pontas saem da mesma.

**D2 — Precedência: alvo declarado pela família vence limiar de doutrina.** Na
metodologia dona desta métrica, o desvio só é definido contra o alvo declarado — substituir `alvo_pct` por
número de config não torna o conselho mais correto, **destrói a métrica**, porque
`desvio_pp` é o que decide para onde vai o próximo aporte. E publicar alvo mais
frouxo que o compromisso da família é o produto absolvendo-a da própria meta.
Quando o declarado viola um limiar canônico, publica-se o declarado como `target`
e o limiar vira `risco` — nunca um meio-termo fabricado.

**D3 — Alvo sem fonte única é órfão: publica sem `target`, com `motivo`.** Nunca
número inventado, nunca `needs_review` (ausência de meta é fato esperado e
frequente; usar o canal de retenção para o caso comum queima o canal), e nunca
omitir a métrica — a linha segue publicada como observacional para não perder o
sinal. Quatro órfãos **por decisão de domínio**, não por lacuna:

| KPI | Por quê |
|---|---|
| `carteira_trs` | [[ADR-191]] §D5: TRS efetiva é yield observado e não tem comparador. `≥ IPCA+4%` e `≥ 6% real` diferem em 2pp reais **e** comparam yield de fluxo com retorno total, induzindo "vender growth para perseguir DY" — o erro de iniciante que a métrica existe para evitar |
| `protecao_cobertura` | [[ADR-387]] proíbe afirmar capital ideal sem inventário confirmado. O publicado (`≥ 60 meses`) era 2 a 4× mais frouxo que o canon (10× renda anual × fator + dívidas), na métrica cujo erro é irreversível para os dependentes |
| `taxa_poupanca_recorrente` | RV2-24: `poupanca_referencia_pct` (25) e `pontos_fortes_taxa_poupanca_min_pct` (30) descrevem o mesmo conceito sem precedência declarada |
| `if_progresso` | O alvo é o par (ano declarado, 100%); o ano sozinho promete estado futuro sem a probabilidade do cone (persona R20) |

**Regra de segurança:** o resolver encontrando duas fontes para o mesmo conceito
**não escolhe** — publica órfão. Escolher seria inventar regra de domínio com
carimbo de procedência, pior que o alvo do LLM por parecer autoritativo.

**D4 — Leitor único por limiar, no produtor.** O catálogo vive em
`pipeline/domain/services/kpi_target_catalog.py` e é o único leitor de cada
constante. Precisa ser o produtor porque só ele conhece a config **efetiva** após
override por workspace ([[ADR-134]]) — `concentracao_alerta_pct` entra por
parâmetro, não por global. Antes disso `endividamento_maximo_pct` já tinha dois
leitores com default inline duplicado; um terceiro no backend seria a quarta cópia
([[ADR-143]], methodology = code).

## Consequências

- Cobertura medida no payload real do run r7: **6/10 resolvem, 4 órfãos
  documentados**. A premissa "toda métrica % vira drop → a seção esvazia" não se
  materializa: nenhuma métrica é omitida.
- O bloqueio declarado do **catálogo KPI não se aplica a este eixo** — ver
  §Bloqueio abaixo.
- `Metrica` ganha `metrica_key`; `target` passa a `Optional`. Bump do schema de
  saída + `PROMPT_VERSION` ([[ADR-396]] D3 explica por que o bump é load-bearing).
- O LLM emite **menos** tokens (perde `target` e `valor_atual`, ganha um enum
  curto).

## Bloqueio do catálogo KPI: não procede para o eixo `target`

O PE-2 estava registrado como bloqueado pela dependência do catálogo KPI (RV2-01),
sob o argumento de que `parecer_citation_catalog.py` é money-only e sem catálogo
curado toda métrica % viraria drop. **A dependência não existe no código, e está
invertida.** Evidência:

1. `metricas[]` **não tem campo de âncora** — nem `evidencia_path`, nem
   `ancoras[]`. O catálogo de citação alimenta riscos/sugestões/pontos_fortes; não
   tem superfície de contato com `metricas[]`.
2. O catálogo é **input-side**: seu único consumidor renderiza um bloco markdown
   para dentro do prompt. O verificador de saída não o importa — resolve por
   `get_e5_jsonpath`. O catálogo decide o que o LLM é *informado* que pode citar,
   não o que *resolve*.
3. Âncora é afirmação **sobre o payload** ("este número está em `$.path`"); alvo é
   afirmação **normativa** ("deveria ser X"). Prescrição não se ancora em JSONPath
   — ancora-se em config/goals. Eixos ortogonais.

**Inversão:** um registro `metrica_key → {observado_path, target}` entrega à
RV2-01 o path resolvível por métrica **sem** tocar `monetary_only`. Este trabalho
**destrava** a ancoragem de percentual; não é destravado por ela. O **PE-1**
(rota de âncora de citação) segue aberto por mérito próprio, mas deixa de ser
bloqueante — e encolhe, porque perde a exigência de curar limiar normativo.

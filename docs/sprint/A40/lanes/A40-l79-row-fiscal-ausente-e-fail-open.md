---
id: A40.l79
type: lane
title: "A recusa do regime fiscal é fail-open: sem row do ano o default republica, e a seed vence em 2026-12-31"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l79-row-fiscal-ausente-e-fail-open
owner: data-engineer
adrs:
  - "[[ADR-389]]"
  - "[[ADR-135]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/pipeline
  - area/financial-planning
---

# A40.l79 — `row-fiscal-ausente-e-fail-open`

> Aberta em 2026-08-24 no ataque medido às [[A40.l64]]/[[A40.l65]] (#1659). **Não
> é da l64**: vale mesmo que o redutor nunca seja modelado, e a l64 está travada
> em leitura de norma. A [[A40.l56]], que semeou as tabelas, está `shipped` e o
> §Deferimento dela é sobre conferir 2024-2026 no DOU — outro assunto.

## Problema

A [[ADR-389]] D4 pôs a completude do regime **no dado** (`regime_completo` na row
de `fiscal_parameters`) justamente para o consumidor recusar lendo a row em vez
de `if year >= 2026`. A recusa existe e funciona. **Ela não sobrevive à virada do
ano.**

Medido contra `main` em 2026-08-24:

1. A seed (`y3z4a5b6c7d8_seed_fiscal_2024_2026`) grava 2024, 2025 e 2026 com
   `effective_to = date(year, 12, 31)`.
2. `FiscalParameterRepository.list_covering_period` casa
   `effective_from <= início AND (effective_to IS NULL OR effective_to >= fim)`
   — **sem clamp**. Rodado sobre SQLite com as 3 rows: 2026 devolve a row; 2027 e
   2028 levantam `FiscalParameterNotFound`.
3. [`analyze_finances:2184`](../../../../scripts/analyze_finances.py) captura
   `except Exception`, imprime `[warn]` e segue com `fiscal_parameters = None`.
4. O construtor cai em `PrevidenciaConfig.from_fiscal(FISCAL_CONFIG)`, e
   `FISCAL_CONFIG` lê `config/parametros_fiscais.json` — **path proibido**,
   inexistente desde a A7.2b ⇒ `{}` ⇒ `irpf_faixas=()` e `regime_completo=True`,
   o default do dataclass.

Resultado no caso do §Critério 1 da [[A40.l64]] (bruto anual R$ 70.000, que o
redutor da Lei 15.270/2025 zera):

| config | `economia_ir_anual` | `aporte_mensal` | `aliquota_marginal` |
|---|---|---|---|
| AC2026 · row presente (à época) | ausente com motivo | ausente | ausente |
| **AC2027 · row ausente** | **R$ 630,00** | R$ 700,00 | 7,5% (fallback) |

> ### ⚠️ Re-medido em 2026-08-25 — o flip da [[A40.l64]] AGRAVOU este defeito
>
> A tabela acima é de 2026-08-24, quando AC2026 era `regime_completo: false`. O
> #1722 flipou para `true`, e o eixo do dano mudou de lugar.
>
> **Antes:** o fail-open trocava *retenção* por *publicação* — visível, porque a
> row incompleta era a exceção e o `True` do legado destoava.
>
> **Agora:** `regime_completo: true` é o estado NORMAL, e o legado devolve o mesmo
> `True`. O marcador deixou de distinguir qualquer coisa. O fail-open passa a
> trocar o número **certo** por um **errado**, sem sinal nenhum:
>
> | AC2027, bruto R$ 70.000, base R$ 56.000 | `economia_ir_anual` | `aliquota_marginal` |
> |---|---|---|
> | row presente | **R$ 1.891,19** (com redutor) | 27,5% |
> | **row ausente → legado** | **R$ 630,00** | 7,5% (fallback) |
>
> O legado não tem tabela, não tem redutor e não tem piso de IRPFM — e nada nisso
> é observável, porque o único campo que sinalizava incompletude agora diz `true`
> nos dois casos. **A severidade subiu: de "publica quando deveria reter" para
> "publica errado sem deixar rastro".**

**O default `True` está certo para o dict legado** — o comentário em
`PrevidenciaConfig` argumenta que presumir incompleto reteria a prescrição de
todo workspace legado sem defeito medido, e o argumento se sustenta. O defeito é
que **"row ausente" desagua no mesmo ramo que "legado sem defeito medido"**: um
ano sem seed é indistinguível de um workspace pré-A7.2b, e o silêncio favorece
publicar.

### O golden não pega, por construção

`fiscal_store_do_seed(year)` ([`tests/pipeline_golden_substrate.py`](../../../../tests/pipeline_golden_substrate.py))
faz `tabelas[max(a for a in tabelas if a <= year)]` — **clamp que só a fixture
tem**, e a produção não. O comentário da fixture nomeia o risco (*"vira KeyError
silencioso em 2027 — engolido pelo `except Exception`"*): endureceram a fixture
contra o rollover que a produção sofre.

> **Atualizado em 2026-08-25.** O #1722 fez a fixture compor as três migrations, e
> ela agora devolve `regime_completo=True` para 2026+ — alinhada à produção nesse
> campo. **O clamp continua lá**, então o eixo do rollover segue cego: a fixture
> resolve 2027 e 2030 servindo a linha de 2026, enquanto
> `list_covering_period` levanta. O golden não pode ficar vermelho por este
> defeito, e é isso que esta lane tem de consertar.

## Escopo

1. **Distinguir ausência de legado.** O consumidor tem de saber se recebeu "não
   há row para este ano" ou "este workspace não usa `fiscal_parameters`".
   Semear 2027 **não é o fix** — a seed vence de novo em 2028; é no máximo
   mitigação enquanto o fix não entra.
2. Decidir a polaridade da ausência: recusar (reter prescrição, como
   `regime_completo=false`) ou falhar alto. Recusar é o default coerente com a
   [[ADR-375]] D4 — prescrição exige evidência declarada, e row ausente não é
   evidência.
3. O `except Exception` de `analyze_finances` engole a distinção. Ele precisa
   separar "row não existe" de "ConfigStore quebrou".
4. Gate que não seja o golden atual: a fixture não pode clampar o eixo que o
   teste existe para vigiar.

## Entregue — 2026-08-26

**A causa raiz era de vocabulário.** As duas implementações do `ConfigStore`
levantavam exceções **diferentes** para a mesma condição — `FiscalParameterNotFound`
no DB, `KeyError` na in-memory — e o consumidor no pipeline **não pode importar
nenhuma das duas** ([[ADR-089]]). Sem tipo comum, *"não há row para o ano"* era
indistinguível de *"o store quebrou"*, e o `except Exception` tratava as duas
igual: cair no dict legado.

`FiscalParametersAusentes` passa a viver no **port**, e as duas implementações a
levantam. Aí o consumidor consegue separar:

| condição | antes | agora |
|---|---|---|
| row ausente | dict legado ⇒ **R$ 630,00** sem rastro | recusa com `sem_tabela_fiscal_do_ano` |
| store quebrado | dict legado + `[warn]` | inalterado — é falha, não ausência |

O motivo é **próprio**, não `regime_fiscal_incompleto`: aquele **afirma** sobre um
regime conhecido (*"o redutor não está modelado"*); aqui não se conhece nada. A
nota diz o que falta do **nosso** lado — o cliente não tem o que corrigir — e o
espaço de 12% do IRPF continua publicado.

**O clamp da fixture caiu.** `fiscal_store_do_seed` servia a linha de 2026 para
2027 e 2030; a produção resolve por vigência e **levanta**. Agora a fixture levanta
também, e dois testes parametrizados falham se alguém a fizer resolver ano que a
seed não cobre.

> **A fiação quase ficou sem gate.** Os primeiros testes construíam o VO direto e
> provavam a **regra**; a mutação de reverter o `except` do `analyze_finances`
> passava com tudo verde. `TestFiacaoNoAnalyzeFinances` roda o E5 com store sem row
> e assere o motivo no payload — aí a mutação mata. Regra testada e fiação sem
> teste é o modo de falha que esta sprint viu mais vezes.

## Critério de aceite

- Com a seed atual e o relógio em 2027, o caso de bruto R$ 70.000 **não** publica
  economia — e o motivo distingue "sem tabela fiscal do ano" de
  `regime_fiscal_incompleto`.
- Teste que falha se a fixture voltar a resolver um ano que a produção não
  resolve (o clamp da fixture deixa de ser invisível).
- `pytest` do golden continua verde em 2026 sem depender de `date.today()`.

## Fora de escopo

- Modelar o redutor da Lei 15.270/2025 e o IRPFM ([[A40.l64]] PR3/PR4).
- Conferir os valores das tabelas 2024-2026 no DOU ([[A40.l56]], owner-gated).

---
id: A40.l96
type: lane
title: "Tabela de maiores ativos atribui titular a valor que o sistema declara órfão"
sprint: A40
plan: PLAN-report-trust
status: in_progress
priority: P0
branch_slug: a40-l96-titular-atribuido-a-posicao-orfa
owner: data-engineer
adrs:
  - "[[ADR-226]]"
  - "[[ADR-243]]"
  - "[[ADR-394]]"
  - "[[ADR-412]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/in-progress
  - priority/p0
  - area/pipeline
  - area/frontend
  - area/financial-planning
---

# A40.l96 — `titular-atribuido-a-posicao-orfa`

> **Origem:** `RR6-03` da rodada unificada **U2** ([[REPORT-REVIEWS-active]] §r6,
> merge `47970706`). **CONFIRMADO** por cético, com a refutação óbvia derrubada por
> aritmética.

## ~~⚠️ A direção NÃO está determinada~~ — **RESOLVIDA 2026-08-29**

> Era a única das lanes de P0 da U2 cujo alvo do fix não se sabia. A medição
> discriminante está em §Medição abaixo e **as duas hipóteses do brief caem** —
> a resposta é uma terceira, e **o dano inverte**. As seções que seguem ficam
> como foram escritas (o enunciado da rodada é evidência datada); onde a
> medição as contradiz, §Medição prevalece e diz por quê.

## O que está medido e é sólido

A tabela de maiores ativos preenche a coluna de titular em **15 de 15** linhas, enquanto o
mesmo relatório publica uma linha explícita de "investimentos sem titular identificado" e
um risco de severidade **Alta** dizendo que ~metade da carteira financeira não tem
titularidade.

A refutação óbvia — *"as posições órfãs não estão entre as 15 maiores"* — é
**aritmeticamente impossível**: as 15 linhas somam **92,7%** da base (confirmado por duas
âncoras independentes, incluindo o rodapé da própria tabela), logo o residual fora do Top 15
é ≤ 7,3%, e a fatia órfã declarada **não cabe nele, por 2,4×**.

A razão entre o financeiro atribuído ao titular no Top 15 e `patrimonio.investimentos_titular`
é **~3,7×**, e o desbalanceamento **não é simétrico** entre os membros ⇒ é um **modelo de
atribuição diferente**, não "as órfãs foram para o titular".

## O que não se sabe, e é a primeira entrega

Pode ser o **roll-up patrimonial** que erra, não a tabela: o Top 15 talvez leia o titular do
extrato/informe — sinal mais rico que o IRPF. Nesse caso o risco Alta e a
`motivo_supressao` da realocação da reserva é que seriam **espúrios**, e o dano **inverte**:
o produto estaria suprimindo prescrição correta por diagnóstico falso.

**Medição discriminante (antes de qualquer fix):** proveniência **por item** do campo titular
no artefato E4 `investimentos` (`_source` + titular por posição), confrontada com a agregação
de `patrimonio.investimentos_titular` / `investimentos_conjuge`. **Nenhum dos dois lados foi
aberto na rodada.**

## Por que é P0 em qualquer direção

É a rota pela qual o aviso retido de titularidade vira **decisão de sucessão errada**. A
prescrição de planejamento sucessório do parecer é a **única** do relatório que não
condiciona à titularidade — e a tabela que a família abre para executá-la é justamente a que
afirma quem é dono de quê. Secundariamente, a reserva por membro herda o mesmo problema.

## Medição (2026-08-29) — a direção, e por que é uma terceira

**Veredito: o sinal de titularidade existe, é produzido pelo próprio run, e
morre entre o E1 e o E4.** O que o relatório publica como *"49,03% da carteira
financeira está em posições cujo titular não foi identificado"* não descreve a
família: descreve uma quebra de wiring em três camadas. Corrigidas as três, a
fatia sem dono cai de **68,15% → 0,13%** das posições e o número publicado cai
de **49,03% → ~0,10%**, abaixo do `piso_pct: 1.0` que o próprio bloco declara.

Objeto: run `79a61e33`, workspace `1b9f2cf5` — o mesmo do §r6.

### As duas hipóteses do brief, refutadas

**H1 — "o roll-up patrimonial é que erra".** Refutada. `papel_da_chave` trata
chave vazia como `sem_dono` e nunca como titular ([[ADR-412]] §D3), e é isso que
está certo. O roll-up reporta fielmente o que recebeu; o que recebeu é que está
zerado.

**H2 — "o Top 15 lê o titular do extrato, sinal mais rico que o IRPF".**
Refutada por leitura direta do artefato E2 de cada fonte órfã:

| fonte E2 | campo de titular | valor |
|---|---|---|
| `itau_cdbdetalhes` | `titular` | **`None`** |
| `rico_investimentosposicao` | `titular` | **`None`** |
| `c6bank_cdbdetalhes` (LLM) | — | **campo não existe no payload** |
| `binance_investimentosposicao` (LLM) | — | **campo não existe no payload** |
| `santander_cdbdetalhes` | `membro` | `'david'` — a única fonte que carrega |

O extrato é justamente o lado **sem** titular. O Top 15 lê `fonte: irpf_bens` —
o baseline IRPF consolidado, onde **100% dos 60 itens** têm `proprietario`. A
direção é o oposto da hipótese.

### Os três defeitos, e por que cada um é individualmente inerte

O mapa que resolve as órfãs existe: o artefato E1 `members` **deste mesmo run**
traz `banco_membro` com **11 instituições** e `contas[]` com **18 contas** —
incluindo `itau → david`, `rico → david`, `c6bank → david`, exatamente as
instituições das posições órfãs. Ele não chega ao E4 por três razões
independentes.

**D1 — wiring: dois produtores do mesmo mapa, lendo fontes diferentes.**
`extract_members` monta `banco_membro`/`contas` a partir do output do LLM
(`pipeline/stages/extract_members.py:69-77`) e escreve **só no artefato**.
`serialize_family_members` monta o mesmo mapa a partir da tabela `bank_accounts`
(`backend/app/services/config_materializer.py:83-99`) — e é **este** que vira
`ctx.load_config("family_members.json")`, que é o que o E4 consome
(`scripts/categorize_transactions.py:1074`). A rota completa, verificada elo a
elo no closeout (não inferida): `build_config_overrides_from_db`
(`backend/app/services/pipeline/pipeline_adapter.py:740`) → `_family_members_override`
(`:715-729`) → `serialize_family_members` → `config_overrides["family_members.json"]`
→ `ctx.load_config`. **O E1 não reinjeta nada nessa rota:** `extract_members.py:211`
faz apenas `store.write("extract_members", "members", family_json)`. A tabela `bank_accounts` tem **0
rows no banco inteiro**: o único escritor é `family_member_repository.add_account`,
alcançável apenas por `POST /family-members/{id}/accounts` e pelo import de
config (`backend/app/api/config.py:345`) — **nunca pelo pipeline**. Medido:
`serialize_family_members` devolve `['familia', 'membros', 'titular']`, sem
`banco_membro` e sem `contas`.

**D2 — predicado: `ambiguous` conta CONTAS, não MEMBROS — e isso está
ENCODADO, não esquecido.** `AccountResolver._resolve_inner` devolve `ambiguous`
quando `len(contas_bank) > 1`, sem olhar se todas pertencem ao mesmo membro. No
corpus, `itau` tem 2 contas — **ambas `david`** — e `rico` tem 2 contas —
**ambas `david`**. O conjunto de candidatos é um singleton.

> **Correção do closeout (2026-08-29).** A redação anterior desta subseção dizia
> *"o predicado correto é `len({c.member_key for c in contas_bank}) > 1`"*, como
> se fosse descuido. **Não é.** Existe teste que fixa o comportamento:
> `tests/unit/pipeline/test_account_resolver.py:66-69`,
> `test_none_account_number_with_two_same_member_still_ambiguous`, monta
> `_acc("david","itau","123456")` + `_acc("david","itau","789012")` e afirma
> `confidence == "ambiguous"`. Tratar D2 como bug faria o PR2 inverter um teste
> deliberado sem reabrir a decisão.
>
> **O que é defeito de verdade é a divergência ADR↔teste.** A [[ADR-226]]
> declara o caso na lista de aceite do próprio plano de implementação como
> *"ambiguous (**2+ membros** sem account_number)"* — em **membros** —, enquanto
> o §Decisão em prosa fala em *"múltiplas **contas** no mesmo banco sem
> identificador"*. O teste seguiu a prosa; a lista de casos diz o oposto. **Não
> há decisão única a respeitar: há duas, em conflito, dentro da mesma ADR.** O
> PR2 reabre isso com **emenda datada à [[ADR-226]]**, com o `financial-planner`
> decidindo a pergunta de domínio: duas contas do mesmo dono no mesmo banco são
> ambiguidade de **titularidade** (a pergunta do consolidator) ou de **conta**
> (outra pergunta)?

> **Correção da medição (2026-08-31, PR2).** A redação acima diz que *"`itau` tem
> 2 contas — ambas `david` — e `rico` tem 2 contas — ambas `david`"*. Verdadeiro,
> mas **incompleto em duas direções**, e ambas mudam o desenho do fix.
>
> **(i) São 4 instituições, não 2.** Sonda do `AccountResolver` **real** (função
> pura) contra as 18 contas do artefato E1 do run `79a61e33`:
>
> | instituição | contas | membros distintos | `confidence` hoje |
> |---|---|---|---|
> | `bradesco` | 3 | **1** (cônjuge) | `ambiguous` — **falso** |
> | `caixa` | 3 | **1** (titular) | `ambiguous` — **falso** |
> | `itau` | 2 | **1** (titular) | `ambiguous` — **falso** |
> | `rico` | 2 | **1** (titular) | `ambiguous` — **falso** |
> | `nubank` | 2 | **2 — titular E cônjuge** | `ambiguous` — **legítimo** |
>
> As outras 6 instituições resolvem por `fallback_bank`. **4 de 11** são falso-`ambiguous`.
>
> **(ii) Existe ambiguidade GENUÍNA no corpus — mas em OUTRO EIXO, e a primeira
> redação desta correção errou nisso.** O `nubank` tem contas de **dois membros
> diferentes**, então nenhuma versão do predicado o resolve, e nenhuma deveria:
> o estado `ambiguous` tem caso de uso vivo e o critério de aceite não pode
> exigir que ele desapareça. Mas a frase que eu escrevi primeiro — *"o resíduo
> legítimo do fecho completo passa a ser duas coisas: a corretora **e** o
> `nubank`"* — **é falsa**, e o `financial-planner` a derrubou por incompatibilidade
> aritmética com a própria §Contrafactual antes que eu a medisse.
>
> **Medido (2026-08-31):** o eixo carteira do run `79a61e33` tem **5**
> instituições — `Itau`, `Rico`, `Santander`, `binance`, `c6bank` — e o
> `nubank` **não está entre elas**. Os artefatos `nubank` do run são
> `extract_invoices` (fatura) e `reconcile_transactions` (extrato): as 2 contas
> são conta-corrente/cartão, **nenhuma posição de investimento**. O órfão medido
> no artefato E4 `investimentos` é **68,15%** — exatamente o registrado — e o
> resíduo do fecho completo continua sendo **só** a corretora.
>
> **O que a objeção revela, e que vale mais que o erro:** o `AccountResolver`
> tem **dois** call-sites, e o segundo é cópia literal do primeiro
> (`scripts/categorize_transactions.py:339-351` ≡
> `investments_consolidator.py:328-343`). O `nubank` vive no **eixo transações**,
> não no da carteira. Logo, quando D1 fechar e as contas finalmente chegarem ao
> resolver, o `nubank` passa a produzir `membro = "needs_review"` no **fluxo por
> membro** — e o mesmo vale para as 4 singleton enquanto D2 não fechar.
> **Isso é superfície de mutação de E5 que a §Raio de alcance NÃO lista** (ela
> só enumera as 8 superfícies do eixo patrimonial). Sem reauditá-la, a tabela
> dos oito subconjuntos deixa de discriminar, porque um quarto efeito entra no
> espaço sem estar na fixture.
>
> **Consequência para o gate de não-inércia.** Esta sonda é **função pura**: não
> precisa de run de pipeline, só do artefato E1 e do `AccountResolver`. É a
> fixture natural da perna D2 do gate — e ela precisa afirmar **as duas coisas**
> (os 4 singletons resolvem **e** o `nubank` continua `ambiguous`), senão passa
> a medir o vazio no dia em que alguém "consertar" D2 removendo o estado.

**D3 — espaço de chave: a saída do resolver de conta não é canonicalizada.**
O consolidator canonicaliza `membro_raw` do artefato E2 via `MemberNameResolver`
([[ADR-243]]), mas a saída do `AccountResolver` entra crua
(`investments_consolidator.py:328-333`). O artefato E1 usa chaves curtas do LLM
(`'david'`); a identidade do E5 usa a chave canônica longa
(`'david_robert_camargo_ferreira_campos'`). `papel_da_chave('david')` →
**`sem_dono`**.

### Contrafactual — os **oito** subconjuntos

> **Correção do closeout (2026-08-29).** A tabela anterior tinha 4 linhas e
> afirmava que *"qualquer subconjunto próprio dos três deixa o número publicado
> idêntico"*. **A afirmação era falsa** — generalizei de 2 dos 6 subconjuntos
> próprios não-vazios que eu tinha medido. `{D1,D3}` **move**, e é justamente o
> conserto que um PR2 prudente tentaria, por ser o que **não** toca a decisão
> encodada em teste (ver D2).

| subconjunto | **órfão** | `pct_carteira_financeira` | base |
|---|---|---|---|
| ∅ (hoje) | **68,15%** | **49,03%** | medido |
| `{D1}` | 68,15% | 49,03% | medido |
| `{D2}` | 68,15% | 49,03% | medido — sem D1 o resolver não tem contas nem `banco_membro`; devolve `unknown` nas 5 instituições |
| `{D3}` | 68,15% | 49,03% | idem |
| `{D1,D2}` | 68,15% | 49,03% | medido |
| **`{D1,D3}`** | **46,25%** | **~33,3%** | **medido** |
| `{D2,D3}` | 68,15% | 49,03% | idem `{D2}` |
| **`{D1,D2,D3}`** | **0,13%** | **~0,10%** | medido |

**Cinco dos seis subconjuntos próprios não-vazios são inertes.** O sexto,
`{D1,D3}`, é pior que inerte: move o publicado de 49,03% para ~33,3% e
**continua acima do `piso_pct: 1.0`** — as 8 superfícies seguem acesas, o risco
Alta segue impresso e a realocação segue suprimida, enquanto o PR parece
progresso. É esse o caminho que o critério de aceite tem de barrar.

O resíduo de 0,13% no fecho completo é a Binance, que não tem registro de conta
em fonte alguma — órfã legítima.

### Raio de alcance do número falso — 8 superfícies

| # | superfície | o que publica |
|---|---|---|
| 1 | `patrimonio.atribuicao_investimentos` | `status: parcial` + motivo textual |
| 2 | `reserva_emergencia.prescricao_realocacao_suprimida` | `true` |
| 3 | `reserva_emergencia.motivo_supressao` | *"49,0% … sem titular identificado — excedente da reserva depende de quem é o dono"* |
| 4 | parecer `riscos[2]` | severidade **Alta** — *"Titularidade de ~49% da carteira financeira não identificada"* |
| 5 | parecer `sugestoes_execucao[1]` | **P1** — *"Reconciliar a titularidade…"* |
| 6 | parecer `sugestoes_taticas[1]` | a política de alocação sai **condicionada** à reconciliação |
| 7 | parecer `notas_metodologicas[0]` | confiança do diagnóstico = **"insuficiente"** ([[ADR-353]]) |
| 8 | parecer `notas_metodologicas[1]` | escolhe a leitura conservadora **por causa** da titularidade |

Somam-se a razão advisory `domain.investimento_sem_titularidade` e a linha de
`campos_faltantes_pediria_se_iterasse`.

**A ação P1 que o parecer entrega à família — "reconciliar a titularidade dos
investimentos sem dono atribuído" — é uma ação que a família não pode
executar**: o dado não falta do lado dela, o pipeline o descartou.

### Consequência para a cláusula de reinício do contador

O `_README` §Cláusula deixou esta lane **fora** do gatilho *"até a medição
discriminante dizer de que lado está o defeito: se o erro for de render, não
muta E5"*. **Não é de render.** O fix é no consolidator E4 (`membro` por
posição) e propaga para E4 **e** E5 — `investimentos_titular`,
`investimentos_nao_atribuidos`, `atribuicao_investimentos`, a supressão da
reserva e o parecer inteiro. **A l96 entra na cláusula**, ao lado da [[A40.l94]],
da [[A40.l95]] e da [[A42.l15]].

### O que isto faz com a [[A40.l80]] e a [[ADR-412]]

**Não invalida nenhuma das duas** — o domínio ternário, o `else → sem_dono` e as
bases publicadas continuam certos, e a l80 está `open` com sessão viva; esta
lane **não** a toca. O que muda é o **corpus**: a docstring de
`atribuicao_review_reasons` diz *"No corpus que motivou a lane as duas linhas de
cobertura estavam `apurado`/`motivo: null` **e** a maior parte da base não tinha
dono"* — condição que é o sintoma medido aqui, e ele é **fabricado**. Depois do
fix o `sem_dono` deste workspace cai para 0,13%, e as superfícies que a l80
construiu para nomear a fatia órfã deixam de morder neste corpus. **Gate cuja
fixture herda a forma deste workspace precisa de outra fixture, ou passa a medir
o vazio.**

### Correções ao enunciado da rodada

1. **O argumento aritmético do `RR6-03` cai como mecanismo.** Ele exigia base
   única; as duas porcentagens têm denominadores diferentes: o `pct_carteira` do
   Top 15 soma **92,90%** de `investimentos.total` (bens IRPF, dos quais
   **50,16% são imóveis** — 5 das 15 linhas têm `tipo_origem: imovel`), enquanto
   os 49,03% são sobre `patrimonio.investivel_financeiro`. **Não há residual a
   comparar.** A conclusão sobrevive por outra rota — a instituição aparece nas
   duas fotos com estados de atribuição opostos — e a direção do dano é a
   inversa da registrada.
2. **A razão de ~3,7× e a assimetria entre membros são reais, e a leitura delas
   estava certa**: é mesmo um modelo de atribuição diferente. O que a rodada não
   podia saber é que um dos dois modelos opera sobre input zerado.

### Observações secundárias (medidas, não atacadas aqui)

1. **O eixo A tem a convenção oposta ao eixo B.** `_split_investimentos` e
   `_split_imoveis` (`patrimonio_resolvers.py`) são binários com
   `if _is_conjuge_exclusive(...) else → titular`: tudo que não é
   *exclusivamente* do cônjuge vira do titular. É a mesma família do
   `unattributed → titular` que a [[ADR-394]] §D8 cortou no eixo B — e o
   comentário de `build_members_from_consolidated` a nomeia **para o resíduo do
   resumo**, sem aplicá-la ao split item-a-item.
2. **17,29% de `investimentos_consolidados` tem `proprietario` igual à string
   literal `'titular'`** (3 itens Itaú), e `resumo.membros` lista `'titular'`
   como membro ao lado de 3 grafias fragmentadas da mesma pessoa — **6 chaves
   para 2 pessoas + 1 placeholder**.

## Co-design do PR2 (2026-08-31) — `data-engineer` + `financial-planner`

O critério de aceite exigia co-design **antes** do código. Rodou em paralelo. As
duas rodadas convergiram num ponto que **nenhuma das duas tinha no brief**, e
derrubaram três afirmações minhas.

### O que os dois acharam independentemente — e vira pré-condição, não polish

**D4 — o `confidence` é calculado, logado e DESCARTADO no boundary.** Nos dois
call-sites o enum de 4 estados colapsa em `{chave | "needs_review" | ""}`:

```python
if resolution.confidence == "ambiguous": membro = "needs_review"
else:                                    membro = resolution.member_key or ""
```

Consequência que inverte o sinal do fix: fechados D1+D2+D3, `fallback_bank`
(banco de dono único) passa a sustentar **quase toda** a atribuição — e isso é
*hint com boa confiança*, não fato declarado. O Top 15 passaria a afirmar o
titular com o mesmo peso visual da titularidade declarada em IRPF, e as 8
superfícies apagariam **sem que nada registre que a atribuição é inferida**. Sob
[[ADR-394]] (fato ≠ hint) isso é regressão. **A posição carrega
`atribuicao_fonte ∈ {declarada, conta_casada, banco_unico, indeterminada, sem_dono}`
até o E5 — pré-condição do fix, não acabamento.**

Corolário medido: `"needs_review"` como `member_key` é **bug de tipo** — vira
chave em `total_por_membro` (`additionalProperties: number`), um membro fantasma
somando dinheiro. Mesma família da observação secundária #2.

### Três afirmações minhas que caíram

1. **"A família não pode executar a ação P1"** — **falso**. A [[ADR-229]] §1 já
   decidiu: artefato E1 cru = tier 1; **clique do usuário promove a tier 5**. E
   não é ADR de gaveta: `GET /members/suggestions-from-irpf`
   (`backend/app/api/family_members.py:292`) lê exatamente
   `stage=extract_members, key=members`
   (`backend/app/services/irpf_suggestion_adapters.py:52-53`), o fluxo trata
   **contas** com detecção de colisão
   (`get_irpf_suggestions.py:105-177`), e a UI está shipada
   (`config/_useIrpfSuggestions.ts` + `_IrpfDiffModal.tsx`). **As 18 contas do E1
   deste run já são cards clicáveis.** O P0 sobrevive inteiro — o número
   publicado continua fabricado — mas o mecanismo muda: não é *"o pipeline
   descartou o dado"*, é ***"o default do silêncio publica `sem_dono` como fato
   em vez de `inferido, não confirmado`, e nenhuma superfície roteia para a tela
   que resolve"***. Parte do remédio é rota de UI, e isso **barateia** a lane.
2. **"`nubank` é ambiguidade genuína que sobrevive ao fix"** — corrigido em
   §Medição › D2 acima. Ele não está no eixo carteira.
3. **A dicotomia (a)-persistir vs (b)-ler-artefato era falsa** — ver abaixo.

### D1 — dono de `bank_accounts`: **curada pelo usuário**. E há um segundo conflito ADR↔ADR

A tabela responde *"quais contas a família tem"* (entidade editorial: `label`,
número como o usuário digitou, `source_tier`, `irpf_snapshots`, partial unique
index). O E4 faz outra pergunta: *"de quem é esta posição nesta instituição"*.
Hoje as duas têm o mesmo produtor, e quando a curadoria está vazia o pipeline
**não degrada para um tier inferior** — publica ausência de curadoria como fato
sobre a família.

> **Conflito ADR↔ADR, gêmeo do de D2.** A [[ADR-226]] §5 decidiu *"E1 opera em
> modo merge idempotente… existe match exato no DB? → skip… → append nova
> `BankAccount`"* — que é **literalmente a opção (a)**, Decidida em 2026-05-19 e
> **nunca implementada**. A [[ADR-229]] §1 decidiu o mecanismo oposto no dia
> seguinte, sem declarar supersedure. Não há decisão única a respeitar: há duas
> vigentes em conflito. Sem fechar isso por emenda, a próxima lane reabre.

**Decisão: (b′)** — merge de hint no **produtor comum** (`serialize_family_members`),
com precedência por conta e provenance obrigatória. O pipeline **não** escreve
em `bank_accounts`. Precedência: curada vence sempre (tier 5 > tier 1,
[[ADR-146]]/[[ADR-186]]); conta em `workspace_irpf_suggestion_dismissals` **não
entra** (a tabela já é o registro do "não" do usuário); merge é por **conta**,
nunca por instituição — merge por instituição mataria a ambiguidade legítima.

Por que **não (a)**: o partial unique index da ADR-226 PR4 é parcial
(`WHERE account_number IS NOT NULL`), então conta de IRPF sem número ficaria fora
do índice e **duplicaria a cada run**; e `extract_members` skipa em modo
incremental, fazendo o estado do DB depender da ordem de upload. Por que **não
(c)**: `serialize_family_members` é produtor de **três** rotas, não uma — além do
E4, `DBConfigStore.get_family_members` alimenta `consolidate_baseline.py:400,922`
e `extract_informe_aluguel.py:139`. (c) conserta 1 de 3.

### D2 — a ADR não se contradiz: ela colapsou **dois eixos num campo só**

| eixo | pergunta | predicado correto | quem consome hoje |
|---|---|---|---|
| **titularidade** | de quem é? | `\|⋃ titulares(c), c ∈ contas_bank\| ≥ 2` | os 2 call-sites |
| **conta** | em qual conta? | `len(contas_bank) > 1` e não casou por número | **ninguém** |

As duas frases da ADR-226 (`:273` "2+ membros" e `:188` "múltiplas contas") são
**ambas verdadeiras sobre eixos diferentes**. O defeito é um campo carregando
dois vereditos e o consumidor lendo o errado. Isso explica por que o teste parece
deliberado: `test_none_account_number_with_two_same_member_still_ambiguous`
protege uma verdade real — *a conta* não foi identificada — que **não deve ser
revertida**, e sim **re-apontada** para o eixo que ela sempre mediu.

**Decisão:** `AccountResolution` passa a carregar `member_confidence` +
`account_confidence` ortogonais. O teste é **mantido e renomeado**
(`test_two_accounts_same_member_resolves_member_but_not_account`), afirmando
`member_confidence == "fallback_bank"` **e** `account_confidence == "undetermined"`.
Isso satisfaz *"resolvida por decisão, não por patch"* sem reverter decisão
alguma — melhor que inverter o teste.

**Escreva o predicado sobre `titulares(conta)`, nunca sobre `member_key`.** Conta
conjunta e conta de dependente menor são casos em que duas contas do mesmo
`member_key` **são** ambiguidade de titularidade. `is_joint`/`co_titulares`
existem em `BankAccountRecord` e nunca são populados (V2 reservada na ADR-226);
hoje o predicado degenera para `≥2 member_keys`, e no dia do V2 já está certo.
Custo: ~1 linha; evita uma reabertura.

### Ordem dos PRs: **D2 antes de D1** — e não é preferência

Com o predicado **atual** (conta), acrescentar contas de hint **aumenta a
contagem por instituição e fabrica `ambiguous` novo**: instituição com 1 conta
curada + 1 hint do mesmo dono iria de `fallback_bank` (certo) para `ambiguous`
(órfã). **Sem D2, o merge de D1 pode PIORAR workspace que hoje funciona.** Com o
predicado por membro, o merge fica trivialmente seguro.

### Lag de um run — o critério de aceite atual passaria por acidente

`config_overrides` congela **uma vez por run** (`run_context_factory.py:118`),
antes de qualquer stage. O hint do E1 do run corrente **não chega ao E4 do mesmo
run**. O critério *"run novo do `1b9f2cf5` publica abaixo do piso"* passaria —
porque lá o E1 já rodou antes — e **falharia no primeiro run de um workspace
novo**, que é o momento que importa. Remédio: hook pós-stage em
`pipeline_task.py` (ao lado de `_persist_planner_review_if_applicable`)
recomputando `ctx.config_overrides["family_members.json"]` quando
`stage_name == "extract_members"`, com log — mutação de campo de objeto per-run
não viola [[ADR-111]].

### Decisões de domínio (`financial-planner`)

1. **Papel ternário ganha `casal`.** "Não sei qual dos dois cônjuges" **não** é
   "não sei se é da família": sob comunhão parcial o bem adquirido na constância
   é comum ainda que o CPF titular seja de um só. `investimentos_nao_atribuidos`
   passa a significar estritamente **`sem_dono`**. Vocabulário já existe
   (`_membro_label` renderiza "Casal", [[ADR-246]]) — reusar, não inventar.
   **Um piso só** por escopo; segunda base é **§Deferimento com dono
   `financial-planner`**, condição de retomada: primeiro workspace com fatia
   `casal` ≥ 5%.
2. **Confiança do diagnóstico não deve ser rebaixada por atribuição.**
   `diagnostico_confianca` ([[ADR-353]]) mede cobertura de **classificação de
   lançamentos**; atribuição contaminando o diagnóstico comportamental inteiro é
   o over-reach que produziu a superfície 7.
3. **Risco Alta nunca por percentual.** O manifest deixa de entregar
   `pct_carteira_financeira` cru e passa a entregar o par (`sem_dono`/`casal`) +
   **o efeito** (quais prescrições estão suprimidas). Severidade decorre do que a
   incerteza impede, não do seu tamanho — hoje é anchoring: o LLM que recebe
   *"49% sem dono"* produz Alta por construção.
4. **Suprimir vira condicionar, nunca silenciar.** Mesmo com diagnóstico
   verdadeiro, prescreva em intervalo com a base viajando junto ([[ADR-425]] D2).
5. **Regra transversal:** *só é lícito prescrever à família uma ação de
   reconciliação quando a lacuna é do lado dela.* Lacuna do pipeline é razão
   advisory / `needs_review` operacional — **nunca** item do plano de ação.
   Mesmo naipe da [[ADR-425]] D1.
6. **"Titularidade formal ≠ partilha."** Em comunhão parcial há meação de 50%
   antes da herança. A prescrição sucessória é executada lendo essa tabela.
   Uma linha de qualificação na tabela e no manifest — maior razão dano/esforço
   da lane inteira.

### Achados novos, ortogonais aos três defeitos

- **`acima_do_piso` herdou a régua errada.** `SupressaoPorAtribuicao.do_patrimonio`
  define `acima_do_piso = bool(bloco.get("motivo"))` — o `PISO_AGREGADO_PCT = 1.0`
  de nomeação. Mas o comentário **desse mesmo piso** declara: *"Suprimir veredito
  é outro degrau, com teste de sensibilidade — não é este piso"*. A materialidade
  já vive em `_cruza`/`_spread` (meses/anos). Duas réguas para uma decisão é o que
  a [[ADR-425]] §Emenda combateu.
- **Produtor duplicado:** `categorize_transactions.py:339-351` é **cópia literal**
  de `investments_consolidator.py:328-343`. Corrigir um só garante inércia parcial
  no outro.
- **Duas rotas silenciosas fora do escopo declarado:** `consolidate_baseline` e
  `extract_informe_aluguel` leem o mesmo mapa vazio. Ninguém mediu.
- **O E1 não tem schema.** É dos poucos stages fora de `SCHEMA_BY_STAGE` — foi
  por isso que o contrato quebrou mudo por meses. Mecanismo já existe (hook
  pós-write, [[ADR-212]] PR3a).
- **`extract_members` é `tier="premium"`** — no free tier o hint não existe. A
  copy não pode prometer o que a tier não entrega, e a fixture do gate não pode
  ser free-tier, ou mede o vazio.

### Fora desta lane, com dono nomeado

O corte do `else → titular` em `_split_investimentos`/`_split_imoveis`
([[ADR-394]] §D8 aplicada ao eixo A) muta `investimentos_titular`, o split de
imóveis, o Top 15 e os KPIs por pessoa. **Lane própria.** Se entrar de carona,
um quarto defeito entra no espaço e o gate dos oito subconjuntos **deixa de
discriminar** — exatamente o que a §Contrafactual pagou caro para descobrir. O
"fallback visível na célula" do critério de aceite **só tem call-site depois
desse corte**: hoje `build_members_from_consolidated` monta **dois** baldes
(titular/cônjuge) e não existe balde `sem_dono` no eixo A, então implementá-lo
como está escrito produz código inalcançável.

## Critério de aceite

- ✅ **A medição discriminante publicada, com veredito de qual lado erra** — §Medição
  (PR1, 2026-08-29). Nenhuma linha de produção.
- O mapa instituição→membro extraído no E1 alcança o E4 **no espaço de chave
  canônico** — verificável por `banco_membro`/`contas` não-vazios no
  `family_members.json` materializado de um run novo.
- **A divergência ADR↔teste sobre `ambiguous` é resolvida por decisão, não por
  patch**: emenda datada à [[ADR-226]] escolhendo entre *"2+ membros"* (lista de
  casos do plano) e *"múltiplas contas"* (prosa do §Decisão), e
  `tests/unit/pipeline/test_account_resolver.py:66-69` passa a refletir a
  escolha — invertido **ou** mantido com o porquê no nome. Reverter o teste sem
  a emenda não é aceite.
- A saída do `AccountResolver` passa pelo `MemberNameResolver` antes de virar
  `membro` — teste que casa a chave curta do E1 com a chave canônica do E5.
- **Gate de não-inércia:** teste que falha se qualquer *um* dos três for
  revertido, **e que reprova explicitamente `{D1,D3}`** — o subconjunto que
  move o número sem resolver o problema. A fixture é a tabela dos **oito**
  subconjuntos de §Contrafactual, não os 4 estados da versão anterior.
  **Emenda 2026-08-31 (PR2):** a perna D2 do gate afirma **duas** coisas, não
  uma — que as 4 instituições singleton passam a resolver **e** que o `nubank`
  (2 membros) **continua `ambiguous`**. Gate que só afirma a primeira fica verde
  para o "fix" que remove o estado `ambiguous`, e passa a medir o vazio. Ver
  §Medição › D2 › Correção da medição (2026-08-31).
- Run novo do workspace `1b9f2cf5` publica `atribuicao_investimentos` abaixo do
  piso, sem o risco Alta e sem `prescricao_realocacao_suprimida`.
- Ainda vale, para o resíduo legítimo (Binance): **fallback visível na célula**
  quando o titular não é conhecido, e as duas superfícies declarando bases
  distintas de forma legível.

### Adições do co-design (2026-08-31)

- **Provenance (D4) é bloqueante:** `atribuicao_fonte` por posição chega ao E5, e
  `banco_unico` é distinguível de `conta_casada` no publicado. **Quarta perna do
  gate de não-inércia:** teste que falha se a provenance não sobreviver ao E5 —
  sem ela o PR sai verde publicando "0,10% sem dono" e apagando a distinção
  declarado↔inferido que a [[A40.l80]]/[[ADR-412]] construíram.
- **Emenda datada à [[ADR-226]]** cobrindo **duas** divergências, não uma: o
  desdobramento de `confidence` em dois eixos (§3) **e** a §5 morta, cujo "merge
  idempotente" foi supersedido de facto pela [[ADR-229]] §1. Supersedure de
  cláusula não existe file-level ⇒ emenda em 226 + regra nova na ADR `Proposto`.
- **Teste `test_account_resolver.py:66-69` mantido e renomeado**, medindo os dois
  eixos — não invertido. Inverter reverteria decisão real.
- **Veto do usuário respeitado:** teste de que conta em
  `workspace_irpf_suggestion_dismissals` **não** entra no merge.
- **Lag:** teste de run completo em **workspace novo** (E1 na mesma execução)
  provando que o E4 **do mesmo run** enxerga o hint. O critério "run novo do
  `1b9f2cf5`" sozinho passa por acidente e não cobre isto.
- **Os dois call-sites unificados** — corrigir só um garante inércia parcial no
  outro.
- **Superfícies de mutação de E5 reauditadas** com o predicado novo: o fluxo por
  membro do eixo transações entra na §Raio de alcance, ou os oito subconjuntos
  deixam de discriminar.
- **Escopo lateral medido:** `consolidate_baseline` e `extract_informe_aluguel`
  antes/depois. Se o mapa vazio move número lá, é achado novo com linha própria
  — não passageiro deste PR.
- **`casal` tem fixture própria** (não depende do dogfood) e teste que falha se o
  estado virar inalcançável — precedente `nao_apurado` 0/114 em
  `investimentos_cobertura.py`.
- **Fixture do gate não pode ser free-tier** — `extract_members` é `premium`; no
  free tier o hint não existe e o gate mediria o vazio.
- **`"needs_review"` deixa de aparecer como chave** em `total_por_membro`.

> **A tentação a evitar no PR2:** o fix "óbvio" é injetar o artefato E1 no
> `InvestmentsConsolidatorConfig`. Isso resolve D1 e **não** resolve D3 — o
> artefato E1 fala o espaço de chave curto do LLM. O contrafactual mostra que
> esse PR sairia verde no relatório sem mover o número.

## Sequência

- **PR1 (entregue):** medição + registro. Zero produção.
- **PR2 (co-design entregue 2026-08-31):** ver §Co-design. Substituído pela
  sequência abaixo — o co-design achou um quarto defeito (D4, provenance) e
  inverteu a ordem, porque **D1 antes de D2 pode piorar workspace que hoje
  funciona**.
- **PR2a** — contrato, zero comportamento: schema `e1_members` registrado em
  `SCHEMA_BY_STAGE`; campo de origem em `BankAccountRecord`; **emenda datada à
  [[ADR-226]]** (dois eixos em §3 + §5 morta); ADR `Proposto` nova.
- **PR2b** — **D2**: predicado por `titulares(conta)`; teste mantido/renomeado
  medindo os dois eixos; fixture das 5 instituições do corpus. **Inerte sozinho
  por medição** ⇒ seguro em `main` isolado.
- **PR2c** — **D1+D3+D4**: merge com precedência + dismissals em
  `serialize_family_members`; refresh pós-E1 (lag); canonicalização via
  `MemberNameResolver`; provenance até o E5; **unificação dos dois call-sites**.
  Fecha os três de uma vez — **nunca mergeie `{D1,D3}` em `main`**.
- **PR2d** — gate de não-inércia (8 subconjuntos + perna de provenance) +
  rebaseline. **Muta E5 ⇒ entra na janela de rebaseline.**

## Já registrado

`PV9-35` (duas tabelas discordam sobre titularidade) — `MEDIÇÃO-DE-CONHECIDO`; o novo é o
quantum e a rota de decisão nomeada (**sucessão**, não alocação).

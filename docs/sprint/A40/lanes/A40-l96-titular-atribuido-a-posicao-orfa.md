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
(`scripts/categorize_transactions.py:1074`). A tabela `bank_accounts` tem **0
rows no banco inteiro**: o único escritor é `family_member_repository.add_account`,
alcançável apenas por `POST /family-members/{id}/accounts` e pelo import de
config (`backend/app/api/config.py:345`) — **nunca pelo pipeline**. Medido:
`serialize_family_members` devolve `['familia', 'membros', 'titular']`, sem
`banco_membro` e sem `contas`.

**D2 — predicado: `ambiguous` conta CONTAS, não MEMBROS.**
`AccountResolver._resolve_inner` devolve `ambiguous` quando
`len(contas_bank) > 1`, sem olhar se todas pertencem ao mesmo membro. No corpus,
`itau` tem 2 contas — **ambas `david`** — e `rico` tem 2 contas — **ambas
`david`**. Não há ambiguidade: o conjunto de candidatos é um singleton. O
predicado correto é `len({c.member_key for c in contas_bank}) > 1`.

**D3 — espaço de chave: a saída do resolver de conta não é canonicalizada.**
O consolidator canonicaliza `membro_raw` do artefato E2 via `MemberNameResolver`
([[ADR-243]]), mas a saída do `AccountResolver` entra crua
(`investments_consolidator.py:328-333`). O artefato E1 usa chaves curtas do LLM
(`'david'`); a identidade do E5 usa a chave canônica longa
(`'david_robert_camargo_ferreira_campos'`). `papel_da_chave('david')` →
**`sem_dono`**.

### Contrafactual — nenhuma dupla move o número

| cenário | titular | cônjuge | **órfão** | `pct_carteira_financeira` |
|---|---|---|---|---|
| hoje (medido) | 31,85% | 0,00% | **68,15%** | **49,03%** |
| D1 só (wiring) | 31,85% | 0,00% | **68,15%** | 49,03% |
| D1+D2 (predicado) | 31,85% | 0,00% | **68,15%** | 49,03% |
| **D1+D2+D3** | **99,87%** | 0,00% | **0,13%** | **~0,10%** |

É a propriedade que trava a ordem do conserto: **qualquer subconjunto próprio
dos três deixa o número publicado idêntico**, e um PR que feche só D1 sai verde
no relatório sem ter mudado nada. O resíduo de 0,13% é a Binance, que não tem
registro de conta em fonte alguma — órfã legítima.

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

## Critério de aceite

- ✅ **A medição discriminante publicada, com veredito de qual lado erra** — §Medição
  (PR1, 2026-08-29). Nenhuma linha de produção.
- O mapa instituição→membro extraído no E1 alcança o E4 **no espaço de chave
  canônico** — verificável por `banco_membro`/`contas` não-vazios no
  `family_members.json` materializado de um run novo.
- `AccountResolver` só devolve `ambiguous` quando os `member_key` das contas da
  instituição **divergem**: teste com 2 contas do mesmo membro devolvendo
  `fallback_bank`, e com 2 membros distintos devolvendo `ambiguous`.
- A saída do `AccountResolver` passa pelo `MemberNameResolver` antes de virar
  `membro` — teste que casa a chave curta do E1 com a chave canônica do E5.
- **Gate de não-inércia:** teste que falha se qualquer *um* dos três for
  revertido. O contrafactual de §Medição é a fixture, e ela discrimina os 4
  estados. Sem isso, dois dos três regridem em silêncio.
- Run novo do workspace `1b9f2cf5` publica `atribuicao_investimentos` abaixo do
  piso, sem o risco Alta e sem `prescricao_realocacao_suprimida`.
- Ainda vale, para o resíduo legítimo (Binance): **fallback visível na célula**
  quando o titular não é conhecido, e as duas superfícies declarando bases
  distintas de forma legível.

> **A tentação a evitar no PR2:** o fix "óbvio" é injetar o artefato E1 no
> `InvestmentsConsolidatorConfig`. Isso resolve D1 e **não** resolve D3 — o
> artefato E1 fala o espaço de chave curto do LLM. O contrafactual mostra que
> esse PR sairia verde no relatório sem mover o número.

## Sequência

- **PR1 (entregue):** medição + registro. Zero produção.
- **PR2:** co-design **antes** do código — `data-engineer` (D1: quem é o dono da
  tabela `bank_accounts`; persistir do E1 vs. ler o artefato; contrato E1→E4) +
  `financial-planner` (o que a família deve ver enquanto a titularidade for
  parcial **de verdade**). Só então ADR `Proposto`, depois o fix nos três pontos
  com o gate de não-inércia. **Muta E5 ⇒ entra na janela de rebaseline.**

## Já registrado

`PV9-35` (duas tabelas discordam sobre titularidade) — `MEDIÇÃO-DE-CONHECIDO`; o novo é o
quantum e a rota de decisão nomeada (**sucessão**, não alocação).

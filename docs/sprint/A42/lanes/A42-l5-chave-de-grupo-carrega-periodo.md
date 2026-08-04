---
id: A42.l5
type: lane
title: "Chave de agrupamento do razão carrega o período do documento"
sprint: A42
status: planned
priority: P1
branch_slug: a42-l5-chave-de-grupo-carrega-periodo
adrs:
  - "[[ADR-354]]"
  - "[[ADR-310]]"
depends_on:
  - "[[A40.l2]]"
tags:
  - type/lane
  - sprint/a42
  - status/planned
  - priority/p1
  - area/pipeline
---

# A42.l5 — `chave-de-grupo-carrega-periodo` (LC02, LC03, LC04)

> **Origem:** [[LEDGER-CERTIFY-active]] §r4 2026-08-04 — LC02 (Alto, P1), LC03
> (contexto de desenho), LC04 (P1, contrato de identidade). Corolário da definição
> *period-free* da [[ADR-310]]; a [[ADR-354]] é `Proposto` e **não tem emenda** — se
> esta lane exigir mudança de decisão, a forma é emenda datada a ela, escrita nesta lane.

> **Serializada atrás de [[A40.l2]]** — `depends_on`, não `parallel_with`. A razão foi
> medida pelo `senior-cto` em 2026-08-04 e **invalida o critério de aceite que esta lane
> tinha**: reagrupar *period-free* **muta input de hash sem tocar a função de hash**.
> Cadeia verificada linha a linha:
>
> 1. a chave period-free faz duas pernas da mesma conta caírem no mesmo grupo;
> 2. o merge posicional escreve `member_key = base.member_key` (= a 1ª perna da lista);
> 3. a serialização grava **um** `titular` por artefato (`e3_serialization.py:96`);
> 4. o classificador **lê** `account["titular"]` do artefato E3 (`transaction_classifier.py:300`);
> 5. e o alimenta em `build_hash_inputs` (`:350`) → `_hash_v2` → `transaction_hash`;
> 6. o hash muda ⇒ a constraint única de override não casa ⇒ **override manual do dono
>    é orfanado**.
>
> A promessa antiga ("nenhuma alteração na função de hash") é **verdadeira e
> irrelevante**: esta lane canonicaliza **fora** do hash, e o guarda anti-regressão da
> [[A40.l2]] protege só contra canonicalizar **dentro**. Os vetores-golden pinam
> `HashInputs → hash`; **ninguém pina `artefato E3 → HashInputs`**. A [[A40.l2]] PR4
> re-ancora overrides contra um baseline que esta lane move — daí a ordem ser dura.

> **Divisão de escopo com a [[A40.l2]]:** a l2 é dona da identidade de **transação**
> (`_tx_identity`, agrupador de conta) e do colapsador cross-documento; esta lane é
> dona da chave de **artefato** do razão. **Nunca** tocar a função de hash de
> identidade (proibida por [[ADR-278]] D1).

> **Colisão de arquivo declarada com [[A42.l6]]** (mesma onda): as duas tocam
> `pipeline/domain/services/e3_reconciler_adapter.py`, em funções diferentes — esta
> lane no sítio de seleção de saldo de fechamento, a l6 no sítio do predicado de
> extração. Não é disjunção real, é **partição declarada**: quem mergear primeiro
> avisa; a segunda rebaseia. Acoplamento semântico a vigiar: o guard "por expectativa"
> da l6 conta grupos que o run escreveu, e é **esta** lane que muda o keying que define
> esse conjunto — logo se a l6 mergear depois, o número esperado dela mudou.

> **LC04 é medido pelo KR-C da sprint** ("nenhum artefato onde o sentinela de ausência
> é indecidível do literal") e por isso tem de ter dono **aqui**. A trilha original do
> §r4 aponta "A40.l2 PR-B", e esse PR **não existe** no escopo escrito da l2 (que vai de
> PR0 a PR4) — KR sem lane que o entregue é KR órfão.

## Problema

O repositório tem **duas noções concorrentes de "mesma conta"**:

- a chave de agrupamento de conta é **period-free**, como [[ADR-310]] decidiu;
- a chave de agrupamento do **artefato** do razão carrega o **período do documento**.

Consequência: duas pernas da mesma conta que vêm de documentos com períodos
diferentes **nunca se encontram** no dedup — independentemente de qualquer melhoria
na identidade de transação. O repo tem a definição certa e agrupa pela errada.

Isso importa mesmo depois de a [[A40.l2]] fechar: a l2 ataca o par
nativo↔escalado que produz as ocorrências medidas hoje. A classe **latente**
nativo↔nativo — mesmo banco emitindo extrato mensal e consolidado anual da mesma
conta — permanece aberta enquanto a chave carregar período. É por isso que esta lane
existe separada, e é ela que fecha a classe.

## Decisão

1. **Decidir a tupla inteira da chave de artefato — não só "tirar o período".** O repo
   tem **três** noções concorrentes de "mesma conta", e elas discordam sobre qual
   discriminante é identidade: o agrupador de conta usa `(banco, tipo_conta, moeda)`
   — **sem membro**; o agrupamento da reconciliação usa `(instituição, membro, moeda)`
   — **sem tipo_conta**; e a chave de artefato usa `(banco, tipo_conta, MOEDA, período)`.
   Remover o período alinha à primeira e **descarta o membro** que a segunda preserva —
   e é exatamente esse descarte que dispara a cadeia de hash acima. Esta lane é a única
   que pode fechar a divergência: ela **declara a tupla final**, nomeando as três, e
   prova por fixture se membro entra ou sai. O ratchet de conservação de população é
   **cego** a isso — over-merge não perde linha nenhuma.
2. **Rótulo de período derivado do span real** dos lançamentos (achado migrado da
   [[A42.l6]] no split de 2026-08-04): com a chave period-free, o período do artefato
   deixa de ser cosmético e passa a ser a **única** representação honesta do span.
   Deixá-lo noutra lane era deixar metade da decisão de período fora da lane que decide
   período.
2. **Seleção de saldo por período máximo** — ao fundir pernas, o saldo de fechamento
   tem de vir da perna de período mais recente, não da posição na lista. Este ponto é
   o que impede o modo de falha que a medição do §r4 identificou: fundir sem escolher
   o saldo correto insere um statement sem saldo e, por seleção posicional, **apaga a
   conta inteira**.
3. **Não reusar** o predicado de duplicidade existente (LC03): ele exige descrição
   bruta byte-idêntica e o §r4 mediu teto de colapso em torno de **metade** dos casos —
   é o que torna "fundir os grupos" um fix parcial que fecha verde pagando o preço
   máximo. Usar a chave normalizada que já roda dentro do caminho de produção.
4. **Sentinela reservado, fora do vocabulário canônico** (LC04): o token residual do
   contrato de extração por LLM é **byte-idêntico** ao default de "desconhecido" do
   código, em três sítios — a jusante é **indecidível** se o dado disse ou se o código
   defaultou. Dois dos três sítios estão no arquivo que esta lane já possui. Fix:
   sentinela reservado fora do conjunto canônico nos três sítios + tipo fechado
   validado no boundary. **É defeito de contrato, não alucinação** — o modelo cumpriu a
   instrução que recebeu.

Forma: corolário da definição *period-free* da [[ADR-310]] para a chave de artefato.
Se a decisão da [[ADR-354]] (`Proposto`) precisar mudar, a forma é **emenda datada** a
ela — heading **sem** wikilink e `amended_at` no frontmatter, no mesmo commit.

## Critério de aceite

- Nenhum par de grupos do razão da mesma conta *period-free* com chaves de artefato
  distintas (KR-C da sprint).
- **Teste da classe latente:** fixture sintética com duas pernas nativo↔nativo da
  mesma conta, períodos diferentes e sobrepostos ⇒ um único grupo. Hoje são dois.
  Este teste é a razão de ser da lane; sem ele, o fix fecha verde contra o corpus
  atual (onde a classe é latente) sem provar nada.
- **Estabilidade de `transaction_hash` sob o merge — o critério que faltava.** Teste
  novo que pina `artefato E3 → HashInputs` (hoje **nada** pina esse trecho; os
  vetores-golden começam depois dele). Fixture sintética PII-zero com **duas pernas
  nativo↔nativo de titular divergente e períodos diferentes** ⇒ o hash de **todas** as
  transações é idêntico pré e pós-merge. A mesma fixture serve ao teste da classe
  latente acima. Prova por mutação: reverter o fix mata o teste.
- **Delta de override orfanado igual a zero**, medido e reportado no PR — o mesmo gate
  que a [[A40.l2]] usa, aqui também. A conservação de população **não** cobre isso, e a
  versão anterior desta lane afirmava que cobria.
- **Conservação de população** como ratchet: nenhuma linha desaparece no
  reagrupamento. Contagem também **por tupla de identidade**, não só total de linhas —
  senão over-merge passa verde. O desenho fail-closed foi eliminado por medição no §r4 (cobertura de
  contraparte em torno de metade ⇒ quarentenar vocabulário desconhecido apagaria
  centenas de linhas de fonte única) e o ratchet existe para ele não voltar por
  acidente.
- Saldo de fechamento do grupo fundido vem do período máximo, provado por fixture com
  as pernas em ordem invertida na lista.
- **LC04:** grep prova que o sentinela de ausência não colide com nenhum valor
  canônico nos três sítios; teste que **falha** se alguém reintroduzir a colisão. É a
  entrega que sustenta a segunda metade do KR-C.
- Golden do razão verde com delta declarado; **nenhuma** alteração na função de hash
  de identidade.
- **Contrato de `artifact_key` re-congelado:** `dev/go_parity_gate.py:55` declara que a
  chave de artefato do razão é o filename lógico determinístico. Esta lane **move** esse
  contrato ⇒ o controle de paridade Py↔Py precisa ser re-congelado, com o baseline
  anterior arquivado. O gate é owner-gated (nunca rodou) — declarar, não rotear.

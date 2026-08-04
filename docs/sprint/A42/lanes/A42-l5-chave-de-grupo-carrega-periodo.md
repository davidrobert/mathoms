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
depends_on: []
parallel_with:
  - "[[A40.l2]]"
tags:
  - type/lane
  - sprint/a42
  - status/planned
  - priority/p1
  - area/pipeline
---

# A42.l5 — `chave-de-grupo-carrega-periodo` (LC02)

> **Origem:** [[LEDGER-CERTIFY-active]] §r4 2026-08-04 — LC02 (Alto, P1). Corolário
> novo da emenda [[ADR-354]].

> **Paralela a [[A40.l2]]**, não dependente: a l2 é dona da identidade de
> **transação** (`_tx_identity`, agrupador de conta) e do colapsador cross-documento;
> esta lane é dona da chave de **artefato** do razão. Arquivos disjuntos, mas o
> resultado de uma muda o que a outra observa — coordenar antes de rebaselinar
> golden, e **nunca** tocar a função de hash de identidade (proibida por [[ADR-278]]
> D1 e pelo risco de orfanar override).

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

1. **Reagrupamento period-free** na chave de artefato do razão, alinhando-a à
   definição já canônica de conta.
2. **Seleção de saldo por período máximo** — ao fundir pernas, o saldo de fechamento
   tem de vir da perna de período mais recente, não da posição na lista. Este ponto é
   o que impede o modo de falha que a medição do §r4 identificou: fundir sem escolher
   o saldo correto insere um statement sem saldo e, por seleção posicional, **apaga a
   conta inteira**.
3. **Não reusar** o predicado de duplicidade existente: ele exige descrição bruta
   byte-idêntica e tem teto de colapso medido em torno de metade dos casos. Usar a
   chave normalizada que já roda dentro do caminho de produção.

Forma: **corolário da emenda [[ADR-354]]** — a decisão já existe, o que falta é
declarar que a chave de artefato herda a mesma política.

## Critério de aceite

- Nenhum par de grupos do razão da mesma conta *period-free* com chaves de artefato
  distintas (KR-C da sprint).
- **Teste da classe latente:** fixture sintética com duas pernas nativo↔nativo da
  mesma conta, períodos diferentes e sobrepostos ⇒ um único grupo. Hoje são dois.
  Este teste é a razão de ser da lane; sem ele, o fix fecha verde contra o corpus
  atual (onde a classe é latente) sem provar nada.
- **Conservação de população** como ratchet: nenhuma linha desaparece no
  reagrupamento. O desenho fail-closed foi eliminado por medição no §r4 (cobertura de
  contraparte em torno de metade ⇒ quarentenar vocabulário desconhecido apagaria
  centenas de linhas de fonte única) e o ratchet existe para ele não voltar por
  acidente.
- Saldo de fechamento do grupo fundido vem do período máximo, provado por fixture com
  as pernas em ordem invertida na lista.
- Golden do razão verde com delta declarado; **nenhuma** alteração na função de hash
  de identidade.

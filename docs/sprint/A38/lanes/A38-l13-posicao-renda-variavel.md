---
id: A38.l13
type: lane
title: "Posição de renda variável: custódia e carteira consolidada não classificam; dupla contagem latente"
sprint: A38
status: planned
priority: P2
branch_slug: a38-l13-posicao-renda-variavel
adrs: []
depends_on: ["[[A38.l1]]", "[[A38.l3]]"]
tags:
  - type/lane
  - sprint/a38
  - status/planned
  - priority/p2
  - area/pipeline
  - area/dados
---

# A38.l13 — `posicao-renda-variavel` (corpus de investimentos 2026-07-22)

## Problema (certificação empírica 2026-07-22)

1. **Posição Acionária** (PDF de custódia do banco: papel + quantidade,
   **sem valor de mercado**) e **carteira consolidada XLSX** (multi-classe,
   valorada, "Sua carteira"/"Total investido") caem em **conf 0.0** — a
   TypeRule `investimentosposicao` exige "Posição Consolidada/de
   Investimentos/de Carteira" e não casa nenhum dos dois; a XLSX ainda sai
   com **instituição None** (zero marcador).
2. **Dupla contagem latente:** os mesmos papéis com as mesmas quantidades
   aparecem nos dois documentos (posição custodiada reportada por 2 fontes).
   Hoje é dormante — mas com uma pegadinha inversa: o `InvestmentsConsolidator`
   soma **null→0** em `total_por_membro`, então custódia sem marcação
   **deflaciona** o patrimônio sem sinal. A dupla contagem nasce no momento
   em que alguém valorar a custódia sem regra de identidade.

## Escopo (ordem interna OBRIGATÓRIA — decisão do painel)

1. **TypeRules + instituição** (hotspot `type_classifier.py` — entra na
   sequência de coordenação l6→l5→l10→l13): âncoras p/ "Posição Acionária"
   e p/ carteira consolidada ("Sua carteira" + "Total investido");
   resolução de instituição da XLSX (marcador na planilha ou rótulo
   canônico; **instituição vazia é proibida** — cai em key `("","")` órfã
   no consolidador e some do `titular_key` do E5).
2. **ADR `Proposto` ANTES do PR de implementação** (invariante de domínio +
   read-path, análogo a [[ADR-271]] — que continua valendo p/ RF/genérico;
   esta é um **eixo novo**, não emenda):
   - **Chave de identidade RV listada = `ticker_norm + proprietário`**
     (B3: 4 letras + 1-2 dígitos, sufixo fracionário colapsado; ISIN quando
     houver).
   - **Resolução:** mesmo ticker+quantidade com 1 fonte valorada + outra(s)
     só-quantidade ⇒ **colapsa na valorada** (custódia confirma quantidade,
     não adiciona valor); 2+ fontes **valoradas** com mesmo ticker+qtd ⇒
     `needs_review` (espelho × lotes distintos é indistinguível — auto-merge
     some patrimônio, auto-soma dobra); mesmo ticker com **quantidade
     diferente** ⇒ nunca funde (flag `possivel_posicao_espelho`).
   - **Calibração herdada da [[ADR-271]]:** na dúvida, não funde → escala.
   - **Auto-resolução** (qual valor vence entre fontes valoradas) fica
     registrada como follow-up **A39** na própria ADR (padrão PR1→PR2/PR3).
3. **Semântica null-não-soma no `InvestmentsConsolidator`** (a mudança de
   maior superfície — sai primeiro nos PRs de implementação): valor `None`
   = posição **listada** em `dados` e contada em `n_posicoes`, **fora** de
   `total_por_membro`, com flag estruturada `posicao_sem_marcacao` — nunca
   0 silencioso, nunca bloqueia o relatório (degradação graciosa; card de
   alocação carrega ressalva quando houver posições sem marcação).
4. **Parsers**: carteira XLSX (openpyxl, seções por classe, checksum
   `Σ classes == total investido` em cents) e posição acionária (papel +
   quantidade; **checksum de contagem** `n_papéis` — não há valor p/
   conservação); `quantidade` no `$defs/posicao_investimento` da [[A38.l12]].
5. **Valoração emprestada** (qty × último preço de fonte valorada) **só
   depois** da regra da ADR em `main` — hard dependency: shippar valoração
   da custódia sem a regra **cria** a dupla contagem que esta lane mata.
6. **Proventos no fluxo** (aceite herdado do extrato Rico): JCP/dividendo
   creditado em conta de corretora → categoria de **proventos** (renda de
   investimento), nunca receita operacional (não pode inflar taxa de
   poupança) nem transferência interna; distinção JCP × dividendo
   preservada; TRS continua IRPF-derived (precedência extrato×IRPF é V2).

## Critério de aceite

- Golden do consolidador: (a) posição valor-null conta em `n_posicoes` e
  NÃO soma; (b) custódia qty-only + carteira valorada ⇒ total = só a
  valorada, **patrimônio não dobra**; (c) 2 fontes valoradas mesmo
  ticker+qtd ⇒ `needs_review`, nenhuma soma automática; (d) instituição
  resolvida (nunca vazia) na carteira.
- TypeRules: os 2 docs do corpus saem de conf 0.0 para ≥ 0.8 com tipo
  correto (harness [[A38.l1]]); zero mudança no corpus de classification
  existente (KR-E).
- Checksums: carteira Σclasses==total (cents); posição acionária n_papéis;
  falha ⇒ escalação (emenda [[ADR-342]] da l12).
- JCP "JUROS S/ CAPITAL" do extrato Rico → proventos; taxa de poupança
  recorrente não muda ao incluir/excluir a linha.
- ADR flippada para `Decidido (A38)` no merge; auto-resolução registrada
  como follow-up A39.

## Risco

Médio-alto (contrato E2→E4 + invariante de domínio novo). Mitigação: ordem
interna obrigatória, ADR-gated, calibração "não funde → escala", e o corpus
local como gate empírico. Reservar o ID da ADR **cedo** (sessão longa =
risco de colisão de ID).

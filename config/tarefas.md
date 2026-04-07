# Tarefas — Pipeline Ferreira Campos
## Versão: 5.3 — abr/2026

---

## Instruções

Este arquivo é o **backlog curado** de tarefas da família. Atualizado a cada ciclo pelo titular.

**Fluxo de dados:**
- `config/tarefas.md` → E5 (parser determinístico → `tarefas[]` no JSON) → E5.N (LLM enriquece/sugere) → E6 (renderiza)
- O E5.N pode sugerir novas tarefas em `tarefas_sugeridas[]` com base nos dados financeiros — o titular decide se inclui no próximo ciclo.

**Formato de cada tarefa:**

```
| # | Tarefa | Categoria | Prazo | Prioridade | Status | Ref |
```

- **#**: Número sequencial (não reordenar — manter estável para tracking entre ciclos)
- **Tarefa**: Descrição acionável e específica
- **Categoria**: Invest. | Orçamento | Tributário | Seguros | Imóveis | Financeiro | Plan. EUA | Jurídico | Sucessório | Pipeline
- **Prazo**: Data ou período (Hoje, Semana, 05/04, Abr/2026, T3/26, Antes EUA, 2027)
- **Prioridade**: S (Essencial) | R (Recomendada) | O (Opcional)
- **Status**: pendente | feito | cancelado
- **Ref**: Referência a decisão (D01, D02...) ou fonte (life_plan, methodology)

**Regras:**
- Tarefas `feito` permanecem no arquivo por 1 ciclo (para histórico), depois são movidas para "Concluídas"
- Tarefas `cancelado` são movidas imediatamente para "Canceladas" com motivo
- Novas tarefas são adicionadas ao final de cada bloco de prioridade
- O E5.N pode sugerir novas tarefas, mas elas só entram neste arquivo após aprovação do titular

---

## Essenciais (S)

| # | Tarefa | Categoria | Prazo | Status | Ref |
|---|---|---|---|---|---|
| 1 | Quitar financiamento Ed. Gisele: C6 PJ R$117.430 + CDB-DI Itaú R$117.213 | Invest. | Hoje | pendente | D01 |
| 2 | Zerar cheque especial Santander (R$291) | Orçamento | Hoje | feito | — |
| 3 | Solicitar resgate Safari 30 na Rico (~R$16.614, prazo D+60 para liquidação) | Invest. | Semana | pendente | — |
| 4 | Cancelar seguro de conta Santander (R$10/mês). Manter seguro de conta C6 (R$20/mês). | Orçamento | Semana | pendente | D08 |
| 5 | Configurar aporte R$20k/mês (dia 5): R$10k Cofrinhos Itaú + R$5k Tesouro IPCA+ + R$3k IVVB11 + R$2k Wise USD (ver Seção 3) | Invest. | 05/04 | pendente | D02 |
| 6 | Reunião AccountTech (pauta completa): (a) regularizar carnê-leão David + Mariana 2025, (b) confirmar risco multa isolada 2024, (c) DAS mensal automático dia 20 via C6 PJ, (d) parar impostos PJ por contas pessoais, (e) Simples vs LP, (f) Carnê-Leão mensal para ambos | Tributário | Abr/2026 | pendente | — |
| 7 | Cotar seguro de vida Term Life R$3-5M, 20 anos (SulAmérica, Porto Seguro, Prudential) | Seguros | Abr/2026 | pendente | — |
| 8 | Cotar seguro de invalidez (60% da renda, ~R$100-200/mês) | Seguros | Abr/2026 | pendente | — |
| 9 | CAIXA: confirmar valor do FGTS Kiwify + solicitar saque na mesma visita. Levar: RG, CPF, CTPS digital, termo de rescisão. Incluir valor no patrimônio investível. | Financeiro | Abr/2026 | pendente | — |
| 10 | Regularizar registro do Ed. Gisele no cartório (matrícula ainda no nome do antigo dono) | Imóveis | Abr/2026 | pendente | — |
| 11 | Configurar transferência automática R$5k C6 PJ → C6 PF no dia 1 de cada mês (eliminar cheque especial) | Orçamento | Abr/2026 | pendente | D14 |
| 12 | Criar login Gov.br nível Prata ou Ouro para David + Mariana (pré-requisito para Carnê-Leão Web no e-CAC) | Tributário | Abr/2026 | feito | — |
| 13 | Entregar IRPF 2026 David + Mariana (com carnê-leão de ambos regularizado antes da entrega) | Tributário | Mai/2026 | pendente | — |
| 14 | Configurar carnê-leão automático mensal David + Mariana (lançar aluguéis no Carnê-Leão Web e pagar DARF até último dia útil do mês seguinte) | Tributário | Jun/2026 | pendente | — |

---

## Recomendadas (R)

| # | Tarefa | Categoria | Prazo | Status | Ref |
|---|---|---|---|---|---|
| 15 | Vender BRKM5 (300 ações, prejuízo R$3.516). Compensar prejuízo com lucros futuros para IR. | Invest. | Abr/2026 | pendente | — |
| 16 | Crypto: vender ADA e AXS. Iniciar DCA R$500/mês (R$400 BTC + R$100 ETH) até 1% da carteira (~R$12.845). Fonte: folga mensal. | Invest. | Abr/2026 | pendente | D04 |
| 17 | Consolidar corretoras — fase 1: transferir PicPay R$53k para Cofrinhos Itaú + resgatar C6 investimentos R$2k | Invest. | Abr/2026 | pendente | — |
| 18 | Confirmar taxa real PGBL Itaú (app ou central 4004-4828). Se >1% a.a., solicitar portabilidade para BTG ou XP. | Invest. | Abr/2026 | pendente | — |
| 19 | Iniciar aportes PGBL R$1.800/mês (economia IRPF R$5.940/ano). Quanto antes, melhor. | Tributário | Abr/2026 | pendente | — |
| 20 | Solicitar avaliação do Barão de Capanema (Pça Calixto) com corretora local — pode valer R$900k-1,1M | Imóveis | Abr/2026 | pendente | — |
| 21 | Reinvestir resgate Safari 30 (~R$16.614) em IVVB11 ou ETF global (após D+60 da tarefa 3) | Invest. | Mai/2026 | pendente | — |
| 22 | Consultar 2-3 CPAs especialistas em expatriados (BR-US) para FBAR, Form 8938, Form 1040, PFIC | Trib./EUA | T3/26 | pendente | — |
| 23 | Avaliar resgate dos fundos brasileiros classificáveis como PFIC (Alaska, Constellation, Western Asset, BTG) ANTES de se tornar US tax resident — tributação punitiva nos EUA | Invest./EUA | T3/26 | pendente | — |
| 24 | Avaliar desempenho Alaska Black FIA BDR (-13,24%). Se persistir negativo, resgatar e realocar em IVVB11. | Invest. | Set/2026 | pendente | — |
| 25 | Iniciar CGFNS + TOEFL para Mariana (NCLEX). Pode ser feito do Brasil — reduz gap de renda nos EUA em 3-9 meses. | Plan. EUA | T4/26 | pendente | life_plan |
| 26 | Definir timeline F1/F2 Anderson University (semestre de início, duração, logistics) | Plan. EUA | T4/26 | pendente | life_plan |
| 27 | Iniciar processo matrícula e visto F1 (se timeline definir início em 2027) | Plan. EUA | T4/26 | pendente | life_plan |
| 28 | Procurações em cartório (mesma visita): (a) procuração pública para Rubens administrar imóveis e contas, (b) procuração duradoura David → Mariana + Rubens para emergências/incapacidade | Jurídico | Antes EUA | pendente | life_plan |
| 29 | Configurar débito automático IPTU e condomínio de todos os 7 imóveis | Imóveis | Antes EUA | pendente | — |
| 30 | Separar R$3k/mês como "reserva de desejos" da folga mensal (para compras planejadas acima de R$2k — ver Orçamento Prospectivo) | Orçamento | Abr/2026 | pendente | D13 |
| 31 | Revisar assinaturas: Gympass R$80 (usa?), Livelo Clube R$45, MeliMais R$20. Economia potencial: ~R$145/mês. | Orçamento | Abr/2026 | pendente | — |
| 32 | Seguro residencial Tasso: cotar Porto Seguro, SulAmérica, Tokio Marine (economia 20-40% vs Santander atual) | Seguros | T3/26 | pendente | — |
| 33 | Verificar vigência dos seguros veiculares (Toro + NMax) e agendar renovação antes de viajar | Seguros | Antes EUA | pendente | — |
| 34 | Após reserva emergência atingir 12 meses (R$382k), realocar os R$10k dos Cofrinhos: R$5k → reserva de oportunidade (CDB liquidez, meta R$50-80k) + R$5k → Tesouro IPCA+ 2035/2040 (contrafluxo, travar IPCA+7%) | Invest. | Jan/27 | pendente | — |
| 35 | Avaliar venda Living Concept (yield 3,2% vs CDI 13,15%). Imóvel ficou vago 7 meses em 2025. | Imóveis | 2027 | pendente | D15 |
| 41 | Atualizar cadastro e pagar anuidade do Clube de Tiro Águia de Haia | Financeiro | Abr/2026 | pendente | — |

---

## Opcionais (O)

| # | Tarefa | Categoria | Prazo | Status | Ref |
|---|---|---|---|---|---|
| 36 | Advogado sucessório/tributarista SP — contratar para testamento + holding | Sucessório | Abr/2026 | pendente | life_plan |
| 37 | Testamento público David + Mariana (cartório BR). Depende de advogado (tarefa 36) | Sucessório | Mai/2026 | pendente | life_plan |
| 38 | Atualizar beneficiários PGBL e seguro de vida | Sucessório | Abr/2026 | pendente | life_plan |
| 39 | Avaliar holding patrimonial com tributarista | Sucessório | T4/2026 | pendente | life_plan |
| 40 | Testamento americano (BR assets) + Standby Guardianship para Theo | Sucessório | Após mudança EUA | pendente | life_plan |

---

## Concluídas (histórico)

| # | Tarefa | Data conclusão | Detalhe |
|---|---|---|---|
| 2 | Zerar cheque especial Santander (R$291) | Mar/2026 | Quitado |
| 12 | Login Gov.br Prata/Ouro David + Mariana | Mar/2026 | Ambos com nível Prata ou Ouro |

---

## Notas

- **1ª semana de abril:** Tarefas #6 (AccountTech), #11 (transf. auto C6), #12 (Gov.br) são pré-requisitos para as demais e devem ser feitas primeiro.
- **Tarefas de Planejamento Sucessório (#36-40)** ficam como Opcionais no ciclo atual porque dependem de contratar advogado. Podem subir para Recomendadas após contratação.
- **Tarefas #22-23 (PFIC/CPA)** são urgentes SE a timeline F1/F2 for confirmada para 2027.

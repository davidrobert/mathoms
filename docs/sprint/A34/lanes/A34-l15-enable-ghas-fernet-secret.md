---
id: A34.l15
type: lane
title: "Habilitar GHAS + migrar Fernet dummy para secret"
sprint: A34
plan: PLAN-public-release
status: planned
priority: P1
branch_slug: enable-ghas-fernet-secret
adrs: ["[[ADR-320]]"]
depends_on: []
tags:
  - type/lane
  - sprint/a34
  - status/planned
  - priority/p1
  - area/ci
  - area/seguranca
---

# A34.l15 — `enable-ghas-fernet-secret` (W5 · Hardening)

## Problema

Repo público sem **GitHub Advanced Security (GHAS)** ativo perde a última
barreira automática contra vazamento: secret scanning + **push protection**
(bloqueia o push que introduz segredo, não só alerta depois) + code scanning
SARIF. Em repositório público a GHAS é **gratuita** — não ativá-la é deixar
proteção grátis na mesa enquanto todo o histórico já esteve exposto a Fernet
key ([[PLAN-public-release]] §Tese, camada 2).

Dois débitos concretos de CI/CD travam a superfície pública:

- **Fernet dummy inline no CI.** `ci.yml` injeta uma `MATHOMS_FERNET_KEY`
  dummy via env inline (TODO em `ci.yml:82`). Em repo público, chave de
  teste hardcoded em workflow — mesmo dummy — é ruído para o secret scanner
  e mau exemplo de referência. Deve migrar para `secrets.MATHOMS_FERNET_KEY`.
- **`.github/workflows/**` sem CODEOWNERS.** Sem dono declarado, um PR de
  contribuidor externo (agora possível em público) pode alterar workflow —
  superfície de supply-chain — sem revisão obrigatória do owner.

Complementa [[A34.l13]] (permissions read-all) e [[A34.l14]] (SHA-pin das 4
actions de terceiros); as três fecham a superfície CI/CD do gate **G5**.

## Escopo

1. **Ativar GHAS** no repo (via UI/Settings→Security, ou `gh api` quando o
   repo já for público — GHAS free depende do flag de visibilidade):
   - Secret scanning + **push protection** ligados.
   - Code scanning: workflow SARIF (CodeQL default setup **ou** upload do
     SARIF do gitleaks já existente em `security.yml`, sem duplicar scanner).
2. **Migrar Fernet dummy** de env inline para `secrets.MATHOMS_FERNET_KEY`:
   - Remover o valor dummy hardcoded referenciado no TODO `ci.yml:82`.
   - Criar o secret de repositório com uma Fernet **sintética descartável**
     (nunca a key de prod; nunca a key histórica — essa é inócua só após a
     rotação confirmada em [[A34.l3]]).
   - Job de teste continua verde consumindo o secret.
3. **CODEOWNERS** com regra cobrindo `.github/workflows/**` (e `.github/**`
   por extensão) apontando para o owner — força review em qualquer alteração
   de pipeline vinda de fora.

## Critério de aceite

- GHAS **ativa** no repo: secret scanning + push protection confirmados
  (verificável em Settings→Code security ou `gh api repos/:owner/:repo`
  campo `security_and_analysis`).
- Code scanning produz ao menos 1 análise SARIF (CodeQL ou gitleaks-SARIF)
  visível na aba Security.
- `grep -rn "MATHOMS_FERNET_KEY" .github/workflows/` **não** contém valor
  literal de chave — apenas `${{ secrets.MATHOMS_FERNET_KEY }}`; TODO de
  `ci.yml:82` removido.
- Job de CI que dependia da Fernet dummy roda **verde** com o secret.
- `.github/CODEOWNERS` contém regra que casa `/.github/workflows/` (teste:
  editar um workflow em PR de teste exige review do owner).
- Sem PII/segredo real introduzido: o secret é sintético descartável, nunca
  a key de prod nem a histórica.

## Rollback (toca CI — `CI obrigatório`)

- **Fernet secret:** reverter o step para o env inline dummy anterior
  (`git revert` do commit de `ci.yml`) restaura o job; o secret de repo pode
  ficar órfão sem efeito.
- **GHAS / push protection:** toggle reversível em Settings→Security sem
  impacto em código; desligar não altera histórico nem HEAD.
- **CODEOWNERS:** `git revert` da adição; sem estado externo.
- Nenhuma operação desta lane é destrutiva ou irreversível — toda mudança é
  config de repo ou de workflow, revertível por PR.

**GHAS free exige repo público:** o toggle de secret scanning/push protection
só fica disponível **após** o flip ([[A34.l22]]). Sequência: preparar
CODEOWNERS + migração da Fernet **antes** do flip (mergeáveis via CI normal);
ativar GHAS no pós-flip do gate **G5** / verificação **G8**. Documentar essa
dependência de ordem no PR para não bloquear a lane esperando GHAS num repo
ainda privado.

## Notas

- **Não confunde** com [[A34.l3]] (confirmar rotação Fernet em prod): l3 prova
  que a key **histórica** é inócua; esta lane só troca a **dummy de teste**
  do CI por um secret sintético — são chaves diferentes com propósitos
  diferentes.
- GHAS + push protection resolve o histórico de **budget-block** de Actions
  (minutos ilimitados em público — ver MEMORY §CI budget), removendo a causa
  de falhas de gate por billing.
- Par natural com [[A34.l13]] e [[A34.l14]] no gate **G5**; podem ser 3 PRs
  paralelos, sem `depends_on` cruzado.
- **Prioridade efetiva mista:** CODEOWNERS + migração da Fernet dummy são
  **P0 de fato** (pré-flip, entram no G5); só o *toggle* de GHAS é P1 por ser
  inerentemente pós-flip (item must do **G8** #5). A lane fica marcada `P1`
  pela dependência de ordem — mas os dois primeiros itens NÃO podem faltar no
  minuto do flip. Um orquestrador não deve deprioritizá-los pela tag P1.

## Owner

Owner do repo (GHAS toggle + criação de secret exigem permissão de admin);
lane de config, sem co-design de domínio. Conforma [[ADR-320]] (hardening
CI/CD).

## Referências

- Plano canônico: [[PLAN-public-release]] §Ondas (W5 · G5) + §KRs (KR4).
- ADR de hardening: [[ADR-320]].
- Lanes irmãs de W5: [[A34.l13]] · [[A34.l14]].
- Pré-condição Fernet histórica: [[A34.l3]] · [[ADR-171]].
- Gate de flip que ativa GHAS: [[A34.l22]] ([[TRACK-public-release-flip]]).

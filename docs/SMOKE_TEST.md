# Smoke Test — Pré-deploy

> Lista manual de 30+ verificações que DEVEM passar antes de cada deploy para produção. Complementa a suíte E2E automatizada (ver [TESTING.md](TESTING.md)).
>
> **Quando rodar:** antes de abrir PR para `main` + antes de cada deploy manual para VPS (F7).
>
> **Tempo estimado:** 20-30 minutos com tester experiente.

---

## 0. Pré-requisitos

- [ ] Backend prod-like subindo sem erro (`docker compose -f docker-compose.prod.yml up`)
- [ ] Frontend build sem errors (`npm run build`)
- [ ] `alembic upgrade head` completa sem erros
- [ ] Health check retorna 200: `curl http://localhost:8000/health`

---

## 1. Auth & onboarding

- [ ] **Registro novo** com email único funciona → redirect para `/plano`
- [ ] **Registro duplicado** mostra mensagem "Email já cadastrado" (não HTTP 409)
- [ ] **Registro com senha <6** é bloqueado pela validação HTML5
- [ ] **Login** com credenciais corretas → redirect para `/plano`
- [ ] **Login com credenciais erradas** → "Email ou senha incorretos"
- [ ] **Logout** limpa `localStorage.fin_token` E redireciona para `/login`
- [ ] **Paleta de comandos** abre com **⌘K** / **Ctrl+K** e navega para uma rota
- [ ] **Ajuda de atalhos** abre com **?** fora de campos de texto
- [ ] **Acesso a `/plano` sem token** redireciona para `/login`
- [ ] **Token inválido** (cookie corrompido) faz logout automático
- [ ] Link "Criar conta" em `/login` leva para `/register` e vice-versa

## 2. Config workspace

- [ ] Tab `Membros` carrega lista vazia sem crash
- [ ] Definir "Sobrenome da família" persiste (reload confirma)
- [ ] Criar novo membro (key, nome, role=titular) salva
- [ ] Export JSON (`GET /config/export`) retorna payload válido com todos os campos
- [ ] Tabs `Categorias`, `Pipeline`, `LLM`, `Instituições`, `Layout`, `Import/Export` carregam sem erro

## 3. Documentos & vault

- [ ] Upload PDF (sem senha) → status vai para `ready`
- [ ] Upload PDF **com senha** + vault vazio → status `needs_password`
- [ ] Adicionar senha ao vault + `Tentar desbloquear` → doc muda para `ready`
- [ ] Delete document → confirma via dialog → remove da lista
- [ ] Upload batch (5+ arquivos) mostra progress bar corretamente
- [ ] Arquivo >50MB é rejeitado com erro amigável

## 4. Pipeline

- [ ] Trigger pipeline em free tier usa `skip_llm=true` (DevTools Network)
- [ ] Trigger em premium tier (LLM configurado) usa `skip_llm=false` (**BUG-007 regression**)
- [ ] Stepper mostra **4 fases narrativas** (`Preparando`, `Lendo`, `Organizando`, `Montando`) — não códigos `E*` (**ADR-068 regression**)
- [ ] Código técnico `[E3]` aparece só em disclosure técnico ("Ver detalhes técnicos")
- [ ] WebSocket conecta (status "connected" em DevTools WS tab)
- [ ] Pipeline termina → toast "Relatório gerado com sucesso"
- [ ] Cancel mid-stage muda status para `cancelled`
- [ ] Pipeline failed mostra mensagem de erro user-friendly (não stack trace)
- [ ] **Incremental (ADR-080):** Upload 2 docs → run pipeline → upload 1 doc novo → página Pipeline mostra "1 novo(s) desde última execução"
- [ ] Botão "Processar 1 novo(s)" aparece como primary, "Processar todos (3)" como secondary
- [ ] Run incremental: DevTools Network mostra `{ incremental: true }` no body do POST
- [ ] Após run incremental, contagem de novos volta a 0

## 5. Relatório

- [ ] `/reports` lista reports mais recentes primeiro
- [ ] Click em card de report abre `/reports/{id}` com iframe carregado
- [ ] HTML do report contém `{{COVER_FAMILIA}}` renderizado com o sobrenome (**BUG-015 regression**)
- [ ] Nome do arquivo do report inclui o family_surname
- [ ] Print preview (Ctrl+P) formata corretamente (`@media print` ativa)
- [ ] Download HTML funciona
- [ ] Export tables (CSV/XLSX) de seção específica funciona

### 5.1 Entrega impressa / PDF (F11.3)

- [ ] Relatório nativo (`/reports/[id]`): preview de impressão oculta sidebar/TOC/header de ação (`@media print`)
- [ ] Tipografia em impressão: valores monetários em monoespaçado; corpo legível em A4
- [ ] Quebras: cartões e gráficos não ficam cortados ao meio entre páginas (evitar `break-inside` onde aplicável)
- [ ] Download PDF server-side (`/download.pdf`) abre sem erro quando Playwright/Chromium configurado no backend
- [ ] Capa/hero do PDF reflete período do snapshot e título do relatório (mesmo que tela)

### 5.2 Report Premium UI smoke (humano · pós-Fase 10)

> Pré-condição: workspace com pelo menos 1 relatório gerado (run completa
> até E5). Modos `estrategico`/`tatico`/`usa` ativos desde F4 (commit
> `a3411e6`); a11y automatizada chega via lane
> [`report-a11y-finalize`](BACKLOG.md#lanes-abertas-agora--pickup-table) —
> até lá esta seção é checklist humano provisório.

**Modos**

- [ ] `/reports/<id>?mode=estrategico` carrega seções S1–S10 visíveis
- [ ] `/reports/<id>?mode=tatico` carrega seções T1–T6 visíveis
- [ ] `/reports/<id>?mode=usa` carrega seções U1–U4 visíveis
- [ ] Toggle de modo no header preserva o hash atual (abrir em `#S3`,
      trocar modo, hash continua `#S3` ou equivalente do novo modo)
- [ ] Modo inválido na URL (`?mode=foo`) → fallback silencioso para
      `estrategico` (sem crash, sem página em branco)

**Tema**

- [ ] Light/dark toggle persiste após reload (chave
      `mathoms.report.theme` em localStorage)
- [ ] Cores monetárias respeitam tema em ambos os modos (positivo/negativo
      legíveis em dark e light)
- [ ] Print mode (`?print=1`) força light mesmo com `theme=dark` salvo

**Print / PDF**

- [ ] `Ctrl+P` (ou `?print=1`) oculta TopNav, FloatingNav e ExportToolbar
- [ ] Quebras de página: gráficos S2/S5 não cortam ao meio
- [ ] Cabeçalho de família + número de página aparecem em todas as páginas
- [ ] PDF via `GET /v1/reports/<id>/download.pdf` (Playwright) sai em A4,
      hero ocupa 1ª página, KPIs em monoespaçado (JetBrains Mono)

**Colaboração (notas + kanban — ADR-123)**

- [ ] Notas em qualquer seção persistem no localStorage **e** sincronizam
      via `reports_collab` API; recarregar página mantém conteúdo
- [ ] Kanban em T6 permite mover card entre colunas (botões — DnD real
      é débito consciente, ver BACKLOG)
- [ ] Limpar `localStorage` (`mathoms.report.*`) não apaga notas
      server-side (precisa endpoint `DELETE /v1/reports/<id>/collab/*`)
- [ ] Logout zera UI local; novo login carrega notas do servidor

**Lineage / consolidação**

- [ ] `ReportSourceStrip` no header mostra "Consolidado de N documentos"
      coerente com o que o workspace tem em `/documents`
- [ ] Apêndice A lista runs do pipeline (timestamps + stages executados)
- [ ] Apêndice E (changelog) renderiza vazio se feature flag
      `enabled: false` no `report_layout.yaml` — não quebra layout

**Navegação**

- [ ] FloatingNav mostra seções do modo ativo (não vaza T-/U- no
      `estrategico`)
- [ ] Click em item da TOC ancora suavemente na seção
- [ ] FontScaleToggle (header) ajusta tipografia globalmente; persiste

## 6. Dashboard & Transactions

- [ ] Dashboard carrega KPIs (Receitas, Despesas, Saldo, Score)
- [ ] Dashboard mostra empty state quando não há análise
- [ ] Click em categoria no pie chart → redireciona para `/transactions?category=X`
- [ ] Click em mês no bar chart → `/transactions?date_from=...&date_to=...`
- [ ] Transactions page: busca por termo funciona
- [ ] Transactions page: filtro por banco funciona
- [ ] Category override inline persiste após refresh
- [ ] Export CSV de transactions filtradas vem com BOM UTF-8 e delimitador `;`

## 7. Segurança

- [ ] Transação com `<script>alert(1)</script>` na descrição **não executa** (XSS smoke)
- [ ] Member com `<img onerror>` no nome renderiza escapado
- [ ] Vault label com HTML é sanitizado
- [ ] localStorage APÓS logout tem zero tokens/secrets
- [ ] JWT expirado mid-session → próxima call 401 → redirect `/login`

## 8. Multi-tenant (**roleta russa sem isso**)

- [ ] User A registra → User B registra → A não vê dados de B em /documents
- [ ] A não vê reports de B em /reports
- [ ] A não vê members de B em /config
- [ ] A tenta DELETE `/documents/{id_de_B}` → retorna 404 (não 403 que vaza existência)
- [ ] A tenta PATCH `/config/workspace` do tenant de B → impossível (workspace scoped por owner_id)

## 9. Performance & UX

- [ ] Home page / login carrega em <2s (3G throttled DevTools)
- [ ] LCP em `/plano` (home) é <2.5s
- [ ] LCP em `/dashboard` com KPIs é <2.5s
- [ ] Dark mode toggle funciona + persiste após reload
- [ ] Sidebar mobile (<1024px) abre via menu hambúrguer
- [ ] Todos os botões que disparam API têm loading state (disabled + spinner)
- [ ] Todas as empty states têm CTA acionável (ADR-063)
- [ ] Focus management: modal close retorna foco para trigger

## 10. Resilience

- [ ] Backend 502/503 mostra toast amigável, não Error genérico
- [ ] WS drop força fallback para polling após 3 tentativas
- [ ] `navigator.onLine=false` mostra banner "Sem conexão" (F7)
- [ ] Slow 3G não trava UI (skeletons visíveis durante loading)

## 11. Acessibilidade (axe-core)

- [ ] `/login` passa axe (0 violations critical/serious)
- [ ] `/plano` passa axe (0 violations critical/serious)
- [ ] `/dashboard` passa axe (0 violations critical/serious)
- [ ] `/documents` com docs listed passa axe (incluindo botões delete com aria-label)
- [ ] Navegação completa via teclado (Tab) funciona em todas as pages

## 12. LGPD pré-beta

- [ ] Nenhum dado real em `frontend/tests/mocks/fixtures.ts` (CPFs = placeholder)
- [ ] Nenhum PDF real em `tests/fixtures/pdfs/` (só sintéticos de `pdf_generator.py`)
- [ ] PDFs “reais” só em `tests/fixtures/e2_real_pdf_anon/`, **totalmente redigidos** e com nome canônico — ver README da pasta (Fase 2 opcional)
- [ ] `python tests/utils/lint_no_real_pii.py` retorna green
- [ ] `config/family_members.json` do projeto contém dados reais do founder (**OK — não é fixture; neutralizado via API pela 6.5E.6**)
- [ ] Fernet key (`MATHOMS_FERNET_KEY`) está persistida em `.env` (nunca commitada)
- [ ] `DELETE /api/account` (F7) remove TODOS os dados do user (cascade no DB + storage)

## 13. Observabilidade (F7)

- [ ] Sentry recebe evento de erro teste (backend + frontend)
- [ ] Logs estruturados (structlog JSON) em prod mode
- [ ] UptimeRobot pinga `/health` e fica green

---

## Resultado

- **Deploy OK?** Todos os checks acima ✅ + suíte E2E verde + Golden Path verde.
- **Rollback triggers** (não deploy):
  - Qualquer item da seção **1. Auth & onboarding** falha
  - Qualquer item da seção **8. Multi-tenant** falha (vazamento = incidente de segurança)
  - **BUG-015 regression:** cover do relatório sem family_surname
  - **BUG-007 regression:** premium tier enviando `skip_llm=true`
  - **ADR-068 regression:** códigos `E*` vazando na UI

## Histórico

| Data       | Versão | Executado por | Resultado | Notas            |
| ---------- | ------ | ------------- | --------- | ---------------- |
| YYYY-MM-DD | v1.0.0 | @founder      | ☐ Pass    | Dogfood inicial  |

---

## Ver também

- [`TESTING.md`](TESTING.md) — guia de contribuidor de testes
- [`BACKLOG.md#f65`](BACKLOG.md#f65--frontend-testing--qa) — status da F6.5
- [`DECISIONS.md#adr-063`](DECISIONS.md#adr-063--hardening-fintech-em-sub-fase-65d) — ADR Hardening Fintech
- [`DECISIONS.md#adr-068`](DECISIONS.md#adr-068--códigos-internos-do-pipeline-nunca-vazam-na-ui) — ADR Phases narrativas

# Brief de decisão — Gate G0 (W0) do repo público

> **Anexo do plano [[PLAN-public-release]]** (mesmo padrão do
> [audit-2026-07-08.md](audit-2026-07-08.md)). Material de leitura única
> para a sessão de decisão do owner: consolida as 6 ADRs owner-gated
> (313–318), o checklist G0 e o pré-mortem da operação irreversível (W3).
> **As decisões são assinadas nas próprias ADRs** (flip `Proposto` →
> `Decidido` com texto datado); o §6 aqui é só o registro da sessão.
> Preparado em 2026-07-09; conteúdo fiel às ADRs — em divergência, a ADR
> vence.

## 0. O que está sendo decidido (e o que não está)

**Sendo decidido (6 ADRs owner-gated):** licença ([[ADR-313]]) · escopo
público de IP ([[ADR-314]]) · estratégia de rewrite de histórico
([[ADR-315]]) · aceite de risco de metadados OU repo novo ([[ADR-316]]) ·
identidade de autoria no mailmap ([[ADR-317]]) · fronteira de idioma
([[ADR-318]]).

**Já decidido — não reabrir:** [[ADR-319]] (gates anti-regressão PII/sigilo)
e [[ADR-320]] (hardening CI/CD + EXEMPLO sintético) são técnicas, fechadas
pela síntese do co-design e já `Decidido (A34)`.

**Confirmações operacionais que também travam G0** (assinadas dentro da
ADR-315): backup mirror off-site + tag `pre-public-flip-backup`
([[A34.l2]]) · rotação Fernet em prod com `old_key_decryptable=0`
([[A34.l3]]) · aprovação da janela de FREEZE (W3→W8).

**Custo de errar:** das 6, duas são efetivamente permanentes (§1 e §2.3/§2.4)
— por isso o formato pré-mortem. As ondas W2/W1/W5 já estão em `main`;
nada do trabalho já feito é perdido por nenhuma das escolhas abaixo.

## 1. Decida PRIMEIRO: [[ADR-316]] — in-place × repo novo (o nó central)

Esta escolha condiciona todo o resto: **Opção 1 (in-place)** mantém W3
(rewrite) e W4 (triagem de metadados); **Opção 2 (repo novo)** elimina as
duas e reabre [[ADR-314]]/[[ADR-315]].

| | Opção 1 — in-place + aceite T3 | Opção 2 — repo público novo |
|---|---|---|
| Metadados (855 PRs/issues/logs) | **Risco residual permanente**: cache de commits referenciados por PRs continua servível; purga total só via ticket ao GitHub Support (manual, sem prazo garantido) | **Zero-risco imediato** — nada dos metadados existe no repo novo |
| Rewrite de histórico (W3) | Necessário — operação **irreversível**, bypass de Ruleset, FREEZE de merges | **Dispensado** — push do HEAD já saneado |
| Custo operacional | Triagem T1 (~15 itens) + ticket Support | Recriar config: Ruleset, environment `production` + secrets/chaves LLM, 30 labels, Projects, Actions/GHAS, re-autorizar GitHub App de deploy — **maior risco: errar o re-aponte do deploy quebra produção no cutover** |
| O que NÃO muda | W0, W1, W2, W5, W6, W8 acontecem igual nas duas opções | idem |

**Objeção registrada (4 dos 5 especialistas):** in-place é
arquiteturalmente inferior para a Camada 3, e o repo privado nunca teve
tráfego externo (0 fork, 1 star, 0 watcher) — o custo-benefício do
in-place é fraco. **Cláusula lógica da ADR:** se você exige zero-risco em
metadados, o flip in-place é incompatível por construção — decida isso
aqui, não em W8 depois de gastar W3.

**Pré-mortem:** *"6 meses após o flip, alguém encontra dado sensível…"* —
na Opção 1, o vetor mais provável é o cache de PR pré-rewrite (mitigável
só via Support); na Opção 2, o vetor é erro humano na recriação de config
(mitigável com checklist e verificação G8). Escolha qual classe de risco
você prefere operar.

## 2. As outras 5 decisões

### 2.1 [[ADR-313]] — Licença (semi-irreversível)

**Pergunta:** qual licença? Sem `LICENSE`, repo público é
all-rights-reserved de fato — o default é destrutivo para contribuição.
**Leading:** BSL 1.1 source-available (uso não-comercial/dev/avaliação/
self-host individual liberados; vedado operar como serviço a terceiros;
Change License Apache-2.0 em 4 anos rolantes). **Alternativas:** AGPL-3.0
(pureza OSS > proteção comercial) · Apache/MIT (só se "referência
open-source" for alavanca validada — hoje não é, ver §4).
**Reversibilidade:** revogar permissão de quem já clonou é impraticável —
barato mudar antes do flip, caro depois. **Risco dominante:** BSL não é
OSI-aprovada — README diz "source-available", não "open source"; narrar
mal gera atrito reputacional. **Nota:** requer revisão jurídica antes de
assinar.

### 2.2 [[ADR-314]] — Escopo público de IP (define o superset)

**Pergunta:** por categoria, o que vai público / redigido / privado?
**Leading por categoria:** prompts de produto → **split privado** (stub
sintético público, injeção build-time); plano competitivo → **mover para
privado**; pricing → **genericizar em faixas**; diagnósticos de dogfood →
**anonimizar** (já coberto por W1). **Reversibilidade:** re-triagem cara
depois do flip — o superset definido aqui é o que os gates da ADR-319
protegem. **Risco dominante:** prompts são o moat e citam fontes
metodológicas nominalmente (marca de terceiro sem licença); split
introduz custo de manutenção de paridade stub↔real. **Depende de:** a
execução fina é da [[A34.l12]]; reaberta se §1 = Opção 2.

### 2.3 [[ADR-315]] — Estratégia de rewrite (IRREVERSÍVEL; dispensada se §1 = Opção 2)

**Pergunta:** aprovar `git-filter-repo` em clone `--mirror`, passada única
(paths → replace-text → replace-message → mailmap), validação dupla
gitleaks (árvore E histórico = 0), e a janela de FREEZE W3→W8?
**Alternativas rejeitadas na ADR:** BFG (não cobre mensagens/mailmap) ·
squash-to-genesis (destrói arqueologia) · shallow-truncate (blobs
recuperáveis). **Reversibilidade:** nenhuma após o force-push — o estado
anterior só existe no backup off-site (retenção ≥30d). **Pré-mortem — o
force-push só acontece com TODOS verdadeiros:**

- [ ] Backup mirror off-site íntegro e **testado com clone de verificação** ([[A34.l2]])
- [ ] Tag `pre-public-flip-backup` no HEAD de `main`
- [ ] Fernet rotacionada em prod: `old_key_decryptable=0` ([[A34.l3]]) — sem isso, o blob histórico é abrível
- [ ] FREEZE anunciado; zero PR aberto; 85 branches `agent/*` deletadas ([[A34.l19]])
- [ ] `.mailmap` exaustivo, revisado pelo owner, mantido **fora do repo** (o lado-origem é PII)
- [ ] Validação dupla gitleaks no mirror reescrito = 0 achados (árvore + histórico completo)
- [ ] Plano de reativação do Ruleset `main-protection` verificado ([[A34.l20]])
- [ ] Rollback entendido: **não existe** — só restauração do backup

### 2.4 [[ADR-317]] — Identidade de autoria no mailmap (irreversível pós-flip)

**Pergunta (duas escolhas):** (a) os 813 commits com e-mail Gmail pessoal
viram o quê? **Leading:** `noreply` do owner com nome de exibição estável
(preserva crédito sem expor Gmail); alternativas: identidade de organização
(perde crédito individual) · manter Gmail (correlaciona persona real com
todo o timeline — incoerente com KR1). (b) trailers `Co-Authored-By` de
agente: **leading** preservar (transparência do fluxo assistido).
**Reversibilidade:** corrigir depois = novo rewrite completo.
**Risco dominante:** mailmap não-exaustivo deixa endereço passar intacto —
o smoke de G8 grepa o Gmail em `git log` de todas as refs e falha se achar.

### 2.5 [[ADR-318]] — Fronteira de idioma (reversível)

**Pergunta:** aprovar EN só na apresentação pública (README, CONTRIBUTING,
LICENSE, SECURITY, CoC) com vault 100% PT-BR, fronteira path-baseada?
E confirmar que docs-EN **não** sinaliza intenção de mercado internacional
do produto (produto-i18n segue `paused`). **Alternativas rejeitadas:**
traduzir o vault (~300 docs, quebra wikilinks) · superfície EN sem
fronteira formal (erosão por osmose) · incluir pt-PT (unânime contra).
**Reversibilidade:** baixa — nenhum id/filename/wikilink muda. É a decisão
mais barata das 6; não gaste mais que minutos nela.

## 3. Ordem recomendada da sessão (~1-2h)

1. **§1 (ADR-316)** — 30min. Se Opção 2, a sessão encurta: pule 2.3 e a
   triagem W4; ADR-314/315 voltam para redesenho antes de reagendar.
2. **§2.3 (ADR-315)** + confirmações operacionais — 20min (só se Opção 1).
3. **§2.1 (ADR-313)** — 20min + encaminhar revisão jurídica.
4. **§2.2 (ADR-314)** — 15min (a execução fina fica na [[A34.l12]]).
5. **§2.4 (ADR-317)** — 10min. **§2.5 (ADR-318)** — 5min.

## 4. Objeção de GTM registrada (ler antes de assinar qualquer uma)

*"Ser referência open-source" não é alavanca GTM validada para o ICP* —
público que admira ≠ público que paga. Se o objetivo real do repo público
é transparência metodológica para confiança do cliente, um **whitepaper
público** resolve sem expor o motor competitivo (caminho complementar
registrado na [[ADR-314]] como opção D). Antes do flip, articule em uma
frase **qual objetivo de negócio o repo público serve** (recrutamento?
investidores? contribuidores?) — se a frase não sair, o flip pode esperar;
as ondas já mergeadas (gates + saneamento + hardening) valem por si como
higiene, independente do flip.

## 5. Checklist G0 (critério de aceite do gate)

- [ ] 6 ADRs (313–318) mergeadas com decisão textual datada do owner
- [ ] Aceite de risco de metadados assinado ([[ADR-316]] Opção 1) **OU** restrição in-place reaberta (Opção 2)
- [ ] Backup mirror restaurável + tag `pre-public-flip-backup` ([[A34.l2]])
- [ ] Fernet: `rotate_fernet_secrets.py` com `old_key_decryptable=0` ([[A34.l3]])

## 6. Registro da sessão de decisão

| ADR | Decisão | Data | Registrado por |
|---|---|---|---|
| [[ADR-316]] in-place × repo novo | | | |
| [[ADR-315]] rewrite + FREEZE | | | |
| [[ADR-313]] licença | | | |
| [[ADR-314]] escopo IP | | | |
| [[ADR-317]] mailmap | | | |
| [[ADR-318]] idioma | | | |

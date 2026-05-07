---
id: ADR-081
type: adr
title: "Classificação de documentos unificada (P2)"
status: Decidido
date: "2026-04-17"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 081"]
tags:
  - area/llm
  - area/pipeline
  - phase/f11-4a
  - status/decidido
  - type/adr
size_lines: 31
---

# ADR-081 — Classificação de documentos unificada (P2)

**Status:** Decidido • **Data:** 2026-04-17

**Contexto:** O backlog P2 exige eliminar drift entre classificação no upload web, no pipeline (E0-route) e em reclassificação manual. Antes desta ADR, a lógica já era majoritariamente compartilhada via ``classify_document`` em ``document_processor.py``, mas o contrato não estava formalizado e o roteamento por nome (CLI sem backend) era um segundo caminho.

**Decisão:**

1. **Módulo único** ``backend/app/services/document_classification.py`` expõe:
   - ``classify_document(path, base_dir, use_llm=…) -> dict`` — regex sobre preview de conteúdo → LLM opcional → ``needs_review`` se confiança < 0,7;
   - ``ClassificationResult`` (Pydantic) com ``.as_dict()`` compatível com o formato histórico;
   - ``classification_can_route_to_data(dict)`` — gate para mover inbox → ``data/`` (exige ``dest_group`` + ``e0_doc_type`` e ``needs_review=False``);
   - ``map_e0_doc_type_to_document_type`` — mapa códigos E0 → ``DocumentType`` API.
2. **Entradas:**
   - **Upload web:** ``process_uploaded_document`` chama o classificador após unlock; JSON E1/E1.5 seguem detector estrutural (fora do classificador de PDF).
   - **Batch / inbox (``data/`` via CLI):** ``scripts/e0_route.route_file`` usa o **mesmo** ``classify_document`` quando o pacote ``backend`` é importável; caso contrário, fallback **filename regex + LLM** (legado documentado).
   - **Reclassificação:** ``POST /workspaces/.../documents/reclassify`` e ``backend.app.scripts.reclassify_documents`` chamam o mesmo ``classify_document``.
3. **LLM:** participa só como fallback quando a camada regex tem confiança < 0,8 e credenciais existem; erros de API são classificados (P1.4) em transiente/permanente no ``classification_meta``.
4. **Compatibilidade:** ``canonical_routing.rename_to_canonical`` / ``route_inbox_to_canonical_data`` continuam a receber o dict de classificação; ``POST`` de correção manual (tipo/banco) permanece o fluxo de ajuste quando a UI marca incerteza (P2.4).
5. **Paridade nome canônico:** testes garantem que ``build_final_name`` + ``classify_by_name`` reproduzem ``institution`` e ``doc_type`` para padrões representativos (evita drift pasta ↔ basename).

**Consequências:**

- ✅ Um lugar para evoluir limiares e meta de classificação.
- ✅ E0-route alinhado ao upload quando o worker/CLI roda com venv do projeto.
- ⚠️ CLI totalmente offline sem pacote ``backend`` mantém comportamento por nome — documentado como fallback.
- ❌ Linhagem por ``document_id`` por seção de relatório não é escopo desta ADR (F11.4a).

**Refinamento (2026-04-23):** exports de corretoras (Rico/XP) frequentemente vêm nomeados ``*_extratoconta_*`` mas o conteúdo é dashboard de posição de investimentos, sem transações. Sem guard, isso cai em ``extratoconta`` → parser E2 roda → 0 transações → ERROR espúrio. Adicionada regra determinística em ``content_classifier.py`` (``_maybe_apply_investment_override``): filename contém ``extratoconta`` **E** conteúdo tem ≥3 marcadores de investimento (posição a mercado, fundos, renda variável, rentabilidade, tickers B3, Tesouro Direto, proventos, alocação) **E** zero marcadores de extrato bancário (saldo anterior, lançamentos, TED/PIX, agência+conta) ⇒ reclassifica como ``investimentosposicao`` com ``force_review=True`` (gera ``needs_review=true`` para revisão humana). Confidence 0.85 para pular o LLM fallback. É um *refinamento* do ADR-081, não uma reversão — filename entra **apenas como guard** quando o conteúdo é ambíguo; a regra ainda é content-first.

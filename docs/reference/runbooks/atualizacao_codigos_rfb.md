# Runbook — Atualização anual dos códigos RFB do e16

> **ADR:** [[ADR-137]] (config versionada fora de prompt) · [[ADR-307]]
> (cache LLM por hash de conteúdo) · lane [[A33.l8]]
> (W4-T02 do [[PLAN-llm-prompts-hardening]]).
> **Owner:** Engenharia (qualquer dev via PR-flow; sem ação de infra).
> **Janela alvo:** ~1h, sem downtime — mudança de config versionada em git.

## Quando usar

- **Todo fevereiro**, quando a Receita Federal publica o Manual de
  Preenchimento DIRPF do novo exercício (ano-base = ano-calendário anterior).
- Fora de época: quando declaração real trouxer código RFB relevante caindo
  no fallback `99_outro` (sinal: `needs_review` recorrente no E1.6).

## Contexto

O stage `extract_irpf_full` (E1.6) injeta as tabelas código→categoria no
**user prompt** a partir de `config/prompts/e16_codigos_rfb_<ano_base>.yaml`
(loader: `pipeline/llm/rfb_codes.py`). Seleção de ano: hint do filename da
declaração se houver YAML correspondente; senão o ano-base mais recente
disponível. Sem nenhum YAML, o loader falha-fast.

Editar/adicionar YAML **não** exige bump de `PROMPT_VERSION` — o cache LLM
(ADR-307) usa hash do conteúdo do prompt, que já muda com o YAML.

## Fonte

Manual de Preenchimento DIRPF do exercício corrente (Receita Federal —
busca: "Manual DIRPF <exercício>") + "Perguntão IRPF" do mesmo exercício.
Fichas relevantes:

1. Rendimentos Isentos e Não Tributáveis
2. Rendimentos Sujeitos à Tributação Exclusiva/Definitiva
3. Pagamentos Efetuados (códigos e tetos — ex.: teto de educação muda de valor por ano)

## Passos

1. Copie o YAML do ano anterior:

   ```bash
   cp config/prompts/e16_codigos_rfb_<ano-1>.yaml config/prompts/e16_codigos_rfb_<ano>.yaml
   ```

2. Atualize `ano_base`, `fonte` e os valores year-specific (teto de educação
   em `pagamentos_efetuados."11"`, novos códigos, descrições alteradas).
3. Confira código a código contra as 3 fichas do Manual DIRPF. **Não invente
   código** — só o que consta na fonte oficial.
4. Código novo que mereça categoria própria (não `99_outro`): os enums em
   `pipeline/llm/schemas/e16_irpf_full.py` precisam crescer — isso é schema
   change (`PROMPT_VERSION` bump + goldens) e sai do escopo deste runbook;
   abra lane dedicada.

## Validação

1. Loader + render local:

   ```bash
   python3 -c "from pipeline.llm.rfb_codes import load_rfb_codes, render_rfb_codes_block; print(render_rfb_codes_block(load_rfb_codes(<ano>)))"
   ```

2. Suíte do loader: `pytest tests/unit/pipeline/test_rfb_codes.py -q`.
3. Pós-merge, rode uma declaração do novo exercício em staging e confira no
   payload E1.6 que `rendimentos_isentos`/`pagamentos_efetuados` não caem em
   `99_outro` para códigos previstos.

## Rollback

Reverter o PR basta: sem o YAML do ano novo, `resolve_rfb_codes` volta ao
ano-base mais recente remanescente. Nenhum flush de cache LLM é necessário
(prompt novo = cache key nova; entradas antigas expiram sozinhas).

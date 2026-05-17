# Mathoms AI — Produto

> Documento de produto. Evergreen. Atualizar só quando visão/estratégia mudar.

---

## 1. Visão

**Mathoms AI** é um planejador financeiro pessoal inteligente que consolida automaticamente extratos, faturas, investimentos e declarações de IRPF de múltiplos bancos brasileiros, gerando um relatório profissional unificado com score financeiro, análise patrimonial, fluxo de caixa e recomendações.

### Proposta de valor

> "Envie seus PDFs bancários. Receba um retrato financeiro completo da sua família em minutos — não em semanas de planilha."

---

## 2. Público-alvo

| Segmento           | Perfil                                                          | Dor principal                                          |
| ------------------ | --------------------------------------------------------------- | ------------------------------------------------------ |
| **Primário**       | Profissionais PJ/CLT alta renda, múltiplas contas               | Não conseguem ver o retrato completo das finanças      |
| **Secundário**     | Famílias com patrimônio diversificado (imóveis + investimentos) | Consolidação manual em planilha demora dias            |
| **Futuro (B2B2C)** | Planejadores financeiros independentes                          | Ferramenta white-label para atender clientes           |

---

## 3. Diferenciais competitivos

1. **Parsers nativos para bancos BR** — não depende de Open Banking (ainda limitado no Brasil)
2. **Consolidação multi-banco, multi-membro** — visão família, não indivíduo
3. **IRPF-aware** — cruza dados fiscais com patrimoniais
4. **LLM-augmented** — extrai documentos sem parser determinístico via fallback inteligente (E1, E1.5, E2-llm, E6-parecer)
5. **Relatório com narrativa** — não é só número, é contexto e recomendação

---

## 4. Modelo de negócio

| Camada       | O que é                                                                   | Modelo                   |
| ------------ | ------------------------------------------------------------------------- | ------------------------ |
| **Free**     | Pipeline determinístico completo (E0→E7, sem LLM). Relatório sem review.  | Gratuito                 |
| **Premium**  | LLM stages habilitados (E1, E1.5, E2-llm, E6-parecer). Parecer holístico do planejador.   | BYOK (Bring Your Own Key) |

**BYOK = user traz sua própria API key** (Anthropic, OpenAI, Ollama, etc. via LiteLLM).
- Zero custo para a plataforma
- User controla provedor/modelo
- Token tracking + cost estimation por call

Billing próprio (Stripe) está adiado para pós-launch. Ver [ROADMAP.md](../_MOC/_generated/ROADMAP.md).

---

## 5. Estratégia de lançamento

| Estágio         | Quem                                  | Critério de passagem                                                              |
| --------------- | ------------------------------------- | --------------------------------------------------------------------------------- |
| **Dogfood**     | 1 user (founder)                      | Refinar até estar perfeito antes de abrir                                         |
| **Beta fechado**| Família + 2-3 convidados (5 users)    | Onboarding sem suporte, latência p95 <1s, LGPD verificado                         |
| **GA**          | Público                               | Landing page + demo mode + billing (se aplicável). Suporte básico (FAQ, email).   |

---

## 6. Métricas de sucesso

### De produto (longo prazo)

| Métrica                | Meta 3 meses | Meta 6 meses | Meta 12 meses |
| ---------------------- | ------------ | ------------ | ------------- |
| Usuários registrados   | 1 (dogfood)  | 10 (beta)    | 100           |
| Relatórios gerados/mês | 2            | 20           | 200           |
| Bancos suportados      | 11           | 15           | 20+           |
| MRR                    | R$0          | R$0          | R$2.000+      |

### De qualidade (pipeline)

| Métrica                         | Meta                              |
| ------------------------------- | --------------------------------- |
| Pipeline premium sem intervenção| >95% runs sem erro                |
| Latência end-to-end             | <5min (parser det.) / <15min (LLM)|
| Accuracy de categorização       | >90% transações corretas          |
| Uptime produção                 | >99.5%                            |

Métricas de engenharia (coverage, CI gates, etc.) estão em [ROADMAP.md](../_MOC/_generated/ROADMAP.md).

---

## 7. Decisões estratégicas-chave

| Decisão                | Escolha                                  | Rationale                                                                              |
| ---------------------- | ---------------------------------------- | -------------------------------------------------------------------------------------- |
| Modelo de negócio      | **Freemium**                             | Free = pipeline determinístico. Premium = LLM + features avançadas                     |
| Primeiro cliente       | **Dogfood (founder)**                    | Refinar até estar perfeito antes de abrir                                              |
| LLM strategy           | **BYOK (Bring Your Own Key)**            | Zero custo para plataforma. User paga direto ao provedor                               |
| Pricing                | **Pendente**                             | Definir antes do GA (pós-beta)                                                         |

Decisões técnicas (stack, arquitetura) estão em [DECISIONS.md](../DECISIONS.md).

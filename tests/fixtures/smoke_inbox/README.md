# smoke_inbox — Fixtures para Smoke Test (A6b.5)

Arquivos sintéticos para o teste humano de A6b. Copiados para o inbox de cada
workspace pelo `seed_smoke.py`. Não contêm dados financeiros reais.

## Arquivos

| Arquivo | Tipo | Cenário |
|---------|------|---------|
| `c6bank_extratoconta_202501-smoke.csv` | Extrato C6 (CSV) | Parser determinístico |
| `c6bank_extratoconta_202502-smoke.csv` | Extrato C6 (CSV) | Segundo mês consecutivo |
| `c6bank_extratoconta_202501-smoke_dup.csv` | Extrato C6 (CSV) | **Duplicata** do 202501 — mesmo conteúdo |
| `nubank_extratoconta_202501-smoke.csv` | Extrato Nubank (CSV) | Parser Nubank |
| `nubank_faturacartao_202501-smoke.csv` | Fatura Nubank (CSV) | Parser de faturas |
| `life_plan_goals.md` | Plano de vida | Metas / independência financeira |
| `ambiguous_document-smoke.txt` | Ambíguo | Deve gerar `needs_review=true` |

## Cenários cobertos

- Upload e classificação automática (regex content-first)
- Deduplicação exata (mesmo SHA-256 → bloqueado na 2ª vez)
- Deduplicação fuzzy (mesmo tipo/banco/período, hash diferente)
- Documento ambíguo (`needs_review=true`)
- Extrato com período completo (E2 determinístico)
- Fatura de cartão (E2 determinístico)
- Plano de vida copiado para config do workspace

## Arquivos que precisam ser adicionados manualmente (não automatizáveis)

Estes arquivos **não são gerados automaticamente** por limitações técnicas
(conteúdo real ou ferramentas de criação de PDF/XLSX necessárias):

- PDF protegido por senha → testar E0-unlock
- XLSX de banco → testar parser XLSX do Itaú/Santander
- IRPF simulado → testar E1.5 (LLM, requer API key)

Consulte `docs/SMOKE_TEST_HUMAN.md` §3 para instruções de como providenciá-los.

# Sprint A8 — Ondas paralelas

> Sprint sem ondas paralelas formais. Lanes A8.0–A8.4 foram puxadas conforme demanda, sem diagrama de dependência prescrito.

Dependências práticas observadas:

- **A8.0** independente, fechou logo após A7.5.
- **A8.2** (IRPF) depende de A7 ✅ (config DB-first); destrava S_IRPF_RENDA + S_IRPF_OTIMIZACAO no relatório premium.
- **A8.3** (TRS real) depende de A7 ✅ + A8.2 ✅ (consome IRPF effective rate); orquestrado em 2 fases (PR-A Calculator+ratios, PR-B fix bucket aluguéis paralelos; PR-C wire+UI+ADR sequencial).
- **A8.4** (Cenários de Estresse) depende de A7 ✅ + A8.2 ✅; 6 PRs sequenciais (PR0 docs · PR1 schema rename · PR2 gate + analyzer · PR3 frontend + APP_C · PR4 delete USA · PR5 limpeza).
- **A8.1** (MileageProgram) depende apenas de A7 ✅; permaneceu planejada como débito técnico — bridge `storage/<ws>/notes/milhas.md` em A7.6 ADR-147.

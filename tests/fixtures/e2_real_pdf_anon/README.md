# PDFs reais anonimizados (E2 — Fase 2 opcional)

Pasta para **binários PDF** derivados de extratos reais, com **redação completa**, usados em regressão de layout (pdfplumber, quebras de página, ruído) **além** do `pdf_generator` sintético.

## Primeiro arquivo sugerido: C6 Bank

No inventário típico de `data/financial_statements/`, os PDFs C6 costumam ser **extrato global USD/EUR** (`c6bank_extratocontaglobalusd_…`, `c6bank_extratocontaglobaleur_…`) ou **carteira** — nem sempre há `c6bank_extratoconta_…` (conta BRL) nessa pasta. O parser em `scripts/e2/banks/c6bank.py` trata **global** e **conta**; o nome do arquivo deve continuar a casar com o regex do módulo (ex.: `extratocontaglobalusd` no nome).

**Fluxo (você executa no seu clone):**

1. **Escolher** um original, ex.:
   `data/financial_statements/c6bank_extratocontaglobalusd_202601_202604-0_original.pdf`
2. **Redigir o corpo do PDF** (obrigatório): nomes, contas, valores identificáveis, etc. — Preview, Adobe Acrobat, ou ferramenta equivalente. Só limpar metadados **não** anonimiza o extrato.
3. **Salvar** com nome canônico + sufixo, mantendo o tipo no meio do nome, por exemplo:
   `c6bank_extratocontaglobalusd_202601_202604_redacted.pdf`
4. **Remover só metadados** (passo extra, não substitui o passo 2):

   ```bash
   python dev/strip_pdf_metadata.py caminho/do/redigido.pdf tests/fixtures/e2_real_pdf_anon/c6bank_extratocontaglobalusd_202601_202604_redacted.pdf
   ```

5. **Validar:** `pytest tests/test_e2_real_pdf_regression.py -q`
6. **Abrir PR** com revisão explícita — nunca commitar o `-0_original.pdf` nem cópias não redigidas.

## Critérios antes de commitar

1. **Redação:** nenhum nome, conta, agência, CPF/CNPJ, endereço ou valor identificável de terceiros; metadados do PDF revisados.
2. **Nome do arquivo** alinhado ao contrato E0/registry para o parser desejado, ex.:
   - `itau_extratoconta_202604_redacted.pdf`
   - `c6bank_extratoconta_202604_redacted.pdf`
   O sufixo `_redacted` (ou `anon`) deixa explícito que passou por revisão.
3. **PR:** inclusão de PDF real exige revisão explícita no PR.
4. **Lint PII:** o lint de CPF (`tests/utils/lint_no_real_pii.py`) atinge `.py`/`.json`/`.md` em `tests/` — não varre bytes do PDF; a responsabilidade da redação é humana + review.

## Testes

`tests/test_e2_real_pdf_regression.py` percorre `*.pdf` nesta pasta e executa `route_to_parser(filename)` + parse. Com **zero** arquivos, o teste passa (CI verde). Ao adicionar PDFs, o mesmo teste passa a validar cada um.

## Relação com outras pastas

- **`tests/fixtures/pdfs/`** (se existir): histórico de só sintéticos — não misturar PDFs “reais redigidos” lá sem alinhar o time.
- **Sintético obrigatório no dia a dia:** continua sendo `tests/fixtures/pdf_generator.py` + `tests/test_e2_synthetic_pdf_parsers.py`.

Ver [PIPELINE_ARTIFACTS.md](../../../docs/PIPELINE_ARTIFACTS.md) § *E2 — sintético e real anonimizado*.

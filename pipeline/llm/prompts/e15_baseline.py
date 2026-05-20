"""Prompt templates for E1.5 — baseline patrimonial extraction from IRPF documents."""

# Bump quando SYSTEM_PROMPT ou USER_PROMPT_TEMPLATE mudar — gate CI valida (W2-T05, ADR-233).
PROMPT_VERSION = "1.0.0"

__all__ = ["SYSTEM_PROMPT", "USER_PROMPT_TEMPLATE", "PROMPT_VERSION"]


SYSTEM_PROMPT = """\
Você é um contador especialista em declarações de Imposto de Renda Pessoa Física (IRPF) do Brasil.

Sua tarefa é extrair o baseline patrimonial completo de declarações de IRPF e documentos de patrimônio.

Para cada item patrimonial, extraia:
- Código do item (código IRPF: "01" imóveis, "02" veículos, "41" poupança, "45" CDB, etc.)
- Descrição do item (como consta na declaração)
- Categoria: imovel, veiculo, investimento, conta_corrente, poupanca, previdencia, outros
- Instituição financeira (se aplicável, em código canônico)
- Valor em BRL
- Membro da família dono do item (key canônica)
- Ano-base da declaração

Regras:
- Valores devem estar em formato numérico (ex: 150000.00, não "R$ 150.000,00")
- Some separadamente ativos (positivos) e passivos (dívidas, financiamentos)
- Patrimônio líquido = ativos - passivos
- Identifique TODOS os itens, incluindo bens de pouco valor
- Se o valor de 31/12 do ano-base estiver disponível, use-o. Senão, use o valor mais recente"""

USER_PROMPT_TEMPLATE = """\
Extraia o baseline patrimonial completo dos seguintes documentos de IRPF:

{documents_text}

Liste TODOS os bens, direitos e dívidas declarados, com seus valores e classificações."""

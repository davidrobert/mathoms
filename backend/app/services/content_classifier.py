"""Content-based document classifier.

Classifies financial documents by inspecting their **contents** (not filenames).
Bank-exported filenames are frequently wrong or misleading, so we ignore them
entirely for classification purposes.

Pipeline:
    1. Extract text preview (first pages of PDF, first rows of XLSX/CSV).
    2. Match institution markers (razão social, CNPJ, headers).
    3. Match document-type markers in priority order (IRPF > fatura > extrato
       > investimento > CDB). Each type has REQUIRED and SUPPORTING markers;
       confidence = 1.0 if required + ≥1 supporting, 0.7 if only required,
       0.5 if only supporting.
    4. Extract period from content (DD/MM/YYYY ranges, MM/YYYY, YYYY).
    5. Return dict compatible with ``scripts.e0_route.classify_by_name``.

The caller decides what to do with low-confidence results (LLM fallback,
``needs_review`` flag, etc.). This module has no LLM calls and no network.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Institution markers — matched against file text content
# ---------------------------------------------------------------------------
# Order matters only for disambiguation; first match wins.
INSTITUTION_CONTENT_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Receita Federal — deve vir PRIMEIRO: declarações de IRPF listam contas bancárias
    # em "Bens e Direitos", então o texto contém "BRADESCO", "C6 BANK", etc. como dados
    # do contribuinte. Se RFB não fosse avaliada primeiro, o banco seria detectado antes.
    # Usamos âncoras institucionais fortes que NÃO aparecem em informes bancários:
    # "Receita Federal do Brasil" (cabeçalho do órgão), "DIRPF" (software de declaração),
    # CNPJ oficial da RFB. Excluídos: "Imposto de Renda da Pessoa Física" e "Declaração
    # de Ajuste Anual" — esses aparecem em informes de rendimentos emitidos por bancos.
    (
        re.compile(
            r"Receita\s*Federal\s*do\s*Brasil"
            r"|Secretaria\s*(Especial\s*)?da\s*Receita\s*Federal"
            r"|RFB\s*[-–]\s*Receita"
            r"|\bDIRPF\s*20\d{2}\b"
            r"|00\.?394\.?460[/.]0058-?87",
            re.I,
        ),
        "receitafederal",
    ),
    # C6 Bank: razão social, marca Carbon, CNPJ 31.872.495, C6 Invest (app de CDB).
    # Também detecta o formato CSV de exportação da fatura Carbon: a combinação
    # "Valor (em US$)" + "Cotação (em R$)" é exclusiva desse extrato — o cartão
    # Carbon exibe transações em dólar com cotação de conversão para BRL.
    (
        re.compile(
            r"C6\s*CARBON|C6\s*BANK|BANCO\s*C6\s*S\.?A\.?|31\.?872\.?495"
            r"|C6\s*Invest"  # app de investimentos C6
            r"|Valor\s*\(em\s*US\$\).*Cota[çc][ãa]o\s*\(em\s*R\$\)",
            re.I,
        ),
        "c6bank",
    ),
    # Itaú: Personnalité, razão social
    (re.compile(r"ITA[UÚ]\s*(UNIBANCO|PERSONNALIT[ÉE])?|PERSONNALIT[ÉE]\s*ITA[UÚ]", re.I), "itau"),
    # Santander: razão social, Unique, CDB exports, Central de Atendimento, account-specific markers.
    # "CDB DI/PROG SANTANDER" e "Central de Atendimento Santander" aparecem nos PDFs do IB.
    # "Seguro do limite da conta" é linha no rodapé do extrato XLS (além dos 2000 chars).
    # "Conta: NNNN-NN.NNNNNN.N" é o formato exclusivo de conta-corrente Santander que aparece
    #   na linha 3 do XLS, dentro dos primeiros 200 chars — âncora primária para esse formato.
    # "JUROS SALDO UTILIZ ATE LIMITE" é o encargo do "Limite Facilitado" Santander.
    # "^data,lançamento,valor" é o header exato do CSV export do Santander Unique.
    (
        re.compile(
            r"SANTANDER\s*(BRASIL|UNIQUE|S\.?A\.?)|BANCO\s*SANTANDER"
            r"|CDB\s+(?:DI|PROG|MASTER|MAIS|METASERVAS?)\s+SANTANDER"  # CDB products
            r"|Central\s+de\s+Atendimento\s+Santander"  # IB footer
            r"|Seguro\s+do\s+limite\s+da\s+conta"  # XLS rodapé
            r"|Conta:\s*\d{4}-0[01]\.\d{4,8}\.\d"  # conta Santander: 1234-01.001234.5
            r"|JUROS\s+SALDO\s+UTILIZ\s+ATE\s+LIMITE"  # Limite Facilitado
            r"|^\ufeff?data,lan[çc]amento,valor\s*$",  # CSV Santander Unique (com/sem BOM)
            re.I | re.MULTILINE,
        ),
        "santander",
    ),
    # Bradesco: razão social e marca forte.
    # Também detecta exportações do Internet Banking Bradesco via markers visíveis
    # no topo da página (antes dos 2000 chars do preview):
    #   - "Ágora Home Broker" — corretora exclusiva do grupo Bradesco, presente
    #     na barra de navegação do IB. Impossível de confundir com outro banco.
    #   - "Fone Fácil" + "0800 570 0022" — central de atendimento Bradesco
    #     (backup caso Ágora não esteja na nav).
    (
        re.compile(
            r"BRADESCO|BANCO\s*BRADESCO"
            r"|[AÁ]gora\s*Home\s*Broker"  # nav do IB Bradesco (dentro dos 2000 chars)
            r"|Fone\s*F[aá]cil",  # marca registrada do atendimento Bradesco
            re.I,
        ),
        "bradesco",
    ),
    # BTG Pactual (before PicPay — evita falso PicPay em PDFs de corretora)
    (re.compile(r"BTG\s*PACTUAL|BANCO\s*BTG|BTG\s+Pactual", re.I), "btgpactual"),
    # Bank of America
    (re.compile(r"Bank\s*of\s*America|BofA", re.I), "bankofamerica"),
    # PicPay — exige marca forte (evita match em menções promocionais)
    (
        re.compile(r"PicPay\s*(?:Bank|Servi[çc]os|Institui[çc][ãa]o\s+de\s+Pagamento)", re.I),
        "picpay",
    ),
    # Wise (TransferWise)
    (re.compile(r"\bWise\b|TransferWise", re.I), "wise"),
    # Rico / XP — inclui "Rico Corretora de Títulos..." (razão social completa nos PDFs de extrato).
    # Exige sufixo identificador (Investimentos, CTVM, Corretora) para evitar falso positivo
    # em descrições de transações com o sobrenome/nome comercial "Rico".
    (
        re.compile(
            r"Rico\s*(?:Investimentos|CTVM|Corretora)"
            r"|RICO\s+CORRETORA"  # razão social em maiúsculas nos PDFs
            r"|\bXP\s*Investimentos",
            re.I,
        ),
        "rico",
    ),
    # QuintoAndar
    (re.compile(r"Quinto\s*Andar|QuintoAndar", re.I), "quintoandar"),
    # Caixa Econômica Federal — razão social, CNPJ 00.360.305, marca CEF.
    # "Alô CAIXA" / "SAC CAIXA" são rodapés de serviço presentes em extratos.
    # "0800 726" cobre os dois ramais canônicos da CEF (0101 e 0104).
    (
        re.compile(
            r"CAIXA\s*ECON[ÔO]MICA\s*FEDERAL|CEF\b|00\.?360\.?305"
            r"|Al[oô]\s*CAIXA|SAC\s*CAIXA"
            r"|0800\s*726",
            re.I,
        ),
        "caixa",
    ),
    # Binance
    (re.compile(r"Binance", re.I), "binance"),
]


# ---------------------------------------------------------------------------
# Document-type rules — matched against file text content
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TypeRule:
    """A content-based document-type matcher."""

    code: str
    dest_group: str
    required: tuple[re.Pattern, ...]  # ALL must match
    supporting: tuple[re.Pattern, ...]  # at least one boosts confidence to 1.0
    priority: int = 100  # lower = evaluated first


def _c(pattern: str) -> re.Pattern:
    return re.compile(pattern, re.I | re.MULTILINE)


# Priority: specific (IRPF, faturas, poupança) → generic (extrato, fatura)
TYPE_RULES: tuple[TypeRule, ...] = (
    # ---------- IRPF / Receita Federal (most specific first) ----------
    TypeRule(
        code="irpfdeclaracao",
        dest_group="income_tax_br",
        # Aceita as variações mais comuns em PDFs gerados pelo PGD/e-CAC:
        #   "Declaração IRPF 20XX", "Declaração de Ajuste Anual",
        #   "Declaração de Imposto de Renda Pessoa Física",
        #   "DIRPF 20XX", "Modelo Completo/Simplificado".
        # Marcadores de suporte cobrem seções internas (Bens e Direitos,
        # Rendimentos Tributáveis, Dependentes, Resumo, etc.).
        required=(
            # Âncoras estritas — sempre começam por "Declaração" ou por "DIRPF"
            # (sigla exclusiva da declaração). Evita colidir com informes
            # financeiros que só mencionam "IRPF 20XX" como ano-calendário.
            _c(
                r"Declara[çc][ãa]o\s*(?:de\s*)?(?:IRPF|"
                r"de\s*Ajuste\s*Anual|"
                r"de\s*Imposto\s*de\s*Renda|"
                r"Pessoa\s*F[ií]sica)"
                r"|\bDIRPF\s*20\d{2}\b"
            ),
        ),
        supporting=(
            _c(r"Bens\s*e\s*Direitos"),
            _c(r"Rendimentos\s*Tribut[aá]veis"),
            _c(r"Rendimentos\s*Isentos"),
            _c(r"Ano-?[Cc]alend[aá]rio"),
            _c(r"Imposto\s*(a\s*)?(Pagar|Restituir)"),
            _c(r"Dependentes"),
            _c(r"Resumo\s*(da\s*)?Declara[çc][ãa]o"),
        ),
        priority=1,
    ),
    TypeRule(
        code="irpfrecibo",
        dest_group="income_tax_br",
        # Recibos da RFB usam formulações variáveis: alguns dizem "Recibo de Entrega
        # da Declaração de Imposto sobre a Renda da Pessoa Física" (sem a sigla "IRPF"
        # inline), outros "Recibo da Entrega da Declaração IRPF". Aceitamos qualquer
        # combinação "Recibo (de|da) Entrega" próxima a "Declaração", "Imposto (de|sobre a)
        # Renda" ou "IRPF" — incluindo a forma curta "Recibo da Declaração".
        required=(
            _c(
                r"Recibo\s*(?:de|da)\s*Entrega.*"
                r"(?:IRPF|Declara[çc][ãa]o|Imposto\s*(?:de|sobre\s*a)\s*Renda|Pessoa\s*F[ií]sica)"
                r"|Recibo\s*da\s*Declara[çc][ãa]o\s*(?:de\s*)?(?:IRPF|Imposto\s*(?:de|sobre\s*a)\s*Renda)"
                r"|IRPF.*Recibo\s*de\s*Entrega"
            ),
        ),
        supporting=(
            _c(r"N[uú]mero\s*do\s*Recibo"),
            _c(r"Hash\s*do\s*Recibo"),
            _c(r"Modelo\s*(?:Completo|Simplificado)"),
            _c(r"Exerc[ií]cio\s*20\d{2}"),
            _c(r"Recibo\s*da\s*Declara[çc][ãa]o"),
        ),
        priority=1,
    ),
    TypeRule(
        code="informerendimentosaluguel",
        dest_group="income_tax_br",
        required=(_c(r"Informe.*Rendiment"), _c(r"Aluguel|Locat[áa]rio|Loca[çc][ãa]o")),
        supporting=(_c(r"Rendimento\s*Bruto"),),
        priority=2,
    ),
    TypeRule(
        code="informerendimentos",
        dest_group="income_tax_br",
        required=(
            _c(r"Informe\s*de\s*Rendimentos\s*Financeiros|Informe\s*Anual\s*de\s*Rendimentos"),
        ),
        supporting=(
            _c(r"Rendimentos\s*Tribut[aá]veis|Isentos\s*e\s*N[ãa]o\s*Tribut[aá]veis"),
            _c(r"Fonte\s*Pagadora"),
            _c(r"Ano-?[Cc]alend[aá]rio"),
        ),
        priority=3,
    ),
    # ---------- Fatura de aluguel (specific before cartão) ----------
    TypeRule(
        code="faturaaluguel",
        dest_group="financial_statements",
        # "Faturas de aluguel" (plural) é o cabeçalho do PDF do QuintoAndar.
        required=(_c(r"Faturas?\s*de\s*Aluguel|Boleto\s*de\s*Aluguel"),),
        supporting=(_c(r"Locador|Locat[áa]rio|QuintoAndar"),),
        priority=5,
    ),
    # ---------- Fatura de cartão ----------
    TypeRule(
        code="faturaunique",
        dest_group="financial_statements",
        # Dois formatos possíveis do Santander Unique:
        # (a) PDF de fatura: contém "SANTANDER UNIQUE" no cabeçalho.
        # (b) CSV de exportação do app: header exato "data,lançamento,valor"
        #     (3 colunas em português, datas no formato YYYY-MM-DD) — esse
        #     formato é exclusivo do export CSV do Santander Unique e não
        #     contém nenhum marcador institucional explícito.
        required=(
            _c(
                r"SANTANDER\s*UNIQUE|Cart[ãa]o\s*Santander\s*Unique"
                r"|^\ufeff?data,lan[çc]amento,valor\s*$"  # CSV header (Santander Unique app, com/sem BOM)
            ),
        ),
        supporting=(
            _c(r"Total\s*a\s*Pagar"),
            _c(r"Vencimento\s*(da)?\s*Fatura"),
            _c(r"Limite\s*(de)?\s*Cr[eé]dito"),
            _c(r"PAGAMENTO EFETUADO"),  # entrada de pagamento no CSV
            _c(r"\d{4}-\d{2}-\d{2},"),  # data no formato ISO no CSV
        ),
        priority=10,
    ),
    TypeRule(
        code="faturacarbon",
        dest_group="financial_statements",
        # Dois formatos possíveis do C6 Carbon:
        # (a) PDF de fatura: contém "C6 Carbon" no cabeçalho.
        # (b) CSV de exportação: colunas "Valor (em US$)" + "Cotação (em R$)"
        #     na mesma linha — exclusivo do extrato CSV do cartão Carbon.
        required=(_c(r"C6\s*Carbon" r"|Valor\s*\(em\s*US\$\).*Cota[çc][ãa]o\s*\(em\s*R\$\)"),),
        supporting=(
            _c(r"Subtotal\s*deste\s*cart[ãa]o"),
            _c(r"Vencimento\s*da\s*Fatura"),
            _c(r"Total\s*desta\s*Fatura"),
            _c(r"Data\s+de\s+Compra"),  # CSV: coluna de data da transação
            _c(r"Final\s+do\s+Cart[ãa]o"),  # CSV: coluna com 4 últimos dígitos
        ),
        priority=10,
    ),
    TypeRule(
        code="faturapaoacucar",
        dest_group="financial_statements",
        required=(_c(r"P[ãa]o\s*de\s*A[çc][uú]car|Cart[ãa]o\s*Pao\s*de\s*A[çc]ucar"),),
        supporting=(
            _c(r"Total\s*desta\s*fatura"),
            _c(r"Lan[çc]amentos\s*atuais"),
            _c(r"Vencimento"),
        ),
        priority=10,
    ),
    # Santander — cartões que não são "Unique" (Elite, Free, etc.): texto costuma
    # misturar "Cartão de Crédito" + vencimento sem a palavra FATURA na 1ª página.
    TypeRule(
        code="faturasantander",
        dest_group="financial_statements",
        required=(
            _c(r"BANCO\s+SANTANDER|BANCO\s+SANTANDER\s+S\.?\s*A\.?|SANTANDER\s+BRASIL"),
            _c(
                r"(?:\bFATURA\b|Fatura\s+[Dd]igital|Resumo\s+da\s+[Ff]atura|"
                r"Demonstrativo\s+de\s+[Ff]atura|"
                r"Data\s+de\s+[Vv]encimento|Vencimento\s+(?:da\s+)?[Ff]atura|"
                r"Total\s+a\s+Pagar|Total\s+da\s+[Ff]atura|"
                r"Pagamento\s+[Mm][íi]nimo|Limite\s+(?:de\s+)?Cr[eé]dito|"
                r"Cart[ãa]o\s+de\s+Cr[eé]dito)"
            ),
        ),
        supporting=(
            _c(r"R\$\s*[\d\.\s]+|R\$\s*[\d,\.]+"),
            _c(r"Lan[çc]amentos|Compras|Parcelas|rotativo|final\s*\d{4}"),
        ),
        priority=11,
    ),
    # Generic fatura de cartão — um único padrão OR (evita exigir \bFATURA\b + linha
    # financeira ao mesmo tempo, o que falhava em muitos PDFs reais).
    TypeRule(
        code="fatura",
        dest_group="financial_statements",
        required=(
            _c(
                r"(?:"
                r"(?:\bFATURA\b|Fatura\s+[Dd]igital|Demonstrativo\s+da\s+[Ff]atura)"
                r".{0,1200}?"
                r"(?:Total\s*(?:a\s*Pagar|da\s*Fatura|desta\s*Fatura)|"
                r"Vencimento\s*(?:da\s*)?\s*[Ff]atura|Data\s+de\s+[Vv]encimento|"
                r"Limite\s*(?:de\s*)?\s*Cr[eé]dito|Pagamento\s*[Mm][íi]nimo)"
                r"|"
                r"Cart[ãa]o\s+de\s+Cr[eé]dito"
                r".{0,2600}?"
                r"(?:Total\s+a\s*Pagar|Total\s+da\s+[Ff]atura|"
                r"Vencimento\s+(?:da\s+)?[Ff]atura|Data\s+de\s+[Vv]encimento|"
                r"Pagamento\s+[Mm][íi]nimo|Limite\s+(?:de\s+)?Cr[eé]dito|"
                r"\bFATURA\b)"
                r")"
            ),
        ),
        supporting=(
            _c(r"Cart[ãa]o|Cr[eé]dito|Final\s*\d{4}"),
            _c(r"Lan[çc]amentos|Compras|Parcelas|R\$\s*[\d\.,]+"),
        ),
        priority=21,
    ),
    # ---------- Investimentos (CDB, posição, renda fixa) ----------
    TypeRule(
        code="investimentosposicao",
        dest_group="financial_statements",
        required=(_c(r"Posi[çc][ãa]o\s*(Consolidada|de\s*Investimentos|de\s*Carteira)"),),
        supporting=(
            _c(r"Renda\s*Fixa|Renda\s*Vari[aá]vel|Fundos\s*de\s*Investimento"),
            _c(r"Saldo\s*(Total|Consolidado)"),
        ),
        priority=15,
    ),
    TypeRule(
        code="carteirarendafixa",
        dest_group="financial_statements",
        required=(_c(r"Carteira\s*(de\s*)?Renda\s*Fixa"),),
        supporting=(_c(r"Vencimento"), _c(r"Rentabilidade")),
        priority=15,
    ),
    TypeRule(
        code="cdbdetalhes",
        dest_group="financial_statements",
        required=(_c(r"\bCDB\b|Certificado\s*de\s*Dep[oó]sito\s*Banc[aá]rio"),),
        supporting=(
            _c(r"Dispon[ií]vel\s*para\s*Resgate"),
            _c(r"Rentabilidade"),
            _c(r"Vencimento"),
            _c(r"Valor\s*(Total|Aplicado|Bruto)"),
        ),
        priority=18,
    ),
    # ---------- Extratos bancários ----------
    TypeRule(
        code="extratopoupanca",
        dest_group="financial_statements",
        required=(_c(r"Extrato.*Poupan[çc]a|Conta\s*Poupan[çc]a|Caderneta\s*de\s*Poupan[çc]a"),),
        supporting=(_c(r"Rendimento"), _c(r"Saldo\s*Anterior|Saldo\s*Atual")),
        priority=25,
    ),
    TypeRule(
        code="extratocontaglobalusd",
        dest_group="financial_statements",
        required=(
            _c(r"Extrato.*(Global|Internacional)|Account\s*Statement"),
            _c(r"US\$|USD\b|Dollar|D[oó]lar"),
        ),
        supporting=(_c(r"Saldo|Balance"),),
        priority=25,
    ),
    TypeRule(
        code="extratocontaglobaleur",
        dest_group="financial_statements",
        required=(
            _c(r"Extrato.*(Global|Internacional)|Account\s*Statement"),
            _c(r"€|EUR\b|Euro"),
        ),
        supporting=(_c(r"Saldo|Balance"),),
        priority=25,
    ),
    # Bank of America style statement (English)
    TypeRule(
        code="extratocontausd",
        dest_group="financial_statements",
        required=(
            _c(r"Account\s*Statement|Account\s*number"),
            _c(r"Beginning\s*balance|Ending\s*balance"),
        ),
        supporting=(_c(r"Transaction|Deposit|Withdrawal"),),
        priority=28,
    ),
    # Caixa Econômica Federal — "Extrato por período" (texto visível ou via LLM vision).
    # Dois formatos: PDFs com camada de texto (usam razão social ou CEF) e PDFs
    # somente-imagem (classificados pelo LLM via vision — regra usada apenas para
    # validação pós-LLM, não precisa de match regex).
    # Marcadores de suporte cobrem campos canônicos do extrato CEF: "Conta",
    # "Período" e rodapés de serviço "Alô CAIXA" / "SAC CAIXA".
    TypeRule(
        code="extratoconta",
        dest_group="financial_statements",
        required=(_c(r"CAIXA\s*ECON[ÔO]MICA\s*FEDERAL|CEF\b|Al[oô]\s*CAIXA|SAC\s*CAIXA"),),
        supporting=(
            _c(r"Extrato\s*por\s*per[ií]odo|Lan[çc]amentos\s*do\s*dia"),
            _c(r"SALDO\s*(ANTERIOR|DO\s*DIA|ATUAL)"),
            _c(r"Per[ií]odo\s*(dos\s*lan[çc]amentos)?"),
            _c(r"Conta\s*[:\-]?\s*\d"),  # "Conta: 00012345-6"
            _c(r"0800\s*726"),  # central de atendimento CEF
        ),
        priority=27,
    ),
    # Generic extrato de conta corrente (Brazilian).
    # Inclui marcadores específicos do XLS exportado pelo Itaú Internet Banking:
    #   - "Logotipo Itaú" na linha 0 (cabeçalho fixo do XLS do Itaú)
    #   - "lançamento.*saldos (R$)" nos títulos de coluna (linha 8 do XLS)
    # Esses marcadores permitem classificação sem depender da palavra "EXTRATO",
    # que não aparece no formato XLS do Itaú.
    TypeRule(
        code="extratoconta",
        dest_group="financial_statements",
        required=(
            _c(
                r"EXTRATO\s*(DA\s*CONTA|DE\s*CONTA|CORRENTE)?"
                r"|Lan[çc]amentos\s*(da\s*)?Conta"
                r"|Movimenta[çc][õo]es"
                r"|Logotipo\s+Ita[uú]"  # Itaú XLS: cabeçalho fixo linha 0
                r"|lan[çc]amento.*saldos?\s*\(R\$\)"  # Itaú XLS: título da coluna "saldos (R$)"
            ),
        ),
        supporting=(
            _c(r"SALDO\s*(ANTERIOR|DO\s*DIA|DISPON[IÍ]VEL?|FINAL|ATUAL)"),
            _c(r"Ag[êe]ncia\s*[:\-]?\s*\d+.*Conta\s*[:\-]?\s*[\d-]+"),
            _c(r"Per[ií]odo\s*:?\s*\d{2}/\d{2}/\d{4}"),
            _c(r"Atualiza[çc][ãa]o\s*:"),  # Itaú XLS: "Atualização: DD/MM/YYYY"
        ),
        priority=30,
    ),
)


# ---------------------------------------------------------------------------
# Period extraction from content
# ---------------------------------------------------------------------------
_PERIOD_RANGE_RE = re.compile(
    r"(\d{1,2})/(\d{1,2})/(\d{4}).{0,20}?(?:a|at[eé]|to|-)\s*(\d{1,2})/(\d{1,2})/(\d{4})",
    re.I | re.DOTALL,
)
_YYYYMM_RE = re.compile(r"\b(20\d{2})[-/](0?[1-9]|1[012])\b")
_MESES = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}
_MONTH_YEAR_BR_RE = re.compile(
    r"\b(jan(?:eiro)?|fev(?:ereiro)?|mar(?:[çc]o)?|abr(?:il)?|mai(?:o)?|jun(?:ho)?|"
    r"jul(?:ho)?|ago(?:sto)?|set(?:embro)?|out(?:ubro)?|nov(?:embro)?|dez(?:embro)?)"
    r"[\s/\-]+(20\d{2})",
    re.I,
)


def _mm(month_name: str) -> int:
    key = month_name.lower()[:3]
    for full, n in _MESES.items():
        if full.startswith(key):
            return n
    return 0


def extract_period_from_content(text: str) -> str | None:
    """Try to extract a YYYYMM or YYYYMM_YYYYMM period from document text."""
    m = _PERIOD_RANGE_RE.search(text)
    if m:
        _, m1, y1, _, m2, y2 = m.groups()
        return f"{int(y1):04d}{int(m1):02d}_{int(y2):04d}{int(m2):02d}"
    m = _YYYYMM_RE.search(text)
    if m:
        y, mn = m.groups()
        return f"{int(y):04d}{int(mn):02d}"
    m = _MONTH_YEAR_BR_RE.search(text)
    if m:
        name, year = m.groups()
        mn = _mm(name)
        if mn:
            return f"{int(year):04d}{mn:02d}"
    # Year-only fallback
    m = re.search(r"\b(20\d{2})\b", text)
    if m:
        return m.group(1)
    return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
@dataclass
class ContentClassification:
    doc_type: str | None
    dest_group: str | None
    institution: str | None
    period: str | None
    confidence: float  # 0.0 to 1.0
    source: str = "content_regex"
    matched_required: int = 0
    matched_supporting: int = 0
    force_review: bool = False

    def to_dict(self) -> dict:
        return {
            "institution": self.institution,
            "doc_type": self.doc_type,
            "dest_group": self.dest_group,
            "period": self.period,
            "member": None,
            "confidence": self.confidence,
            "source": self.source,
            "matched_required": self.matched_required,
            "matched_supporting": self.matched_supporting,
            "force_review": self.force_review,
        }


def detect_institution_by_content(text: str) -> str | None:
    for pattern, code in INSTITUTION_CONTENT_PATTERNS:
        if pattern.search(text):
            return code
    return None


def detect_type_by_content(text: str) -> tuple[TypeRule | None, int, int]:
    """Return (best rule, required_matches, supporting_matches).

    Evaluates rules in priority order. The first rule whose REQUIRED patterns
    all match wins — supporting matches just adjust confidence.
    """
    for rule in sorted(TYPE_RULES, key=lambda r: r.priority):
        req_matches = sum(1 for p in rule.required if p.search(text))
        if req_matches < len(rule.required):
            continue
        sup_matches = sum(1 for p in rule.supporting if p.search(text))
        return rule, req_matches, sup_matches
    return None, 0, 0


def _compute_confidence(rule: TypeRule, req: int, sup: int) -> float:
    """All required + ≥1 supporting → 1.0. All required, 0 supporting → 0.7."""
    if req < len(rule.required):
        return 0.0
    if sup >= 1:
        return 1.0
    # Only required matched — tight rules (single required pattern, e.g. IRPF)
    # are still high-confidence; generic rules with no supporting match are
    # weaker.
    if len(rule.required) >= 2:
        return 0.85
    return 0.7


def _empty_classification(
    institution: str | None = None,
    period: str | None = None,
    *,
    source: str | None = None,
) -> ContentClassification:
    return ContentClassification(
        doc_type=None,
        dest_group=None,
        institution=institution,
        period=period,
        confidence=0.0,
        source=source,
        matched_required=0,
        matched_supporting=0,
    )


def _resolve_institution(rule: TypeRule, detected: str | None) -> str | None:
    # IRPF lista contas bancárias em "Bens e Direitos" — regex de banco bate primeiro
    if rule.dest_group == "income_tax_br":
        return "receitafederal"
    return detected


def classify_text(text: str) -> ContentClassification:
    """Classify a preview text extracted from a financial document."""
    if not text or len(text.strip()) < 20:
        return _empty_classification(source="content_regex_empty")

    institution = detect_institution_by_content(text)
    rule, req, sup = detect_type_by_content(text)
    period = extract_period_from_content(text)

    if rule is None:
        return _empty_classification(institution=institution, period=period)

    return ContentClassification(
        doc_type=rule.code,
        dest_group=rule.dest_group,
        institution=_resolve_institution(rule, institution),
        period=period,
        confidence=_compute_confidence(rule, req, sup),
        matched_required=req,
        matched_supporting=sup,
    )


# ---------------------------------------------------------------------------
# Filename-guarded investment override
# ---------------------------------------------------------------------------
# Contexto: exports de corretoras (Rico, XP) vêm nomeados `*_extratoconta_*`
# mas o conteúdo é dashboard de posição de investimentos, não extrato de conta.
# Isso força o parser E2 a rodar e extrair 0 transações (ERROR espúrio).
# Heurística determinística: se o filename sugere extrato, mas o conteúdo
# mostra marcadores de investimento (≥3) e zero marcadores de extrato
# bancário, reclassificamos como ``investimentosposicao`` e marcamos
# ``force_review=True`` para revisão humana.
_INVESTMENT_MARKERS: tuple[re.Pattern, ...] = (
    re.compile(r"Posi[çc][ãa]o\s*(a\s*mercado|consolidada|de\s*carteira)", re.I),
    re.compile(r"Fundos?\s*de\s*Investimentos?", re.I),
    re.compile(r"Renda\s*Vari[aá]vel", re.I),
    re.compile(r"Rentabilidade\s*(L[ií]quida|Bruta|Acumulada)?", re.I),
    re.compile(r"\bproventos?\b", re.I),
    re.compile(r"Aloca[çc][ãa]o(\s+da\s+carteira)?", re.I),
    re.compile(r"Tesouro\s*(Direto|Selic|IPCA|Prefixado|Nacional)", re.I),
    re.compile(r"\bETFs?\b|\bFIIs?\b|\bBDRs?\b"),
    re.compile(r"\b[A-Z]{4}\d{1,2}\b"),  # B3 tickers: PETR4, ITSA4, MGLU3
    re.compile(r"Carteira\s+de\s+(Renda|Investimentos)", re.I),
)

_BANK_STATEMENT_MARKERS: tuple[re.Pattern, ...] = (
    re.compile(r"Saldo\s+anterior", re.I),
    re.compile(r"Lan[çc]amentos\s+(do\s+dia|da\s+conta|do\s+per[ií]odo)", re.I),
    re.compile(r"SALDO\s+(DO\s+DIA|ATUAL|DISPON[IÍ]VEL)", re.I),
    re.compile(r"Ag[êe]ncia\s*[:\-]?\s*\d+.{0,40}Conta\s*[:\-]?\s*[\d-]+", re.I | re.DOTALL),
    re.compile(r"TED\s+(Enviad|Recebid)", re.I),
    re.compile(r"D[ée]bito\s+autom[aá]tico", re.I),
    re.compile(r"PIX\s+(Enviad|Recebid)", re.I),
    re.compile(r"Hist[oó]rico\s+de\s+Lan[çc]amentos", re.I),
)


def _maybe_apply_investment_override(
    result: ContentClassification, filename: str, text: str
) -> ContentClassification:
    if "extratoconta" not in filename.lower():
        return result
    invest_hits = sum(1 for p in _INVESTMENT_MARKERS if p.search(text))
    if invest_hits < 3:
        return result
    bank_hits = sum(1 for p in _BANK_STATEMENT_MARKERS if p.search(text))
    if bank_hits > 0:
        return result
    # Skip LLM (conf >= 0.8) and force human review.
    return ContentClassification(
        doc_type="investimentosposicao",
        dest_group="financial_statements",
        institution=result.institution,
        period=result.period,
        confidence=0.85,
        source="content_regex_investment_override",
        matched_required=invest_hits,
        matched_supporting=0,
        force_review=True,
    )


def classify_file(filepath: Path, preview_extractor) -> ContentClassification:
    """Classify a file by its content.

    ``preview_extractor`` is a callable ``(Path) -> str`` that extracts a text
    preview from the file. We inject it (rather than importing) so tests can
    pass fake text and so we don't pull in pdfplumber/openpyxl at import time.
    """
    try:
        text = preview_extractor(filepath)
    except Exception as exc:  # preview extraction failed — fall through
        return ContentClassification(
            doc_type=None,
            dest_group=None,
            institution=None,
            period=None,
            confidence=0.0,
            source=f"content_regex_preview_error:{type(exc).__name__}",
        )
    result = classify_text(text or "")
    return _maybe_apply_investment_override(result, filepath.name, text or "")

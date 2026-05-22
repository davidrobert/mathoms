"""Institution detection via content markers (CNPJ, razão social, brand markers)."""

from __future__ import annotations

import re

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
    # C6 Bank PJ — PDFs "Extrato → Exportar" do app Conta PJ NÃO mencionam razão
    # social do banco no preview (só dados do cliente). Detectamos pelo layout
    # único: fraseado "Extrato exportado no dia DD de mês de ANO" + bullets "•"
    # entre rótulo e valor ("Saldo do dia • DD ...", "Cheque Especial contratado
    # • ..."), ou pelo produto "C6TAG" (telepedágio C6) presente em descrições
    # de transações. Exigimos **2+ tokens** via lookahead para evitar falso-
    # positivo em PDFs futuros de outros bancos que adotem bullets similares.
    (
        re.compile(
            # Match quando: (a) "Extrato exportado no dia" presente E pelo menos
            # 1 dos tokens C6-específicos, OU (b) "C6TAG" sozinho (patognomônico).
            r"(?=.*Extrato\s+exportado\s+no\s+dia)"
            r"(?=.*(?:•|Cheque\s+Especial\s+contratado|Saldo\s+do\s+dia\s+•|"
            r"Entradas:\s*R\$\s+[\d.,]+\s+•\s+Sa[ií]das))"
            r"|\bC6TAG\b",
            re.I | re.S,
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


def detect_institution_by_content(text: str) -> str | None:
    for pattern, code in INSTITUTION_CONTENT_PATTERNS:
        if pattern.search(text):
            return code
    return None

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Caixa Econômica Federal — extrato conta corrente (PDF "Extrato por período").

Suporta dois formatos:
  - PDF com camada de texto: extração determinística via pdfplumber
  - PDF somente-imagem (gerado pelo app Caixa): extração via visão LLM (Anthropic)
"""

import base64
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from scripts.e2.common import (
    BANCO_CAIXA,
    detect_member_from_text,
    infer_periodo_from_filename,
    log,
    make_result_template,
    parse_brl,
)

LOG_PREFIX = "E2-EXTRATO"

PARSERS = [
    (r"^caixa_extratoconta_", "parse_caixa"),
    (r"^caixaeconomica_extratoconta_", "parse_caixa"),
]

# Índices das colunas da tabela Caixa:
# Data Mov. | Nr. Doc | Histórico/Complemento | Favorecido | CPF/CNPJ | Valor | Saldo
_COL_DATA = 0
_COL_NRDOC = 1
_COL_HISTORICO = 2
_COL_FAVORECIDO = 3
_COL_VALOR = 5
_COL_SALDO = 6

_LLM_MODEL = "claude-sonnet-4-6"
_LLM_MAX_TOKENS = 2048


# =============================================================================
# Helpers de parsing
# =============================================================================

def _parse_valor_cd(text: str) -> Optional[float]:
    """Parse valor Caixa: '20.000,00 D' → -20000.0 | '127.651,19 C' → 127651.19."""
    if not text:
        return None
    text = str(text).strip()
    negative = text.upper().endswith("D")
    text = re.sub(r'\s*[CDcd]\s*$', '', text).strip()
    val = parse_brl(text)
    if val is None:
        return None
    return -val if negative else val


def _classify(historico: str) -> str:
    h = historico.upper()
    if "PIX ENVIADO" in h:
        return "Saída PIX"
    if "PIX RECEBIDO" in h or "PIX CREDITO" in h or "PIX CREDIT" in h:
        return "Entrada PIX"
    if "PIX" in h and ("DEVOL" in h or "DEVOLUC" in h):
        return "Devolução PIX"
    if "TED" in h and ("ENVIAD" in h or "SAIDA" in h or "DEBIT" in h):
        return "Saída TED/Transferência"
    if "TED" in h and ("RECEBID" in h or "CREDIT" in h or "ENTRADA" in h):
        return "Entrada TED/Transferência"
    if "TED" in h:
        return "TED"
    if "DOC" in h and "ENVIAD" in h:
        return "Saída DOC"
    if "DOC" in h and "RECEBID" in h:
        return "Entrada DOC"
    if "BOLETO" in h or "PAGAMENTO" in h:
        return "Pagamento Boleto"
    if "SAQUE" in h:
        return "Saque"
    if "DEPOSITO" in h or "DEPÓSITO" in h:
        return "Depósito"
    if "TARIFA" in h or "TAXA" in h:
        return "Tarifa Bancária"
    if "JUROS" in h or "IOF" in h:
        return "Encargos Bancários"
    if "RENDIMENTO" in h or "APLICAC" in h:
        return "Investimento/Rendimento"
    if "RESGATE" in h:
        return "Resgate Investimento"
    if "SALARIO" in h or "SALÁRIO" in h:
        return "Salário"
    if "TRANSFERENCIA" in h or "TRANSFERÊNCIA" in h:
        return "Transferência"
    if "COMPRA" in h:
        return "Compra/Débito"
    return "Outros"


def _date_iso(date_str: str) -> Optional[str]:
    """Converte 'DD/MM/YYYY' (com ou sem ' - HH:MM:SS') para 'YYYY-MM-DD'."""
    m = re.match(r'(\d{2})/(\d{2})/(\d{4})', date_str)
    if not m:
        return None
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"


# =============================================================================
# Extração determinística (PDF com camada de texto)
# =============================================================================

def _extract_from_text(all_text: str, result: Dict[str, Any]) -> None:
    """Preenche result com dados extraídos do texto do PDF."""
    result["titular"] = detect_member_from_text(all_text)

    m = re.search(r'Conta\s+([\d]+\s*/\s*[\d.]+[-\d]*)', all_text)
    if m:
        result["numero_conta"] = m.group(1).strip()

    pm = re.search(
        r'Per[íi]odo dos lan[çc]amentos\s+(\d{2}/\d{2}/\d{4})\s+at[ée]\s+(\d{2}/\d{2}/\d{4})',
        all_text,
    )
    if pm:
        result["periodo"]["inicio"] = _date_iso(pm.group(1))
        result["periodo"]["fim"] = _date_iso(pm.group(2))

    sm = re.search(r'SALDO ANTERIOR\s+R\$\s*([\d.,]+)\s*([CD])', all_text)
    if sm:
        saldo_ant = parse_brl(sm.group(1))
        if sm.group(2).upper() == "D" and saldo_ant is not None:
            saldo_ant = -saldo_ant
        result["saldo_inicial"] = saldo_ant


def _row_to_tx(cells: List[str]) -> Optional[Dict[str, Any]]:
    """Converte linha da tabela em transação ou sentinela de saldo."""
    if len(cells) <= _COL_VALOR:
        return None

    date_raw = cells[_COL_DATA]
    nr_doc = cells[_COL_NRDOC] if len(cells) > _COL_NRDOC else ""
    historico = cells[_COL_HISTORICO] if len(cells) > _COL_HISTORICO else ""
    favorecido = cells[_COL_FAVORECIDO] if len(cells) > _COL_FAVORECIDO else ""
    valor_str = cells[_COL_VALOR] if len(cells) > _COL_VALOR else ""
    saldo_str = cells[_COL_SALDO] if len(cells) > _COL_SALDO else ""

    if not re.match(r'\d{2}/\d{2}/\d{4}', date_raw):
        return None

    if historico.upper().strip() == "SALDO DIA":
        return {"_saldo_dia": _parse_valor_cd(saldo_str)}

    valor = _parse_valor_cd(valor_str)
    if valor is None:
        return None

    data_iso = _date_iso(date_raw)
    if not data_iso:
        return None

    desc = historico.strip()
    if favorecido and favorecido not in ("None", ""):
        desc = f"{historico} — {favorecido}"

    tx: Dict[str, Any] = {
        "data": data_iso,
        "descricao": desc,
        "valor": valor,
        "tipo_lancamento": _classify(historico),
    }
    if nr_doc and nr_doc not in ("000000", "None", ""):
        tx["nr_doc"] = nr_doc

    return tx


def _parse_text_fallback(all_text: str) -> List[Dict[str, Any]]:
    """Fallback linha-a-linha quando extract_tables() não retorna dados."""
    transactions = []
    pat = re.compile(
        r'(\d{2}/\d{2}/\d{4})\s*-\s*\d{2}:\d{2}:\d{2}\s+'
        r'(\d+)\s+'
        r'([A-ZÁÉÍÓÚÃÕÇ][A-ZÁÉÍÓÚÃÕÇa-záéíóúãõç /\-]+?)\s+'
        r'([\d.]+,\d{2})\s+([CD])'
    )
    for m in pat.finditer(all_text):
        historico = m.group(3).strip()
        if historico.upper() == "SALDO DIA":
            continue
        val = parse_brl(m.group(4))
        if val is None:
            continue
        if m.group(5).upper() == "D":
            val = -val
        data_iso = _date_iso(m.group(1))
        if not data_iso:
            continue
        transactions.append({
            "data": data_iso,
            "descricao": historico,
            "valor": val,
            "tipo_lancamento": _classify(historico),
        })
    return transactions


# =============================================================================
# Extração via LLM (PDF somente-imagem)
# =============================================================================

_LLM_PROMPT = """Você está analisando um extrato bancário da Caixa Econômica Federal (PDF).
Extraia todos os dados do extrato e retorne APENAS um JSON válido (sem markdown) com esta estrutura:

{
  "numero_conta": "string ou null",
  "titular": "nome do titular ou null",
  "periodo_inicio": "YYYY-MM-DD ou null",
  "periodo_fim": "YYYY-MM-DD ou null",
  "saldo_inicial": número ou null,
  "saldo_final": número ou null,
  "transacoes": [
    {
      "data": "YYYY-MM-DD",
      "descricao": "histórico completo (incluindo favorecido se houver)",
      "valor": número (negativo para débito/saída, positivo para crédito/entrada),
      "tipo_lancamento": "Saída PIX | Entrada PIX | Devolução PIX | Saída TED/Transferência | Entrada TED/Transferência | Pagamento Boleto | Saque | Depósito | Tarifa Bancária | Encargos Bancários | Salário | Transferência | Outros"
    }
  ]
}

Regras:
- Ignore linhas "SALDO DIA" — são marcadores de saldo, não transações reais
- Valores com sufixo "D" (débito) → negativos; "C" (crédito) → positivos
- Datas no formato DD/MM/YYYY → converter para YYYY-MM-DD
- saldo_inicial = valor do campo "SALDO ANTERIOR" (positivo se "C", negativo se "D")
- saldo_final = saldo da última linha de "SALDO DIA" ou última transação
- Não inclua CPF/CNPJ mascarado na descrição"""


def _extract_via_llm(pdf_path: Path, result: Dict[str, Any]) -> bool:
    """Usa visão LLM para extrair dados de PDF somente-imagem.

    Retorna True se a extração teve sucesso.
    """
    try:
        import anthropic
    except ImportError:
        log(LOG_PREFIX, "WARN", "anthropic SDK não instalado — LLM fallback desabilitado")
        return False

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        log(LOG_PREFIX, "WARN", "ANTHROPIC_API_KEY não definida — LLM fallback desabilitado")
        return False

    log(LOG_PREFIX, "INFO", "  PDF sem camada de texto — usando extração via LLM (visão)")

    pdf_bytes = pdf_path.read_bytes()
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    client = anthropic.Anthropic(api_key=api_key, timeout=60.0)
    try:
        response = client.messages.create(
            model=_LLM_MODEL,
            max_tokens=_LLM_MAX_TOKENS,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {"type": "text", "text": _LLM_PROMPT},
                ],
            }],
        )
        raw = response.content[0].text.strip()

        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)

        data = json.loads(raw)
    except json.JSONDecodeError as e:
        log(LOG_PREFIX, "ERROR", f"  LLM retornou JSON inválido: {e}")
        return False
    except Exception as e:
        log(LOG_PREFIX, "ERROR", f"  LLM extração falhou: {e}")
        return False

    # Preenche o result com os dados extraídos
    if data.get("numero_conta"):
        result["numero_conta"] = data["numero_conta"]
    if data.get("titular"):
        result["titular"] = data["titular"]
    if data.get("periodo_inicio"):
        result["periodo"]["inicio"] = data["periodo_inicio"]
    if data.get("periodo_fim"):
        result["periodo"]["fim"] = data["periodo_fim"]
    if data.get("saldo_inicial") is not None:
        result["saldo_inicial"] = data["saldo_inicial"]
    if data.get("saldo_final") is not None:
        result["saldo_final"] = data["saldo_final"]

    for tx in data.get("transacoes", []):
        if not tx.get("data") or tx.get("valor") is None:
            continue
        result["transacoes"].append({
            "data": tx["data"],
            "descricao": tx.get("descricao", ""),
            "valor": float(tx["valor"]),
            "tipo_lancamento": tx.get("tipo_lancamento", "Outros"),
        })

    result["notas"].append("Transações extraídas via LLM (PDF somente-imagem)")
    log(LOG_PREFIX, "INFO", f"  LLM extraiu {len(result['transacoes'])} transações")
    return True


# =============================================================================
# Parser principal
# =============================================================================

def parse_caixa(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Parse Caixa Econômica Federal 'Extrato por período' PDF.

    Tenta extração determinística via pdfplumber primeiro.
    Se o PDF for somente-imagem (sem camada de texto), usa LLM com visão.
    """
    log(LOG_PREFIX, "INFO", f"Parsing Caixa Econômica Federal: {filename}")
    result = make_result_template(BANCO_CAIXA, "extratoconta", "BRL")
    result["tipo_conta"] = "corrente"

    periodo_inicio, periodo_fim = infer_periodo_from_filename(filename)
    result["periodo"]["inicio"] = periodo_inicio
    result["periodo"]["fim"] = periodo_fim

    if pdfplumber is None:
        log(LOG_PREFIX, "WARN", "pdfplumber não instalado — tentando LLM")
        if not _extract_via_llm(pdf_path, result):
            result["notas"].append("pdfplumber e LLM indisponíveis")
            result["requires_llm_fallback"] = True
        return result

    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_text = "\n".join(p.extract_text() or "" for p in pdf.pages)
            has_text = bool(all_text.strip())

            if has_text:
                _extract_from_text(all_text, result)

                saldo_final_candidate = None
                for page in pdf.pages:
                    for table in page.extract_tables() or []:
                        for row in table:
                            if not row:
                                continue
                            cells = [str(c).strip() if c is not None else "" for c in row]
                            if cells[0] in ("Data Mov.", "Data"):
                                continue
                            parsed = _row_to_tx(cells)
                            if parsed is None:
                                continue
                            if "_saldo_dia" in parsed:
                                if parsed["_saldo_dia"] is not None:
                                    saldo_final_candidate = parsed["_saldo_dia"]
                            else:
                                result["transacoes"].append(parsed)

                if saldo_final_candidate is not None:
                    result["saldo_final"] = saldo_final_candidate

                if not result["transacoes"]:
                    log(LOG_PREFIX, "WARN", "  Tabelas vazias — fallback de texto")
                    result["transacoes"] = _parse_text_fallback(all_text)
                    if result["transacoes"]:
                        result["notas"].append("Transações extraídas via fallback de texto")

            if not result["transacoes"]:
                # PDF somente-imagem — delegar para LLM
                if not _extract_via_llm(pdf_path, result):
                    result["requires_llm_fallback"] = True

    except Exception as e:
        log(LOG_PREFIX, "ERROR", f"  Falha ao processar {filename}: {e}")
        result["notas"].append(f"Erro no parsing: {e}")
        result["requires_llm_fallback"] = True

    log(LOG_PREFIX, "INFO", f"  → {len(result['transacoes'])} transações extraídas")
    return result

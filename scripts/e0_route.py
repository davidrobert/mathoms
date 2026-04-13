#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
E0-route — Roteamento automático de arquivos do inbox para diretórios de destino.

Dois modos de classificação:
  Camada 1 (determinística): regex sobre o nome do arquivo
  Camada 2 (LLM fallback):  extrai conteúdo, consulta Claude para classificar

Usage:
  python scripts/e0_route.py                  # Roteia tudo (regex + LLM)
  python scripts/e0_route.py --dry-run        # Apenas mostra o que faria
  python scripts/e0_route.py --no-llm         # Apenas regex, sem fallback LLM
  python scripts/e0_route.py --file X.pdf     # Roteia um arquivo específico

Integração com e_reset.py:
  from e0_route import route_all
  stats = route_all(base_dir, dry_run=False, use_llm=True)

Author: Claude Opus 4.6
Date: 2026-04-09
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths — re-inicializáveis via _init_config()
# ---------------------------------------------------------------------------
_DEFAULT_BASE_DIR = Path(__file__).resolve().parent.parent


def _load_json_config(path: Path, label: str = "") -> dict:
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"  ⚠️  Error loading {label or path.name}: {e}")
    else:
        print(f"  [WARN] {label or path.name} não encontrado — usando defaults hardcoded")
    return {}


def _init_config(base_dir: Path) -> None:
    """(Re-)inicializa paths e configs globais a partir de base_dir."""
    global BASE, INBOX, INBOX_PROCESSED, LOGS, DATA, MEMBERS
    global INST_CONFIG, PIPE_CONFIG, FAMILY_CONFIG
    BASE = base_dir
    INBOX = BASE / "inbox"
    INBOX_PROCESSED = BASE / "inbox_processed"
    LOGS = BASE / "logs"
    DATA = BASE / "data"
    MEMBERS = BASE / "members"
    INST_CONFIG = _load_json_config(BASE / "config" / "institutions.json", "institutions.json")
    PIPE_CONFIG = _load_json_config(BASE / "config" / "pipeline.json", "pipeline.json")
    FAMILY_CONFIG = _load_json_config(BASE / "config" / "family_members.json", "family_members.json")


_init_config(_DEFAULT_BASE_DIR)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
_LOG_LINES: list[str] = []

def log(level: str, msg: str) -> None:
    line = f"[{level}] {msg}"
    print(line)
    _LOG_LINES.append(line)

# ---------------------------------------------------------------------------
# Institution patterns  (Seção 3.1, Passo 2 do manual) — from config
# ---------------------------------------------------------------------------
def _build_institution_patterns() -> list[tuple[re.Pattern, str]]:
    cfg_list = INST_CONFIG.get("institution_patterns", [])
    if cfg_list:
        return [(re.compile(p["regex"], re.I), p["canonical"]) for p in cfg_list]
    print("  [WARN] institution_patterns não encontrado em institutions.json — usando defaults hardcoded")
    return [
        (re.compile(r"c6|carbon|c6bank", re.I),                   "c6bank"),
        (re.compile(r"itau|itaú|personnalite|paoacucar", re.I),   "itau"),
        (re.compile(r"santander|unique", re.I),                    "santander"),
        (re.compile(r"bradesco", re.I),                            "bradesco"),
        (re.compile(r"btg|btgpactual", re.I),                     "btgpactual"),
        (re.compile(r"rico|xp", re.I),                              "rico"),
        (re.compile(r"picpay", re.I),                              "picpay"),
        (re.compile(r"wise|transferwise", re.I),                   "wise"),
        (re.compile(r"bofa|bankofamerica|bank.of.america", re.I), "bankofamerica"),
        (re.compile(r"quintoandar|quinto.andar", re.I),           "quintoandar"),
        (re.compile(r"binance", re.I),                             "binance"),
        (re.compile(r"receita|rfb|irpf", re.I),                   "receitafederal"),
        (re.compile(r"einstein|sociedade.beneficente", re.I),      "einstein"),
    ]

INSTITUTION_PATTERNS = _build_institution_patterns()

# ---------------------------------------------------------------------------
# Document-type patterns  (Seção 3.1, Passo 3 do manual) — from config
# ---------------------------------------------------------------------------
def _build_doc_type_patterns() -> list[tuple[re.Pattern, str, str]]:
    cfg_list = INST_CONFIG.get("doc_type_patterns", [])
    if cfg_list:
        return [(re.compile(p["regex"], re.I), p["type"], p["group"]) for p in cfg_list]
    print("  [WARN] doc_type_patterns não encontrado em institutions.json — usando defaults hardcoded")
    return [
        (re.compile(r"irpf.*declara[cç]", re.I),               "irpfdeclaracao",       "income_tax_br"),
        (re.compile(r"irpf.*recibo|recibo.*irpf", re.I),       "irpfrecibo",           "income_tax_br"),
        (re.compile(r"informe.*rendimento.*aluguel", re.I),    "informerendimentosaluguel", "income_tax_br"),
        (re.compile(r"informe.*rendimento", re.I),              "informerendimentos",   "income_tax_br"),
        (re.compile(r"dados?.?im[oó]ve", re.I),                "dados_imoveis",        "real_estate"),
        (re.compile(r"dados?.?ve[ií]culo|vehicles|carros", re.I), "dados_veiculos",    "vehicles"),
        (re.compile(r"curriculo|resume|cv(?!\d)", re.I),       "curriculo",            "members"),
        (re.compile(r"holerite|contracheque|folha.?pagamento", re.I), "holerite",      "members"),
        (re.compile(r"\brg\b|registro.?geral|identidade", re.I), "rg",                "members"),
        (re.compile(r"\bcpf\b|pessoa.?f[ií]sica", re.I),       "cpf",                 "members"),
        (re.compile(r"passaporte|passport", re.I),              "passaporte",           "members"),
        (re.compile(r"visto\b|visa\b", re.I),                   "visto",               "members"),
        (re.compile(r"certid[aã]o.*nascimento", re.I),         "certidao_nascimento",  "members"),
        (re.compile(r"certid[aã]o.*casamento", re.I),          "certidao_casamento",   "members"),
        (re.compile(r"\bssn\b|social.?security", re.I),         "ssn",                 "members"),
        (re.compile(r"driver|carteira.?motorista", re.I),       "drivers_license",      "members"),
        (re.compile(r"green.?card|resident", re.I),             "green_card",           "members"),
        (re.compile(r"(?:extrato.*)?personnalite", re.I),       "extratocontapersonnalite", "financial_statements"),
        (re.compile(r"extrato.*pj|pj.*extrato", re.I),        "extratocontapj",       "financial_statements"),
        (re.compile(r"extrato.*global.*usd|usd.*global", re.I), "extratocontaglobalusd", "financial_statements"),
        (re.compile(r"extrato.*global.*eur|eur.*global", re.I), "extratocontaglobaleur", "financial_statements"),
        (re.compile(r"extrato.*poupan[cç]a|caderneta|savings", re.I), "extratopoupanca", "financial_statements"),
        (re.compile(r"extrato.*conta.*brl|extratocontabrl", re.I), "extratocontabrl", "financial_statements"),
        (re.compile(r"extrato.*conta.*usd|extratocontausd", re.I), "extratocontausd", "financial_statements"),
        (re.compile(r"extrato.*conta.*eur|extratocontaeur", re.I), "extratocontaeur", "financial_statements"),
        (re.compile(r"extrato|lan[cç]amento|statement", re.I), "extratoconta",         "financial_statements"),
        (re.compile(r"fatura.*carbon", re.I),                   "faturacarbon",         "financial_statements"),
        (re.compile(r"fatura.*unique", re.I),                   "faturaunique",         "financial_statements"),
        (re.compile(r"fatura.*p[aã]o.?a[cç][uú]car", re.I),   "faturapaoacucar",      "financial_statements"),
        (re.compile(r"fatura.*aluguel.*\w+", re.I),              "faturaaluguel",        "financial_statements"),
        (re.compile(r"fatura.*aluguel", re.I),                 "faturaaluguel",        "financial_statements"),
        (re.compile(r"fatura", re.I),                          "fatura",               "financial_statements"),
        (re.compile(r"posi[cç][aã]o|carteira.*invest", re.I), "investimentosposicao", "financial_statements"),
        (re.compile(r"carteira.*renda.?fixa", re.I),           "carteirarendafixa",    "financial_statements"),
        (re.compile(r"cdbdetalhesdi1|cdb.*detalhe.*di.?1", re.I), "cdbdetalhesdi1",  "financial_statements"),
        (re.compile(r"cdbdetalhesdi2|cdb.*detalhe.*di.?2", re.I), "cdbdetalhesdi2",  "financial_statements"),
        (re.compile(r"cdbdetalhesprog|cdb.*detalhe.*prog", re.I), "cdbdetalhesprog",  "financial_statements"),
        (re.compile(r"cdbmetaservas|cdb.*meta.*servas", re.I), "cdbmetaservas",       "financial_statements"),
        (re.compile(r"cdbdi|cdb.*\bdi\b", re.I),               "cdbdi",               "financial_statements"),
        (re.compile(r"renda.?fixa|cdb.*detalhe", re.I),        "cdbdetalhes",         "financial_statements"),
        (re.compile(r"cdb.*resumo|resumo.*cdb", re.I),         "cdbresumo",           "financial_statements"),
        (re.compile(r"cdb", re.I),                              "cdb",                 "financial_statements"),
    ]

DOC_TYPE_PATTERNS = _build_doc_type_patterns()

_doc_type_examples = sorted(
    set(p[1] for p in DOC_TYPE_PATTERNS) | set(INST_CONFIG.get("tipo_aliases", {}).keys())
)
_DOC_TYPE_LIST = ", ".join(_doc_type_examples)

# Period extraction regex — from config
_period_cfg = PIPE_CONFIG.get("period_regex", {})
PERIOD_RE = re.compile(_period_cfg.get("period", r"(\d{6})(?:_(\d{6}))?"))
YEAR_RE   = re.compile(_period_cfg.get("year_fallback", r"(20\d{2})"))

# Member name patterns (for GRUPO E routing) — from config
MEMBER_NAMES = [k for k in FAMILY_CONFIG.get("membros", {}).keys() if not k.startswith("_")]
_TITULAR_KEY = FAMILY_CONFIG.get("titular", MEMBER_NAMES[0] if MEMBER_NAMES else "")

# Pipeline parameters — from config
_file_limits = PIPE_CONFIG.get("file_limits", {})
_PREVIEW_MAX_CHARS = _file_limits.get("preview_max_chars", 2000)
_PREVIEW_MAX_ROWS = _file_limits.get("preview_max_rows", 20)
_MIN_PDF_BYTES = _file_limits.get("min_pdf_bytes", 1024)

_llm_cfg = PIPE_CONFIG.get("llm", {})
_LLM_MODEL = _llm_cfg.get("model", "claude-sonnet-4-20250514")
_LLM_MAX_TOKENS = _llm_cfg.get("max_tokens", 500)
_LLM_CONFIDENCE_THRESHOLD = _llm_cfg.get("confidence_threshold", 0.7)

# ---------------------------------------------------------------------------
# Camada 1 — Classificação determinística por regex
# ---------------------------------------------------------------------------

def detect_institution(filename: str) -> str | None:
    """Detect institution from filename. Returns entity code or None."""
    for pattern, entity in INSTITUTION_PATTERNS:
        if pattern.search(filename):
            return entity
    return None


def detect_doc_type(filename: str) -> tuple[str, str] | None:
    """Detect document type from filename.
    Returns (type_code, destination_group) or None."""
    for pattern, type_code, dest_group in DOC_TYPE_PATTERNS:
        if pattern.search(filename):
            return type_code, dest_group
    return None


def extract_period(filename: str) -> str:
    """Extract period from filename. Returns YYYYMM, YYYYMM_YYYYMM, YYYY, or today's date."""
    m = PERIOD_RE.search(filename)
    if m:
        if m.group(2):
            return f"{m.group(1)}_{m.group(2)}"
        return m.group(1)
    m = YEAR_RE.search(filename)
    if m:
        return m.group(1)
    return date.today().strftime("%Y%m%d")


def detect_member(filename: str) -> str | None:
    """Detect which family member a file belongs to (for GRUPO E)."""
    lower = filename.lower()
    for name in MEMBER_NAMES:
        if name in lower:
            return name
    return None


def classify_by_name(filename: str) -> dict | None:
    """Camada 1: Classify file by filename patterns.
    Returns dict with keys: institution, doc_type, dest_group, period, member
    or None if unrecognized."""
    institution = detect_institution(filename)
    type_result = detect_doc_type(filename)

    if type_result is None:
        return None

    doc_type, dest_group = type_result
    period = extract_period(filename)
    member = detect_member(filename)

    # Special: einstein holerites go to members/
    if institution == "einstein" and doc_type == "holerite":
        dest_group = "members"
        institution = None  # member name is the prefix for members/

    return {
        "institution": institution,
        "doc_type": doc_type,
        "dest_group": dest_group,
        "period": period,
        "member": member,
        "source": "regex",
    }


# ---------------------------------------------------------------------------
# Camada 2 — Classificação por LLM (fallback)
# ---------------------------------------------------------------------------

def _extract_file_preview(filepath: Path, max_chars: int = _PREVIEW_MAX_CHARS) -> str:
    """Extract text preview from file for LLM classification."""
    ext = filepath.suffix.lower()

    if ext == ".pdf":
        try:
            import pdfplumber
            with pdfplumber.open(filepath) as pdf:
                text = ""
                for page in pdf.pages[:3]:
                    text += (page.extract_text() or "") + "\n"
                    if len(text) >= max_chars:
                        break
                return text[:max_chars]
        except Exception as e:
            return f"[Erro ao ler PDF: {e}]"

    elif ext in (".xls", ".xlsx"):
        try:
            if ext == ".xlsx":
                import openpyxl
                wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
                ws = wb.active
                rows = []
                for i, row in enumerate(ws.iter_rows(values_only=True)):
                    rows.append(" | ".join(str(c) if c is not None else "" for c in row))
                    if i > _PREVIEW_MAX_ROWS:
                        break
                wb.close()
                return "\n".join(rows)[:max_chars]
            else:
                import xlrd
                wb = xlrd.open_workbook(filepath)
                ws = wb.sheet_by_index(0)
                rows = []
                for i in range(min(ws.nrows, _PREVIEW_MAX_ROWS)):
                    rows.append(" | ".join(str(ws.cell_value(i, j)) for j in range(ws.ncols)))
                return "\n".join(rows)[:max_chars]
        except Exception as e:
            return f"[Erro ao ler planilha: {e}]"

    elif ext == ".csv":
        try:
            return filepath.read_text(encoding="utf-8", errors="replace")[:max_chars]
        except Exception as e:
            return f"[Erro ao ler CSV: {e}]"

    elif ext in (".jpg", ".jpeg", ".png"):
        return f"[Imagem {ext} — classificar apenas pelo nome do arquivo]"

    else:
        try:
            return filepath.read_text(encoding="utf-8", errors="replace")[:max_chars]
        except Exception:
            return "[Arquivo binário — não pode ser lido como texto]"


def classify_by_llm(filepath: Path) -> dict | None:
    """Camada 2: Use Claude to classify an unrecognized file.
    Returns dict compatible with classify_by_name output, or None if low confidence."""
    try:
        import anthropic
    except ImportError:
        log("WARN", "anthropic SDK não instalado. LLM fallback desabilitado. pip install anthropic")
        return None

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        log("WARN", "ANTHROPIC_API_KEY não definida. LLM fallback desabilitado.")
        return None

    preview = _extract_file_preview(filepath)
    filename = filepath.name

    member_options = " | ".join(MEMBER_NAMES) if MEMBER_NAMES else "unknown"
    prompt = f"""Analise o arquivo abaixo e classifique para roteamento no pipeline financeiro familiar.

Nome do arquivo: {filename}
Extensão: {filepath.suffix}
Tamanho: {filepath.stat().st_size} bytes

Conteúdo (preview):
---
{preview}
---

Classifique o arquivo retornando APENAS um JSON válido (sem markdown) com estes campos:
{{
  "institution": "código da instituição (c6bank, itau, santander, bradesco, btgpactual, rico, picpay, wise, bankofamerica, quintoandar, binance, receitafederal) ou null",
  "doc_type": "código do tipo ({_DOC_TYPE_LIST}, etc.)",
  "dest_group": "financial_statements | income_tax_br | real_estate | vehicles | members | income_tax_us",
  "period": "YYYYMM ou YYYYMM_YYYYMM ou YYYY",
  "member": "{member_options} | null",
  "final_name": "nome final completo no padrão [instituição]_[tipo]_[período]-0_original.[ext]",
  "confidence": 0.0 a 1.0
}}

Regras:
- Período deve ser extraído do conteúdo se não estiver no nome
- Se não conseguir identificar, use confidence < 0.5
- Para imagens (JPG/PNG), classifique pelo nome e contexto se possível
- Member é relevante apenas para GRUPO E (members/) — documentos pessoais
"""

    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model=_LLM_MODEL,
            max_tokens=_LLM_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()

        # Parse JSON — handle markdown-wrapped responses
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)

        result = json.loads(raw)
        confidence = result.get("confidence", 0)

        if confidence < _LLM_CONFIDENCE_THRESHOLD:
            log("INFO", f"LLM classificou '{filename}' com confiança baixa ({confidence:.1%}) — nao_identificados/")
            return None

        log("INFO", f"LLM classificou '{filename}' → {result.get('dest_group')}/{result.get('final_name')} (confiança {confidence:.0%})")
        result["source"] = "llm"
        return result

    except Exception as e:
        log("ERROR", f"LLM fallback falhou para '{filename}': {e}")
        return None


# ---------------------------------------------------------------------------
# File operations
# ---------------------------------------------------------------------------

def file_hash(filepath: Path) -> str:
    """SHA-256 hash of file content."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def build_final_name(classification: dict, original_ext: str) -> str:
    """Build the standardized filename from classification result."""
    # If LLM gave a final_name, sanitize and use it
    if classification.get("source") == "llm" and classification.get("final_name"):
        sanitized = Path(classification["final_name"]).name
        if sanitized and ".." not in sanitized:
            return sanitized

    parts = []
    dest_group = classification["dest_group"]

    if dest_group == "members":
        member = classification.get("member") or _TITULAR_KEY
        doc_type = classification["doc_type"]
        period = classification.get("period", "")
        if period and doc_type in ("holerite",):
            parts = [f"{member}_{doc_type}_{period}-0_original{original_ext}"]
        else:
            parts = [f"{member}_{doc_type}-0_original{original_ext}"]
    elif dest_group in ("real_estate", "vehicles"):
        doc_type = classification["doc_type"]
        parts = [f"{doc_type}-0_original{original_ext}"]
    else:
        institution = classification.get("institution") or "unknown"
        doc_type = classification["doc_type"]
        period = classification.get("period", date.today().strftime("%Y%m%d"))
        # Preserve member suffix for income_tax_br and informe docs (e.g., IRPF[mariana], informerendimentosaluguel[mariana])
        member = classification.get("member")
        member_suffix = ""
        if member and dest_group == "income_tax_br" and member != _TITULAR_KEY:
            member_suffix = member  # e.g., irpfdeclaracaomariana, informerendimentosaluguelmariana
        if member_suffix:
            parts = [f"{institution}_{doc_type}{member_suffix}_{period}-0_original{original_ext}"]
        else:
            parts = [f"{institution}_{doc_type}_{period}-0_original{original_ext}"]

    return parts[0]


def resolve_collision(dest_path: Path, src_hash: str) -> Path | None:
    """Handle name collisions per manual rules (Passo 7).
    Returns the final destination path, or None if duplicate."""
    if not dest_path.exists():
        return dest_path

    existing_hash = file_hash(dest_path)
    if existing_hash == src_hash:
        log("INFO", f"DUPLICATA IGNORADA: '{dest_path.name}' (hash idêntico)")
        return None

    # Collision — different content, same name. Apply letter suffix.
    stem = dest_path.stem  # e.g. "itau_extratoconta_202603-0_original"
    ext = dest_path.suffix

    # Parse: everything before "-0_original" is the base
    m = re.match(r"^(.+?)(-0_original)$", stem)
    if not m:
        # Fallback if pattern doesn't match
        m = re.match(r"^(.+)$", stem)
        base = m.group(1) if m else stem
        suffix_tag = ""
    else:
        base = m.group(1)
        suffix_tag = m.group(2)

    # Check if existing already has a letter suffix
    letter_match = re.match(r"^(.+?)([a-z])$", base)
    if not letter_match:
        # Rename existing to add 'a'
        new_existing = dest_path.parent / f"{base}a{suffix_tag}{ext}"
        if not new_existing.exists():
            log("INFO", f"COLISÃO: renomeando existente '{dest_path.name}' → '{new_existing.name}'")
            dest_path.rename(new_existing)
        base_for_new = base
        next_letter = "b"
    else:
        base_for_new = letter_match.group(1)
        last_letter = letter_match.group(2)
        next_letter = chr(ord(last_letter) + 1)

    new_path = dest_path.parent / f"{base_for_new}{next_letter}{suffix_tag}{ext}"
    while new_path.exists():
        next_letter = chr(ord(next_letter) + 1)
        new_path = dest_path.parent / f"{base_for_new}{next_letter}{suffix_tag}{ext}"

    log("INFO", f"COLISÃO: novo arquivo receberá sufixo '{next_letter}' → '{new_path.name}'")
    return new_path


def dest_dir_for_group(base: Path, group: str) -> Path:
    """Map destination group to actual directory."""
    if group == "members":
        return base / "members"
    return base / "data" / group


# ---------------------------------------------------------------------------
# Core routing
# ---------------------------------------------------------------------------

def route_file(filepath: Path, base: Path, *, dry_run: bool = False,
               use_llm: bool = True, today: str | None = None) -> dict:
    """Route a single file from inbox to its destination.
    Returns a status dict."""
    today = today or date.today().isoformat()
    filename = filepath.name
    ext = filepath.suffix.lower()

    # Validate integrity (Passo 8a)
    size = filepath.stat().st_size
    min_size = _MIN_PDF_BYTES if ext == ".pdf" else 1  # PDFs < threshold are suspect
    if size < min_size:
        log("WARN", f"Arquivo '{filename}' muito pequeno ({size} bytes) — NÃO roteado")
        return {"file": filename, "status": "skipped", "reason": f"too_small ({size}B)"}

    # Camada 1: regex
    classification = classify_by_name(filename)

    # Camada 2: LLM fallback
    if classification is None and use_llm:
        log("INFO", f"Regex não identificou '{filename}' — tentando LLM...")
        classification = classify_by_llm(filepath)

    if classification is None:
        # Não identificado
        nao_id_dir = base / "inbox_processed" / today / "nao_identificados"
        if not dry_run:
            nao_id_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(filepath), str(nao_id_dir / filename))
        log("WARN", f"NÃO IDENTIFICADO: '{filename}' → nao_identificados/")
        return {"file": filename, "status": "unidentified", "dest": "nao_identificados/"}

    # Build final name
    final_name = build_final_name(classification, ext)
    dest_group = classification["dest_group"]
    dest_directory = dest_dir_for_group(base, dest_group)
    dest_path = dest_directory / final_name

    # Hash for collision detection
    src_hash = file_hash(filepath)

    # Resolve collisions
    resolved = resolve_collision(dest_path, src_hash)
    if resolved is None:
        # Duplicate — audit copy only
        audit_dir = base / "inbox_processed" / today
        if not dry_run:
            audit_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(filepath), str(audit_dir / filename))
            filepath.unlink()
        return {"file": filename, "status": "duplicate", "dest": final_name}

    dest_path = resolved
    final_name = dest_path.name

    if dry_run:
        log("INFO", f"[DRY-RUN] '{filename}' → {dest_group}/{final_name} ({classification['source']})")
        return {
            "file": filename, "status": "would_route",
            "dest": f"{dest_group}/{final_name}",
            "source": classification["source"],
        }

    # Audit copy (nome original)
    audit_dir = base / "inbox_processed" / today
    audit_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(filepath), str(audit_dir / filename))

    # Move to destination
    dest_directory.mkdir(parents=True, exist_ok=True)
    shutil.move(str(filepath), str(dest_path))

    log("INFO", f"ROTEADO: '{filename}' → {dest_group}/{final_name} ({classification['source']})")
    return {
        "file": filename, "status": "routed",
        "dest": f"{dest_group}/{final_name}",
        "source": classification["source"],
    }


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def route_all(base: Path | None = None, *, dry_run: bool = False,
              use_llm: bool = True, file_filter: str | None = None) -> dict:
    """Route all files in inbox. Returns summary stats dict.
    Importable by e_reset.py."""
    base = base or BASE
    inbox = base / "inbox"
    today = date.today().isoformat()

    if not inbox.exists():
        log("ERROR", f"Inbox não encontrado: {inbox}")
        return {"total": 0, "error": "inbox_not_found"}

    # Collect files (skip hidden, skip directories)
    if file_filter:
        target = (inbox / file_filter).resolve()
        if not str(target).startswith(str(inbox.resolve())):
            log("ERROR", f"Caminho inválido (fora do inbox): {file_filter}")
            return {"total": 0, "error": "invalid_path"}
        files = [target]
        if not files[0].exists():
            log("ERROR", f"Arquivo não encontrado: {file_filter}")
            return {"total": 0, "error": "file_not_found"}
    else:
        files = sorted(
            [f for f in inbox.iterdir() if f.is_file() and not f.name.startswith(".")],
            key=lambda f: f.name,
        )

    if not files:
        log("INFO", "Inbox vazio — nada a rotear.")
        return {"total": 0, "routed": 0, "duplicates": 0, "unidentified": 0, "skipped": 0}

    log("INFO", f"{'[DRY-RUN] ' if dry_run else ''}Iniciando roteamento de {len(files)} arquivo(s)...")

    stats = {"total": len(files), "routed": 0, "duplicates": 0, "unidentified": 0,
             "skipped": 0, "details": [],
             "by_dest": {"financial_statements": 0, "income_tax_br": 0,
                         "real_estate": 0, "vehicles": 0, "members": 0,
                         "income_tax_us": 0}}

    for filepath in files:
        result = route_file(filepath, base, dry_run=dry_run, use_llm=use_llm, today=today)
        stats["details"].append(result)

        status = result["status"]
        if status in ("routed", "would_route"):
            stats["routed"] += 1
            # Count by destination
            dest = result.get("dest", "")
            for group in stats["by_dest"]:
                if dest.startswith(group):
                    stats["by_dest"][group] += 1
                    break
        elif status == "duplicate":
            stats["duplicates"] += 1
        elif status == "unidentified":
            stats["unidentified"] += 1
        elif status == "skipped":
            stats["skipped"] += 1

    # Write inbox_log entry
    if not dry_run:
        _write_inbox_log(base, today, stats)

    # Summary
    prefix = "[DRY-RUN] " if dry_run else ""
    log("INFO", f"{prefix}Roteamento concluído: {stats['routed']} roteados, "
        f"{stats['duplicates']} duplicatas, {stats['unidentified']} não identificados, "
        f"{stats['skipped']} pulados")

    return stats


def _write_inbox_log(base: Path, today: str, stats: dict) -> None:
    """Append routing summary to inbox_log.md (Seção 3.3 do manual)."""
    logs_dir = base / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "inbox_log.md"

    by_dest = stats["by_dest"]
    entry = f"""
## Ciclo {today} — {stats['total']} arquivos recebidos (e0_route.py)

### Resumo

| Métrica | Valor |
|---|---|
| Arquivos detectados | {stats['total']} |
| Roteados com sucesso | {stats['routed']} |
| Duplicatas ignoradas | {stats['duplicates']} |
| Não identificados | {stats['unidentified']} |
| Pulados (integridade) | {stats['skipped']} |
| financial_statements/ | {by_dest['financial_statements']} |
| income_tax_br/ | {by_dest['income_tax_br']} |
| real_estate/ | {by_dest['real_estate']} |
| vehicles/ | {by_dest['vehicles']} |
| members/ | {by_dest['members']} |

"""
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(root_dir: Path = None):
    if root_dir:
        _init_config(root_dir)
    parser = argparse.ArgumentParser(
        description="E0-route — Roteamento automático de arquivos do inbox",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Apenas mostra o que faria, sem mover arquivos")
    parser.add_argument("--no-llm", action="store_true",
                        help="Desabilita fallback LLM (apenas regex)")
    parser.add_argument("--file", type=str, default=None,
                        help="Roteia um arquivo específico do inbox")
    parser.add_argument("--base", type=str, default=None,
                        help="Diretório base do projeto (default: auto-detect)")

    args = parser.parse_args()
    base = Path(args.base) if args.base else BASE

    stats = route_all(
        base=base,
        dry_run=args.dry_run,
        use_llm=not args.no_llm,
        file_filter=args.file,
    )

    # Exit code
    if stats.get("error"):
        sys.exit(1)
    if stats["unidentified"] > 0:
        sys.exit(2)  # Partial success
    sys.exit(0)


if __name__ == "__main__":
    main()

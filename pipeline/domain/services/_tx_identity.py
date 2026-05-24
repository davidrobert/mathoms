"""Identidade determinística de transações para dedup cross-document (ADR-255)."""

from __future__ import annotations

import hashlib
import re
import unicodedata

_WHITESPACE_RE = re.compile(r"\s+")

# ADR-255 iteração 2-3 — sufixos de roteamento que o mesmo banco emite de
# forma inconsistente entre PDFs (extratos cumulativos do C6 omitem ou incluem
# o tag conforme a versão). Strip antes do hash para que extratos sobrepostos
# colapsem corretamente. Whitelist conservadora — só remove o segmento FINAL
# após ` — ` (em-dash com espaços) ou ` - ` (hífen com espaços), preservando
# descrições legítimas com em-dash no meio (ex.: "Aluguel apto 12").
#
# Iteração 3 (2026-05-24, ADR-255 it.3): observação em prod do report
# b042c210 mostrou 3 novos padrões não-cobertos pela it.2:
# (a) CPF/CNPJ + nome remetente em TED inbound (` — 27788253634-JAIR DE SOUZA`)
# (b) Placa Mercosul/legacy + local em C6TAG (` — GDK6A27-AEROPORTO DE...`)
# (c) Descritor cliente livre tipo `— Salários PJ` extendido (` — mentoria 4Valor unitário...`)
# (a) e (b) têm pattern estável; (c) ficou fora (texto livre cliente é frágil).
_ROUTING_SUFFIX_RE = re.compile(
    r"""
    \s*[—-]\s*           # separador ` — ` ou ` - ` (com whitespace ao redor)
    (?:
        TRANSF\ ENVIADA\ PIX            # C6 — débito PIX outbound
        | SAL[ÁA]RIOS?\ PJ              # C6 — receita PJ recorrente
        | 13\ SAL[ÁA]RIO                # C6 — décimo terceiro
        | BOLETO                        # C6 — pagamento boleto
        | NFS?\s+\d+                    # C6 — NF/NFS numerada (NFS 25, NF 26)
        # ADR-255 it.3: CPF (11 dígitos) ou CNPJ (14) + traço + nome PF/PJ.
        # Pattern restrito: começa com dígitos, traço, depois nome em maiúsculas.
        | \d{11,14}-[A-Z][A-Z\s]*[A-Z]
        # ADR-255 it.3: placa brasileira (Mercosul ABC1D23 ou legacy ABC1234)
        # + traço + local em maiúsculas (C6TAG ESTACIONAMENTO).
        | [A-Z]{3}\d[A-Z\d]\d{2}-[A-Z][A-Z\s]*[A-Z]
    )
    \s*$                  # opcional trailing whitespace + fim de string
    """,
    re.IGNORECASE | re.VERBOSE,
)

# DARF detalhada — C6 às vezes anexa "SIMPLES NACIONAL" no fim sem separador.
# Trato à parte porque não casa o padrão ` — sufixo` (sem em-dash).
_DARF_DETAIL_RE = re.compile(r"\s+SIMPLES\s+NACIONAL\s*$", re.IGNORECASE)


def _strip_accents(text: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn"
    )


def _strip_routing_suffixes(text: str) -> str:
    """Remove sufixos de roteamento bancário do final da descrição (ADR-255 it.2)."""
    # Aplicado antes do lowercase+whitespace-collapse: preserva conteúdo de
    # negócio (remetente/destinatário, parcela N/M, nome próprio).
    text = _ROUTING_SUFFIX_RE.sub("", text)
    text = _DARF_DETAIL_RE.sub("", text)
    return text


def normalize_banco(value: str | None) -> str:
    """Robust contra drift de casing/espacing (`"C6Bank"` vs `"C6 Bank"`)."""
    if not value:
        return ""
    return _WHITESPACE_RE.sub("", _strip_accents(value).lower())


def normalize_titular(value: str | None) -> str:
    if not value:
        return ""
    return _WHITESPACE_RE.sub("", _strip_accents(value).lower())


def normalize_tipo_conta(value: str | None) -> str:
    if not value:
        return ""
    return _WHITESPACE_RE.sub("", _strip_accents(value).lower())


def normalize_descricao(value: str | None) -> str:
    """Lowercase + strip + collapse whitespace + strip sufixos PIX (ADR-255 it.2)."""
    if not value:
        return ""
    # ADR-255 it.2: strip sufixos de roteamento ANTES do lowercase para que
    # extratos sobrepostos do C6 (mesma tx com/sem " — Salários PJ" / etc.)
    # produzam o mesmo hash. Lista finita em _ROUTING_SUFFIX_RE.
    stripped = _strip_routing_suffixes(value.strip())
    return _WHITESPACE_RE.sub(" ", stripped.lower())


def cents_int(valor: float | int) -> int:
    """Converte ``valor`` para int em centavos (evita float drift, ADR-090 §wire)."""
    return int(round(float(valor) * 100))


def compute_transaction_hash(
    *,
    data: str | None,
    banco: str | None,
    titular: str | None,
    tipo_conta: str | None,
    valor: float | int,
    descricao: str | None,
) -> str:
    """sha256[:16] determinístico — chave K4 da ADR-255 (sinal em ``kind``)."""
    parts = (
        data or "",
        normalize_banco(banco),
        normalize_titular(titular),
        normalize_tipo_conta(tipo_conta),
        str(cents_int(abs(valor))),
        normalize_descricao(descricao),
    )
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]

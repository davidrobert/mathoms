"""Gate de PII no view-model do relatório ([[ADR-337]] critério 4 · A40.l6).

Varre campos de descrição do payload que o React/PDF consomem. Não imprime o
valor casado — só o dot-path e o tipo (mesma disciplina de ``lint_no_real_pii``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pipeline.observability.pii_patterns import contains_identifier, scrub_identifiers

DESCRIPTION_KEYS = frozenset({"descricao", "detalhe"})

_CONTRATO = re.compile(
    r"(?i)\b(matr[íi]cula|contrato|inscri[cç][aã]o)\s*(?:n[ºo°.]?\s*)?([\d][\d./-]{5,})"
)
_CEP = re.compile(r"\b\d{5}-?\d{3}\b")
_ENDERECO = re.compile(
    r"\b(?:(?i:Rua|Avenida|Pra[çc]a|Alameda|Travessa)|[Aa][Vv]\.?)\s+"
    r"[A-ZÀ-Ü][\wÀ-ü.]*(?:\s+[\wÀ-ü.]+){0,5},?\s+\d{1,5}\b"
)

_TOKEN_CONTRATO = "[matricula-redigida]"
_TOKEN_CEP = "[cep-redigido]"
_TOKEN_ENDERECO = "[endereco-redigido]"


@dataclass(frozen=True)
class ViewModelPiiHit:
    path: str
    tipo: str

    def format(self) -> str:
        return f"{self.path}: {self.tipo}"


def redact_cartorial(text: str) -> str:
    """Remove identificadores cartoriais do texto; idempotente."""
    out = scrub_identifiers(text)
    out = _CONTRATO.sub(_TOKEN_CONTRATO, out)
    out = _CEP.sub(_TOKEN_CEP, out)
    return _ENDERECO.sub(_TOKEN_ENDERECO, out)


def cartorial_pii_tipos(text: str) -> tuple[str, ...]:
    """Tipos presentes no texto, sem devolver o match."""
    found: list[str] = []
    if contains_identifier(text):
        found.append("IDENTIFICADOR")
    if _CONTRATO.search(text):
        found.append("MATRICULA")
    if _ENDERECO.search(text):
        found.append("ENDERECO")
    if _CEP.search(text):
        found.append("CEP")
    return tuple(found)


def scan_view_model_pii(
    payload: object, *, keys: frozenset[str] | None = None
) -> tuple[ViewModelPiiHit, ...]:
    """Percorre o payload e aponta descrições com PII cartorial."""
    scanned_keys = DESCRIPTION_KEYS if keys is None else keys
    hits: list[ViewModelPiiHit] = []
    _walk(payload, "", scanned_keys, hits)
    return tuple(hits)


def _record_if_description(
    key: str, value: object, child: str, keys: frozenset[str], hits: list[ViewModelPiiHit]
) -> bool:
    if key not in keys or not isinstance(value, str):
        return False
    hits.extend(ViewModelPiiHit(path=child, tipo=tipo) for tipo in cartorial_pii_tipos(value))
    return True


def _walk_dict(node: dict, path: str, keys: frozenset[str], hits: list[ViewModelPiiHit]) -> None:
    for key, value in node.items():
        child = f"{path}.{key}" if path else str(key)
        if not _record_if_description(key, value, child, keys, hits):
            _walk(value, child, keys, hits)


def _walk_list(node: list, path: str, keys: frozenset[str], hits: list[ViewModelPiiHit]) -> None:
    for idx, item in enumerate(node):
        _walk(item, f"{path}[{idx}]", keys, hits)


def _walk(node: object, path: str, keys: frozenset[str], hits: list[ViewModelPiiHit]) -> None:
    if isinstance(node, dict):
        _walk_dict(node, path, keys, hits)
        return
    if isinstance(node, list):
        _walk_list(node, path, keys, hits)


__all__ = [
    "DESCRIPTION_KEYS",
    "ViewModelPiiHit",
    "cartorial_pii_tipos",
    "redact_cartorial",
    "scan_view_model_pii",
]

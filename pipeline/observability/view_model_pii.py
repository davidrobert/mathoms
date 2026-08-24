"""Gate de PII no view-model do relatório ([[ADR-337]] critério 4 · A40.l6).

Varre **toda string** do payload que o React/PDF consomem — não uma allowlist de
chave. O allowlist era o ponto cego: o fix do #1569 tirou a PII de ``descricao`` e
a pôs em ``endereco_canonical``, que o gate não varria (§Ataque A1). Predicado que
chaveia no VALOR segue o dado quando o render muda de campo; predicado que chaveia
no NOME do campo não. Custo medido: 631 strings nas 6 fixtures de relatório do
repo, 2 hits, zero falso-positivo.

Não imprime o valor casado — só o dot-path e o tipo (disciplina de
``lint_no_real_pii``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pipeline.observability.pii_patterns import (
    contains_bare_identifier,
    contains_identifier,
    scrub_bare_identifiers,
    scrub_identifiers,
)

# `[^\d\n]{0,14}` entre o rótulo e o número: cobre "(IPTU): ", " nº ", ". ".
# Sem isso, "INSCRICAO MUNICIPAL (IPTU): 999.999" atravessava (§Ataque A6).
_CONTRATO = re.compile(
    r"(?i)\b(matr[íi]cula|matr\.|contrato|inscri[cç][aã]o(?:\s+municipal)?|iptu)"
    r"[^\d\n]{0,14}([\d][\d./-]{4,})"
)
_CEP = re.compile(r"\b\d{5}-?\d{3}\b")
# Abreviações são a forma comum em descrição de IRPF; só `Av.` estava coberta.
_ENDERECO = re.compile(
    r"(?i)\b(?:rua|avenida|pra[çc]a|alameda|travessa|estrada|rodovia|av\.|r\.|"
    r"trav\.|al\.|p[çc]\.|rod\.|est\.)\s+"
    r"[\wÀ-ü.]+(?:\s+[\wÀ-ü.]+){0,5},?\s+\d{1,5}\b"
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
    out = scrub_bare_identifiers(scrub_identifiers(text))
    out = _CONTRATO.sub(_TOKEN_CONTRATO, out)
    out = _CEP.sub(_TOKEN_CEP, out)
    return _ENDERECO.sub(_TOKEN_ENDERECO, out)


def cartorial_pii_tipos(text: str) -> tuple[str, ...]:
    """Tipos presentes no texto, sem devolver o match."""
    found: list[str] = []
    if contains_identifier(text) or contains_bare_identifier(text):
        found.append("IDENTIFICADOR")
    if _CONTRATO.search(text):
        found.append("MATRICULA")
    if _ENDERECO.search(text):
        found.append("ENDERECO")
    if _CEP.search(text):
        found.append("CEP")
    return tuple(found)


def scan_view_model_pii(payload: object) -> tuple[ViewModelPiiHit, ...]:
    """Percorre o payload e aponta QUALQUER string com PII cartorial."""
    hits: list[ViewModelPiiHit] = []
    _walk(payload, "", hits)
    return tuple(hits)


# Redigir só no produtor deixa exposto tudo que já está gravado: o relatório
# re-renderiza artefato ARMAZENADO, e o anterior ao fix carrega a descrição
# cartorial crua que `/reports/{id}/data` serve (A40.l6). Leitura e escrita
# passam a usar a MESMA definição de PII — duas divergiriam. No-op sobre
# payload limpo: só reescreve string que o scanner acusaria.
def redact_view_model(node: object) -> object:
    """Gêmeo de escrita de ``scan_view_model_pii`` — redige o que ele acusaria."""
    if isinstance(node, dict):
        return {key: redact_view_model(value) for key, value in node.items()}
    if isinstance(node, list):
        return [redact_view_model(item) for item in node]
    if isinstance(node, str) and cartorial_pii_tipos(node):
        return redact_cartorial(node)
    return node


def _walk(node: object, path: str, hits: list[ViewModelPiiHit]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            _walk(value, f"{path}.{key}" if path else str(key), hits)
        return
    if isinstance(node, list):
        for idx, item in enumerate(node):
            _walk(item, f"{path}[{idx}]", hits)
        return
    if isinstance(node, str):
        hits.extend(ViewModelPiiHit(path=path, tipo=tipo) for tipo in cartorial_pii_tipos(node))


__all__ = [
    "ViewModelPiiHit",
    "cartorial_pii_tipos",
    "redact_cartorial",
    "redact_view_model",
    "scan_view_model_pii",
]

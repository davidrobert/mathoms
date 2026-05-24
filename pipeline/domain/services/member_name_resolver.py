"""Normaliza ``membro`` emitido pelo LLM em chave canônica (ADR-243 + ADR-267)."""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal, Optional

from pipeline.domain.services._cpf_identity import normalize_cpf

_logger = logging.getLogger("mathoms.pipeline.member_name_resolver")

Confidence = Literal[
    "cpf",  # ADR-267 — estratégia 0, identidade primária via CPF normalizado
    "exact",
    "full_name",
    "short_name",
    "nome_nascimento",
    "substring",
    "ambiguous",
    "unknown",
]

_MIN_SUBSTRING_LEN = 5


@dataclass(frozen=True)
class MemberRecord:
    """Snapshot tipado de uma linha de ``family_members`` para resolução."""

    key: str
    full_name: str = ""
    short_name: str = ""
    nome_nascimento: str = ""
    cpf: str = ""  # ADR-267: CPF normalizado (11 dígitos, sem máscara) ou vazio


@dataclass(frozen=True)
class MemberNameResolution:
    """Resultado de ``MemberNameResolver.resolve``."""

    canonical_key: Optional[str]
    confidence: Confidence
    matched_via: str = ""  # campo do record que casou (key/full_name/...)


def _slugify(text: str) -> str:
    """Slug ASCII canônico — minúsculo, sem acentos, separador ``_``."""
    if not text:
        return ""
    t = unicodedata.normalize("NFKD", str(text))
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower().strip()
    t = re.sub(r"[^a-z0-9_]+", "_", t)
    t = re.sub(r"_+", "_", t).strip("_")
    return t


class MemberNameResolver:
    """Resolve nome bruto → ``family_members.key`` canônica (ADR-243)."""

    def __init__(self, members: Iterable[MemberRecord]) -> None:
        self._members: list[MemberRecord] = list(members)
        self._slug_index: dict[str, list[tuple[MemberRecord, str]]] = {}
        # ADR-267: index CPF → MemberRecord para resolução O(1) por estratégia 0.
        # Membros sem CPF não entram no índice; resolver cai no name fallback.
        self._cpf_index: dict[str, MemberRecord] = {}
        for m in self._members:
            self._index_member(m)

    def _index_member(self, m: MemberRecord) -> None:
        """Popula slug_index + cpf_index para 1 record (chamado por __init__)."""
        for field_name, value in (
            ("key", m.key),
            ("full_name", m.full_name),
            ("short_name", m.short_name),
            ("nome_nascimento", m.nome_nascimento),
        ):
            slug = _slugify(value)
            if not slug:
                continue
            self._slug_index.setdefault(field_name, []).append((m, slug))
        cpf_norm = normalize_cpf(m.cpf)
        if cpf_norm:
            self._cpf_index[cpf_norm] = m

    @classmethod
    def from_family_config(cls, family: dict[str, Any] | None) -> "MemberNameResolver":
        """Constrói a partir do ``family_members.json`` (ou DB equivalente)."""
        records: list[MemberRecord] = []
        fam = family or {}
        membros = fam.get("membros") or {}
        if isinstance(membros, dict):
            for key, raw in membros.items():
                if not isinstance(raw, dict):
                    continue
                records.append(
                    MemberRecord(
                        key=str(key),
                        full_name=str(raw.get("nome") or ""),
                        short_name=str(raw.get("nome_curto") or ""),
                        nome_nascimento=str(
                            raw.get("nome_nascimento")
                            or (raw.get("extra") or {}).get("nome_nascimento")
                            or ""
                        ),
                        # ADR-267: extrai CPF (com/sem máscara); normaliza no índice.
                        cpf=str(raw.get("cpf") or ""),
                    )
                )
        elif isinstance(membros, list):
            for raw in membros:
                if not isinstance(raw, dict):
                    continue
                key = str(raw.get("key") or raw.get("id") or "")
                if not key:
                    continue
                records.append(
                    MemberRecord(
                        key=key,
                        full_name=str(raw.get("full_name") or raw.get("nome") or ""),
                        short_name=str(raw.get("short_name") or raw.get("nome_curto") or ""),
                        nome_nascimento=str(
                            (raw.get("extra") or {}).get("nome_nascimento")
                            or raw.get("nome_nascimento")
                            or ""
                        ),
                        cpf=str(raw.get("cpf") or ""),  # ADR-267
                    )
                )
        return cls(records)

    # -- API --

    def resolve_by_cpf(self, cpf_raw: Optional[str] = None) -> MemberNameResolution:
        """Resolve por CPF normalizado — confidence='cpf' (ADR-267 estratégia 0)."""
        # CPF é invariante imutável (sobrevive a casamento/divórcio/retificação).
        # `unknown` se CPF inválido (não 11 dígitos) ou ausente do índice.
        cpf_norm = normalize_cpf(cpf_raw)
        if not cpf_norm:
            return _emit(MemberNameResolution(None, "unknown", matched_via="cpf:invalid"))
        member = self._cpf_index.get(cpf_norm)
        if member is None:
            return _emit(MemberNameResolution(None, "unknown", matched_via="cpf:miss"))
        return _emit(
            MemberNameResolution(canonical_key=member.key, confidence="cpf", matched_via="cpf")
        )

    def resolve(self, name_raw: Optional[str]) -> MemberNameResolution:
        """Resolve ``name_raw`` para `MemberNameResolution`. ``None`` em vazio."""
        if not name_raw:
            return _emit(MemberNameResolution(None, "unknown"))
        if not self._members:
            return _emit(MemberNameResolution(None, "unknown"))

        raw_slug = _slugify(name_raw)
        if not raw_slug:
            return _emit(MemberNameResolution(None, "unknown"))

        # 1-4: exact slug match em key / full_name / short_name / nome_nascimento.
        for field_name in ("key", "full_name", "short_name", "nome_nascimento"):
            for member, slug in self._slug_index.get(field_name, []):
                if slug == raw_slug:
                    return _emit(
                        MemberNameResolution(
                            canonical_key=member.key,
                            confidence=_FIELD_TO_CONFIDENCE[field_name],
                            matched_via=field_name,
                        )
                    )

        # 5. substring match (ambos os lados; ≥ _MIN_SUBSTRING_LEN para evitar
        # match de "ana" em "fernanda").
        if len(raw_slug) >= _MIN_SUBSTRING_LEN:
            candidates: list[tuple[MemberRecord, str]] = []
            seen_keys: set[str] = set()
            for field_name in ("key", "full_name", "short_name", "nome_nascimento"):
                for member, slug in self._slug_index.get(field_name, []):
                    if len(slug) < _MIN_SUBSTRING_LEN:
                        continue
                    if raw_slug in slug or slug in raw_slug:
                        if member.key not in seen_keys:
                            candidates.append((member, field_name))
                            seen_keys.add(member.key)
            if len(candidates) == 1:
                member, field_name = candidates[0]
                return _emit(
                    MemberNameResolution(
                        canonical_key=member.key,
                        confidence="substring",
                        matched_via=field_name,
                    )
                )
            if len(candidates) > 1:
                return _emit(
                    MemberNameResolution(
                        canonical_key=None,
                        confidence="ambiguous",
                        matched_via=",".join(sorted(m.key for m, _ in candidates)),
                    )
                )

        return _emit(MemberNameResolution(None, "unknown"))


_FIELD_TO_CONFIDENCE: dict[str, Confidence] = {
    "key": "exact",
    "full_name": "full_name",
    "short_name": "short_name",
    "nome_nascimento": "nome_nascimento",
}


def _emit(result: MemberNameResolution) -> MemberNameResolution:
    """Telemetria estruturada — observabilidade para validar a feature."""
    _logger.info(
        "mathoms.pipeline.member_name_resolver.resolved",
        extra={
            "confidence": result.confidence,
            "canonical_key": result.canonical_key or "",
            "matched_via": result.matched_via,
        },
    )
    return result

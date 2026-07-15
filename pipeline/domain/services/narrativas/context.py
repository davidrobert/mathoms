"""NarrativasContext — keys dinâmicas por membro (A6d.3.2).

Value object ISP (R9/ADR-097) que concentra os 10+ ``_KEY_*`` strings
derivados de ``family_members.json``, evitando que os narradores
acessem globals de módulo em ``scripts/generate_narratives.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NarrativasContext:
    """Contexto tipado para os narradores E5.N.

    Todos os campos derivam de ``family_members.json`` — construído
    uma vez em :meth:`from_family_config`.
    """

    titular_key: str
    conjuge_key: str
    titular_nome: str
    conjuge_nome: str

    # Keys derivadas (paridade com globals legados)
    key_inv_titular: str
    key_inv_conjuge: str
    # `cenarios_conjuge` é chave estável universal: ADR-166 fixou no payload E5,
    # ADR-176 fixou também no bloco de narrativas E5.N (era `<conjuge>_cenarios`).
    # `from_family_config` injeta o literal; campo é a única fonte para narrators.
    key_cenarios_conjuge: str
    key_idade_titular_if: str
    key_sal_conjuge: str
    key_inst_titular: str
    key_inst_conjuge: str
    # ADR-168 cleanup (Sprint A10.1): `key_f1f2_titular`, `key_f1f2_conjuge` e
    # `key_renda_conjuge_eua_proj` removidos — metadados do Modo USA descontinuado
    # em A8.4 PR4 que não tinham leitor após remoção das narrativas órfãs em E5.N.

    @classmethod
    def from_family_config(cls, family: dict[str, Any]) -> "NarrativasContext":
        """Constrói contexto a partir de ``family_members.json``."""
        membros = family.get("membros", {}) or {}
        titular_key = family.get("titular", "") or ""
        conjuge_key = next(
            (k for k, v in membros.items() if isinstance(v, dict) and v.get("papel") == "conjuge"),
            "",
        )
        titular_nome = membros.get(titular_key, {}).get("nome_curto") or titular_key.title()
        conjuge_nome = membros.get(conjuge_key, {}).get("nome_curto") or conjuge_key.title()

        return cls(
            titular_key=titular_key,
            conjuge_key=conjuge_key,
            titular_nome=titular_nome,
            conjuge_nome=conjuge_nome,
            # ADR-338: chaves role-keyed (nunca derivadas do nome).
            key_inv_titular="investimentos_titular",
            key_inv_conjuge="investimentos_conjuge",
            key_cenarios_conjuge="cenarios_conjuge",  # ADR-166 + ADR-176: chave estável universal
            key_idade_titular_if="idade_titular_if",
            key_sal_conjuge="salario_conjuge",
            key_inst_titular="titular_instituicoes",
            key_inst_conjuge="conjuge_instituicoes",
        )

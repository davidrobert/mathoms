"""Códigos RFB do e16 (`extract_irpf_full`) — YAML anual versionado (A33.l8).

O Manual DIRPF muda códigos/tetos anualmente e não há API pública; as tabelas
vivem em ``config/prompts/e16_codigos_rfb_<ano_base>.yaml`` e são injetadas no
user prompt do stage. Atualização anual (fevereiro):
``docs/reference/runbooks/atualizacao_codigos_rfb.md``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

_DEFAULT_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "config" / "prompts"
_RFB_FILENAME_RE = re.compile(r"^e16_codigos_rfb_(\d{4})\.yaml$")
_REQUIRED_SECTIONS = ("rendimentos_isentos", "tributacao_exclusiva", "pagamentos_efetuados")
_RUNBOOK = "docs/reference/runbooks/atualizacao_codigos_rfb.md"


@dataclass(frozen=True)
class RFBCodes:
    """Tabelas código→categoria de 1 ano-base (fichas isentos/exclusiva/pagamentos)."""

    ano_base: int
    fonte: str
    rendimentos_isentos: dict[str, str]
    tributacao_exclusiva: dict[str, str]
    pagamentos_efetuados: dict[str, str]


def rfb_codes_path(ano_base: int, prompts_dir: Optional[Path] = None) -> Path:
    return (prompts_dir or _DEFAULT_PROMPTS_DIR) / f"e16_codigos_rfb_{ano_base}.yaml"


def available_rfb_years(prompts_dir: Optional[Path] = None) -> list[int]:
    """Anos-base com YAML presente, ordenados ascendente."""
    base = prompts_dir or _DEFAULT_PROMPTS_DIR
    if not base.exists():
        return []
    matches = (_RFB_FILENAME_RE.match(f.name) for f in base.iterdir())
    return sorted(int(m.group(1)) for m in matches if m)


def load_rfb_codes(ano_base: int, prompts_dir: Optional[Path] = None) -> RFBCodes:
    """Carrega o YAML do ano-base — falha-fast com valor ofensor se ausente/malformado."""
    path = rfb_codes_path(ano_base, prompts_dir)
    if not path.exists():
        available = available_rfb_years(prompts_dir) or "nenhum"
        raise FileNotFoundError(
            f"ano_base {ano_base}: arquivo {path} não existe — "
            f"anos disponíveis: {available}; ver {_RUNBOOK}"
        )
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return _parse_rfb_yaml(raw, ano_base, path)


def _parse_rfb_yaml(raw: object, ano_base: int, path: Path) -> RFBCodes:
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: esperado mapping no topo, got {type(raw).__name__}={raw!r}")
    declared = raw.get("ano_base")
    if declared != ano_base:
        raise ValueError(f"{path}: ano_base declarado {declared!r} != {ano_base} do filename")
    sections: dict[str, dict[str, str]] = {}
    for section in _REQUIRED_SECTIONS:
        table = raw.get(section)
        if not isinstance(table, dict) or not table:
            raise ValueError(
                f"{path}: seção {section!r} ausente ou vazia — got {type(table).__name__}={table!r}"
            )
        sections[section] = {str(k): str(v) for k, v in table.items()}
    return RFBCodes(ano_base=ano_base, fonte=str(raw.get("fonte", "")), **sections)


def resolve_rfb_codes(
    year_hint: Optional[int] = None, prompts_dir: Optional[Path] = None
) -> RFBCodes:
    """YAML do ``year_hint`` (ex.: ano no filename da declaração) se existir;
    senão o ano-base mais recente disponível. Sem nenhum YAML → falha-fast.
    """
    years = available_rfb_years(prompts_dir)
    if not years:
        base = prompts_dir or _DEFAULT_PROMPTS_DIR
        raise FileNotFoundError(
            f"nenhum e16_codigos_rfb_<ano_base>.yaml encontrado em {base} — ver {_RUNBOOK}"
        )
    ano = year_hint if year_hint in years else max(years)
    return load_rfb_codes(ano, prompts_dir)


def render_rfb_codes_block(codes: RFBCodes) -> str:
    """Bloco de user prompt com as 3 tabelas código→categoria do ano-base."""
    fonte = f" (fonte: {codes.fonte})" if codes.fonte else ""
    parts = [
        f"Códigos RFB — ano-base {codes.ano_base}{fonte}:",
        _render_table("Rendimentos isentos e não tributáveis", codes.rendimentos_isentos),
        _render_table(
            "Rendimentos sujeitos à tributação exclusiva/definitiva",
            codes.tributacao_exclusiva,
        ),
        _render_table("Pagamentos efetuados (dedutíveis)", codes.pagamentos_efetuados),
    ]
    return "\n\n".join(parts)


def _render_table(title: str, table: dict[str, str]) -> str:
    lines = [f"{title} (código → categoria):"]
    lines.extend(f'- "{codigo}": {descricao}' for codigo, descricao in table.items())
    return "\n".join(lines)

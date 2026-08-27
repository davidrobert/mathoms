#!/usr/bin/env python3
"""Emissor sem leitor no entregue — polaridade inversa do `check_view_model_contract`.

O gate irmão pega *leitor sem emissor* (TS lê bloco que o produtor não tipa); este
pega o que o produtor emite e o entregue não consome: campo do parecer sem renderer,
seção com componente pronto e sem dispatch, custom property declarada e nunca lida.
Origem: U1 2026-08-26 (RR5-01/RR5-03/RR5-04 · A40.l88).
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dev.report_layout_nav_targets import SHELL_RENDERED_SECTIONS

FRONTEND_SRC = REPO_ROOT / "frontend" / "src"
PARECER_DTO = FRONTEND_SRC / "lib" / "api" / "planner-review.ts"
COMPONENTS = FRONTEND_SRC / "components"
DISPATCHER = COMPONENTS / "report" / "MigratedSection.tsx"

# Receptores que fazem contabilidade sobre o NOME do campo sem renderizar o
# campo: `gated.notas_metodologicas` é um `GatedCounts`, não o array do parecer.
# Sem esta exclusão a colisão de nome deixaria o gate verde sobre o defeito.
BOOKKEEPING_RECEIVERS = frozenset({"gated", "gated_counts", "limits", "counts"})

# Nome de campo curto colide fora da superfície do parecer — `pkg.version` num
# comentário do shell dava o campo `version` por lido. O leitor legítimo de
# `ParecerPlanejadorContent` mora na seção que o consome; procurar fora dela é
# procurar homônimo.
PARECER_SURFACE = "SParecer"
PARECER_CONTENT_TYPE = "ParecerPlanejadorContent"

# Emissor sem leitor conhecido e ainda não consertado. Chave `CODE:identificador`,
# valor = (motivo, dono). Waiver que deixa de ser necessário FALHA — não é data de
# validade (que trava o repo sozinha), é ratchet: consertou, remove a linha.
WAIVED: dict[str, tuple[str, str]] = {
    "PARECER_FIELD:version": (
        "discriminador v1/v2 do payload; o comentário do DTO afirma um dispatch "
        "por content.version que nenhum renderer faz — achado fora do escopo da l88",
        "A40.l88",
    ),
}


@dataclass(frozen=True)
class MissingConsumer:
    code: str
    subject: str
    detail: str

    @property
    def key(self) -> str:
        return f"{self.code}:{self.subject}"

    def format(self) -> str:
        return f"[{self.code}] {self.subject}: {self.detail}"


def _iter_source(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    found = [p for suffix in suffixes for p in root.rglob(f"*{suffix}")]
    return sorted(p for p in found if "generated" not in p.parts)


def _relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path)


_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"(?<!:)//[^\n]*")


def _only_newlines(match: re.Match[str]) -> str:
    return "\n" * match.group(0).count("\n")


def strip_comments(source: str) -> str:
    """Prosa não é leitor. Preserva `://` (URL em string) e as quebras de linha —
    apagar `\n` de bloco comentado deslocaria o número de linha do achado."""
    return _LINE_COMMENT.sub(_only_newlines, _BLOCK_COMMENT.sub(_only_newlines, source))


# --------------------------------------------------------------------------
# 1. Campo do parecer emitido e não renderizado (RR5-01)
# --------------------------------------------------------------------------

_INTERFACE_BODY = re.compile(
    r"export interface ParecerPlanejadorContent\s*\{(?P<body>.*?)\n\}", re.DOTALL
)
_FIELD_DECL = re.compile(r"^\s{2}(?P<name>[a-z_][\w]*)\??\s*:", re.MULTILINE)


def parecer_content_fields(source: str) -> list[str]:
    """Campos declarados em `ParecerPlanejadorContent` (o contrato servido à UI)."""
    match = _INTERFACE_BODY.search(source)
    if not match:
        return []
    return [m.group("name") for m in _FIELD_DECL.finditer(match.group("body"))]


def _field_reader_pattern(field: str) -> re.Pattern[str]:
    return re.compile(rf"(?P<receiver>[A-Za-z_$][\w$]*)\??\.{re.escape(field)}\b")


def has_rendering_reader(field: str, source: str) -> bool:
    """Alguém que não é a contabilidade de `gated_counts` lê o campo."""
    return any(
        m.group("receiver") not in BOOKKEEPING_RECEIVERS
        for m in _field_reader_pattern(field).finditer(source)
    )


def parecer_surface_sources(components: Path = COMPONENTS) -> list[str]:
    """Arquivos que podem renderizar o parecer: a seção dele, ou quem tipa o content."""
    sources = []
    for path in _iter_source(components, (".ts", ".tsx")):
        text = path.read_text(encoding="utf-8")
        if PARECER_SURFACE in path.parts or PARECER_CONTENT_TYPE in text:
            sources.append(strip_comments(text))
    return sources


def find_unrendered_parecer_fields(
    dto_path: Path = PARECER_DTO, components: Path = COMPONENTS
) -> list[MissingConsumer]:
    fields = parecer_content_fields(dto_path.read_text(encoding="utf-8"))
    sources = parecer_surface_sources(components)
    return [
        MissingConsumer(
            "PARECER_FIELD",
            field,
            f"{_relative(dto_path)} declara o campo e a seção do parecer não o renderiza",
        )
        for field in fields
        if not any(has_rendering_reader(field, source) for source in sources)
    ]


# --------------------------------------------------------------------------
# 2. Seção com componente pronto e sem dispatch no entregue (RR5-03)
# --------------------------------------------------------------------------

_SECTION_RENDER = re.compile(r"<ReportSection\s+id=\"(?P<id>[A-Za-z0-9_]+)\"")
_DISPATCH_CASE = re.compile(r"case\s+\"(?P<id>[A-Za-z0-9_]+)\"\s*:")
_MIGRATED_SET = re.compile(r"MIGRATED_SECTIONS[^=]*=\s*new Set\(\[(?P<body>.*?)\]\)", re.DOTALL)


def dispatched_section_ids(source: str) -> set[str]:
    """Ids que o dispatcher realmente serve: no conjunto E com `case`."""
    declared = _MIGRATED_SET.search(source)
    listed = set(re.findall(r"\"([A-Za-z0-9_]+)\"", declared.group("body"))) if declared else set()
    return listed & {m.group("id") for m in _DISPATCH_CASE.finditer(source)}


def find_undispatched_sections(
    components: Path = COMPONENTS, dispatcher: Path = DISPATCHER
) -> list[MissingConsumer]:
    served = dispatched_section_ids(dispatcher.read_text(encoding="utf-8"))
    violations: list[MissingConsumer] = []
    for path in _iter_source(components, (".tsx",)):
        source = strip_comments(path.read_text(encoding="utf-8"))
        for match in _SECTION_RENDER.finditer(source):
            section_id = match.group("id")
            if section_id in served or section_id in SHELL_RENDERED_SECTIONS:
                continue
            line = source.count("\n", 0, match.start()) + 1
            violations.append(
                MissingConsumer(
                    "SECTION_DISPATCH",
                    section_id,
                    f"{_relative(path)}:{line}: renderer pronto que nenhum dispatch alcança",
                )
            )
    return violations


# --------------------------------------------------------------------------
# 3. Custom property declarada que nada lê (RR5-04)
# --------------------------------------------------------------------------

_CUSTOM_PROP_DECL = re.compile(r"^\s*(?P<name>--[a-z0-9-]+)\s*:", re.MULTILINE)


def declared_custom_properties(source: str) -> list[str]:
    return [m.group("name") for m in _CUSTOM_PROP_DECL.finditer(source)]


def _inert_violation(path: Path, name: str) -> MissingConsumer:
    detail = f"{_relative(path)}: declarada e nunca lida — não muda estado nenhum"
    return MissingConsumer("INERT_CSS_VAR", name, detail)


def find_inert_custom_properties(
    components: Path = COMPONENTS, frontend_src: Path = FRONTEND_SRC
) -> list[MissingConsumer]:
    """Só CSS de componente: `tokens.css` declara centenas de tokens para o autor
    consumir, e cobrá-los aqui afogaria o sinal no inventário."""
    readers = "\n".join(
        strip_comments(p.read_text(encoding="utf-8"))
        for p in _iter_source(frontend_src, (".ts", ".tsx", ".css"))
    )
    return [
        _inert_violation(path, name)
        for path in _iter_source(components, (".css",))
        for name in declared_custom_properties(path.read_text(encoding="utf-8"))
        if f"var({name}" not in readers
    ]


# --------------------------------------------------------------------------


def collect_violations() -> list[MissingConsumer]:
    """Tudo que o entregue não consome, waiver ainda não aplicado."""
    return (
        find_unrendered_parecer_fields()
        + find_undispatched_sections()
        + find_inert_custom_properties()
    )


def stale_waivers(found: list[MissingConsumer]) -> list[str]:
    live = {v.key for v in found}
    return sorted(key for key in WAIVED if key not in live)


def report(found: list[MissingConsumer]) -> int:
    violations = [v for v in found if v.key not in WAIVED]
    stale = stale_waivers(found)
    for violation in violations:
        print(violation.format(), file=sys.stderr)
    for key in stale:
        print(f"[WAIVER_STALE] {key}: consertado — remova a linha de WAIVED", file=sys.stderr)
    return len(violations) + len(stale)


def main() -> int:
    total = report(collect_violations())
    if total:
        print(f"check_emitter_without_reader: {total} violação(ões)", file=sys.stderr)
        return 1
    print("check_emitter_without_reader: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

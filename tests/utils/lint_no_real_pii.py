"""Lint anti-PII — F6.5D.7, estendido em A34.l4 (ADR-319) ao superset público.

Escaneia o superset de paths que sobrevive ao flip público (docs/, código de
produção, config/, raiz) procurando padrões de PII e falha se encontrar hit
fora da allowlist curada e do baseline burn-down.

Detectores (TIPO → padrão):
- CPF       — ``XXX.XXX.XXX-YY`` com dígito verificador mod-11 VÁLIDO
              (formatado com DV inválido é sintético por construção)
- ENDERECO  — logradouro (Rua/Av./Avenida/Praça/Alameda/Travessa) + número
- PLACA     — Mercosul ``[A-Z]{3}\\d[A-Z0-9]\\d{2}`` (4º char alfanumérico —
              manter idêntico ao regex dos smokes de tracks, ver A34.l4) e
              formato antigo ``[A-Z]{3}-?\\d{4}``
- CONTRATO  — ``(matrícula|contrato) [nº] <número longo>``
- HOMEDIR   — path de máquina local ``/Users/<user>`` (ADR-319 §contrato 3)

Mensagens exibem ``path:linha: TIPO`` — NUNCA o valor casado. Reproduzir o
match no output do gate contaminaria logs de CI (mesma regra do anexo de
auditoria do PLAN-public-release).

Baseline burn-down (``tests/utils/pii_lint_baseline.json``): hits legados
conhecidos por ``(path, tipo)``, zerados pelas lanes W1 (A34.l7–l12). Hit
fora do baseline → exit 1 (gate). ``--no-baseline`` é o modo estrito da
prova G2 (vermelho no HEAD contaminado). ``--update-baseline`` regenera —
usar apenas em lane de saneamento, com diff mostrando encolhimento.

Uso:
    python tests/utils/lint_no_real_pii.py              # gate (com baseline)
    python tests/utils/lint_no_real_pii.py --verbose
    python tests/utils/lint_no_real_pii.py --no-baseline    # prova G2
    python tests/utils/lint_no_real_pii.py --update-baseline
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Callable

CPF_FORMATTED_RE = re.compile(r"\b(\d{3}\.\d{3}\.\d{3}-\d{2})\b")

# Logradouro (qualquer caixa) + nome iniciando em maiúscula + até 5 tokens +
# número (1-5 dígitos). Exigir capital no nome corta prosa ("a rua estava
# cheia" não casa; "RUA TASSO…, 61" e "Av Paulista 1500" casam).
ENDERECO_RE = re.compile(
    r"\b(?:(?i:Rua|Avenida|Pra[çc]a|Alameda|Travessa)|[Aa][Vv]\.?)\s+"
    r"[A-ZÀ-Ü][\wÀ-ü.]*(?:\s+[\wÀ-ü.]+){0,5},?\s+\d{1,5}\b"
)

# Forma abreviada sem número ("R Nome da Sobrenome") — exige partícula
# (da/de/do/das/dos) entre dois nomes capitalizados para não casar prosa.
ENDERECO_ABREV_RE = re.compile(r"\bR\.?\s+[A-ZÀ-Ü][\wà-ü]+\s+d[aeo]s?\s+[A-ZÀ-Ü][\wà-ü]+")

# Mercosul (4º char alfanumérico, idêntico ao smoke dos tracks) + formato
# antigo. Lookarounds evitam casar dentro de token maior (hash, identifier)
# e ID hifenizado com mais dígitos ("CHG-2026-05-12" não é placa; já
# "TST1A23-ESTACIONAMENTO" — padrão C6TAG — casa).
PLACA_RE = re.compile(r"(?<![A-Z0-9-])([A-Z]{3}\d[A-Z0-9]\d{2}|[A-Z]{3}-?\d{4})(?![A-Z0-9])(?!-\d)")

CONTRATO_RE = re.compile(r"(?i)\b(matr[íi]cula|contrato)\s*(?:n[ºo°.]?\s*)?([\d][\d./-]{5,})")

HOMEDIR_RE = re.compile(r"/Users/[A-Za-z0-9_.-]+")

# ---------------------------------------------------------------------------
# Allowlist curada (ADR-319): placeholders sintéticos canônicos. Toda entrada
# exige justificativa — sem allowlist "solta".
# ---------------------------------------------------------------------------

# CPFs LGPD-safe por design (docs de exemplo + fixtures).
ALLOWED_CPFS: set[str] = {
    "000.000.000-00",
    "00000000000",
    "123.456.789-09",  # placeholder canônico em docs de exemplo
    "12345678909",
    "111.111.111-11",
    "11111111111",
}

# Substrings que marcam endereço/matrícula sintéticos canônicos (ADR-183 /
# vocabulário do PLAN-public-release: "Rua Exemplo, 100", matrícula "999.999").
ALLOWED_SNIPPETS: tuple[str, ...] = (
    "Rua Exemplo",
    "Avenida Exemplo",
    "999.999",
)

# Tokens uppercase que casam o shape de placa mas são vocabulário técnico ou
# placeholder sintético canônico. Comparação com hífen normalizado (ISO-8601
# e ISO8601 são o mesmo token).
ALLOWED_TOKENS: set[str] = {
    "ISO8601",  # formato de data — 3 letras + 4 alfanuméricos
    "ABC1D23",  # placa sintética canônica dos docs/schemas (crlv_abc1d23_2024)
    "ABC1234",  # placa sintética formato antigo (fixtures/testes)
    "XYZ9A87",  # placa sintética secundária (fixtures/testes)
}

# Diretórios nunca varridos (gitignored ou vendored).
EXCLUDED_DIRS = {
    "node_modules",
    ".venv",
    ".git",
    "data",
    "inbox",
    "inbox_processed",
    "storage",
    "_archive",
    "_scratch",
    "processed",
    "members",
    "life_plan",
    "logs",
    "output",
    "__pycache__",
    ".next",
    ".pytest_cache",
    "coverage",
    "playwright-results",
    ".claude",
    ".cursor",
}

EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".md",
    ".yaml",
    ".yml",
    ".html",
    ".toml",
}

# Superset público (A34.l4): docs + código de produção + config + raiz.
# `storage/`, `_scratch/`, `data/` ficam fora via EXCLUDED_DIRS (.gitignore).
SCAN_TARGETS = [
    "docs",
    "backend",
    "frontend/src",
    "frontend/tests",
    "pipeline",
    "config",
    "scripts",
    "dev",
    "tests",
    "services",
    "design-tokens",
    ".github",
]

_BASELINE_PATH = Path(__file__).parent / "pii_lint_baseline.json"

# O próprio gate + baseline + teste contêm placeholders/padrões por
# necessidade (definem a política) — fora do scan para não se auto-flagar.
_SELF_PATHS = {
    "tests/utils/lint_no_real_pii.py",
    "tests/utils/pii_lint_baseline.json",
    "tests/test_lint_no_real_pii.py",
}


def _cpf_check_digits_valid(cpf: str) -> bool:
    """True se os dígitos verificadores mod-11 conferem (CPF real potencial)."""
    digits = re.sub(r"\D", "", cpf)
    if len(digits) != 11 or len(set(digits)) == 1:
        return False
    d1 = sum(int(digits[i]) * (10 - i) for i in range(9)) * 10 % 11 % 10
    d2 = sum(int(digits[i]) * (11 - i) for i in range(10)) * 10 % 11 % 10
    return d1 == int(digits[9]) and d2 == int(digits[10])


def _cpf_findings(line: str) -> bool:
    return any(
        m.group(1) not in ALLOWED_CPFS and _cpf_check_digits_valid(m.group(1))
        for m in CPF_FORMATTED_RE.finditer(line)
    )


def _endereco_findings(line: str) -> bool:
    if any(snippet in line for snippet in ALLOWED_SNIPPETS):
        return False
    return ENDERECO_RE.search(line) is not None or ENDERECO_ABREV_RE.search(line) is not None


def _placa_findings(line: str) -> bool:
    return any(m.group(1).replace("-", "") not in ALLOWED_TOKENS for m in PLACA_RE.finditer(line))


def _contrato_findings(line: str) -> bool:
    return any(m.group(2) not in ALLOWED_SNIPPETS for m in CONTRATO_RE.finditer(line))


def _homedir_findings(line: str) -> bool:
    return HOMEDIR_RE.search(line) is not None


DETECTORS: dict[str, Callable[[str], bool]] = {
    "CPF": _cpf_findings,
    "ENDERECO": _endereco_findings,
    "PLACA": _placa_findings,
    "CONTRATO": _contrato_findings,
    "HOMEDIR": _homedir_findings,
}


def scan_file(path: Path) -> list[tuple[int, str]]:
    """Retorna [(linha, TIPO)] com hits de PII — nunca o valor casado."""
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError, OSError):
        return []
    # `# noqa: PII-ok` é anotação de CÓDIGO (CPF gerado mod-11 em fixture).
    # Em .md o marcador é ignorado: prosa que cita "PII-ok" não pode
    # auto-suprimir o gate (caso real: doc de archive transcrevia CPF na
    # mesma linha em que mencionava a anotação).
    marker_active = path.suffix != ".md"
    findings: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if marker_active and "PII-ok" in line:
            continue
        findings.extend((lineno, tipo) for tipo, detect in DETECTORS.items() if detect(line))
    return findings


def _is_excluded(path: Path, root: Path) -> bool:
    # Worktrees em `.claude/worktrees/<slug>/` têm `.claude` no path absoluto;
    # sem rel-to-root o repo inteiro seria excluído rodando de dentro deles.
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        rel_parts = path.parts
    return any(part in EXCLUDED_DIRS for part in rel_parts)


def _iter_files(root: Path, targets: list[str]) -> list[Path]:
    files: list[Path] = []
    for target in targets:
        target_path = root / target
        if not target_path.exists():
            continue
        files.extend(
            p
            for p in target_path.rglob("*")
            if p.is_file() and p.suffix in EXTENSIONS and not _is_excluded(p, root)
        )
    # Arquivos soltos na raiz (README.md, CLAUDE.md, EXEMPLO_DE_RELATORIO.html…).
    files.extend(p for p in root.glob("*") if p.is_file() and p.suffix in EXTENSIONS)
    rels = {str(p.relative_to(root)) for p in files} - _SELF_PATHS
    return sorted(root / r for r in rels)


def _load_baseline(path: Path = _BASELINE_PATH) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return {(e["path"], e["type"]) for e in data.get("entries", [])}


def _write_baseline(entries: set[tuple[str, str]], path: Path = _BASELINE_PATH) -> None:
    payload = {
        "_comment": (
            "Baseline burn-down do lint anti-PII (A34.l4, ADR-319). Hits "
            "legados por (path, tipo) — as lanes W1 do PLAN-public-release "
            "zeram as entradas. NUNCA adicionar entrada nova sem lane de "
            "saneamento correspondente; hit fora do baseline é gate."
        ),
        "entries": [{"path": p, "type": t} for p, t in sorted(entries)],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", "utf-8")


def _report(
    violations: list[tuple[str, int, str]],
    baselined: int,
) -> None:
    for rel, lineno, tipo in violations:
        print(f"{rel}:{lineno}: {tipo} suspeito (fora do baseline)", file=sys.stderr)
    if violations:
        print(
            f"\n✗ {len(violations)} hit(s) de PII fora do baseline. Use os "
            f"placeholders canônicos (CPF 123.456.789-09, 'Rua Exemplo, 100', "
            f"Titular/Cônjuge, matrícula 999.999) ou o gerador mod-11 em "
            f"tests/utils/cpf.py (anote com `# noqa: PII-ok` se for gerado).",
            file=sys.stderr,
        )
    if baselined:
        print(
            f"ℹ {baselined} hit(s) legados no baseline burn-down "
            f"(saneamento nas lanes W1 do PLAN-public-release).",
            file=sys.stderr,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint anti-PII (superset público)")
    parser.add_argument("--root", default=".", help="Raiz do projeto")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument(
        "--targets",
        nargs="+",
        default=SCAN_TARGETS,
        help="Diretórios a escanear (default: superset público)",
    )
    parser.add_argument(
        "--no-baseline",
        action="store_true",
        help="Modo estrito (prova G2): ignora o baseline burn-down",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Regenera o baseline (apenas em lane de saneamento)",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    files = _iter_files(root, args.targets)
    if args.verbose:
        print(f"Escaneando {len(files)} arquivos em {args.targets}...")

    baseline = set() if args.no_baseline else _load_baseline()
    all_hits: set[tuple[str, str]] = set()
    violations: list[tuple[str, int, str]] = []
    baselined = 0
    for f in files:
        rel = str(f.relative_to(root))
        for lineno, tipo in scan_file(f):
            all_hits.add((rel, tipo))
            if (rel, tipo) in baseline:
                baselined += 1
            else:
                violations.append((rel, lineno, tipo))

    if args.update_baseline:
        _write_baseline(all_hits)
        print(f"Baseline regenerado: {len(all_hits)} entradas (path, tipo).")
        return 0

    _report(violations, baselined)
    if violations:
        return 1
    if args.verbose:
        print("✓ Nenhuma PII fora do baseline detectada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

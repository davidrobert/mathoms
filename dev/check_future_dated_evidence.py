#!/usr/bin/env python3
"""Gate: campo de frontmatter que afirma passado não pode ter data no futuro."""

# `date`, `ship_date` e `amended_at` são EVIDÊNCIA: cada um afirma que algo já
# aconteceu (a decisão foi tomada, a lane shipou, a ADR foi emendada). A
# convenção do CLAUDE.md — "snapshot datado que alguém atualiza deixa de ser
# evidência" — pressupõe que a data seja verdadeira; data no futuro é afirmação
# falsa que nenhum gate via.
#
# Origem (2026-08-28, A40.l80): 9 ocorrências em 3 docs de uma sessão só,
# stampadas 1 e 2 dias à frente. `check_adr_amendment_signal` leu o mesmo
# `amended_at` e ficou verde — ele exige que a data do heading EXISTA no
# frontmatter, nunca que ela seja POSSÍVEL. Varredura de `docs/**` no mesmo
# dia: zero dívida histórica, os 2 ofensores eram os da sessão.
#
# Escopo estreito de propósito. `date_target` é PLANO (a A40 mira 2026-09-05);
# prazo de revisão em prosa e decisão owner-gated futura são legítimos. Data em
# prosa/heading fica fora: em ADR o acoplamento já existe via
# `check_adr_amendment_signal` (heading de emenda datado precisa estar em
# `amended_at`), então heading futuro em ADR cai aqui de carona; em lane, não
# cai — limite aceito, varrer prosa custaria falso-positivo sobre agendamento.
#
# O teto é max(hoje local, hoje UTC): absorve a defasagem entre o relógio do dev
# (UTC-3) e o do CI (UTC) sem dar um dia de folga. Contribuidor a leste de UTC
# precisaria de tolerância explícita. O gate só fica MAIS verde com o tempo —
# data futura vira passado —, nunca vermelho sozinho.
#
# Stdlib puro — roda no job Lint sem venv completo.

from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"

EVIDENCE_FIELDS = ("date", "ship_date", "amended_at")
DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
ITEM_DE_BLOCO_RE = re.compile(r"^\s+-\s")


def _teto_hoje() -> str:
    hoje = datetime.date.today()
    utc = datetime.datetime.now(datetime.timezone.utc).date()
    return max(hoje, utc).isoformat()


def _frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    return text[3:end] if end != -1 else ""


def _chave_da_linha(line: str) -> str | None:
    return line.split(":", 1)[0].strip() if line[:1].isalpha() else None


def _futuras_na_linha(campo: str, line: str, teto: str) -> list[tuple[str, str]]:
    return [(campo, d) for d in DATE_RE.findall(line) if d > teto]


# Lê as duas formas de `amended_at` — inline `["a", "b"]` e bloco `- item`. O
# gate irmão aceita ambas; ler só a primeira deixaria metade da superfície muda.
def datas_futuras(fm: str, teto: str) -> list[tuple[str, str]]:
    """Pares (campo, data) cuja data ultrapassa o teto — evidência impossível."""
    achados: list[tuple[str, str]] = []
    aberto: str | None = None
    for line in fm.splitlines():
        if ITEM_DE_BLOCO_RE.match(line):
            achados += _futuras_na_linha(aberto, line, teto) if aberto else []
            continue
        chave = _chave_da_linha(line)
        if chave is None:
            continue
        aberto = chave if chave in EVIDENCE_FIELDS else None
        achados += _futuras_na_linha(aberto, line, teto) if aberto else []
    return achados


def _varrer(teto: str) -> list[str]:
    falhas = []
    for path in sorted(DOCS_DIR.rglob("*.md")):
        fm = _frontmatter(path.read_text(encoding="utf-8", errors="ignore"))
        for campo, data in datas_futuras(fm, teto):
            rel = path.relative_to(REPO_ROOT)
            falhas.append(f"{rel}: {campo} afirma {data}, posterior a hoje ({teto})")
    return falhas


def main() -> int:
    teto = _teto_hoje()
    falhas = _varrer(teto)
    if not falhas:
        return 0
    print("Evidência datada no futuro (frontmatter afirma passado que não ocorreu):\n")
    for f in falhas:
        print(f"  ✗ {f}")
    print(
        "\nCorrija para a data real do fato. Prazo/alvo futuro tem campo próprio"
        " (`date_target`) e não passa por aqui."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())

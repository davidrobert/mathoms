#!/usr/bin/env python3
"""Checks do preflight que auditam ARTEFATOS DE RODADA, nao prontidao de ambiente.

O irmao (`preflight_unified_review.py`) mede se a maquina esta pronta — git, redis,
worker, frontend, budget. Aqui mora o que olha para o que as rodadas ANTERIORES
deixaram em `storage/`: e a unica familia de check em que a rodada N+1 audita a N,
e por isso a unica que nao e auto-declarada pelo executor.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"

FIX_SINTESE_AUSENTE = (
    "escreva a sintese da rodada anterior nos DOIS formatos (runbook §5 F5 passo 1)"
)

# O `.html` virou obrigatorio na U3; rodada anterior deve so o `.md`. A fronteira e o id,
# que e monotonico — data exigiria parsear nome de pasta e nao e o que ordena as rodadas.
SINTESE_HTML_DESDE = 3


@dataclass(frozen=True)
class Check:
    nome: str
    nivel: str
    detalhe: str
    fix: str = ""


def _storage_root(root: Path) -> Path:
    """`MATHOMS_STORAGE_ROOT` vence o cwd — o storage nao acompanha o worktree."""
    return Path(os.environ.get("MATHOMS_STORAGE_ROOT") or root / "storage")


def _formatos_devidos(nome: str) -> tuple[str, ...]:
    n = nome.partition("-")[0].lstrip("U")
    if n.isdigit() and int(n) >= SINTESE_HTML_DESDE:
        return ("SINTESE.md", "SINTESE.html")
    return ("SINTESE.md",)


def check_sintese_anterior(root: Path, ws: str) -> Check:
    """Rodada unificada anterior sem a sintese nos formatos devidos bloqueia esta."""
    dirs = sorted((_storage_root(root) / ws / "reviews").glob("U*"))
    falta = [
        f"{d.name}/{f}" for d in dirs for f in _formatos_devidos(d.name) if not (d / f).exists()
    ]
    if falta:
        return Check("sintese-anterior", FAIL, f"ausente: {', '.join(falta)}", FIX_SINTESE_AUSENTE)
    return Check("sintese-anterior", PASS, f"{len(dirs)} rodada(s) completas")


def check_baselines(root: Path, ws: str) -> Check:
    """Sem baseline duravel a rodada e fotografia, nao gate anti-regressao."""
    raiz = _storage_root(root)
    reviews = sorted((raiz / ws / "reviews").glob("*")) if (raiz / ws / "reviews").exists() else []
    ledger = (
        sorted((raiz / ws / "ledger_certify").glob("*"))
        if (raiz / ws / "ledger_certify").exists()
        else []
    )
    if not reviews and not ledger:
        return Check("baselines", WARN, "nenhum baseline duravel", "a rodada vira fotografia")
    return Check(
        "baselines", PASS, f"{len(reviews)} review(s) + {len(ledger)} ledger para --compare"
    )

#!/usr/bin/env python3
"""Gera a denylist HMAC de valores do dogfood, fora da árvore (ADR-442).

Decifra os artefatos do banco local in-process ([[ADR-231]]), mantém o tier A
(≥ R$ 10.000,00 com ≥ 6 dígitos significativos) e as variantes em reais inteiros,
subtrai constantes públicas e grava HMAC-SHA256 em `~/.config/mathoms/` (0600).
Não imprime valor algum — só contagens.

Uso (no checkout que tem o `.env` com a chave Fernet, ou com `--env-file`):
    python3 dev/build_dogfood_denylist.py --db /caminho/mathoms.db
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sqlite3
import subprocess
import sys
from collections.abc import Iterable, Iterator
from datetime import datetime, timezone
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN, Decimal, DecimalException
from pathlib import Path
from typing import Any

_DEV = Path(__file__).resolve().parent
sys.path.insert(0, str(_DEV))
sys.path.insert(0, str(_DEV.parent))

from _dogfood_values import (  # noqa: E402
    DENYLIST_NAME,
    KEY_NAME,
    MANIFEST_NAME,
    centavos_da_linha,
    digest,
    diretorio_da_denylist,
    e_tier_a,
)
from golden_diff import is_monetary  # noqa: E402

CONSTANTES_PUBLICAS = _DEV / "dogfood_public_constants.json"
_CENT = Decimal("0.01")
_ARREDONDAMENTOS = (ROUND_HALF_EVEN, ROUND_FLOOR, ROUND_CEILING)
_MAX_TEXTO_ESCALAR = 40
# Acima de 10^13 não é dinheiro (timestamp, id). `adjusted()` mede sem contexto: `abs()` e
# `quantize` estouram (`Overflow`) com expoente enorme vindo de texto do LLM.
_EXPOENTE_MAXIMO = 13


def centavos_do_escalar(valor: Any) -> set[int]:
    """Centavos de uma folha: half-even, floor e ceil cobrem float com fração de centavo."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float, str)):
        return set()
    try:
        numero = Decimal(str(valor).strip())
    except DecimalException:
        return _centavos_de_texto_curto(valor)
    if not numero.is_finite() or numero.adjusted() >= _EXPOENTE_MAXIMO:
        return set()
    return {abs(int(numero.quantize(_CENT, rounding=r) * 100)) for r in _ARREDONDAMENTOS}


def _centavos_de_texto_curto(valor: Any) -> set[int]:
    texto = str(valor)
    return set(centavos_da_linha(texto)) if len(texto) <= _MAX_TEXTO_ESCALAR else set()


def folhas_monetarias(no: Any, caminho: str = "") -> Iterator[int]:
    """Centavos de toda folha monetária (por `is_monetary`) de um payload JSON."""
    for caminho_filho, filho in _filhos(no, caminho):
        yield from folhas_monetarias(filho, caminho_filho)
    if not isinstance(no, (dict, list)) and caminho and is_monetary(caminho):
        yield from centavos_do_escalar(no)


def _filhos(no: Any, caminho: str) -> Iterator[tuple[str, Any]]:
    if isinstance(no, dict):
        yield from ((f"{caminho}.{k}" if caminho else str(k), v) for k, v in no.items())
    elif isinstance(no, list):
        yield from ((f"{caminho}[{i}]", v) for i, v in enumerate(no))


def variantes(cents: int) -> set[int]:
    """O valor e as formas em reais inteiros (`R$ 123.456`) que ainda são tier A."""
    reais = Decimal(cents) / 100
    inteiros = {int(reais.quantize(Decimal(1), rounding=r)) * 100 for r in _ARREDONDAMENTOS}
    return {v for v in {cents, *inteiros} if e_tier_a(v)}


def valores_do_dogfood(payloads: Iterable[Any]) -> set[int]:
    """Tier A de todos os payloads, com as variantes."""
    valores: set[int] = set()
    for cents in (c for payload in payloads for c in folhas_monetarias(payload) if e_tier_a(c)):
        valores |= variantes(cents)
    return valores


def constantes_publicas(con: sqlite3.Connection, arquivo: Path = CONSTANTES_PUBLICAS) -> set[int]:
    """Centavos públicos: `fiscal_parameters` inteiro + a lista commitada, com fonte."""
    curadas = {int(c["cents"]) for c in json.loads(arquivo.read_text(encoding="utf-8"))}
    return curadas | set(_centavos_fiscais(con))


def _centavos_fiscais(con: sqlite3.Connection) -> Iterator[int]:
    cursor = con.execute("select * from fiscal_parameters")
    colunas = [d[0] for d in cursor.description]
    for linha in cursor:
        for coluna, valor in zip(colunas, linha):
            yield from _cents_da_coluna_fiscal(coluna, valor)


def _cents_da_coluna_fiscal(coluna: str, valor: Any) -> Iterator[int]:
    if coluna.endswith("_cents") and isinstance(valor, int):
        yield valor
    elif isinstance(valor, str) and valor.startswith(("{", "[")):
        yield from _cents_do_json_fiscal(json.loads(valor))


def _cents_do_json_fiscal(no: Any, chave: str = "") -> Iterator[int]:
    for chave_filho, filho in _filhos_com_chave(no, chave):
        yield from _cents_do_json_fiscal(filho, chave_filho)
    if chave.endswith("_cents") and isinstance(no, int) and not isinstance(no, bool):
        yield no


def _filhos_com_chave(no: Any, chave: str) -> Iterator[tuple[str, Any]]:
    if isinstance(no, dict):
        yield from no.items()
    elif isinstance(no, list):
        yield from ((chave, filho) for filho in no)


def payloads_do_banco(con: sqlite3.Connection, workspace: str | None) -> Iterator[Any]:
    from backend.app.services.security.crypto import decrypt_artifact_payload

    sql, params = "select content_json from pipeline_artifacts", ()
    if workspace:
        sql, params = sql + " where workspace_id = ?", (workspace,)
    for (conteudo,) in con.execute(sql, params):
        yield decrypt_artifact_payload(json.loads(conteudo))


def canario(reais: set[int]) -> int:
    """Valor sintético tier A fora do conjunto real — prova de ponta a ponta do gate."""
    while True:
        candidato = secrets.randbelow(9 * 10**8) + 10**8
        if e_tier_a(candidato) and candidato not in reais:
            return candidato


def recusar_dentro_de_repo(diretorio: Path) -> None:
    alvo = diretorio if diretorio.exists() else diretorio.parent
    dentro = subprocess.run(
        ["git", "-C", str(alvo), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    )
    if dentro.returncode == 0 and dentro.stdout.strip() == "true":
        raise SystemExit("✗ a denylist não pode morar dentro de um repositório git (ADR-442 D1)")


def _gravar_0600(caminho: Path, conteudo: str) -> None:
    temporario = caminho.with_suffix(caminho.suffix + ".tmp")
    descritor = os.open(temporario, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descritor, "w", encoding="utf-8") as f:
        f.write(conteudo)
    os.replace(temporario, caminho)


def chave_hmac(diretorio: Path, rotacionar: bool) -> bytes:
    arquivo = diretorio / KEY_NAME
    if rotacionar or not arquivo.exists():
        _gravar_0600(arquivo, secrets.token_hex(32) + "\n")
    return bytes.fromhex(arquivo.read_text().strip())


def gravar_denylist(diretorio: Path, valores: set[int], rotacionar: bool) -> dict[str, Any]:
    """Grava digests + manifesto (0600) e devolve só as contagens."""
    recusar_dentro_de_repo(diretorio)
    diretorio.mkdir(mode=0o700, parents=True, exist_ok=True)
    chave = chave_hmac(diretorio, rotacionar)
    valor_canario = canario(valores)
    digests = sorted({digest(chave, v) for v in valores | {valor_canario}})
    _gravar_0600(diretorio / DENYLIST_NAME, "\n".join(digests) + "\n")
    manifesto = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tier": "A",
        "n_valores": len(valores),
        "n_digests": len(digests),
        "canary_cents": valor_canario,
    }
    _gravar_0600(diretorio / MANIFEST_NAME, json.dumps(manifesto, indent=2) + "\n")
    return manifesto


def _carregar_env(env_file: Path | None) -> None:
    if env_file is None:
        return
    from dotenv import dotenv_values

    for chave in ("MATHOMS_FERNET_KEY", "MATHOMS_FERNET_KEYS"):
        if valor := dotenv_values(env_file).get(chave):
            os.environ[chave] = valor


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Gera a denylist HMAC do dogfood (ADR-442)")
    p.add_argument("--db", required=True, type=Path, help="arquivo SQLite com pipeline_artifacts")
    p.add_argument("--env-file", type=Path, help=".env com MATHOMS_FERNET_KEY(S)")
    p.add_argument("--workspace", help="restringe a um workspace_id")
    p.add_argument("--rotacionar-chave", action="store_true", help="gera chave HMAC nova")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    _carregar_env(args.env_file)
    con = sqlite3.connect(f"file:{args.db.resolve()}?mode=ro", uri=True)
    valores = valores_do_dogfood(payloads_do_banco(con, args.workspace)) - constantes_publicas(con)
    manifesto = gravar_denylist(diretorio_da_denylist(), valores, args.rotacionar_chave)
    print(
        f"✓ {manifesto['n_valores']} valores · {manifesto['n_digests']} digests → {diretorio_da_denylist()}"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — a mensagem pode carregar valor decifrado; só o tipo sai
        print(f"✗ build_dogfood_denylist: erro ({type(exc).__name__})", file=sys.stderr)
        sys.exit(2)

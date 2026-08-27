"""A40.l91 ([[ADR-418]]) — de que base saiu a meta de IF publicada num run.

Responde a pergunta que o PV9-16 deixou aberta e a que a [[ADR-418]] fechou:

1. a meta é **declarada** pelo dono ou **derivada**? (resíduo contra a identidade bruta
   no `derived_json` do Goal, mais a lista de inputs);
2. a meta publicada no E5 é a bruta ou a líquida? (resíduo contra as duas);
3. quanto o par numerador↔meta custa em cada regime do toggle `imoveis_no_if`.

Imprime **apenas resíduos, razões e pontos percentuais** — nenhum valor monetário
absoluto (CLAUDE.md §Regras críticas › dados sensíveis).

    PYTHONPATH=. .venv/bin/python dev/measure_if_base.py <run_id>
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from decimal import Decimal
from pathlib import Path

_E5_STAGES = ("analyze_finances", "E5")


def _dec(value) -> Decimal:
    return Decimal(str(value))


def _decrypt(payload: dict) -> dict:
    """Import lazy — o vault Fernet exige env de backend ([[ADR-231]])."""
    from backend.app.services.security.crypto import (
        decrypt_artifact_payload,
        is_encrypted_payload,
    )

    return decrypt_artifact_payload(payload) if is_encrypted_payload(payload) else payload


def _load_e5(conn: sqlite3.Connection, run_id: str) -> dict:
    row = conn.execute(
        "SELECT content_json FROM pipeline_artifacts WHERE pipeline_run_id=? "
        f"AND stage IN {_E5_STAGES} AND artifact_key='analise_financeira' "
        "ORDER BY created_at DESC LIMIT 1",
        (run_id,),
    ).fetchone()
    if row is None:
        raise SystemExit(f"run {run_id}: nenhum artefato E5 `analise_financeira`")
    return _decrypt(json.loads(row[0]))


def _load_goal(conn: sqlite3.Connection, run_id: str) -> tuple[dict, dict] | None:
    ws = conn.execute("SELECT workspace_id FROM pipeline_runs WHERE id=?", (run_id,)).fetchone()
    if ws is None:
        raise SystemExit(f"run {run_id} não existe")
    row = conn.execute(
        "SELECT params_json, derived_json FROM goals WHERE workspace_id=? "
        "AND type='INDEPENDENCIA_FINANCEIRA' AND effective_to IS NULL",
        (ws[0],),
    ).fetchone()
    return (json.loads(row[0])["inputs"], json.loads(row[1])) if row else None


def _report_goal(goal: tuple[dict, dict] | None) -> None:
    print("== 1. a meta é declarada ou derivada? ==")
    if goal is None:
        print("   sem Goal IF vigente — inconclusivo")
        return
    inputs, derived = goal
    residuo = abs(
        _dec(derived["if_meta_brl"])
        - _dec(inputs["renda_passiva_mensal_brl"]) * 12 / (_dec(inputs["trs_pct"]) / 100)
    )
    print(f"   inputs do Goal: {sorted(inputs)}")
    print(f"   resíduo |if_meta_brl − renda_alvo × 12 ÷ TRS| = R$ {residuo:.2f}")
    print("   → DERIVADA se o resíduo é zero e nenhum input a declara")


def _report_base(goals: dict, investivel: Decimal) -> tuple[Decimal, Decimal]:
    trs, alvo = _dec(goals["if_trs"]), _dec(goals["if_trs_monthly_value"])
    meta, observada = _dec(goals["if_meta"]), _dec(goals["renda_passiva_mensal_observada_brl"])
    bruta = alvo * 12 / (trs / 100)
    liquida = max(Decimal(0), (alvo - observada) * 12 / (trs / 100))
    print("\n== 2. a meta publicada é bruta ou líquida? ==")
    print(f"   resíduo contra a BRUTA   = R$ {abs(meta - bruta):.2f}")
    print(f"   razão  meta ÷ líquida    = {meta / liquida:.4f}   (1,0000 = é a líquida)")
    print(f"   razão  observada ÷ alvo  = {observada / alvo:.4f}")
    print(f"   progresso publicado      = {_dec(goals['if_pct']):.2f} %")
    print(f"   investível ÷ bruta       = {investivel / bruta * 100:.2f} %")
    return bruta, liquida


def _report_regimes(e5: dict, bruta: Decimal) -> None:
    pat, fontes = e5["patrimonio"], e5["passive_income"]["renda_passiva_por_fonte_brl"]
    trs = _dec(e5["goals"]["if_trs"])
    alvo = _dec(e5["goals"]["if_trs_monthly_value"])
    aluguel_mes = _dec(fontes.get("alugueis", 0)) / 12
    inv_ef, inv_fin = _dec(pat["investivel_efetivo"]), _dec(pat["investivel_financeiro"])
    gerador = _dec(e5["goals"]["patrimonio_gerador_brl"])
    print(f"\n== 3. o par numerador↔meta (toggle publicado: {pat['imoveis_no_if']}) ==")
    print(f"   patrimônio gerador ÷ investível efetivo = {gerador / inv_ef:.4f}")
    print("   → perto de 1 significa que descontar a renda observada INTEIRA dupla-conta")
    liquida_aluguel = max(Decimal("0.01"), (alvo - aluguel_mes) * 12 / (trs / 100))
    hoje, correto = inv_fin / bruta * 100, inv_fin / liquida_aluguel * 100
    print(f"   se o toggle fosse false: numerador ÷ efetivo = {inv_fin / inv_ef:.4f}")
    print(f"     progresso hoje (meta bruta)    = {hoje:.2f} %")
    print(f"     progresso correto (meta líq.)  = {correto:.2f} %  → {correto - hoje:.2f} pp")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    parser.add_argument("--db", default=str(Path.cwd() / "mathoms.db"))
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    e5 = _load_e5(conn, args.run_id)
    _report_goal(_load_goal(conn, args.run_id))
    investivel = _dec(e5["patrimonio"]["investivel_efetivo"])
    bruta, _ = _report_base(e5["goals"], investivel)
    _report_regimes(e5, bruta)


if __name__ == "__main__":
    main()

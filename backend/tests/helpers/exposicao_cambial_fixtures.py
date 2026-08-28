"""Builders do artefato E5 consumido pelo card Exposição Cambial V2 (ADR-224)."""

from __future__ import annotations

from decimal import Decimal

from backend.app.models import AssetCatalog, PipelineArtifact, PipelineRun, WorkspaceAssetOverride


# Até 2026-08 esta fixture fabricava `patrimonio_full`/`investimentos_atuais`, nomes de
# variável interna do domínio. Nenhum artefato jamais os teve: a fixture e o código
# compartilhavam a mesma crença errada, e a suíte ficou verde três meses sobre um
# endpoint que devolvia zero em produção. `posicoes` não tem onde morar — o E5 publica
# agregados, não posições individuais (elas vivem no E4); o parâmetro segue na
# assinatura para os testes que documentam a lacuna.
# A40.l80: o card só julga faixa com TODOS os componentes apurados — o mesmo
# predicado do `_tier` do E5. Sem isso, `indeterminado`.
# A40.l80: o bloco vem do PRODUTOR, não escrito à mão. Antes ele fixava
# `valor_brl: 0.0` e não trazia `por_moeda` — estado que produção nunca emite, e que
# escondia a divergência de 6× entre o E5 e este card (a linha `moeda_estrangeira_irpf`
# nasce com `moeda="BRL"` e o card a descartava). Com a fixture fabricada, nenhum dos
# testes caía.
#
# `cobertura` continua sobrescrita à mão porque o produtor fixa
# `carteira_lastro_estrangeiro` em `indeterminado` incondicionalmente (ADR-403 §D1): sem o
# override, os ramos de tier `verde`/`amarelo`/`vermelho` seriam inalcançáveis. Eles
# testam regime que produção HOJE não alcança — está declarado, não é acidente.
def _componentes(cobertura: str, caixa_detalhes: list[dict], investivel: Decimal) -> dict:
    from pipeline.domain.services.exposicao_cambial_analyzer import compute_exposicao_cambial

    publicado = compute_exposicao_cambial(
        caixa_detalhes=caixa_detalhes,
        investimentos_atuais=None,
        investivel_financeiro=float(investivel),
    ).to_dict()
    for componente in publicado["componentes"].values():
        componente["cobertura"] = cobertura
    return publicado


def _patrimonio(caixa_detalhes: list[dict], investivel: Decimal, serie_corrente: bool) -> dict:
    # str porque JSON column não serializa Decimal nativamente; _to_decimal lê string corretamente
    out = {"caixa_detalhes": caixa_detalhes, "investivel_financeiro": str(investivel)}
    if serie_corrente:
        out["base_versao"] = 1
    return out


def _e5_payload(
    *,
    posicoes: list[dict],
    caixa_detalhes: list[dict],
    investivel: Decimal,
    cobertura: str = "apurado",
    serie_corrente: bool = True,
) -> dict:
    """Shape REAL do artefato E5 — as chaves que `e5_serialization` emite."""
    payload = {
        "patrimonio": _patrimonio(caixa_detalhes, investivel, serie_corrente),
        "investimentos": {"total_financeiro": str(investivel), "tabela_classes": []},
        "exposicao_cambial": _componentes(cobertura, caixa_detalhes, investivel),
    }
    assert "dados" not in payload["investimentos"], (
        "o E5 não publica posições individuais — se passou a publicar, ligue o braço de "
        "ativos do V2 em vez de reintroduzir a fixture fictícia"
    )
    return payload


def _pos_ivvb11(montante: Decimal) -> dict:
    return {
        "ticker": "IVVB11",
        "descricao": "IVVB11",
        "valor": str(montante),
        "tipo": "Internacional",
        "classe": "Internacional",
    }


def _caixa_usd(conta: str, montante: Decimal) -> dict:
    return {"conta": conta, "moeda": "USD", "valor_brl": str(montante), "saldo_original": "0"}


async def _seed_e5_artifact(db, workspace_id: str, payload: dict) -> PipelineArtifact:
    run = PipelineRun(
        workspace_id=workspace_id,
        status="success",
    )
    db.add(run)
    await db.flush()
    art = PipelineArtifact(
        workspace_id=workspace_id,
        pipeline_run_id=run.id,
        stage="analyze_finances",
        artifact_key="analise_financeira",
        content_json=payload,
    )
    db.add(art)
    await db.commit()
    return art


async def _seed_override(db, workspace_id: str, match_kind: str, key: str, moeda: str) -> None:
    override = WorkspaceAssetOverride(
        workspace_id=workspace_id,
        match_kind=match_kind,
        asset_match_key=key,
        lastro_moeda=moeda,
        override_source="user_manual",
    )
    db.add(override)
    await db.commit()


async def _seed_catalog_entry(db, *, ticker: str, lastro_moeda: str = "USD") -> None:
    """Seed direto na tabela (test DB usa Base.metadata.create_all, sem rodar seed da migration)."""
    entry = AssetCatalog(
        catalog_version=1,
        ticker=ticker,
        cnpj=None,
        match_keyword=None,
        asset_class="Internacional",
        lastro_moeda=lastro_moeda,
        lastro_source="catalog",
    )
    db.add(entry)
    await db.commit()

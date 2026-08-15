"""Cache fiscal versionado por shape (A40.l56 · ADR-389 D5)."""

from __future__ import annotations

import json

import pytest

from backend.app.services.storage import fiscal_cache


@pytest.fixture
def redis_fake(monkeypatch):
    """Substitui as primitivas Redis por um dict — o alvo é a lógica de shape."""
    store: dict[str, str] = {}
    monkeypatch.setattr(fiscal_cache, "_redis_get", lambda k: store.get(k))
    monkeypatch.setattr(fiscal_cache, "_redis_set", lambda k, v, ttl: store.__setitem__(k, v))
    return store


def test_chave_carrega_a_versao_do_shape(redis_fake):
    assert fiscal_cache.fiscal_cache_key(2026) == "fiscal:v2:y=2026"


def test_round_trip_devolve_o_payload_sem_o_carimbo(redis_fake):
    fiscal_cache.store_fiscal_cache(2026, {"ir_brackets_anual": {"faixas": []}})
    lido = fiscal_cache.get_cached_fiscal(2026)
    assert lido == {"ir_brackets_anual": {"faixas": []}}
    assert "schema_version" not in lido


def test_payload_de_shape_antigo_e_miss_nao_faixas_vazias(redis_fake):
    """O modo de falha real: leitor novo × cache pré-deploy não pode devolver dict."""
    redis_fake[fiscal_cache.fiscal_cache_key(2026)] = json.dumps(
        {"ir_brackets": [{"aliquota_pct": "7.5"}], "schema_version": 1}
    )
    assert fiscal_cache.get_cached_fiscal(2026) is None


def test_payload_sem_carimbo_e_miss(redis_fake):
    """Entrada gravada antes do bump, ou por escritor que esqueceu de carimbar."""
    redis_fake[fiscal_cache.fiscal_cache_key(2026)] = json.dumps({"ir_brackets": []})
    assert fiscal_cache.get_cached_fiscal(2026) is None


def test_escritor_carimba_de_fato(redis_fake):
    """Gravar a versão é metade do trabalho; sem isto o leitor rejeitaria tudo."""
    fiscal_cache.store_fiscal_cache(2026, {"ir_brackets_anual": {}})
    bruto = json.loads(redis_fake[fiscal_cache.fiscal_cache_key(2026)])
    assert bruto["schema_version"] == fiscal_cache._FISCAL_CACHE_SCHEMA


# Por que o carimbo existe ALÉM da chave versionada: uma entrada gravada entre o
# deploy do bump e o deploy do rename tem a chave NOVA e o payload ANTIGO —
# cenário que a chave, sozinha, não distingue.
def test_a_chave_sozinha_nao_bastaria(redis_fake):
    """Chave nova com payload antigo é miss."""
    redis_fake[fiscal_cache.fiscal_cache_key(2026)] = json.dumps({"ir_brackets": []})
    assert fiscal_cache.get_cached_fiscal(2026) is None


def test_nao_dict_e_miss(redis_fake):
    redis_fake[fiscal_cache.fiscal_cache_key(2026)] = json.dumps(["lista"])
    assert fiscal_cache.get_cached_fiscal(2026) is None

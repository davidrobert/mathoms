"""A chave de identidade ancorada no CNPJ do documento ([[A42.l15]] PR2, critérios 2/3/5).

Cascata: `("cnpj", raiz)` ⊳ `("desc", tipo, inst_norm, desc_norm)` ⊳ recusa.

Medido em 836 artefatos `E1.5a` / 28 grupos (pooled `|A∩B|/|A∪B|`): a chave antiga
`(tipo,inst,desc)` dá **37,68%**; com a âncora na frente, **61,78%**. O subconjunto
ancorado sozinho é **91,71%** estável, contra 50,9% de cobertura.

Três invariantes distintos, e nenhum implica o outro:

- **Âncora manda** — mudar a descrição não move o hash quando há CNPJ. É a classe que
  a lane mediu: `MANTIDA NO BRASIL` → `MANTIDA EM BRASIL` quebrava o merge cross-year.
- **Recusa carrega motivo** (critério 3) — sem âncora E sem descrição, `investment_id`
  é `None` **e** a entrada sai com `review_reason`. Recusar calado é indistinguível de
  esquecer.
- **Era não move a chave** (critério 5) — o bump `PROMPT_VERSION` 1.3.0 → 1.4.0 passou
  a emitir `cnpj_emissor`; um item de era antiga (CNPJ só no texto) e o mesmo item de
  era nova (campo declarado) têm de colidir no MESMO hash. É o que dispensa a
  re-extração que a [[ADR-311]] D3 exclui.
"""

from __future__ import annotations

import contextlib
import io

import pytest

from pipeline.domain.services.ancora_cnpj import ancora_da_entrada, medir_cobertura
from pipeline.domain.services.investimentos_dedup import dedup_investimentos_consolidados
from scripts.consolidate_baseline import consolidate_from_itens

_CNPJ = "12345678000195"
_RAIZ = "12345678"


def _entrada(**over) -> dict:
    base = {
        "descricao": "CDB BANCO EXEMPLO",
        "tipo": "renda_fixa",
        "proprietario": "david",
        "valores_31_12": {"2024": 1000.0},
    }
    base.update(over)
    return base


def _ids(entradas: list[dict]) -> list[str | None]:
    return [
        e.get("investment_id") for e in dedup_investimentos_consolidados(entradas).investimentos
    ]


class TestAncoraMandaSobreODescricao:
    def test_rename_de_descricao_nao_move_o_hash(self) -> None:
        """A classe medida na lane: o extrator reescreve a prosa, o CNPJ fica."""
        a = _entrada(descricao="DEPOSITO MANTIDA NO BRASIL", cnpj_emissor=_CNPJ)
        b = _entrada(descricao="DEPOSITO MANTIDA EM BRASIL", cnpj_emissor=_CNPJ)
        assert _ids([a])[0] == _ids([b])[0]

    def test_sem_ancora_o_rename_AINDA_move_o_hash(self) -> None:
        """Controle: sem o degrau forte a instabilidade permanece — o fix não é global."""
        a = _entrada(descricao="DEPOSITO MANTIDA NO BRASIL")
        b = _entrada(descricao="DEPOSITO MANTIDA EM BRASIL")
        assert _ids([a])[0] != _ids([b])[0]

    def test_cnpjs_diferentes_nao_fundem(self) -> None:
        a = _entrada(cnpj_emissor=_CNPJ)
        b = _entrada(cnpj_emissor="98765432000110")
        assert dedup_investimentos_consolidados([a, b]).count_after == 2

    def test_ancora_nao_se_compoe_com_tipo(self) -> None:
        """`("cnpj",raiz,tipo)` mede 63,49% contra 69,20% — `tipo` churna e contamina."""
        a = _entrada(cnpj_emissor=_CNPJ, tipo="renda_fixa")
        b = _entrada(cnpj_emissor=_CNPJ, tipo="fundo_investimento")
        assert _ids([a])[0] == _ids([b])[0]

    def test_instituicao_FICA_na_perna_fraca(self) -> None:
        """Tirá-la pagava +7,4pp e fundia o mesmo título em duas corretoras
        ([[ADR-271]] §139: falso-positivo some patrimônio)."""
        a = _entrada(instituicao="XP")
        b = _entrada(instituicao="BTG")
        assert dedup_investimentos_consolidados([a, b]).count_after == 2


class TestRecusaCarregaMotivo:
    """Critério 3 — o único invariante sobre a DECISÃO, não sobre o número."""

    def test_sem_ancora_e_sem_descricao_recusa(self) -> None:
        r = dedup_investimentos_consolidados([_entrada(descricao="")])
        assert r.investimentos[0].get("investment_id") is None

    def test_a_recusa_diz_por_que(self) -> None:
        r = dedup_investimentos_consolidados([_entrada(descricao="")])
        codes = [x["code"] for x in r.investimentos[0]["review_reasons"]]
        assert "dedup.identidade_sem_ancora" in codes

    def test_ancora_sem_descricao_NAO_recusa(self) -> None:
        """A perna forte não pode depender da fraca — o molde de `dividas_dedup` exige
        `desc` antes de olhar o contrato, e isso é defeito que não replico."""
        r = dedup_investimentos_consolidados([_entrada(descricao="", cnpj_emissor=_CNPJ)])
        assert r.investimentos[0]["investment_id"] is not None
        assert not r.investimentos[0].get("review_reasons")

    def test_recusa_e_idempotente(self) -> None:
        """O dedup roda sobre a própria saída; a razão não pode acumular."""
        primeira = dedup_investimentos_consolidados([_entrada(descricao="")])
        segunda = dedup_investimentos_consolidados(primeira.investimentos)
        assert len(segunda.investimentos[0]["review_reasons"]) == 1


class TestEraNaoMoveAChave:
    """Critério 5 — a política de era do bump 1.3.0 → 1.4.0, provada por mutação."""

    def test_era_antiga_e_nova_colidem_no_mesmo_hash(self) -> None:
        # 1.3.0: nenhum `cnpj_emissor`; o CNPJ existe só no texto da descrição.
        antiga = _entrada(descricao="CDB BANCO EXEMPLO CNPJ 12.345.678/0001-95")
        # 1.4.0: o mesmo item, agora com o campo declarado.
        nova = _entrada(descricao="CDB BANCO EXEMPLO CNPJ 12.345.678/0001-95", cnpj_emissor=_CNPJ)
        assert _ids([antiga])[0] == _ids([nova])[0]

    def test_e_elas_FUNDEM_entre_si(self) -> None:
        """Não basta o hash bater: o merge cross-era é o que evita duplicar a posição."""
        antiga = _entrada(descricao="CDB CNPJ 12.345.678/0001-95", valores_31_12={"2023": 900.0})
        nova = _entrada(
            descricao="CDB do Banco Exemplo",
            cnpj_emissor=_CNPJ,
            valores_31_12={"2024": 1000.0},
        )
        assert dedup_investimentos_consolidados([antiga, nova]).count_after == 1

    @pytest.mark.parametrize("mascarado", ["12.345.678/0001-95", "12345678000195"])
    def test_a_grafia_do_cnpj_no_texto_nao_importa(self, mascarado: str) -> None:
        com_campo = _entrada(cnpj_emissor=_CNPJ, descricao="x")
        no_texto = _entrada(descricao=f"CDB {mascarado}")
        assert _ids([com_campo])[0] == _ids([no_texto])[0]


class TestCoberturaPublicada:
    """Critério 2 — no ARTEFATO, não em voo. É o invariante que mata o modo inerte."""

    def test_ancora_da_entrada_prefere_o_campo_ao_texto(self) -> None:
        assert (
            ancora_da_entrada({"cnpj_emissor": _CNPJ, "descricao": "CNPJ 98.765.432/0001-10"})
            == _RAIZ
        )

    def test_cobertura_conta_os_tres_degraus(self) -> None:
        c = medir_cobertura([_entrada(cnpj_emissor=_CNPJ), _entrada(), _entrada(descricao="")])
        assert (c.total, c.com_ancora, c.por_descricao, c.sem_identidade) == (3, 1, 1, 1)
        assert c.pct_ancora == pytest.approx(33.33)

    def test_o_consolidador_publica_a_cobertura(self) -> None:
        itens = [
            {
                "codigo": "41",
                "descricao": "CDB CNPJ 12.345.678/0001-95",
                "categoria_hint": "investimento",
                "valor_brl": "1000.00",
                "membro": "david",
                "ano": 2025,
            }
        ]
        with contextlib.redirect_stdout(io.StringIO()):
            out = consolidate_from_itens({"resumo": {"ano_referencia": 2025}, "itens": itens})
        cobertura = out["investimentos_ancora_cobertura"]
        assert cobertura["total"] == 1 and cobertura["com_ancora"] == 1
        assert cobertura["pct_ancora"] == 100.0

    def test_cobertura_zero_e_publicada_e_nao_omitida(self) -> None:
        """`com_ancora: 0` é justamente o sinal que delata perna forte sem produtor."""
        c = medir_cobertura([_entrada(), _entrada()])
        assert c.to_dict()["com_ancora"] == 0 and c.to_dict()["total"] == 2

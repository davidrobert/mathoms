"""Allowlists do classificador monetário-por-default do `golden_diff` (A23.l2).

Extraídas de `dev/golden_diff.py` em 2026-10-08: o módulo estava em 499 linhas, e o
conserto número↔null da [[ADR-439]] o levava a 523. Dado puro — a lógica de
classificação (`is_monetary`) continua lá.
"""

from __future__ import annotations

# Chaves-folha numéricas que NÃO são monetárias (percentuais, contagens, idades,
# anos, ratios, score). Tudo o mais numérico é tratado como monetário (default).
NON_MONETARY_EXACT = frozenset(
    {
        "pct",
        "peso",
        "nota",
        "max",
        "n",
        "count",
        "sigma_usado",
        "fator_reduzido",
        "aliquota_marginal",
        "data",
        "idade_david",
        "idade_meta_usada",
        "ano_if",
        "anos_if",
        "if_pct",
        "if_trs",
        "folga_pct",
        "n_imoveis_total",
        "janela_n_meses",
        "transacoes_total",
        "transacoes_duplicadas_removidas",
        # Contador do bloco `fluxo_caixa.provisionado` (corte de provisionado).
        # Monetário-por-default leria `transacoes=4` como R$ 0,04 e reportaria
        # delta_cents fantasma — mesma classe de `transacoes_total` acima.
        "transacoes",
        "acumuladores_pct_gerador",
        "percentual_patrimonio",
        # ADR-401: ano-base do saldo da dívida. O prefixo `ano_` do
        # classificador não alcança `saldo_ano_referencia`, e monetário-por-
        # default leria 2024 como R$ 20,24 no snapshot do view-model — mesma
        # classe que motivou o rename `taxa_juros` -> `taxa_juros_aa`.
        "saldo_ano_referencia",
        # ADR-369 D2 aposentou estas duas do contrato; ficam porque o diff também
        # compara goldens HISTÓRICOS, onde elas existem — remover reintroduziria
        # o delta_cents fantasma nessas comparações.
        "prob_if_ate_idade_meta",
        "taxa_poupanca_recorrente",
        "taxa_poupanca_total",
        "meses_alvo",  # alvo da reserva em meses (A28.l1), não R$
        # A40.l93: valor-alvo de `kpi_targets.*`. A unidade mora no IRMÃO `unidade`
        # (pct | pct_aa | meses | ano | ratio_0_1), nunca no nome — nenhum sufixo a
        # carrega, então a entrada é exata, como `saldo_ano_referencia`. Monetário-por-
        # default publicava 4 alvos ×100 no snapshot do view-model: 50 (pct) como
        # R$ 5.000, 10 (pct) como R$ 1.000, 20 (pct) como R$ 2.000 e — o pior —
        # 18 MESES como R$ 1.800. A isenção é segura enquanto nenhum membro do enum de
        # `unidade` for monetário, e isso é asserido em
        # tests/test_parecer_metrica_stamping.py, não confiado.
        "limiar",
        # ADR-360 — proveniência do Monte Carlo. Monetário-por-default trataria
        # `seed_usado=360` como R$ 3,60 e reportaria delta_cents fantasma.
        "seed_usado",
        "n_simulacoes_usado",
        # A40.l80: ORDINAL (rank no top de ativos). `posicao=1` virava R$ 1,00 e o
        # snapshot publicava 100. Entrada exata e não prefixo: não há família de
        # ordinais aqui, e `posicao_*` monetário é plausível num domínio de carteira.
        "posicao",
        "contagem",  # A27.l3: CONTAGEM, ao lado do irmão que é dinheiro.
    }
)
NON_MONETARY_SUFFIXES = (
    "_pct",
    "_meses",
    "_anos",
    "_idade",
    "_idade_if",
    "_ano_if",
    "idade_if",
    "_aa",
    "_count",
    # A40.l80: número de VERSÃO não é dinheiro. Monetário-por-default lia
    # `base_versao=1` como R$ 0,01 e o snapshot o publicava como 100. Sufixo, e
    # não entrada exata, porque `definicao_versao` ([[ADR-403]]) e
    # `score_version` ([[ADR-217]]) tinham o mesmo defeito latente — fechar por
    # instância deixaria o próximo campo de versão nascer com o mesmo bug.
    "_versao",
    "_version",
)
NON_MONETARY_PREFIXES = (
    "idade_",
    "anos_",
    "ano_",
    "nivel_",
    "prazo_",
    "prazos_",
    "pct_",
    # ADR-361: `prob_*` é fração 0-1, não R$. Sem o prefixo o classificador
    # monetário-por-default leria `prob_if_ate_horizonte=0.44` como R$ 0,44 e
    # reportaria delta_cents fantasma — terceiro remendo da mesma classe.
    "prob_",
    # A40.l80 (destrava A40.l90): `n_*` é CONTAGEM. `n_posicoes=1` virava R$ 1,00 e
    # o snapshot o publicava como 100. Prefixo porque `n_imoveis_total` e
    # `janela_n_meses` já estavam como entrada exata — a família existe.
    "n_",
    # Concentração é sempre RAZÃO. `ratios.concentracao_imobiliaria` publica 82,19 e
    # o classificador lia R$ 82,19 — mover o campo reportava delta monetário
    # FABRICADO, o que bloquearia a A40.l90 com justificativa falsa no manifesto.
    # A causa fica a montante e está roteada: o produtor calcula
    # `concentracao_imobiliaria_pct` e publica a chave SEM o `_pct`
    # (`ratios_calculator.py`), então o nome publicado perde a unidade que a
    # propriedade interna carrega.
    "concentracao_",
)

# Blocos inteiros que não publicam dinheiro. Diferente de `NON_MONETARY_PREFIXES`,
# que olha a FOLHA: aqui o discriminante é o BLOCO, e ele é NECESSÁRIO, não conveniente
# — `score.*` ([[ADR-217]]) publica pontos em `valor` e `contribuicao`, dois nomes que
# em OUTROS blocos são dinheiro (`investimentos.tabela_classes[].valor`,
# `patrimonio.composicao[].valor`). Nenhuma regra por folha consegue separar os dois.
# `cobertura_publicada.` publica MÉTRICA (A27.l3): `denominador` 17→20 saía +300 cents no golden.
NON_MONETARY_NAMESPACES = ("score.", "cobertura_publicada.")

# Unidade é TOKEN, não sufixo. `equivalente_meses_poupanca` carrega `meses` no meio e
# escapava de `NON_MONETARY_SUFFIXES`; fechar por entrada exata deixaria o próximo
# `<algo>_meses_<algo>` nascer com o mesmo bug — a lição que `_versao` já registrou.
# Raio de explosão medido contra `config/schemas/e5_analysis.schema.json` (2026-08-28):
# 7 nomes mudam de classe e nenhum é monetário; zero toca `*_brl` ou `valor`.
# A27.l3: `pontos` é CONTAGEM (`pontos_revisao` era a única folha "monetária" de `narrativas`).
NON_MONETARY_UNIT_TOKENS = frozenset(
    {"pct", "meses", "anos", "idade", "aa", "ano", "ratio", "pontos"}
)


# O marcador de moeda na folha VENCE o bloco. Sem isto, declarar `score.` como
# namespace abriria a porta que o design fecha: um `score.premio_brl` futuro passaria
# mudo. Namespace afrouxa o monetário-por-default, e este é o preço de mantê-lo alto.
MARCADORES_MONETARIOS = ("_brl", "_usd", "_eur", "_reais", "_cents")

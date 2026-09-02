"""Universo declarado de folhas do E5 que NÃO são projetadas ao parecer.

Extraído de ``dev/_planner_coverage_internals.py`` em 2026-09-01: o módulo estava
em 499 linhas — uma abaixo do teto P2 de 500 —, então QUALQUER entrada nova aqui
reprovava o gate de code style. Duas mudanças independentes colidiram nesse teto
no mesmo dia. Declarar exceção é o uso normal deste dict, e o uso normal não pode
custar um refactor a cada vez.
"""

from __future__ import annotations

E5_FIELDS_FORA_DO_PARECER: dict[str, str] = {
    "$._lineage": "rastro de proveniência do pipeline — insumo de debug, não de conselho",
    # [[ADR-420]] §D1/§D6: TERMOS de razão, não conclusões. O parecer já recebe as duas
    # conclusões que eles produzem — a concentração e `imobilizacao_patrimonial_pct` (§D3,
    # criado para o ativo fora-de-alocação não sumir da superfície de risco).
    "$.patrimonio.imoveis_alocacao": "termo do numerador; o parecer recebe a razão",
    "$.patrimonio.imoveis_fora_alocacao": "termo fora do numerador; chega por §D3",
    # [[A40.l114]]: extremo, como as bases acima; já redundante via `classificacao`.
    "$.score.piso": "extremo conservador do score; a `classificacao` projetada já deriva dele",
    "$.narrativas": "texto já destilado em outra superfície; projetá-lo duplicaria prosa",
    "$.protection_computation_inputs_v1": "insumos crus do cálculo de proteção; o parecer lê o resultado",
    # A40.l80 ([[ADR-412]] §D0): base que AMPUTA a fatia sem titular. Ambas têm
    # `publicavel_sozinha() is False` — só valem como extremo inferior de um
    # intervalo declarado. Projetá-las cruas convidaria o modelo a citar o número
    # amputado como se fosse o patrimônio da família, que é o defeito da lane.
    # O parecer recebe o INTERVALO e o motivo, não a ponta.
    "$.patrimonio.bases.carteira_com_titular_identificado": (
        "extremo conservador de intervalo; o parecer recebe o intervalo, nunca a ponta amputada"
    ),
    "$.patrimonio.bases.carteira_produtiva_com_titular_identificado": (
        "extremo conservador de intervalo; o parecer recebe o intervalo, nunca a ponta amputada"
    ),
    # A40.l80 §Completude: esta base existe para AUDITAR o denominador da
    # concentração ([[ADR-340]]) — o parecer já recebe `ratios.concentracao_imobiliaria`
    # e o hint que nomeia a base. O valor cru é rastro de auditoria do gate
    # `tests/test_cobertura_de_base.py`, não insumo de conselho; projetá-lo daria ao
    # modelo um segundo número de "carteira produtiva" para confundir com o primeiro,
    # que é exatamente o defeito que declarar a base foi feito para matar.
    # A40.l80 §Completude: rótulo de auditoria da base do pct — o manifest já entrega o
    # pct com a base nomeada na própria label (#1780). Projetar o campo daria ao modelo um
    # segundo lugar de onde tirar o mesmo nome.
    # A40.l80: termo de base publicado para tornar o bloco `bases` auditável só do
    # payload. É rastro de auditoria, não insumo de conselho — o parecer recebe o
    # patrimônio, não os termos que somam cada denominador.
    "$.patrimonio.cat2_efetivo": (
        "termo de base; rastro de auditoria do bloco `bases`, não insumo de conselho"
    ),
    "$.exposicao_cambial.base_pct_investivel_financeiro": (
        "rótulo de auditoria; a label do pct já nomeia a base ao modelo"
    ),
    "$.patrimonio.bases.carteira_produtiva_fixa": (
        "rastro de auditoria do denominador da concentração; o parecer recebe a razão"
    ),
    # 2026-09-01 ([[ADR-236]] §D5): declarar a raiz no schema a trouxe para este gate.
    "$.tributario": "bloco fiscal nunca projetado ao parecer; declaração registra o status quo",
}

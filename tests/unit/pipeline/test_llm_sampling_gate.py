"""O gate de amostragem pega call-site de LLM sem `temperature`/`seed`.

Sucede `test_extraction_sampling_gate.py`. As mutações rodam sobre uma **árvore
espelho** em `tmp_path` (via `--root`), não escrevendo arquivo-probe na árvore
real — probe em `pipeline/stages/` some se o teste morre no meio.

Mutação → quem falha (a discriminação é o ponto: (a) verde E (b)/(c)/(d)
vermelhos na mesma execução; um gate que retorna 0 incondicionalmente satisfaz
(a) sozinho):

| mutação no gate                                   | teste que falha        |
|---------------------------------------------------|------------------------|
| arquivo do gate deletado                          | (a)                    |
| `return 0` cedo / gate cego                       | (b), (c), (d)          |
| escopo volta a `pipeline/stages/extract_*.py`     | (b), (c)               |
| casamento volta a `ast.Name id == "service"`      | (b), (c)               |
| `seed=` removido do parecer em produção           | (a)                    |
| `scripts/` fora de `RAIZES`                       | (e), (f)               |
| detector de SDK cru cego / `_confere_residuo` mudo| (e), (f), (g)          |
| resíduo vira isenção por arquivo (sem contagem)   | (f)                    |
| entrada de resíduo sobrevive à dívida paga        | (g)                    |
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
GATE = REPO_ROOT / "dev" / "check_llm_sampling.py"
PARECER = Path("backend/app/services/parecer_orchestrator.py")


def _roda(root: Path | None = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(GATE)]
    if root is not None:
        cmd += ["--root", str(root)]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)


def _espelho(tmp_path: Path, relativo: Path, conteudo: str) -> Path:
    alvo = tmp_path / relativo
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_text(conteudo, encoding="utf-8")
    return tmp_path


def test_a_arvore_atual_passa() -> None:
    assert _roda().returncode == 0


# Call-site inventado no teste mede um fantasma: sobrevive a alguém reescrever o
# call-site de produção. Aqui o texto vem do arquivo shipado, com o `seed=`
# extirpado por cirurgia de string.
def test_b_call_site_real_sem_seed_reprova(tmp_path: Path) -> None:
    """Mutação derivada da FONTE REAL do parecer — não de um call-site à mão."""
    fonte = (REPO_ROOT / PARECER).read_text(encoding="utf-8")
    mutado = fonte.replace("        seed=PARECER_SEED,\n", "", 1)
    assert mutado != fonte, "âncora do `seed` sumiu do call-site — atualize a mutação"

    resultado = _roda(_espelho(tmp_path, PARECER, mutado))

    assert resultado.returncode == 1
    assert "parecer_orchestrator.py" in resultado.stdout
    assert "seed" in resultado.stdout


# É o teste que falha se alguém "simplificar" o gate de volta p/ glob de path ou
# p/ nome de receptor — os dois eixos que vazavam no gate anterior.
def test_c_call_site_novo_em_arquivo_e_receptor_novos_reprova(tmp_path: Path) -> None:
    """Arquivo fora do path histórico, receptor que não se chama `service`."""
    root = _espelho(
        tmp_path,
        Path("backend/app/services/zz_gate_probe.py"),
        "def run(client, prompt, S):\n"
        "    return client.call(system_prompt=prompt, output_schema=S)\n",
    )
    resultado = _roda(root)

    assert resultado.returncode == 1
    assert "temperature" in resultado.stdout and "seed" in resultado.stdout


def test_d_kwarg_pela_metade_tambem_reprova(tmp_path: Path) -> None:
    """Passar só `temperature` é o erro mais provável — o gate tem de pegá-lo."""
    root = _espelho(
        tmp_path,
        Path("pipeline/stages/extract_zz_gate_probe.py"),
        "def run(service, prompt, S):\n"
        "    return service.call(system_prompt=prompt, output_schema=S, temperature=0.0)\n",
    )
    resultado = _roda(root)

    assert resultado.returncode == 1
    assert "seed" in resultado.stdout


# Sem esta asserção o gate viraria "todo `.call(system_prompt=...)`" e passaria a
# exigir amostragem de adapters que não falam com provider nenhum.
def test_adapter_sem_output_schema_nao_e_alvo(tmp_path: Path) -> None:
    """`SectionSummaryLLMClient.call` é protocolo, não `LLMService.call`."""
    root = _espelho(
        tmp_path,
        Path("pipeline/domain/services/zz_adapter_probe.py"),
        "def run(llm, prompt):\n"
        "    return llm.call(system_prompt=prompt, user_prompt='x', section_id='S1')\n",
    )
    assert _roda(root).returncode == 0


# ---------------------------------------------------------------------------
# Rota alternativa ao choke-point (A42.l17)
# ---------------------------------------------------------------------------

CAIXA = Path("scripts/e2/banks/caixa.py")


def test_e_sdk_cru_em_arquivo_nao_declarado_reprova(tmp_path: Path) -> None:
    """O eixo que a assinatura `LLMService.call` nunca alcança: o SDK cru."""
    root = _espelho(
        tmp_path,
        Path("scripts/zz_bypass_probe.py"),
        "import anthropic\n"
        "def go(k):\n"
        "    c = anthropic.Anthropic(api_key=k)\n"
        '    return c.messages.create(model="m", messages=[])\n',
    )
    resultado = _roda(root)

    assert resultado.returncode == 1
    assert "zz_bypass_probe.py" in resultado.stdout
    # Sem os sítios impressos, a contagem manda procurar no arquivo inteiro.
    assert "zz_bypass_probe.py:3" in resultado.stdout


def test_f_sitio_extra_em_arquivo_declarado_reprova(tmp_path: Path) -> None:
    """Resíduo é contagem exata, não isenção por arquivo — derivado da FONTE REAL."""
    fonte = (REPO_ROOT / CAIXA).read_text(encoding="utf-8")
    mutado = fonte + "\n\ndef _zz_extra(k):\n    return anthropic.Anthropic(api_key=k)\n"

    resultado = _roda(_espelho(tmp_path, CAIXA, mutado))

    assert resultado.returncode == 1
    assert "esperava 2" in resultado.stdout and "achou 3" in resultado.stdout


def test_g_residuo_que_sobrevive_a_divida_paga_reprova(tmp_path: Path) -> None:
    """Entrada que perde o ofensor tem de sair do registry — senão apodrece."""
    root = _espelho(tmp_path, CAIXA, "def parse_caixa(p, f):\n    return {}\n")
    resultado = _roda(root)

    assert resultado.returncode == 1
    assert "dívida paga" in resultado.stdout


def test_sdk_cru_dentro_do_choke_point_nao_e_ofensor(tmp_path: Path) -> None:
    """`pipeline/llm/` é o dono do client — é lá que a chamada crua deve morar."""
    root = _espelho(
        tmp_path,
        Path("pipeline/llm/zz_client_probe.py"),
        "import anthropic\ndef c(k):\n    return anthropic.Anthropic(api_key=k)\n",
    )
    assert _roda(root).returncode == 0

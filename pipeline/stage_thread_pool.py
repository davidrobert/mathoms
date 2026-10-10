"""Pool de threads de stage que não drena a fila depois de um aborto."""

# `with ThreadPoolExecutor(...)` sai por `shutdown(wait=True)` sem `cancel_futures`:
# se o bloco aborta, o `__exit__` processa TODA tarefa ainda enfileirada antes de a
# exceção seguir. No `extract_with_llm` o soft time limit estoura no `as_completed` da
# thread principal, e o pool fazia a chamada LLM de cada documento pendente antes de
# o run saber que acabou (ADR-446). `wait=True` fica: soltar as threads em voo deixaria
# o executor vivo depois do status terminal do run.

from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager


@contextmanager
def cancelling_thread_pool(max_workers: int) -> Iterator[ThreadPoolExecutor]:
    """``ThreadPoolExecutor`` em que um aborto cancela o que não começou e espera o que está em voo."""
    pool = ThreadPoolExecutor(max_workers=max_workers)
    try:
        yield pool
    except BaseException:
        pool.shutdown(wait=True, cancel_futures=True)
        raise
    pool.shutdown(wait=True)

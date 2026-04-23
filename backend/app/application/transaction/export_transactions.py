"""Use case: export CSV (BOM UTF-8) das transações filtradas."""

from __future__ import annotations

import csv
import io

from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.transaction._loading import load_filtered_transactions
from backend.app.application.transaction.filters import TransactionFilters

_CSV_HEADER = ["Data", "Descrição", "Categoria", "Valor", "Membro", "Banco", "Origem", "Editado"]


async def export_transactions_csv(
    workspace_id: str,
    filters: TransactionFilters,
    *,
    db: AsyncSession,
) -> StreamingResponse:
    transactions = await load_filtered_transactions(workspace_id, filters, db=db)

    buf = io.StringIO()
    buf.write("\ufeff")  # BOM para Excel
    writer = csv.writer(buf)
    writer.writerow(_CSV_HEADER)
    for tx in transactions:
        writer.writerow(
            [
                tx.data,
                tx.descricao,
                tx.categoria,
                tx.valor,
                tx.membro,
                tx.banco,
                tx.origem,
                "Sim" if tx.reviewed else "",
            ]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="transacoes.csv"'},
    )

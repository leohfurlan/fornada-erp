"""Preview legacy names; apply only with an explicit tenant and --aplicar.

Run from backend with PYTHONPATH=. and the intended DATABASE_URL.
No historical snapshots or editorial fields are rewritten.
"""

import argparse
import asyncio
import json
from uuid import UUID

from sqlalchemy import select
from infrastructure.database.session import AsyncSessionLocal
from infrastructure.database.models import Receita
from infrastructure.database.compras_models import ProdutoCompra
from domain.nomes import padronizar_nome_existente
from domain.receitas.historico import HistoricoReceita
from domain.receitas.repository import ReceitaRepository


async def padronizar(db, tenant_id: UUID, aplicar: bool = False) -> list[dict]:
    """Return a reviewable preview; invalid names are left for manual correction."""
    if aplicar:
        await ReceitaRepository(db).travar_composicao(tenant_id)
    changes = []
    for model, tipo in ((Receita, "receita"), (ProdutoCompra, "produto")):
        statement = select(model).where(model.tenant_id == tenant_id, model.deleted_at.is_(None))
        if aplicar:
            statement = statement.with_for_update()
        for row in (await db.scalars(statement)).all():
            try:
                nome = padronizar_nome_existente(row.nome)
            except ValueError as error:
                changes.append({"tipo": tipo, "id": str(row.id), "antes": row.nome, "erro": str(error)})
                continue
            if nome == row.nome:
                continue
            changes.append({"tipo": tipo, "id": str(row.id), "antes": row.nome, "depois": nome})
            if aplicar:
                if tipo == "receita":
                    history = HistoricoReceita(db)
                    await history.inicial(row.id, tenant_id, origem="base_anterior")
                    row.nome = nome
                    await db.flush()
                    await history.registrar(row.id, tenant_id, None, "padronizacao_nome")
                else:
                    row.nome = nome
                    row.revisao += 1
        await db.flush()
    return changes


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant-id", type=UUID, required=True)
    parser.add_argument("--aplicar", action="store_true")
    args = parser.parse_args()
    async with AsyncSessionLocal() as db:
        changes = await padronizar(db, args.tenant_id, args.aplicar)
        if args.aplicar:
            await db.commit()
        else:
            await db.rollback()
        print(json.dumps({"aplicado": args.aplicar, "alteracoes": changes}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

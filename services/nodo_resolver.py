import logging
from dataclasses import dataclass

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)


@dataclass
class NodoRecord:
    id: str
    codigo: str
    zona_id: str | None


class NodoResolver:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def find_by_codigo(self, codigo: str) -> NodoRecord | None:
        async with self._pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT id::text, codigo, zona_id::text
                    FROM app.nodos
                    WHERE codigo = %s AND activo = true
                    LIMIT 1
                    """,
                    (codigo,),
                )
                row = await cur.fetchone()

        if not row:
            logger.warning("Nodo no registrado o inactivo: codigo=%s", codigo)
            return None

        return NodoRecord(
            id=row["id"],
            codigo=row["codigo"],
            zona_id=row["zona_id"],
        )

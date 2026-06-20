import json
import logging
import uuid
from typing import Any

from nats.aio.client import Client as NATS

logger = logging.getLogger(__name__)


class EventPublisher:
    def __init__(self, nats: NATS, request_timeout: float = 10.0) -> None:
        self._nats = nats
        self._request_timeout = request_timeout

    async def _request(self, pattern: str, data: Any) -> dict | list | str | None:
        payload = {
            "pattern": pattern,
            "data": data,
            "id": str(uuid.uuid4()),
        }
        message = json.dumps(payload).encode("utf-8")
        response = await self._nats.request(
            pattern,
            message,
            timeout=self._request_timeout,
        )
        body = json.loads(response.data.decode("utf-8"))

        if isinstance(body, dict) and body.get("err"):
            raise RuntimeError(body["err"])

        if isinstance(body, dict) and "response" in body:
            return body["response"]

        return body

    async def create_evento(self, evento_dto: dict) -> dict | list | str | None:
        logger.info(
            "Publicando eventos.create nodoId=%s evento=%s",
            evento_dto.get("nodoId"),
            evento_dto.get("metadatos", {}).get("evento_id_origen"),
        )
        return await self._request("eventos.create", evento_dto)

    async def heartbeat(self, nodo_id: str) -> dict | list | str | None:
        logger.debug("Publicando nodos.heartbeat nodoId=%s", nodo_id)
        return await self._request("nodos.heartbeat", nodo_id)

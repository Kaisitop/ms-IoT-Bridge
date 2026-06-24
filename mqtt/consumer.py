import asyncio
import json
import logging
from typing import Callable, Awaitable

from nats.aio.client import Client as NATS
from psycopg_pool import AsyncConnectionPool
from paho.mqtt.client import Client as MQTTClient, MQTTMessage

from config import settings
from models.mqtt_event import MqttEventPayload
from services.audio_storage import AudioStorage
from services.event_publisher import EventPublisher
from services.nodo_resolver import NodoResolver

logger = logging.getLogger(__name__)


class MqttConsumer:
    def __init__(
        self,
        pool: AsyncConnectionPool,
        nats: NATS,
        on_status_change: Callable[[bool], None] | None = None,
    ) -> None:
        self._pool = pool
        self._nats = nats
        self._on_status_change = on_status_change
        self._loop: asyncio.AbstractEventLoop | None = None
        self._client = MQTTClient(client_id=settings.mqtt_client_id)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

        self._nodo_resolver = NodoResolver(pool)
        self._audio_storage = AudioStorage(settings.audio_storage_path)
        self._publisher = EventPublisher(nats)

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._client.connect(settings.mqtt_host, settings.mqtt_port, keepalive=60)
        self._client.loop_start()
        logger.info(
            "MQTT conectando a %s:%s topic=%s",
            settings.mqtt_host,
            settings.mqtt_port,
            settings.mqtt_topic,
        )

    def stop(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()
        if self._on_status_change:
            self._on_status_change(False)

    def _on_connect(self, client: MQTTClient, userdata, flags, reason_code, properties=None) -> None:
        if reason_code == 0:
            client.subscribe(settings.mqtt_topic, qos=1)
            logger.info("MQTT conectado y suscrito a %s", settings.mqtt_topic)
            if self._on_status_change:
                self._on_status_change(True)
        else:
            logger.error("MQTT fallo de conexion: %s", reason_code)

    def _on_disconnect(self, client: MQTTClient, userdata, reason_code, properties=None) -> None:
        logger.warning("MQTT desconectado: %s", reason_code)
        if self._on_status_change:
            self._on_status_change(False)

    def _on_message(self, client: MQTTClient, userdata, msg: MQTTMessage) -> None:
        if not self._loop:
            return
        asyncio.run_coroutine_threadsafe(self._handle_message(msg), self._loop)

    async def _handle_message(self, msg: MQTTMessage) -> None:
        try:
            raw = json.loads(msg.payload.decode("utf-8"))
            event = MqttEventPayload.from_raw(raw)
        except Exception as exc:
            logger.error("Payload MQTT invalido: %s", exc)
            return

        nodo = await self._nodo_resolver.find_by_codigo(event.codigo_nodo)
        if not nodo:
            return

        try:
            audio_path = await self._audio_storage.save_wav(event.evento_id, event.audio_b64)
        except ValueError as exc:
            logger.error("%s", exc)
            return

        severidad = 2 if event.nivel_audio >= settings.severidad_umbral_db else 1
        evento_dto = {
            "tipo": "audio",
            "subtipo": "otro",
            "nodoId": nodo.id,
            "latitud": event.latitud,
            "longitud": event.longitud,
            "confianza": None,
            "severidad": severidad,
            "fuente": "app_movil",
            "audioUrl": audio_path,
            "metadatos": {
                "evento_id_origen": event.evento_id,
                "codigo_nodo": event.codigo_nodo,
                "nivel_audio_db": event.nivel_audio,
                "duracion_seg": event.duracion,
                "timestamp_origen": event.timestamp,
                "deteccion": "umbral_db",
            },
        }

        try:
            created = await self._publisher.create_evento(evento_dto)
            await self._publisher.heartbeat(nodo.id)

            if isinstance(created, dict) and created.get("id"):
                await self._publisher.publish_audio_ready(
                    {
                        "eventoId": created["id"],
                        "audioUrl": audio_path,
                        "nodoId": nodo.id,
                        "evento_id_origen": event.evento_id,
                        "codigo_nodo": event.codigo_nodo,
                    }
                )

            logger.info(
                "Evento procesado codigo=%s evento_id=%s severidad=%s db_id=%s",
                event.codigo_nodo,
                event.evento_id,
                severidad,
                created.get("id") if isinstance(created, dict) else None,
            )
        except Exception as exc:
            logger.exception("Error publicando a NATS: %s", exc)

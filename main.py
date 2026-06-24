import asyncio
import logging
import sys
from contextlib import asynccontextmanager

# psycopg async no funciona con ProactorEventLoop (default en Windows)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn
from fastapi import FastAPI
from nats.aio.client import Client as NATS
from psycopg_pool import AsyncConnectionPool

from config import settings
from mqtt.consumer import MqttConsumer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ms-iot-bridge")

nats_client = NATS()
db_pool: AsyncConnectionPool | None = None
mqtt_consumer: MqttConsumer | None = None
mqtt_connected = False


def _set_mqtt_status(connected: bool) -> None:
    global mqtt_connected
    mqtt_connected = connected


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, mqtt_consumer

    db_pool = AsyncConnectionPool(
        conninfo=settings.database_url,
        min_size=1,
        max_size=5,
        open=False,
    )
    await db_pool.open()
    logger.info("PostgreSQL conectado")

    await nats_client.connect(settings.nats_servers)
    logger.info("NATS conectado: %s", settings.nats_servers)

    loop = asyncio.get_running_loop()
    mqtt_consumer = MqttConsumer(db_pool, nats_client, on_status_change=_set_mqtt_status)
    mqtt_consumer.start(loop)

    yield

    if mqtt_consumer:
        mqtt_consumer.stop()
    if db_pool:
        await db_pool.close()
    if nats_client.is_connected:
        await nats_client.close()


app = FastAPI(title="ms-IoT-Bridge", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {
        "service": "ms-IoT-Bridge",
        "status": "ok",
        "mqtt_connected": mqtt_connected,
        "nats_connected": nats_client.is_connected,
        "database_connected": db_pool is not None,
        "mqtt_topic": settings.mqtt_topic,
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.http_host,
        port=settings.http_port,
        reload=False,
    )

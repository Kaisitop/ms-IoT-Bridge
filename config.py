from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_topic: str = "centinela/evento"
    mqtt_client_id: str = "centinela-iot-bridge"

    nats_servers: str = "nats://localhost:4222"

    database_url: str = "postgresql://postgres:123@localhost:5432/coreDB"

    audio_storage_path: str = "./data/audio"

    http_port: int = 8100
    http_host: str = "0.0.0.0"

    severidad_umbral_db: float = 80.0


settings = Settings()

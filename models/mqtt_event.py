from pydantic import BaseModel, Field


class MqttEventPayload(BaseModel):
    codigo_nodo: str = Field(min_length=1, max_length=50)
    evento_id: str = Field(min_length=1)
    timestamp: int
    duracion: int = Field(ge=1)
    nivel_audio: float
    latitud: float
    longitud: float
    audio_b64: str = Field(min_length=1)

    @classmethod
    def from_raw(cls, data: dict) -> "MqttEventPayload":
        codigo = data.get("codigo_nodo") or data.get("nodo_id")
        if not codigo:
            raise ValueError("Falta codigo_nodo o nodo_id en el payload MQTT")

        return cls(
            codigo_nodo=str(codigo),
            evento_id=str(data["evento_id"]),
            timestamp=int(data["timestamp"]),
            duracion=int(data["duracion"]),
            nivel_audio=float(data["nivel_audio"]),
            latitud=float(data["latitud"]),
            longitud=float(data["longitud"]),
            audio_b64=str(data["audio_b64"]),
        )

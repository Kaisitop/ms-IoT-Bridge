# ms-IoT-Bridge

Puente MQTT → NATS para nodos IoT de CENTINELA (UNEMI).

Recibe eventos de `nodo_app` por Mosquitto, guarda el audio WAV y publica `eventos.create` + `nodos.heartbeat` hacia `ms-core`.

## Flujo

```text
nodo_app → MQTT centinela/evento → ms-IoT-Bridge → NATS → ms-core → PostgreSQL (app.eventos)
```

## Requisitos

- Python 3.11+
- **Mosquitto instalado en tu máquina** (broker MQTT en `:1883`)
- NATS (:4222) — mismo que `ms-core`
- PostgreSQL + PostGIS — misma BD que `ms-core`
- `ms-core` corriendo como consumer NATS

## Mosquitto (Windows)

Este servicio **no incluye** el broker MQTT: debes tener [Mosquitto](https://mosquitto.org/download/) instalado y corriendo en tu PC antes de levantar `ms-IoT-Bridge`.

### Comprobar que Mosquitto está escuchando

En PowerShell o CMD:

```powershell
netstat -ano | findstr :1883
```

Si Mosquitto está activo, verás una línea con `LISTENING` en el puerto **1883**. Si no aparece nada, inicia el servicio Mosquitto o ejecuta `mosquitto.exe -v` desde su carpeta de instalación.


## Configuración

```powershell
cd ms-IoT-Bridge
copy .env.example .env
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Edita `.env` si tu MQTT/BD difieren de los defaults.

## Levantar el servicio

```powershell
python main.py
```

Health check: `GET http://localhost:8100/health`

## Payload MQTT esperado (desde nodo_app)

Topic: `centinela/evento`

```json
{
  "codigo_nodo": "nodo_audio_001",
  "evento_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": 1718640000000,
  "duracion": 4,
  "nivel_audio": 72.5,
  "latitud": -2.1345,
  "longitud": -79.5890,
  "audio_b64": "<WAV en Base64>"
}
```

## Prerequisito: nodo registrado

El `codigo_nodo` debe existir en `app.nodos`:

```http
POST /api/nodos
Authorization: Bearer {{token}}

{
  "codigo": "nodo_audio_001",
  "zonaId": "{{uuid_zona}}",
  "latitud": -2.1345,
  "longitud": -79.5890
}
```

## Prueba rápida con mosquitto_pub

Primero confirma que Mosquitto escucha en `:1883` (comando `netstat` arriba).

En Windows, `mosquitto_pub` suele **no estar en el PATH**. Entra a la carpeta de instalación y publica un evento de prueba:

```powershell
cd "C:\Program Files (x86)\Mosquitto"

.\mosquitto_pub -h localhost -t centinela/evento -m "{\"codigo_nodo\":\"nodo_audio_001\",\"evento_id\":\"test-002\",\"timestamp\":1718640001000,\"duracion\":5,\"nivel_audio\":97,\"latitud\":-2.1345,\"longitud\":-79.5890,\"audio_b64\":\"VGhpcyBpcyBhIHRlc3QgYXVkaW8gYmFzZTY0IHN0cmluZw==\"}"
```

Si `mosquitto_pub` ya está en tu PATH, puedes omitir el `cd`.

Luego verifica:

```sql
SELECT id, tipo, subtipo, nodo_id, severidad, fuente, created_at
FROM app.eventos
ORDER BY created_at DESC
LIMIT 5;
```

## Reglas fase 1 (sin ms-ia)

- `subtipo`: `otro`
- `fuente`: `app_movil`
- `severidad`: 2 si `nivel_audio >= 80`, else 1
- Si `codigo_nodo` no existe en BD → se descarta el mensaje (log warning)

## Estructura

```text
ms-IoT-Bridge/
├── main.py                 # FastAPI + lifespan
├── config.py               # variables de entorno
├── mqtt/consumer.py        # subscribe centinela/evento
├── services/
│   ├── nodo_resolver.py    # codigo → UUID (app.nodos)
│   ├── audio_storage.py    # audio_b64 → WAV
│   └── event_publisher.py  # NATS eventos.create / nodos.heartbeat
└── models/mqtt_event.py
```

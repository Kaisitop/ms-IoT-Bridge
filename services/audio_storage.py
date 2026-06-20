import base64
import logging
from pathlib import Path

import aiofiles

logger = logging.getLogger(__name__)


class AudioStorage:
    def __init__(self, base_path: str) -> None:
        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)

    async def save_wav(self, evento_id: str, audio_b64: str) -> str:
        safe_id = evento_id.replace("/", "_").replace("\\", "_")
        file_path = self._base_path / f"{safe_id}.wav"

        try:
            wav_bytes = base64.b64decode(audio_b64, validate=True)
        except Exception as exc:
            raise ValueError(f"audio_b64 invalido para evento {evento_id}") from exc

        async with aiofiles.open(file_path, "wb") as file:
            await file.write(wav_bytes)

        logger.info("Audio guardado: %s (%d bytes)", file_path, len(wav_bytes))
        return str(file_path.as_posix())

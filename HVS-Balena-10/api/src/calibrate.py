"""Secuencia de calibracion de la Hollymatic: encender -> esperar N s -> apagar.

Reimplementa la logica de app/src/executors/visionsistem.py::hollymatic_calibrate
corrigiendo el bug del time.sleep bloqueante (usa asyncio.sleep) y anadiendo un
lock para no lanzar dos calibraciones a la vez.
"""
import asyncio
import logging

from src.config import config
from src.mikasa import CONTROLLER

logger = logging.getLogger(__name__)

# Lock a nivel modulo para serializar calibraciones dentro de este servicio.
_calibration_lock = asyncio.Lock()


def is_calibrating() -> bool:
    """True si hay una calibracion en curso (el lock esta tomado)."""
    return _calibration_lock.locked()


async def run_calibration():
    """Enciende el enchufe, espera CALIBRATION_SECONDS y lo apaga.

    Pensada para ejecutarse como BackgroundTask. Si ya hay una calibracion en
    curso, no hace nada (el endpoint responde 409 antes de encolarla).
    """
    if _calibration_lock.locked():
        logger.warning("Calibracion ya en curso; se ignora la nueva solicitud.")
        return

    async with _calibration_lock:
        logger.info("Calibrando Hollymatic: encendiendo enchufe.")
        energized = False
        try:
            await CONTROLLER.update_plugs(True)
            energized = True
            await asyncio.sleep(config.CALIBRATION_SECONDS)
        except Exception as e:
            logger.critical(f"No se ha podido energetizar la hollymatic debido a: {e}")

        # Apagar siempre, aunque el encendido/espera fallara, para no dejar el enchufe encendido.
        try:
            await CONTROLLER.update_plugs(False)
            logger.info("Calibracion finalizada: enchufe apagado.")
        except Exception as e:
            level = logger.critical if energized else logger.error
            level(f"No se ha podido desenergetizar la hollymatic debido a: {e}")

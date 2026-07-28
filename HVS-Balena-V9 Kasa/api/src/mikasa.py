"""Controlador del enchufe Kasa (KP200), copia minima de app/src/mikasa/mikasa.py.

Solo depende de python-kasa: habla con el dispositivo por la LAN (TCP 9999).
No arrastra torch/opencv ni el resto del stack del servicio de vision.
"""
import logging

from kasa import Discover

from src.config import config

logger = logging.getLogger(__name__)


class SmartDeviceController:
    def __init__(self, ip_address, username, password):
        self.ip_address = ip_address
        self.username   = username
        self.password   = password
        self.device     = None

    async def discover_device(self):
        try:
            self.device = await Discover.discover_single(
                host=self.ip_address, port=9999,
                username=self.username, password=self.password,
            )
            await self.device.update()
        except Exception as e:
            # Se atrapa Exception y no SmartDeviceException (alias de KasaException):
            # un TimeoutError/OSError pelado no es KasaException y quedaba sin loggear.
            logger.error(f"Connection issue with the device: {e}")
            raise

    # ------------------------------------------------------------------ #
    #  Helpers internos del control por socket
    # ------------------------------------------------------------------ #
    async def _ensure_fresh_device(self):
        """Deja `self.device` listo y con la cache de estado recien refrescada.

        Actuar sobre cache fresca es imprescindible: IotStrip.turn_on/turn_off
        (kasa/iot/iotstrip.py:162-174) filtran por `plug.is_on` EN CACHE, asi que
        con un snapshot rancio el comando ni se envia al equipo.
        """
        if self.device is None:
            await self.discover_device()
            return
        try:
            await self.device.update()
        except Exception as e:
            # Sesion caida / router reiniciado: se reconstruye el objeto.
            logger.warning(f"No se pudo refrescar el estado del KP200 ({e}); se redescubre.")
            await self.discover_device()

    async def _refresh_states(self):
        """Refresca la cache de estados; un fallo aqui no aborta la secuencia."""
        try:
            await self.device.update()
        except Exception as e:
            logger.warning(f"No se pudo verificar el estado del KP200: {e}")

    def _plugs(self):
        """Sockets a controlar: los hijos del strip, o el propio equipo si no tiene."""
        return list(getattr(self.device, "children", None) or []) or [self.device]

    @staticmethod
    def _plug_name(plug, index):
        return getattr(plug, "alias", None) or getattr(plug, "child_id", None) or f"socket_{index}"

    @staticmethod
    def _is_on(plug):
        """Estado cacheado del socket, o None si no se pudo leer."""
        try:
            return bool(plug.is_on)
        except Exception:
            return None

    @staticmethod
    async def _set_plug(plug, state):
        # set_relay_state es idempotente (kasa/iot/iotplug.py:75-81): se manda
        # siempre, sin condicionar por el estado cacheado.
        if state:
            await plug.turn_on()
        else:
            await plug.turn_off()

    async def update_plugs(self, armado_correcto):
        """Aplica el estado pedido a CADA socket del KP200 de forma independiente.

        No se usa `device.turn_on()/turn_off()` del strip: filtran por el estado
        cacheado y, con cache rancia, el comando nunca se envia. Aqui se refresca
        el estado antes de actuar, se ordena el cambio socket por socket (el fallo
        de uno no impide actuar sobre el otro), se verifica contra el equipo y se
        reintenta una vez el que no obedecio.

        Lanza excepcion si algun socket queda en un estado distinto al pedido.
        """
        state = bool(armado_correcto)
        accion = "encender" if state else "apagar"

        await self._ensure_fresh_device()
        plugs = self._plugs()

        for index, plug in enumerate(plugs):
            try:
                await self._set_plug(plug, state)
            except Exception as e:
                # Un socket que falla NO debe impedir actuar sobre los demas.
                logger.error(f"No se pudo {accion} {self._plug_name(plug, index)}: {e}")

        # Verificacion contra el equipo y un reintento de los que no obedecieron.
        await self._refresh_states()
        reintentos = [(i, p) for i, p in enumerate(plugs) if self._is_on(p) is not state]
        for index, plug in reintentos:
            name = self._plug_name(plug, index)
            logger.warning(f"{name} no quedo en el estado pedido; reintentando {accion}.")
            try:
                await self._set_plug(plug, state)
            except Exception as e:
                logger.error(f"Reintento fallido al {accion} {name}: {e}")
        if reintentos:
            await self._refresh_states()

        estado_final = {self._plug_name(p, i): self._is_on(p) for i, p in enumerate(plugs)}
        logger.info(f"Estado final por socket: {estado_final}")

        incorrectos = [n for n, on in estado_final.items() if on is not state]
        if incorrectos:
            # Propagar para manejo externo (el llamador lo loggea como critical).
            raise RuntimeError(
                f"Sockets que no quedaron en {'ON' if state else 'OFF'}: {incorrectos}"
            )


# Singleton a nivel modulo (mismo patron que app/src/configs/configmikasa.py::CONTROLLER).
# El constructor no hace I/O de red; la primera llamada a update_plugs descubre el dispositivo.
CONTROLLER = SmartDeviceController(
    config.MIKASA_IP, config.MIKASA_USERNAME, config.MIKASA_PASSWORD,
)

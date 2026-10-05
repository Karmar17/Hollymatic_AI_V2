import asyncio
from kasa import Discover
import logging
import os

# Configure the logger to include timestamps and write to app.log
logging.basicConfig(
    filename='app.log',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Get the logger instance
logger = logging.getLogger(__name__)

class SmartDeviceController:
    def __init__(self, ip_address, username, password):
        # Initialize the SmartDeviceController with IP address, username, and password
        self.ip_address = ip_address
        self.username = username
        self.password = password
        self.device = None

    async def discover_device(self):
        # Log the start of device discovery
        try:
            # Discover the device using the provided IP address, username, and password
            self.device = await Discover.discover_single(host=self.ip_address,port=9999, username=self.username, password=self.password)
            # Log the successful discovery and update the device state
            await self.device.update()
        except Exception as e:
            # Se atrapa Exception y no SmartDeviceException (alias de KasaException):
            # un TimeoutError/OSError pelado no es KasaException y quedaba sin loggear.
            logger.error(f"Connection issue with the device: {e}")
            raise

    async def set_plug_state(self, index, state):

        self.device = await Discover.discover_single(host=self.ip_address,port=9999, username=self.username, password=self.password)
        # Get the plug by its index
        plug = self.device.get_plug_by_index(index)
        # Determine the action to take (turn on or turn off) based on the state
        action = plug.turn_on if state else plug.turn_off
        # Perform the action
        await action()

    # ------------------------------------------------------------------ #
    #  Helpers internos del control por socket
    # ------------------------------------------------------------------ #
    async def _ensure_fresh_device(self):
        """Deja `self.device` listo y con la caché de estado recién refrescada.

        Actuar sobre caché fresca es imprescindible: IotStrip.turn_on/turn_off
        (kasa/iot/iotstrip.py:162-174) filtran por `plug.is_on` EN CACHÉ, así que
        con un snapshot rancio el comando ni se envía al equipo. Este proceso vive
        días y no ve lo que hace el contenedor `app` entretanto.
        """
        if not hasattr(self, 'device') or self.device is None:
            await self.discover_device()
            return
        try:
            await self.device.update()
        except Exception as e:
            # Sesión caída / router reiniciado: se reconstruye el objeto.
            logger.warning(f"No se pudo refrescar el estado del KP200 ({e}); se redescubre.")
            await self.discover_device()

    async def _refresh_states(self):
        """Refresca la caché de estados; un fallo aquí no aborta la secuencia."""
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
        cacheado y, con caché rancia, el comando nunca se envía (era la causa de
        que el apagado nocturno dejara un socket energizado). Aquí se refresca el
        estado antes de actuar, se ordena el cambio socket por socket (el fallo de
        uno no impide actuar sobre el otro), se verifica contra el equipo y se
        reintenta una vez el que no obedeció.

        Lanza excepción si algún socket queda en un estado distinto al pedido.
        """
        state = bool(armado_correcto)
        accion = "encender" if state else "apagar"

        await self._ensure_fresh_device()
        plugs = self._plugs()

        for index, plug in enumerate(plugs):
            try:
                await self._set_plug(plug, state)
            except Exception as e:
                # Un socket que falla NO debe impedir actuar sobre los demás.
                logger.error(f"No se pudo {accion} {self._plug_name(plug, index)}: {e}")

        # Verificación contra el equipo y un reintento de los que no obedecieron.
        await self._refresh_states()
        reintentos = [(i, p) for i, p in enumerate(plugs) if self._is_on(p) is not state]
        for index, plug in reintentos:
            name = self._plug_name(plug, index)
            logger.warning(f"{name} no quedó en el estado pedido; reintentando {accion}.")
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


if __name__ == "__main__":
    kasa = SmartDeviceController(ip_address="10.0.0.247",username="x",password="y")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(kasa.update_plugs(True))

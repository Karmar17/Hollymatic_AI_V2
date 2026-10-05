from src.configs.settings import config
from src.tp_link.mikasa import SmartDeviceController 
from src.configs.configlogger import logger_config  

logger = logger_config.main_production_logger

controller = SmartDeviceController(
    ip_address=config.MIKASA_IP,
    username=config.MIKASA_USERNAME,
    password=config.MIKASA_PASSWORD,
)

class kp200:
    async def night_off():
        # Réplica exacta de hollymatic_shut_down (app/src/executors/visionsistem.py:197):
        # se desenergiza siempre, sin validar is_on, con el mismo manejo fail-soft.
        logger.info("Apagando Hollymatic")
        try:
            # Desenergiza socket por socket, con estado fresco, verificación y un
            # reintento; lanza si alguno queda encendido (ver mikasa.update_plugs).
            await controller.update_plugs(False)
        except Exception as e:
            logger.critical(f"No se ha podido desenergetizar la hollymatic debido a: {e}")
        except:
            logger.critical("No se ha podido desenergetizar la hollymatic debido a un error no reconocido.")
import asyncio
from src.configs.configs import config
from src.mikasa.mikasa import SmartDeviceController

class config_mikasa:

    MIKASA_IP = config.MIKASA_IP
    MIKASA_USERNAME = config.MIKASA_USERNAME
    MIKASA_PASSWORD = config.MIKASA_PASSWORD

    CONTROLLER = SmartDeviceController(MIKASA_IP,MIKASA_USERNAME,MIKASA_PASSWORD)
    CONTROLLING = CONTROLLER



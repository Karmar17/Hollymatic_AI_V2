import asyncio
from kasa import Discover, SmartDeviceException
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
        except SmartDeviceException as e:
            # Log any connection issues with the device and raise the exception
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

    async def update_plugs(self, armado_correcto):
        try:
            # Asegurar que el dispositivo está inicializado
            if not hasattr(self, 'device') or self.device is None:
                await self.discover_device()
            
            if armado_correcto == True: await self.device.turn_on() 
            else: await self.device.turn_off()
            
            # Actualizar estado del dispositivo
            await self.device.update()
            
            # Verificar estados
            plug_states = [self.device.get_plug_by_index(i).is_on for i in range(2)]
            logger.info(f"Plug states: {plug_states}")
            if armado_correcto and not all(plug_states):
                logger.warning("One or both plugs did not turn on as expected")
        except SmartDeviceException as e:
            logger.error(f"Error updating plug states: {e}")
            raise  # Propagar la excepción para manejo externo


if __name__ == "__main__":
    kasa = SmartDeviceController(ip_address="10.0.0.247",username="x",password="y")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(kasa.update_plugs(True))


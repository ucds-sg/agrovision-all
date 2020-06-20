"""
The Base Station is our edge device that establishes a long-lived connection to the IoT Hub.
It is responsible for triggering drone flights, managing sensors and uploading telemetry and
image data.

[ Base-Station ]  <----> [ IoT Hub ] <----> [ ML Component ]
                              ^
                              |
                           [ UI ]
"""
import logging
import time

from azure_tools import IoTHubWrapper
from sensors import SensorManager
from messages import RequestMessage
from config import IoTEdge
from farm import farm

logger = logging.getLogger(__name__)

class BaseStation():
    def __init__(self):
        """
        1) Establish link with IOT Hub
        2) Request for farm data
        3) Initialize sensor threads and handlers
        4) Wait for remote invocations and deliver them to the correct handler
        """
        self._init_azure()
        self._load_sensor_manager()
        self._establish_incoming_link()
        self._load_farm_data()
        self._init_sensors()
        self._idle()

    def _init_azure(self):
        """
        Azure SDK methods are wrapped by these helper classes
        """
        self._hub = IoTHubWrapper()

    def _load_sensor_manager(self):
        """
        Sensors are managed by the SensorManager. On init, the module loads list of sensor mappings 
        (ID, sensor type) from cosmos via the Hub
        """
        self._sensor_manager = SensorManager(self._hub)

    def _establish_incoming_link(self):
        """
        A separate thread starts listening for method invocations indefinitely
        """
        self._listen_thread = self._hub.listen_indefinitely(self._remote_method_handler)

    def _remote_method_handler(self, message):
        """
        Do something based on input from cloud (called from indefinite listener)
        """
        {
            "FLY_DRONE": self._sensor_manager.dispatch(message),

        }[message.event]

    def _load_farm_data(self):
        """
        Load all farm related data from the cloud
        Note that this is not a synchronus request and is serviced by the listen thread separately
        We enforce an abstracted synchronus behaviour
        """
        message = RequestMessage('FARM_DATA_LOAD', {})
        response = self._hub.request_from_hub(message)

        farm.initialize(response.data)

    def _init_sensors(self):
        """
        Based on the fetched farm data, initialize sensors
        """
        self._sensor_manager.init_sensors()

    def _idle(self):
        """
        Main control finally idles here. ctrl + c to end.
        """
        logger.info("Close window to end at any time to end simulation")
        try:
            self._listen_thread.join()
        except KeyboardInterrupt:
            logger.info("Ending simulations")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - [%(levelname)s] %(name)s: %(message)s')
    logging.getLogger('azure').setLevel(logging.WARN)
    logging.getLogger('paho').setLevel(logging.WARN)
    logging.getLogger('urllib3').setLevel(logging.WARN)

    BaseStation()

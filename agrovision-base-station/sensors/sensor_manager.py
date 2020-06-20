import logging
from threading import Lock
import json

from .drone import Drone
from .air_humidity import AirHumidity
from .air_pressure import AirPressure
from .air_temperature import AirTemperature
from .ph_sensor import PhSensor
from .salinity import SalinitySensor
from .soil_humidity import SoilHumidity
from .soil_temperature import SoilTemperature

from farm import farm

logger = logging.getLogger(__name__)

class SensorManager():

    MAPPING = {
        'drone': Drone,
        'air_humidity': AirHumidity, 
        'air_pressure': AirPressure, 
        'air_temperature': AirTemperature, 
        'ph_sensor': PhSensor, 
        'salinity_sensor': SalinitySensor, 
        'soil_humidity': SoilHumidity, 
        'soil_temp': SoilTemperature
    }

    def __init__(self, iot_hub):
        self._iot_hub = iot_hub
        self._telemetry_lock = Lock()
        self._telemetry_blob_lock = Lock()
        self._sensors = {}

    def init_sensors(self):
        """
        Initializes sensor objects based on mappings downloaded from the cloud
        Pass a telemetry function to allow individual sensors to transmit data at will
        """
        self._sensor_mappings = farm.sensors
        for mapping in self._sensor_mappings:
            # create appropriate sensor objects
            # every sensor gets its own thread (for simulation's sake)
            sensor_type = mapping['type']
            sensor_id = mapping['id']

            logger.info('Initializing: ' + sensor_type)

            # initialize sensor with its ID and a function reference to send telemetry
            sensor = SensorManager.MAPPING[sensor_type](sensor_id, self._telemetry, self._control)
            self._sensors[sensor_id] = sensor

        return self._sensors

    def _telemetry(self, payload, blob=False, blob_name=None, fpath=None):
        """
        Sensors use this method to transmit data at will 
        The `blob` kwarg allows sensors to upload blobs
        `blob_name` denotes the name of the blob on azure
        `fpath` denotes the file path of the blob to be uploaded
        """
        if not blob:
            # one sensor at a time to prevent conflicts
            self._telemetry_lock.acquire()
            self._iot_hub.send_telemetry(payload)
            self._telemetry_lock.release()

        else:
            # sensor is attempting to upload blob
            self._telemetry_blob_lock.acquire()
            self._iot_hub.upload_blob(blob_name, fpath)
            self._telemetry_blob_lock.release()

    def _control(self, message):
        """
        Sensors use this method to send control data to the cloud
        """
        # one sensor at a time to prevent conflicts
        self._telemetry_lock.acquire()
        self._iot_hub.send_control(message)
        self._telemetry_lock.release()

    def dispatch(self, message):
        """
        :param message: RemoteInvocationMessage
        Remote command received. Dispatch to correct sensor.
        """
        sensor = self._sensors[message.data['sensor_id']]
        sensor.handle_message(message.data)

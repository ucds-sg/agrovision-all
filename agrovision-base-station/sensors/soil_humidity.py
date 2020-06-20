import threading
import time
import random

from .sensor_base import SensorBaseClass
from messages import TelemetryMessage

class SoilHumidity(SensorBaseClass):
    INTERVAL_SEC = 20
    TYPE = 'soil_humidity'
    UNIT = '%'
    CHOICE = [0.01, 0, -0.01]

    def __init__(self, id, telemetry, control):
        """
        Description
        """
        self.id = id
        self.telemetry = telemetry
        # if data needs to be requested
        self.control = control
        self.last = 42.8

        self.thread = threading.Thread(target=self._sense_indefinitely)
        self.thread.daemon = True
        self.thread.start()

    def _sense_indefinitely(self):
        while True:
            time.sleep(SoilHumidity.INTERVAL_SEC)
            sensed_data = self._sense()
            payload = self._marshall_payload(sensed_data)
            self.telemetry(payload)

    def _sense(self):
        value = self.last + random.choice(SoilHumidity.CHOICE) * self.last # generating random value
        self.last = value
        value = round(value, 2)
        return value

    def _marshall_payload(self, sensed_data):
        """
        Creates the body of the telemetry payload
        """
        data = {
            "unit": SoilHumidity.UNIT,
            "value": sensed_data
        }
        payload = TelemetryMessage(self.id, SoilHumidity.TYPE, data)
        return payload

    def handle_message(self, intent):
        pass

import threading
import time
import random

from .sensor_base import SensorBaseClass
from messages import TelemetryMessage

class AirTemperature(SensorBaseClass):
    INTERVAL_SEC = 30
    TYPE = 'air_temperature'
    UNIT = 'C'
    CHOICE = [0.01, 0, -0.01]

    def __init__(self, id, telemetry, control):
        """
        Description
        """
        self.id = id
        self.telemetry = telemetry
        # if data needs to be requested
        self.control = control
        self.last = 29.03

        self.thread = threading.Thread(target=self._sense_indefinitely)
        self.thread.daemon = True
        self.thread.start()

    def _sense_indefinitely(self):
        while True:
            time.sleep(AirTemperature.INTERVAL_SEC)
            sensed_data = self._sense()
            payload = self._marshall_payload(sensed_data)
            self.telemetry(payload)

    def _sense(self):
        value = self.last + random.choice(AirTemperature.CHOICE) * self.last # generating random value
        self.last = value
        value = round(value, 2)
        return value

    def _marshall_payload(self, sensed_data):
        """
        Creates the body of the telemetry payload
        """
        data = {
            "unit": AirTemperature.UNIT,
            "value": sensed_data
        }
        payload = TelemetryMessage(self.id, AirTemperature.TYPE, data)
        return payload

    def handle_message(self, intent):
        pass

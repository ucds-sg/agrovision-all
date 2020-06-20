import threading
import time
import random

from .sensor_base import SensorBaseClass
from messages import TelemetryMessage

class AirPressure(SensorBaseClass):
    INTERVAL_SEC = 10
    TYPE = 'air_pressure'
    UNIT = 'KPa'
    CHOICE = [0.01, 0, -0.01]

    def __init__(self, id, telemetry, control):
        """
        Description
        """
        self.id = id
        self.telemetry = telemetry
        # if data needs to be requested
        self.control = control
        self.last = 101.10

        self.thread = threading.Thread(target=self._sense_indefinitely)
        self.thread.daemon = True
        self.thread.start()

    def _sense_indefinitely(self):
        while True:
            time.sleep(AirPressure.INTERVAL_SEC)
            sensed_data = self._sense()
            payload = self._marshall_payload(sensed_data)
            self.telemetry(payload)

    def _sense(self):
        value = self.last + random.choice(AirPressure.CHOICE) * self.last # generating random value
        value = round(value, 2)
        self.last = value
        return value

    def _marshall_payload(self, sensed_data):
        """
        Creates the body of the telemetry payload
        """
        data = {
            "unit": AirPressure.UNIT,
            "value": sensed_data
        }
        payload = TelemetryMessage(self.id, AirPressure.TYPE, data)
        return payload

    def handle_message(self, intent):
        pass

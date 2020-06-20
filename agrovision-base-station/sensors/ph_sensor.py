import threading
import time
import random

from .sensor_base import SensorBaseClass
from messages import TelemetryMessage

class PhSensor(SensorBaseClass):
    INTERVAL_SEC = 20
    TYPE = 'ph_sensor'
    UNIT = 'pH'
    CHOICE = [0.01, 0, -0.01]

    def __init__(self, id, telemetry, control):
        """
        Description
        """
        self.id = id
        self.telemetry = telemetry
        # if data needs to be requested
        self.control = control
        self.last = 5.5

        self.thread = threading.Thread(target=self._sense_indefinitely)
        self.thread.daemon = True
        self.thread.start()

    def _sense_indefinitely(self):
        while True:
            time.sleep(PhSensor.INTERVAL_SEC)
            sensed_data = self._sense()
            payload = self._marshall_payload(sensed_data)
            self.telemetry(payload)

    def _sense(self):
        value = self.last + random.choice(PhSensor.CHOICE) * self.last # generating random value
        self.last = value
        value = round(value, 1)
        if value > 6.1:
            value = 6
        elif value <= 2:
            value = 2
        return value

    def _marshall_payload(self, sensed_data):
        """
        Creates the body of the telemetry payload
        """
        data = {
            "unit": PhSensor.UNIT,
            "value": sensed_data
        }
        payload = TelemetryMessage(self.id, PhSensor.TYPE, data)
        return payload

    def handle_message(self, intent):
        pass

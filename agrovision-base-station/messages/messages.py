"""
Standard message protocol to communicate with the Hub
"""
import json
from azure.iot.device import Message

from config import IoTEdge
from farm import farm

class BaseMessage():
    def __init__(self):
        self.type = 'DEFAULT'

class RequestMessage(BaseMessage):
    """
    Used to request for specific data
    """
    def __init__(self, event, data):
        """
        :param event: which function it should be routed to
        :param data: dict of data
        :return: azure.iot.device.Message
        """
        self.type = 'REQUEST'
        self.event = event
        self.payload = self._serialize(data)

    def _serialize(self, data):
        """
        Converts it into `Message` object from azure.iot.device
        """
        payload_data = {'data': data}
        payload_data['messageEvent'] = self.event
        message = Message(json.dumps(payload_data))

        message.custom_properties['MESSAGE_TYPE'] = self.type
        message.custom_properties['EVENT'] = self.event
        return message

class ControlMessage(RequestMessage):
    """
    Control messages exchanged between hub and device
    Looks exactly like a request message
    """
    def __init__(self, event, data):
        super().__init__(event, data) # compatibility reasons: for routing it correctlty
        self.event = event

class ResponseMessage(BaseMessage):
    """
    Used to hold response
    """
    def __init__(self, event, payload):
        """
        :param event: which function it came from (corresponding to request)
        :param payload: dict of data
        """
        self.type = 'RESPONSE'
        self.event = event
        self.data = self._deserialize(payload)

    def _deserialize(self, payload):
        return json.loads(payload)

class TelemetryMessage(BaseMessage):
    """
    Used by sensors
    """
    def __init__(self, device_id, device_type, data):
        self.type = 'TELEMETRY'
        self.event = 'SEND_TELEMETRY'
        self.device_id = device_id
        self.device_type = device_type
        self.payload = self._serialize(data)

    def _serialize(self, data):
        """
        Converts it into `Message` object from azure.iot.device
        """
        payload_data = {'data': data}

        # set metadata for remote processing (IoTEdge.DEVICE_ID corresponds to base station ID)
        payload_data['deviceId'] = IoTEdge.DEVICE_ID + '.' + self.device_id
        payload_data['deviceType'] = self.device_type
        payload_data['farmId'] = farm.id

        message = Message(json.dumps(payload_data))
        message.custom_properties['MESSAGE_TYPE'] = self.type
        message.custom_properties['EVENT'] = self.event
        return message

class RemoteInvocationMessage(BaseMessage):
    """
    Incoming message from cloud
    """
    def __init__(self, event, raw_data):
        self.type = 'REMOTE_INV'
        self.event = event
        self.data = self._deserialize(raw_data)

    def _deserialize(self, raw_json):
        return json.loads(raw_json)

import logging
import json

import azure.functions as func
from azure.iot.hub import IoTHubRegistryManager

class IoTHub:
    CONNECTION_STRING = "HostName=agrovision-iot-hub.azure-devices.net;SharedAccessKeyName=service;SharedAccessKey=ITeD77TL9bGmBCB5bJfxzdeyWJfOz9YjuC8nQkPwMRM="

def main(req: func.HttpRequest) -> func.HttpResponse:
    # fetch the deviceId from the request
    try:
        device_id = req.params['device_id']
        sensor_id = req.params['sensor_id']
    except (ValueError, KeyError) as e:
        return func.HttpResponse("Incorrect request body",
            status_code=422
        )

    props = {
        'TYPE': 'REMOTE_INVOCATION',
        'EVENT': 'FLY_DRONE'
    }
    payload = json.dumps({
        'device_id': device_id,
        'sensor_id': sensor_id
    })

    registry_manager = IoTHubRegistryManager(IoTHub.CONNECTION_STRING)
    registry_manager.send_c2d_message(device_id, payload, properties=props)

    return func.HttpResponse("Invoked",
            status_code=200
    )

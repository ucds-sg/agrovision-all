import logging
import azure.functions as func

import json
import requests

from .get_farm_data import get_farm_data
from .run_finished import update_run_id, invoke_pred

def main(event: func.EventHubEvent):
    device_id = event.iothub_metadata['connection-device-id']
    message_event = json.loads(event.get_body())["messageEvent"]

    logging.info(device_id + " " + message_event)

    if message_event == "FARM_DATA_LOAD":
        # send farm data back to the device
        get_farm_data(device_id)
    elif message_event == "RUN_FINISHED":
        # update run_id on cosmos
        run_id = json.loads(event.get_body())["data"]["runId"]
        farm_id = update_run_id(device_id, run_id)
        logging.info("Updated run: " + str(run_id) + " " + farm_id)

        # invoke ML prediction
        response = invoke_pred(farm_id, run_id)
        logging.info(response)

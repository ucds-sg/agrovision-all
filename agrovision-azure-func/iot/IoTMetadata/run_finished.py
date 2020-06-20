import json
import requests
from azure.iot.hub import IoTHubRegistryManager
from azure.cosmos import CosmosClient

from .config import Cosmos, IoTHub, AgroML

def update_run_id(device_id, run_id):
    # first get the appropriate farm
    client = CosmosClient(Cosmos.URL, Cosmos.KEY)
    farms_container = client.get_database_client(Cosmos.DATABASE).get_container_client(Cosmos.FARMS_CONTAINER)

    query = """SELECT c.id as farm_id, f
        FROM farms f
        JOIN c IN f.farms_arr
        WHERE c.base_station.deviceId = @dev_id"""

    items = farms_container.query_items(
        query=query,
        parameters=[{ "name":"@dev_id", "value": device_id }],
        enable_cross_partition_query=True
    )

    item = next(items)
    farm_id = item['farm_id']
    document = item['f']

    # loop through the farms and find the correct farm to update run id
    for farm_obj in document['farms_arr']:
        if farm_obj['id'] == farm_id:
            farm_obj['last_run'] = run_id

    # finally update document
    farms_container.upsert_item(document)

    return farm_id

def invoke_pred(farm_id, run_id):
    pred_url = AgroML.PREDICTION_URL
    ndvi_url = AgroML.PREDICTION_NDVI_URL

    payload = json.dumps({
        'farmid': farm_id,
        'runid': run_id
    })
    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", pred_url, headers=headers, data = payload)
    response = requests.request("POST", ndvi_url, headers=headers, data = payload)

    return response.text.encode('utf8')

import logging
import json
import azure.functions as func
from azure.cosmos import CosmosClient

class Cosmos:
    URL = "https://agrovision-cosmos.documents.azure.com:443/"
    KEY = "GnF5yD8RVjA0e9U1p62BAF4qS8rDmlMoxgMPqtsqgtIuiU589RWyUWCkFxBfnKnsjbhEYbxrvkyOYoDyslq5yw=="
    DATABASE = "agrovision-db"
    TELEMETRY = "telemetry"

DEVICE_TYPES = [
    'air_humidity',
    'air_pressure',
    'air_temperature',
    'ph_sensor',
    'salinity_sensor',
    'soil_humidity',
    'soil_temp'
]


def get_latest_sensor_data(farm_id):
    client = CosmosClient(Cosmos.URL, Cosmos.KEY)
    pred_container = client.get_database_client(Cosmos.DATABASE).get_container_client(Cosmos.TELEMETRY)

    query = """SELECT c.data
            FROM c
            WHERE c.farmId=@farm_id AND c.deviceType=@device_type
            ORDER BY c._ts DESC
            OFFSET 0 LIMIT 1"""

    
    # loop through each device and fetch latest sensor reading for each device
    agg_result = {}
    for device in DEVICE_TYPES:
        items = list(pred_container.query_items(
            query=query,
            parameters=[{ "name":"@farm_id", "value": farm_id },{ "name":"@device_type", "value": device }],
            enable_cross_partition_query=True
        ))
        try:

            agg_result[device] = {
                'unit': items[0]['data']['unit'],
                'value': items[0]['data']['value']
            }
        except: 
            agg_result[device] = None
    
    return agg_result

def main(req: func.HttpRequest) -> func.HttpResponse:
    # fetch the farm_id from the request
    try:
        farm_id = req.params['farm_id']
    except (ValueError, KeyError) as e:
        return func.HttpResponse(
            "Incorrect request body",
            status_code=422
        )

    agg_result = get_latest_sensor_data(farm_id)

    return func.HttpResponse(
        json.dumps(agg_result),
        mimetype="application/json",
        status_code=200
    )

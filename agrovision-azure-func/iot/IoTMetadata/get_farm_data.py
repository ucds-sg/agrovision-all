import json
from azure.iot.hub import IoTHubRegistryManager
from azure.cosmos import CosmosClient

from .config import Cosmos, IoTHub

def get_farm_data(device_id):    
    # query farm data correspoding to device
    client = CosmosClient(Cosmos.URL, Cosmos.KEY)
    farms_container = client.get_database_client(Cosmos.DATABASE).get_container_client(Cosmos.FARMS_CONTAINER)

    query = """SELECT c
                FROM farms f
                JOIN c IN f.farms_arr
                WHERE c.base_station.deviceId = @dev_id"""

    items = list(farms_container.query_items(
        query=query,
        parameters=[{ "name":"@dev_id", "value": device_id }],
        enable_cross_partition_query=True
    ))

    props = {
        'TYPE': 'RESPONSE',
        'EVENT': 'FARM_DATA_LOADED'
    }

    payload = json.dumps(items[0]['c'])
    # write back response to the device
    registry_manager = IoTHubRegistryManager(IoTHub.CONNECTION_STRING)
    registry_manager.send_c2d_message(device_id, payload, properties=props)

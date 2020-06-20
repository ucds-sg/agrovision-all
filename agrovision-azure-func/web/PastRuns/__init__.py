import logging
import json
import azure.functions as func
from azure.cosmos import CosmosClient

class Cosmos:
    URL = "https://agrovision-cosmos.documents.azure.com:443/"
    KEY = "GnF5yD8RVjA0e9U1p62BAF4qS8rDmlMoxgMPqtsqgtIuiU589RWyUWCkFxBfnKnsjbhEYbxrvkyOYoDyslq5yw=="
    DATABASE = "agrovision-db"
    FARMS_CONTAINER = "farms"

def get_past_runs(farm_id):    
    # query for past runs and their timestamps
    client = CosmosClient(Cosmos.URL, Cosmos.KEY)
    pred_container = client.get_database_client(Cosmos.DATABASE).get_container_client(Cosmos.PRED_CONTAINER)

    query = """SELECT predictions.runId, predictions._ts
            FROM predictions
            WHERE predictions.farmId=@farm_id"""

    items = list(pred_container.query_items(
        query=query,
        parameters=[{ "name":"@farm_id", "value": farm_id }],
        enable_cross_partition_query=True
    ))

    try:
        return items
    except IndexError:
        return None


def main(req: func.HttpRequest) -> func.HttpResponse:
    # TODO authenticate user based on user id (get from req perhaps?)
    # fetch the farm_id from the request
    try:
        farm_id = req.params['farm_id']
    except (ValueError, KeyError) as e:
        return func.HttpResponse(
            "Incorrect request body",
            status_code=422
        )

    payload = get_past_runs(farm_id)
    if payload is None:
        return func.HttpResponse(
            "Farm does not exist",
            status_code=404
        )

    return func.HttpResponse(
        json.dumps(payload),
        mimetype="application/json",
        status_code=200
    )

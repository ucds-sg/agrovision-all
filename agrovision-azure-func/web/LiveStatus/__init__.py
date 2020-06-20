import logging
import json
import azure.functions as func
from azure.cosmos import CosmosClient

class Cosmos:
    URL = "https://agrovision-cosmos.documents.azure.com:443/"
    KEY = "GnF5yD8RVjA0e9U1p62BAF4qS8rDmlMoxgMPqtsqgtIuiU589RWyUWCkFxBfnKnsjbhEYbxrvkyOYoDyslq5yw=="
    DATABASE = "agrovision-db"
    PREDICTION = "predictions"


def get_live_status(farm_id, run_id):
    client = CosmosClient(Cosmos.URL, Cosmos.KEY)
    pred_container = client.get_database_client(Cosmos.DATABASE).get_container_client(Cosmos.PREDICTION)

    query = """SELECT p.runId
        FROM predictions p
        WHERE p.farmId=@farm_id AND p.runId=@run_id"""

    items = list(pred_container.query_items(
        query=query,
        parameters=[{ "name":"@farm_id", "value": farm_id },{ "name":"@run_id", "value": int(run_id) }],
        enable_cross_partition_query=True
    ))

    return True if len(items) == 2 else False


def main(req: func.HttpRequest) -> func.HttpResponse:
    # fetch the farm_id from the request
    try:
        farm_id = req.params['farm_id']
        run_id = req.params['run_id']
    except (ValueError, KeyError) as e:
        return func.HttpResponse(
            "Incorrect request body",
            status_code=422
        )

    status = get_live_status(farm_id, run_id)

    return func.HttpResponse(
        json.dumps({'status': status}),
        mimetype="application/json",
        status_code=200
    )

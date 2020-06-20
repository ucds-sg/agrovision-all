import logging
import json
import azure.functions as func
from azure.cosmos import CosmosClient

class Cosmos:
    URL = "https://agrovision-cosmos.documents.azure.com:443/"
    KEY = "GnF5yD8RVjA0e9U1p62BAF4qS8rDmlMoxgMPqtsqgtIuiU589RWyUWCkFxBfnKnsjbhEYbxrvkyOYoDyslq5yw=="
    DATABASE = "agrovision-db"
    PRED_CONTAINER = "predictions"


def get_predictions_from_runId(pred_container, farm_id, run_id, pred_type):

    query = """SELECT p.result, p._ts as unix_ts
            FROM predictions p
            WHERE p.farmId=@farm_id AND p.runId=@run_id AND p.pred_type=@pred_type"""

    items = list(pred_container.query_items(
        query=query,
        parameters=[{ "name":"@farm_id", "value": farm_id },{ "name":"@run_id", "value": int(run_id) },{ "name":"@pred_type", "value": pred_type}],
        enable_cross_partition_query=True
    ))

    try:
        return items[0]['result'], items[0]['unix_ts']
    except IndexError:
        return None, None


def main(req: func.HttpRequest) -> func.HttpResponse:
    # fetch the farm_id from the request
    try:
        farm_id = req.params['farm_id']
        run_id = req.params['run_id']
        pred_type = req.params['pred_type']
    except (ValueError, KeyError) as e:
        return func.HttpResponse(
            "Incorrect request body",
            status_code=422
        )

    client = CosmosClient(Cosmos.URL, Cosmos.KEY)
    pred_container = client.get_database_client(Cosmos.DATABASE).get_container_client(Cosmos.PRED_CONTAINER)

    results, timestamp = get_predictions_from_runId(pred_container, farm_id, run_id, pred_type)

    payload = {
        'results': results,
        'timestamp': timestamp
    }

    return func.HttpResponse(
        json.dumps(payload),
        mimetype="application/json",
        status_code=200
    )

import logging
import json
import azure.functions as func
from azure.cosmos import CosmosClient

class Cosmos:
    URL = "https://agrovision-cosmos.documents.azure.com:443/"
    KEY = "GnF5yD8RVjA0e9U1p62BAF4qS8rDmlMoxgMPqtsqgtIuiU589RWyUWCkFxBfnKnsjbhEYbxrvkyOYoDyslq5yw=="
    DATABASE = "agrovision-db"
    FARMS_CONTAINER = "farms"

def get_farm_data(user_id):    
    # query farm data correspoding to device
    client = CosmosClient(Cosmos.URL, Cosmos.KEY)
    farms_container = client.get_database_client(Cosmos.DATABASE).get_container_client(Cosmos.FARMS_CONTAINER)

    query = """SELECT f
                FROM farms f
                WHERE f.username = @user_id"""

    items = list(farms_container.query_items(
        query=query,
        parameters=[{ "name":"@user_id", "value": user_id }],
        enable_cross_partition_query=True
    ))

    try:
        return items[0]['f']
    except IndexError:
        return None


def main(req: func.HttpRequest) -> func.HttpResponse:
    # fetch the user_id from the request
    try:
        user_id = req.params['user_id']
    except (ValueError, KeyError) as e:
        return func.HttpResponse(
            "Incorrect request body",
            status_code=422
        )

    payload = get_farm_data(user_id)
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

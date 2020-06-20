
import json
import logging
import os

import azure.functions as func
from azure.cognitiveservices.vision.customvision.prediction import CustomVisionPredictionClient #Custom Vision
from msrest.authentication import ApiKeyCredentials
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient #Blob Storage
from azure.cosmos import exceptions, CosmosClient, PartitionKey

import json
import os, uuid

class CosmosClientConstants:
    URL = "https://agrovision-cosmos-dev.documents.azure.com:443/"
    KEY = "7qaihe2e1yBZxRcRjHixB0qeNWyCv47q23brD7Oy4hW5CVBwkSoVj90W3IsHe1hBsNz9FC6FRFD1HTCtCNW7Bw=="
    DATABASE_STR = "farms"
    CONTAINER_STR = "predictions"

class BlobStorage:
    CONNECT_STR = "DefaultEndpointsProtocol=https;AccountName=agrovisionblob;AccountKey=MfWtU/gcPWvGy93tqjFnwBfsxsXSsdZvre40vR90wQY84xlZ36use7Tpzoj2d1GZNgwpAAabIQ2UWIr6WkGqlQ==;EndpointSuffix=core.windows.net"
    CONTAINER_NAME="cv-test"

class CustomVisionPredConstants:
    PREDICTION_KEY = "4657e88b11e94d5b92f2af2b5412725d"
    ENDPOINT = "https://azurehackathoncust-prediction.cognitiveservices.azure.com//"
    PROJECT_ID = "4e40a445-e418-4cac-84df-9ebc365f25b7"
    ITERATION_NAME = "Prediction_Iteration"

def customvision_predict(blob_url):
    prediction_credentials = ApiKeyCredentials(in_headers={"Prediction-key": CustomVisionPredConstants.PREDICTION_KEY})
    predictor = CustomVisionPredictionClient(CustomVisionPredConstants.ENDPOINT, prediction_credentials)
    results = predictor.classify_image_url(CustomVisionPredConstants.PROJECT_ID, CustomVisionPredConstants.ITERATION_NAME, blob_url)
    
    prediction_dict = {}
    for prediction in results.predictions:
        prediction_dict[prediction.tag_name] = round(prediction.probability * 100, 2)
    
    return prediction_dict


def get_predictions(farmid, runid):
    run_prediction_list = []
    SEP = '/'
    run_images_path = str(farmid) + ".basestation" + SEP + str(runid)  #Change this if required
    try:
        blob_service_client = BlobServiceClient.from_connection_string(BlobStorage.CONNECT_STR)
        container_client = blob_service_client.get_container_client(BlobStorage.CONTAINER_NAME)

        blob_list = container_client.list_blobs(name_starts_with=run_images_path)
        for blob in blob_list:
            blob_url = container_client.primary_endpoint + "/" + blob.name
            blob_prediction_dict = customvision_predict(blob_url)
            
            grid_id = blob.name.split(SEP)[-1].split('.')[0]  #Get the grid_id from blob_name 1/2/7.png -> 7
            blob_prediction_dict["grid_id"] = grid_id  #Add grid id to dict 
            run_prediction_list.append(blob_prediction_dict)
        
        logging.info("Prediction Results for all Image: Success")
        return run_prediction_list

    except Exception as ex:
        logging.error(ex)


def sendToCosmos(farmid, runid, result_list):
    client = CosmosClient(CosmosClientConstants.URL, CosmosClientConstants.KEY)
    container = client.get_database_client(CosmosClientConstants.DATABASE_STR)\
                      .get_container_client(CosmosClientConstants.CONTAINER_STR)
    test_string = {  
    "id": str(farmid) + "_" + str(runid),  
    "farmId": str(farmid),
    "runId": runid,
    "result":  result_list
    }
    container.upsert_item(test_string)
    logging.info("Upload to Cosmos Succesful")


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        data = req.get_json()
        farmid, runid = data['farmid'], data['runid']

        run_prediction_list = get_predictions(farmid, runid)
        sendToCosmos(farmid, runid, run_prediction_list)
    except Exception:
        logging.error("Exception while trying to get data from HTTP Request")
        return func.HttpResponse(f"Failure !")
    
    return func.HttpResponse(f"Prediction Results Uploaded to Cosmos Sucessfully")

    
    


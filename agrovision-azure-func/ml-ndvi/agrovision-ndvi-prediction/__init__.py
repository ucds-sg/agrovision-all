import json
import logging
import os
import requests 
import io

import azure.functions as func
import numpy as np
from azure.storage.blob import BlobServiceClient

import torch
import torch.nn as nn
from msrest.authentication import ApiKeyCredentials
from torch.utils.data import ConcatDataset, DataLoader, Dataset
from torchvision import transforms
from azure.cosmos import exceptions, CosmosClient, PartitionKey

class CosmosClientConstants:
    """Azure Cosmos Client Constants 
    """
    URL = "https://agrovision-cosmos.documents.azure.com:443/"
    KEY = "GnF5yD8RVjA0e9U1p62BAF4qS8rDmlMoxgMPqtsqgtIuiU589RWyUWCkFxBfnKnsjbhEYbxrvkyOYoDyslq5yw=="
    DATABASE_STR = "agrovision-db"
    CONTAINER_STR = "predictions"


class NDVITransforms:
    """NDVI Transforms to resize it to 256 * 256 
    with a bilinear transformation
    """
    COMPOSE = transforms.Compose([transforms.ToPILImage(), transforms.Resize((256, 256)), transforms.ToTensor()])

class BlobStorage:
    """Blob Storage Constants
    """
    CONNECT_STR = "DefaultEndpointsProtocol=https;AccountName=agrovisionstore;AccountKey=+1kPv6QocFWNO6Aj468YwbAnzQrMraHW/7pDHr8ShbN6O+gNyNFumMV5rmv6r6roYCscqHcN4CyHlKzDzofTDw==;EndpointSuffix=core.windows.net"
    CONTAINER_NAME="iot-runs"


class NDVIConvNet(nn.Module):
    """Detect Plant Health Probability from NDVI Matrix
    Architecture Conv -> Maxpool -> Linear 
    Labels - 0 Healthy, 1 Unhealthy 
    """
    def __init__(self):
        super(NDVIConvNet, self).__init__()
        self.conv_1 = nn.Conv2d(1, 1, 4)
        self.maxpool_1 = nn.MaxPool2d(kernel_size=8)
        self.linear = nn.Linear(961, 1)

    def forward(self, inputs):
        batch_size = inputs.shape[0]
        x = self.conv_1(inputs)
        x = self.maxpool_1(x)
        x = x.view(batch_size, -1)

        return self.linear(x)


def get_predictions(farmid, runid):
    """Get the predictions for farmid and runid
    """
    logging.info("Get Predictions Function called succesfully")
    np_input_files, grid_list, pred_input_list = [], [], []

    # Model Initialization
    model = NDVIConvNet()
    model.load_state_dict(torch.load("./agrovision-ndvi-prediction/ndvi-mlmodel.pt"))
    model.eval()
    logging.info("Model Loaded Succesfully")

    # Blob Storage
    blob_service_client = BlobServiceClient.from_connection_string(BlobStorage.CONNECT_STR)
    container_client = blob_service_client.get_container_client(BlobStorage.CONTAINER_NAME)
    blob_list = container_client.list_blobs()

    SEP = "/"
    run_images_path = str(farmid) + ".basestation" + SEP + str(runid) + SEP + "ndvi"  #Change this if required
    blob_list = container_client.list_blobs(name_starts_with=run_images_path)
    primary_url = container_client.primary_endpoint
    logging.info("Current Run NDVI Matrix Path: " + run_images_path)

    for blob in blob_list:
        grid_name = blob.name.split(SEP)[-1].split(".")[0]  # Get the grid name

        if blob.name[-3:] == "npy":
            response = requests.get(primary_url + "/" + blob.name)
            response.raise_for_status()
            data = np.load(io.BytesIO(response.content))
            np_input_files.append(data)
            grid_list.append(grid_name)
    
    # Prepare the data for prediction
    for np_matrix in np_input_files:
        numpy_matrix = np.expand_dims(np.float32(np_matrix), 2)
        pred_input_list.append(NDVITransforms.COMPOSE(numpy_matrix))
    pred_input_tensor = torch.cat(pred_input_list).unsqueeze(1)
    logging.info("Prepared data input tensor sucessfully")

    # Get predictions from model
    predictions = torch.sigmoid(model(pred_input_tensor))
    prediction_list = predictions.squeeze(1).tolist()

    # Get the result lists 
    result_list = []
    for grid_name, prediction in zip(grid_list, prediction_list):
        tmp = {}
        tmp["grid_id"] = grid_name
        tmp["health_prob"] = prediction
        result_list.append(tmp)

    return result_list


def sendToCosmos(farmid, runid, result_list):
    client = CosmosClient(CosmosClientConstants.URL, CosmosClientConstants.KEY)
    container = client.get_database_client(CosmosClientConstants.DATABASE_STR)\
                      .get_container_client(CosmosClientConstants.CONTAINER_STR)
    test_string = {  
    "id": str(farmid) + "_" + str(runid) + "ndvi",  
    "farmId": str(farmid),
    "runId": runid,
    "pred_type": "ndvi", 
    "result":  result_list
    }
    container.upsert_item(test_string)
    logging.info("Upload to Cosmos Succesful")


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    try:
        data = req.get_json()
        farmid, runid = data['farmid'], data['runid']

        results = get_predictions(farmid, runid)
        logging.info("Got results sucessfully")

        sendToCosmos(farmid, runid, results)
    except Exception as e:
        logging.error("Exception while trying to get data from HTTP Request" + str(e))
        return func.HttpResponse(f"Failure !")
    
    return func.HttpResponse(f"NDVI Prediction Results Uploaded to Cosmos Sucessfully")



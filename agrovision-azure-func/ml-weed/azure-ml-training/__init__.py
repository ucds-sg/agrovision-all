from azure.cognitiveservices.vision.customvision.training import CustomVisionTrainingClient
from azure.cognitiveservices.vision.customvision.training.models import ImageFileCreateEntry, ImageUrlCreateEntry
from msrest.authentication import ApiKeyCredentials
from azure.storage.blob import BlobServiceClient
import azure.functions as func

import logging
import time
import traceback
import random


class CVTrainConstants:
    ENDPOINT = "https://agrovision-cv.cognitiveservices.azure.com/"
    TRAINING_KEY = "8cf70ac0eaa5404db99678e72a7bd10f"
    PROJECT_ID = "6188441f-05c6-46c4-9dc6-af58aca565ef"  #Initial with train data
    #PROJECT_ID = "b694eef7-5b8d-4eea-8754-7e304ec86c47"  # NEw deV
    MAX_ITERATIONS = 8
    CUR_ITERATION = "Current_Iteration"
    PREDICTION_RES_ID = "/subscriptions/17c0a2b0-6cad-4c1d-b2a8-328a38f600e2/resourceGroups/agrovision-ml/providers/Microsoft.CognitiveServices/accounts/agrovisioncv-Prediction"
    PREDICTION_ITERATION_NAME = "Prediction_Iteration"

class BlobStorage:
    CONNECT_STR = "DefaultEndpointsProtocol=https;AccountName=agrovisionstore;AccountKey=+1kPv6QocFWNO6Aj468YwbAnzQrMraHW/7pDHr8ShbN6O+gNyNFumMV5rmv6r6roYCscqHcN4CyHlKzDzofTDw==;EndpointSuffix=core.windows.net"
    TRAIN_CONTAINER = "rgb-train"
    TEST_CONTAINER = "iot-runs"
    DEV_CONTAINER = "rgb-dev"

def copy_blob_from_url(source_blob_url, new_blob_name, split_name):
    # Instantiate a BlobServiceClient using a connection string
    blob_service_client = BlobServiceClient.from_connection_string(BlobStorage.CONNECT_STR)
    container_name = BlobStorage.TRAIN_CONTAINER if split_name == "train" else BlobStorage.DEV_CONTAINER
    if split_name == "train":
        dest_image_url = blob_service_client.get_container_client(container_name).primary_endpoint
    else:
        dest_image_url = blob_service_client.get_container_client(container_name).primary_endpoint

    try:
        # [START copy_blob_from_url]
        # Get the blob client with the source blob
        copied_blob = blob_service_client.get_blob_client(container_name, new_blob_name)
        # start copy and check copy status
        copy = copied_blob.start_copy_from_url(source_blob_url)
        props = copied_blob.get_blob_properties()
        return dest_image_url + "/" + props.name
    except Exception as e:
        logging.error("Error in Copying from Source URL to New Container" + str(e))


#Add train or dev images 
def add_train_dev_images(farmid, runid, gridlablel_list, tag_dict):
    SEP = '/'
    run_images_path = str(farmid) + SEP + str(runid) + SEP + "rgb" #Change this if required
    train_image_list = []
    try:
        blob_service_client = BlobServiceClient.from_connection_string(BlobStorage.CONNECT_STR)
        container_client = blob_service_client.get_container_client(BlobStorage.TEST_CONTAINER)

        for feedback_grid in gridlablel_list:
            grid_id = feedback_grid["grid_id"]
            rel_image_path = run_images_path + SEP + grid_id + ".png"
            source_blob_url = container_client.primary_endpoint + "/" + rel_image_path  #Get Test Image URL
            dest_image_name = str(farmid) + SEP + str(grid_id) + "-" + feedback_grid["label"] + ".png"  #Set Name for Dest Image
            dest_image_url = copy_blob_from_url(source_blob_url, dest_image_name, feedback_grid["split"])  #Upload to Train Container with new name

            if feedback_grid["split"] == "train":
                image_tag_id = tag_dict[feedback_grid["label"]]
                train_image_list.append(ImageUrlCreateEntry(url=dest_image_url, tag_ids=[image_tag_id]))

        return train_image_list

    except Exception as e:
        logging.error("Error in add_train_dev_images" + str(e))


#Check if number of iterations < MAX_ITERATIONS:
def _check_max_iterations(trainer):
    iterations = trainer.get_iterations(CVTrainConstants.PROJECT_ID)
    if len(iterations) >= CVTrainConstants.MAX_ITERATIONS:
        logging.info("Number of iterations excedded MAX_ITERATIONS")
        logging.info("Deleted Iteration : " + iterations[-1].name)  #Delete last iteration by last train time
        trainer.delete_iteration(CVTrainConstants.PROJECT_ID, iterations[-1].id)


#Train with the new data
def _cv_train(trainer):
    logging.info("Initializing Training")

    #Check max iteration reached for training
    _check_max_iterations(trainer)

    try:
        #Train New Iteration
        dev_iteration = trainer.train_project(CVTrainConstants.PROJECT_ID, training_type="Simple", force_train=True)
        dev_iteration = trainer.update_iteration(CVTrainConstants.PROJECT_ID, dev_iteration.id, "Dev_Iteration")
        while (dev_iteration.status != "Completed"):
            dev_iteration = trainer.get_iteration(CVTrainConstants.PROJECT_ID, dev_iteration.id)
            logging.info("Training status: " + dev_iteration.status)
            time.sleep(10)

        return dev_iteration
    
    except Exception as e:
        logging.error("Error while training: " + str(e))


#Get Predictions for different iterations
def _get_predictions(trainer, iteration_id):
    acc = 0
    try:
        blob_service_client = BlobServiceClient.from_connection_string(BlobStorage.CONNECT_STR)
        container_client = blob_service_client.get_container_client(BlobStorage.DEV_CONTAINER)

        blob_list = container_client.list_blobs()
        for blob in blob_list:
            blob_url = container_client.primary_endpoint + "/" + blob.name
            blob_label = blob.name.split('-')[-1].split('.')[0]

            blob_result = trainer.quick_test_image_url(CVTrainConstants.PROJECT_ID, blob_url, iteration_id)
            blob_pred_class = max(blob_result.predictions, key=lambda x: x.probability)

            if blob_pred_class.tag_name == blob_label:
                acc += 1

        logging.info("Prediction Results for all Image: Success")
        return acc

    except Exception as e:
        logging.error(e)


#Get the best iteration
def best_iteration(trainer):
    dev_iteration = _cv_train(trainer)
    current_iteration = 0
    try:
        for iteration in trainer.get_iterations(CVTrainConstants.PROJECT_ID):
            if iteration.name == CVTrainConstants.CUR_ITERATION:
                current_iteration = iteration

        current_acc = _get_predictions(trainer, current_iteration.id)
        logging.info("Current Correct Images: " + current_acc)
        dev_acc = _get_predictions(trainer, dev_iteration.id)
        logging.info("New Iteration Correct Images: " + dev_acc)

        if dev_acc > current_acc:
            trainer.publish_iteration(CVTrainConstants.PROJECT_ID, dev_iteration.id, CVTrainConstants.PREDICTION_ITERATION_NAME, \
                                    CVTrainConstants.PREDICTION_RES_ID)

            trainer.delete_iteration(CVTrainConstants.PROJECT_ID, current_iteration.id)
            trainer.update_iteration(CVTrainConstants.PROJECT_ID, dev_iteration.id, CVTrainConstants.CUR_ITERATION)
            logging.info("Updated and Published New Model")
        else:
            trainer.delete_iteration(CVTrainConstants.PROJECT_ID, dev_iteration.id)
            logging.info("New Iteration Deleted")
    
    except Exception as e:
        logging.error("Error in getting best iteration: " + str(e))


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        data = req.get_json()
        farmid, runid = data['farmid'], data['runid']
        feedback_list = data['feedback']

        #Decide on the correct split
        for feedback in feedback_list:
            feedback["split"] = "train" if random.random() < 0.5 else "dev"

        #Get Project ID and CustomVision Trainer
        logging.info("Get Project with Project ID : " + CVTrainConstants.PROJECT_ID)
        credentials = ApiKeyCredentials(in_headers={"Training-key": CVTrainConstants.TRAINING_KEY})
        trainer = CustomVisionTrainingClient(CVTrainConstants.ENDPOINT, credentials)

        #Get list of tags in the current project
        tag_dict = {}
        for tag in trainer.get_tags(CVTrainConstants.PROJECT_ID):  ##Can modify dictionary later
            tag_dict[tag.name] = tag.id

        train_image_list = add_train_dev_images(farmid, runid, feedback_list, tag_dict)
        #train_image_list = add_train_dev_images("1", "2", [{"grid_id": "3", "label": "Charlock", "split": "dev"}, \
                                                        #{"grid_id": "7", "label": "Fat Hen", "split": "train"}], tag_dict)

        #Upload to Custom Vision with new tags from train
        if len(train_image_list) != 0: # IF not empty
            upload_result = trainer.create_images_from_urls(CVTrainConstants.PROJECT_ID, images=train_image_list)
            if not upload_result.is_batch_successful:
                logging.error("Image batch upload failed.")
            else:
                logging.info("Image batch upload Success")

        best_iteration(trainer)

    except Exception as e:
        logging.error("Exception while trying to get data from HTTP Request: " + str(e))
        return func.HttpResponse(f"Failure !")

    return func.HttpResponse(f"Trained Sucessfully")



'''
Steps
1. Get all images from test to train (1-2-3.png ) Done
2. Add these images to Train  Done
3. Train new dev_iteration with this new images Done
4. Select between dev_iteration and current iteration Done
5. Random Sample to add between dev and train images.
'''


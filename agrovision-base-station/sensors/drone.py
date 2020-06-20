import threading
import time
import logging
import random
import numpy as np
import cv2
import warnings
warnings.filterwarnings("ignore")

from farm import farm
from .sensor_base import SensorBaseClass
from messages import ControlMessage
from relative_path import get_resource_path

logger = logging.getLogger(__name__ )

class Drone(SensorBaseClass):
    """
    The drone object virtually represents a real life instance of a drone
    """
    INTERVAL_SEC = 2
    TYPE = 'drone'

    def __init__(self, id, telemetry, control):
        self.id = id
        self.telemetry = telemetry
        self.control = control

        self.thread = threading.Thread(target=self._init)
        self.thread.daemon = True
        self.thread.start()

    def _init(self):
        """
        1) Request for path
        """
        self.grid = farm.grid
        self._compute_path()
        logger.info("Drone ready.")

        self._fly_lock = threading.Lock()
        self._fly_now = False
        self._wait_for_trigger()

    def _wait_for_trigger(self):
        """
        Check if flight command is issued
        """
        while True:
            time.sleep(Drone.INTERVAL_SEC)

            # check if flight is issued
            self._fly_lock.acquire()
            if self._fly_now:
                self._fly()
                self._fly_now = False
            self._fly_lock.release()

    def _compute_path(self):
        self._path = self.grid

    def handle_message(self, data):
        """
        Recieved a remote invocation. Update farm run_id and initiate flight.
        """
        farm.last_run = farm.last_run + 1

        self._fly_lock.acquire()
        self._fly_now = True
        self._fly_lock.release()

    def _fly(self):
        """
        Hookup to airsim (if possible) else fallback to console
        After flight upload images to cosmos.
        """
        logger.info(f"Starting flight.. Run #{farm.last_run}")
        self._prepare()
        self._picture_buf = []
        # TODO call airsim stuff / fallback on console

        for coord in self._path:
            # simulate flight
            time.sleep(0.5)
            while True:
                try:
                    logger.info(f"At X={coord['X']}, Y={coord['Y']}, clicking picture..")
                    self._click_picture(coord['id'])
                    break
                except:
                    # something bad happened, try again
                    continue

        # end flight
        logger.info("Finished flight.. Uploading images..")
        self._upload()
        logger.info("Run finished")

    def _prepare(self):
        # for the sake of this hackathon, we ensure that at least 2 - 4 of the pictures uploaded are weed
        # infested
        num_weed = random.choice([3,4,5])
        num_cells = len(self._path)

        weed_ids = random.sample(range(101, 111), num_weed)
        plant_ids = random.sample(range(1,101), num_cells - num_weed) 
        buffer = random.sample(range(1,101), 50)  # in case things go wrong 

        self._picture_to_choose = plant_ids + weed_ids
        random.shuffle(self._picture_to_choose)
        self._picture_to_choose = buffer + self._picture_to_choose


    def _click_picture(self, grid_id):
        image_id = self._picture_to_choose.pop()

        # pick the correct image from our local store
        image_path = get_resource_path('storage/' + str(image_id) + '.png')
        # generate NDVI values
        ir_path, ndvi_path = self._read_ndvi(image_id)

        self._picture_buf.append({
            'name': str(grid_id),
            'image_rgb': image_path,
            'image_ir': ir_path, 
            'ndvi': ndvi_path
        })

    def _upload(self):
        # upload all data pictures
        i = 0
        for picture in self._picture_buf:
            logger.info(f"Uploading {i}/{len(self._path)}")
            try:
                # upload rgb image
                fpath = picture['image_rgb']
                blob_name = str(farm.last_run) + '/rgb/' + str(picture['name']) + '.png'
                self.telemetry({}, blob=True, blob_name=blob_name, fpath=fpath)

                # upload ir image
                fpath = picture['image_ir']
                blob_name = str(farm.last_run) + '/ir/' + str(picture['name']) + '.png'
                self.telemetry({}, blob=True, blob_name=blob_name, fpath=fpath)

                # upload ndvi matrix
                fpath = picture['ndvi']
                blob_name = str(farm.last_run) + '/ndvi/' + str(picture['name']) + '.npy'
                self.telemetry({}, blob=True, blob_name=blob_name, fpath=fpath)
            except:
                # something 
                continue

            i += 1

        # notify run completion
        notification = ControlMessage("RUN_FINISHED", {"runId": farm.last_run})
        self.control(notification)

    def _read_ndvi(self, image_id):
        # for the sake of this hackathon, we try to ensure that some percentage of the plants are
        # unhealthy
        choice = random.choice(range(10))
        image_path = get_resource_path("storage/" + str(image_id) + '.png')

        if choice <= 7:
            image, matrix = self._healthy(image_path)
        else:
            image, matrix = self._unhealthy(image_path)

        ir_path = get_resource_path('stage/' + str(image_id) + '.png')
        ndvi_path = get_resource_path('stage/' + str(image_id))
        cv2.imwrite(ir_path, image)
        np.save(ndvi_path, matrix, allow_pickle=True)
        return ir_path, ndvi_path + '.npy'

    def _healthy(self, path):
        image = cv2.imread(path)
        l = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        l[:,:,0] = np.where(l[:,:,1] > 121, l[:,:,0]*0.7, l[:,:,0])
        l[:,:,1] = np.where(l[:,:,1] > 121, 0, l[:,:,1]*1.25)
        arr = np.asarray(l)*-1*-1
        a = (arr[:,:,1] - arr[:,:,0])/(arr[:,:,1] + arr[:,:,0])
        a[np.isnan(a)] = -1
        return l, a

    def _unhealthy(self, path):
        image = cv2.imread(path)
        l = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        l[:,:,0] = np.where(l[:,:,1] > 121, l[:,:,0]*0.7, l[:,:,0]*1.3)
        l[:,:,1] = np.where(l[:,:,1] > 121, 0, l[:,:,1])
        arr = np.asarray(l)*-1*-1
        a = (arr[:,:,1] - arr[:,:,0])/(arr[:,:,1] + arr[:,:,0])
        a[np.isnan(a)] = -1
        return l, a

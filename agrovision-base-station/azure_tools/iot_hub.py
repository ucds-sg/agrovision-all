import threading
import logging
import json
import time
from azure.iot.device import IoTHubDeviceClient
from azure.storage.blob import BlobClient

from config import IoTEdge
from messages import ResponseMessage, RemoteInvocationMessage

logger = logging.getLogger(__name__)

class IoTHubWrapper():
    def __init__(self):
        self.client = IoTHubDeviceClient.create_from_connection_string(IoTEdge.BASE_STATION_CONNECTION_STRING)

    def listen_indefinitely(self, handler):
        # listen function runs its own thread until connection is torn down
        logger.info("Establishing incoming link from cloud..")
        self._thread = threading.Thread(target=self._listen_indefinitely, args=(handler,))
        self._thread.daemon = True
        self._thread.start()

        return self._thread

    def _listen_indefinitely(self, handler):
        # a special sequence of messages is followed while booting up
        _booting = True
        _queue = []
        while True:
            message = self.client.receive_message()

            message_type = message.custom_properties['TYPE']
            message_event = message.custom_properties['EVENT']
            logger.debug('Received {}'.format(message_type))

            if message_type == "REMOTE_INVOCATION":
                message_obj = RemoteInvocationMessage(message_event, message.data)

            elif message_type == "RESPONSE":
                # received a response for some request that was sent
                message_obj = ResponseMessage(message_event, message.data)
                self._response_recv_msg = message_obj

                # notify blocked thread
                self._response_recv_lock.acquire()
                self._response_recv_flag = True
                self._response_recv_lock.release()

                # premature return.. request_from_hub() will deal with returning data
                _booting = False

                # process any buffered messages
                for msg in _queue:
                    time.sleep(1) # in case other stuff is still initializing
                    handler(msg)

                continue

            if _booting:
                # ignore any pending messages if booting
                _queue.append(message_obj)
                continue

            handler(message_obj)

    def request_from_hub(self, request_message):
        """
        Data needs to be of the messages.RequestMessage type
        This is interpreted by an azure function
        NOTE since this is not a synchronus request/response scheme, we have to force such
        a behaviour
        """
        logger.info("Requesting data from hub.. This may take a while..")

        # locks and flags to wait for response
        self._response_recv_flag = False
        self._response_recv_lock = threading.Lock()
        self._response_recv_msg = None

        message = request_message.payload
        self.client.send_message(message)

        # now we wait
        while True:
            time.sleep(0.5)
            self._response_recv_lock.acquire()
            if self._response_recv_flag:
                self._response_recv_lock.release()
                break
            self._response_recv_lock.release()

        # response received.. return to caller
        return self._response_recv_msg

    def send_telemetry(self, telemetry_message):
        """
        Data needs to be of the messages.TelemetryMessage type
        """
        logger.info(telemetry_message.device_type + " transmitting telemetry..")
        message = telemetry_message.payload

        self.client.send_message(message)

    def send_control(self, control_message):
        """
        Send control messages to the cloud
        """
        logger.info("Sending control message " + control_message.event)
        message = control_message.payload

        self.client.send_message(message)

    def upload_blob(self, blob_name, fpath):
        """
        TODO too numb to think
        """
        blob_info = self.client.get_storage_info_for_blob(blob_name)

        sas_url = "https://{}/{}/{}{}".format(
            blob_info["hostName"],
            blob_info["containerName"],
            blob_info["blobName"],
            blob_info["sasToken"]
        )
        correlation_id = blob_info["correlationId"]

        with BlobClient.from_blob_url(sas_url) as blob_client:
            with open(fpath, "rb") as f:
                blob_client.upload_blob(f, overwrite=True)
                self.client.notify_blob_upload_status(correlation_id, True, 200, "success")


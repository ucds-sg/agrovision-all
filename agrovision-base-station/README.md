# AgroVision BaseStation
A portable application package designed to seamlessly integrate sensors and actuators on your farm. As an Azure IoT component, the BaseStation can be controlled remotely from our app and sends a steady stream of sensor telemetry data to our Cloud based data-stores (Azure CosmosDB and Azure Blobstore). Most importantly, it provides a reliable visual feed for our prediction models.

## How To Run
Our quick start guide contains a link to the binary package (compiled for Windows and Mac). Double clicking on the binary should work.

Feel free to build from source!

## Running from source code
The repo is organized as a standard python application. 

Since sensor data is simulated, the repo itself does not ship with stock images that are uploaded to the cloud for demonstration. Download the zip from the [here](https://drive.google.com/file/d/14Do-sgQknIOVlc8GGUme_xNG4OSdMweD/view?usp=sharing) and place the pictures inside into the `storage/` folder. Note that the pictures are in fact packaged into the binary during compilation.

Create a virtual environment and install dependencies from `requirements.txt`. 
```sh
$ cd <project-root>
$ python3 -m venv ./venv
$ source venv/bin/active
# On windows
> venv\Scripts\activate
$ python base-station.py
```

The connection strings are configured in config.py and will vary from deployment to deployment. By default, it is configued for the dummy user account.

## Compiling a binary
We use `pyinstaller` to compile it into an EXE or macOS binary. From the activated virtualenv, run
```sh
$ pyinstaller -F --onefile --add-data 'storage/:storage' --add-data 'stage/:stage' base-station.py
# On windows
> pyinstaller -F --onefile --add-data 'storage;storage' --add-data 'stage;stage' base-station.py
```

## About the code
The Base Station is our edge device that establishes a long-lived connection to the IoT Hub.
It is responsible for triggering drone flights, managing sensors and uploading telemetry and
image data.

```
[ Base-Station ]  <----> [ IoT Hub ] <----> [ ML Component ]
                              ^
                              |
                           [ UI ]
```

Each sensor or actuator runs its own thread and can send telemetry at will. A complex dispatch mechanism delivers both device-to-cloud and cloud-to-device messages to the right destinations.

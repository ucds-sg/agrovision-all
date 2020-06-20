class IoTHub:
    CONNECTION_STRING = "HostName=agrovision-iot-hub.azure-devices.net;SharedAccessKeyName=service;SharedAccessKey=ITeD77TL9bGmBCB5bJfxzdeyWJfOz9YjuC8nQkPwMRM="

class Cosmos:
    URL = "https://agrovision-cosmos.documents.azure.com:443/"
    KEY = "GnF5yD8RVjA0e9U1p62BAF4qS8rDmlMoxgMPqtsqgtIuiU589RWyUWCkFxBfnKnsjbhEYbxrvkyOYoDyslq5yw=="
    DATABASE = "agrovision-db"
    FARMS_CONTAINER = "farms"

class AgroML:
    PREDICTION_URL = "https://agrovision-ml.azurewebsites.net/api/azure-ml-prediction?code=ULC1FqXHaEA4ZVjaFk00FVxdOPqTX7aqJl3BWMNf7y00G1R4NAMxUQ=="
    PREDICTION_NDVI_URL = "https://agrovision-ndviml.azurewebsites.net/api/agrovision-ndvi-prediction?code=b0BV8Sau2Umc9ktccoY7MmDk05bRqmCMaOCGIhj02g4kgZu1Sv5Btg=="

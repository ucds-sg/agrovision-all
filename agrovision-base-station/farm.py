class Farm():
    """
    Holds all farm level data required by other modules.
    This is downloaded from the hub on initialization.
    Intended to be read-only after initialization.
    """

    def __init__(self):
        self.id = ""
        self.name = ""
        self.city = ""
        self.vertex_lat = 0
        self.vertex_lng = 0
        self.sensors = []
        self.grid = []
        self.last_run = 0

    def initialize(self, data):
        self.id = data['id']
        self.name = data['name']
        self.vertex_lat = data['vertex_lat']
        self.vertex_lng = data['vertex_lng']
        self.sensors = data['sensors']
        self.grid = data['grid']
        self.last_run = data['last_run']

farm = Farm()

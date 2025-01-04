import math

class BusStation:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class Bus:
    def __init__(self, bus_id, route, start_station_index, direction=1, speed=5, stop_time=10):
        """
        Initializes a bus with specified attributes.
        - bus_id: Unique identifier for the bus
        - route: List of stations along the bus route
        - start_station_index: Index of the starting station
        - direction: Travel direction (1 for forward, -1 for reverse)
        - speed: Distance moved per unit time
        - stop_time: Time to wait at each station
        """
        self.bus_id = bus_id
        self.route = route
        self.station_index = start_station_index
        self.direction = direction
        
        # Initialize position using x and y attributes
        self.x = self.route[self.station_index]['x']
        self.y = self.route[self.station_index]['y']
        
        self.speed = speed  # Distance moved per unit time
        self.time_at_station = 0  # Time spent at station
        self.stop_time = stop_time  # Time to stop at each station
        self.status = 'moving'  # Bus status (moving, at_station, etc.)




    def move(self):
        """Defines the movement logic of the bus."""
        if self.status == 'at_station':
            # Bus is waiting at the station
            self.time_at_station += 1
            if self.time_at_station >= self.stop_time:
                # Time to leave the station
                self.status = 'moving'
                self.time_at_station = 0
        else:  # status is 'moving'
            # Bus is moving towards the next station
            next_station_index = self.station_index + self.direction
            if 0 <= next_station_index < len(self.route):
                next_station = self.route[next_station_index]
                # Calculate the Euclidean distance to the next station
                distance_to_next_station = math.sqrt(
                    (self.x - next_station['x']) ** 2 + (self.y - next_station['y']) ** 2
                )

                # Check if bus has reached the next station
                if distance_to_next_station <= self.speed:
                    self.x = next_station['x']
                    self.y = next_station['y']
                    self.station_index += self.direction
                    self.status = 'at_station'
                    # Reverse direction if at route endpoints
                    if self.station_index == 0 or self.station_index == len(self.route) - 1:
                        self.direction *= -1
                else:
                    # Move towards the target proportionally to avoid overshooting
                    move_ratio = self.speed / distance_to_next_station
                    self.x += move_ratio * (next_station['x'] - self.x)
                    self.y += move_ratio * (next_station['y'] - self.y)


class BusSystem:
    def __init__(self, travel_time=30, time_per_station=10):
        self.travel_time = travel_time  # Base time for each transport
        self.time_per_station = time_per_station  # Additional time for each bus station passed
        self.tasks_transported = 0  # Tracks the number of bus transports
        self.buses = []  # List of buses
        self.bus_id_counter = 0  # Used to assign a unique ID to each bus
        self.time = 0  # Global system time

    def initialize_buses(self, bus_lines, bus_stations_df):
        """Initialize buses for each line, adding new buses each time it's called"""
        for line in bus_lines:
            route_stations = [station for station in bus_stations_df.to_dict('records') if station['line'] == line]
            # Add new buses for this line
            self.buses.append(Bus(self.bus_id_counter, route_stations, 0, direction=1))
            self.bus_id_counter += 1
            self.buses.append(Bus(self.bus_id_counter, route_stations, len(route_stations) - 1, direction=-1))
            self.bus_id_counter += 1

    def update_buses(self):
        """Update the position of all buses"""
        for bus in self.buses:
            bus.move()
            # print(f"Bus {bus.bus_id} at ({bus.x}, {bus.y}), Status: {bus.status}, Direction: {bus.direction}")

    def simulate(self, bus_lines, bus_stations_df):
        """Dispatch a bus every 50 time units and update the positions of all buses"""
        # Add new buses every 50 time units
        if self.time % 50 == 0:
            # print(f"Starting new buses on all lines at time {self.time}.")
            self.initialize_buses(bus_lines, bus_stations_df)

        # Update the positions of all buses
        self.update_buses()
        self.time += 1  # Increment time step

    def check_buses_at_station_for_pickup(self, x, y, tolerance=0.1):
        """Check if there is a bus at a station for pickup (allows a certain tolerance to avoid floating-point errors).
        This function does not require a bus ID.
        """
        for bus in self.buses:
            # Check if the bus is at the specified location (using tolerance)
            if math.isclose(bus.x, x, abs_tol=tolerance) and math.isclose(bus.y, y, abs_tol=tolerance):
                # print(f"Bus {bus.bus_id} found at station ({x}, {y}), Status: {bus.status}")
                return bus
        # print(f"No bus found at station ({x}, {y}) for pickup.")
        return None

    def check_buses_at_station_for_delivery(self, x, y, bus_id, tolerance=0.1):
        """Check if a specified bus (by ID) is at a station for delivery (allows a certain tolerance to avoid floating-point errors).
        This function requires a bus ID.
        """
        for bus in self.buses:
            # Check if the bus location and ID match
            if (math.isclose(bus.x, x, abs_tol=tolerance) and 
                math.isclose(bus.y, y, abs_tol=tolerance) and 
                bus.bus_id == bus_id):
                # print(f"Bus {bus.bus_id} found at station ({x}, {y}) for delivery.")
                return bus
        # print(f"No matching bus found at station ({x}, {y}) for delivery with bus_id: {bus_id}")
        return None
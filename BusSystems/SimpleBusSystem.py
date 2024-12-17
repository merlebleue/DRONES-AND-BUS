import math
from Area import Area
import pandas as pd

class BusStation:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class SimpleBus:
    def __init__(self, bus_id, line, route_df, start_station_index, callback_at_station, direction=1, speed_factor=1):
        """
        Initializes a bus with specified attributes.
        - bus_id: Unique identifier for the bus
        - line : Line name
        - route: Df of the line data along the bus route
        - start_station_index: Index of the starting station
        - callback_at_station: A function that is called whenever a bus reach a station.
        - direction: Travel direction (1 for forward, -1 for reverse)
        - speed_factor: Seconds moved per time unit/time step
        """
        self.bus_id = bus_id
        self.line = line
        self.route = route_df
        self.station_index = start_station_index
        self.direction = direction
        
        # Initialize position using x and y attributes
        self.x = self.route.loc[self.station_index, 'POSITION_X']
        self.y = self.route.loc[self.station_index, 'POSITION_Y']
        
        self.speed_factor = speed_factor # number of seconds for a time step
        self.time_steps_at_station = 0  # Time spent at station
        self.time_steps_travelling = 0  # Time spent moving from one station to the other
        self.status = 'moving'  # Bus status (moving, at_station, etc.)

        self.callback_at_station = callback_at_station

    def at_station(self, seconds_left):
        self.time_steps_at_station += seconds_left
        if self.time_steps_at_station >= self.route.loc[self.station_index, 'STOP_TIME']:
            # Time to leave the station
            self.status = 'moving'
            self.time_steps_at_station = 0
            return self.time_steps_at_station - self.route.loc[self.station_index, 'STOP_TIME']
        else :
            # No more seconds left, still at station
            return 0
        
    def moving(self, seconds_left):
        # Bus is moving towards the next station
        next_station_index = self.station_index + self.direction

        if 0 <= next_station_index < len(self.route):
            # Get the next station info
            next_station = self.route.loc[next_station_index]
            # Compute the time left to travel
            time_until_next_station = next_station[f"TIME_{'A' if self.direction > 0 else 'R'}"] - self.time_steps_travelling

            # Check if bus has reached the next station
            if time_until_next_station <= seconds_left:
                # If it has reached it
                self.x = next_station['POSITION_X']
                self.y = next_station['POSITION_Y']
                self.station_index += self.direction
                self.status = 'at_station'

                # Call the callback
                self.callback_at_station(next_station)

                # Reverse direction if at route endpoints
                if self.station_index == 0 or self.station_index == len(self.route) - 1:
                    self.direction *= -1

                return seconds_left - time_until_next_station
            else:
                # Move towards the target proportionally to avoid overshooting
                move_ratio = seconds_left / next_station[f"TIME_{'A' if self.direction > 0 else 'R'}"]
                self.x += move_ratio * (next_station['POSITION_X'] - self.x)
                self.y += move_ratio * (next_station['POSITION_Y'] - self.y)
                
                return 0

    def move(self, time_steps = 1):
        """Defines the movement logic of the bus"""

        seconds_left = self.speed_factor * time_steps
        while seconds_left > 0:
            if self.status == 'at_station':
                seconds_left = self.at_station(seconds_left)
            else:
                # Bus is moving towards the next station
                seconds_left = self.moving(seconds_left)

    def get_status(self):
        return {
            "Bus_id": self.bus_id, 
            "x": self.x, 
            "y": self.y, 
            "Line": self.line, 
            "Direction": self.direction, 
            "Status": self.status, 
            "Last station": self.route.loc[self.station_index].STOP_NAME, 
            "Next station": self.route.loc[self.station_index+self.direction].STOP_NAME
        }


class SimpleBusSystem:
    def __init__(self, area: Area, lines: list, frequency: int, callback_at_station, speed_factor:int = 1, time_type = "real"):
        """
        Create a bus system based on the data for the given area object, with lines in the list `lines`
        
        Args :
            - area: Area -> An Area object corresponding to the area the bus was moved from
            - lines:list[line_names] -> a list of the lines to add to the system
            - frequency: int -> The frequency (i.e. number of time steps) at which the system creates new busses
            - callback_at_station: fct -> A function that is called whenever a bus reach a station. Call is `callback_at_station(station_row)`
            - speed_factor: int = 1 -> Number of seconds per time step
            - time_type:str = 'real' -> The file to open (either 'real' or 'planned'). 'real' is recommanded
        """
        # Data for the lines
        def get_line_data(line_name: str):
            path = area.path_join("TP_Simple", f"{line_name}_{time_type}.csv")
            return pd.read_csv(path, sep = "[ \t]*;[ \t]*")
        self.lines_data = {line_name : get_line_data(line_name) for line_name in lines}

        self.frequency = frequency # Frequency at which to add busses
        self.speed_factor = speed_factor # Number of seconds per time step

        self.callback_at_station = callback_at_station

        self.tasks_transported = 0  # Tracks the number of bus transports
        self.buses = [] # List of buses
        self.bus_id_counter = 0  # Used to assign a unique ID to each bus
        self.time_steps = 0  # Global system time

    def initialize_buses(self):
        """Initialize buses for each line, adding new buses each time it's called"""
        for line, line_data in self.lines_data.items():
            # Add new buses for this line at each terminus
            self.buses.append(SimpleBus(self.bus_id_counter, line, line_data, 0, callback_at_station=self.callback_at_station, direction=1, speed_factor=self.speed_factor))
            self.bus_id_counter += 1
            self.buses.append(SimpleBus(self.bus_id_counter, line, line_data, len(line_data) - 1,  callback_at_station=self.callback_at_station,direction=-1, speed_factor=self.speed_factor))
            self.bus_id_counter += 1

    def update_buses(self, time_steps = 1):
        """Update the position of all buses"""
        for bus in self.buses:
            bus.move(time_steps)
            # print(f"Bus {bus.bus_id} at ({bus.x}, {bus.y}), Status: {bus.status}, Direction: {bus.direction}")

    def simulate(self, time_steps = 1):
        """Dispatch a bus every {frequency} time steps and update the positions of all buses"""
        # Add new buses every {frequency} time steps
        if self.time_steps % self.frequency == 0:
            # print(f"Starting new buses on all lines at time {self.time_steps}.")
            self.initialize_buses()

        # Update the positions of all buses
        self.update_buses(time_steps)
        self.time_steps += time_steps  # Increment time step

    def get_bus_status(self):
        df = pd.DataFrame(columns=["Bus_id", "x", "y", "Line", "Direction", "Status", "Last station", "Next station"])
        for bus in self.buses:
            df.loc[len(df)] = bus.get_status()
        return df

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
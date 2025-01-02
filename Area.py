import os
import folium
from pyproj import CRS
from pyproj import Transformer

import matplotlib as mpl

DATA_FOLDER = "data"

class Area:
    def __init__(self, name: str, x_min:int, x_max:int, y_min:int, y_max:int, data_folder:str = DATA_FOLDER):
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        self.center = (x_max + x_min)/2 , (y_max + y_min)/2
        self.crs = CRS.from_epsg(2056)
        self.to_lat_lon = Transformer.from_crs(self.crs, 4326, always_xy=True).transform

        self.name = name
        self.path = os.path.join(data_folder, name)
        os.makedirs(self.path, exist_ok=True)

        with open(self.path_join(name+"_data.txt"), "w") as f:
            f.write(name + "\n")
            f.write("Coordinates : " + ";".join([str(i) for i in (x_min, x_max, y_min, y_max)]) + "\n")
            
    def path_join (self, *args):
        return os.path.join(self.path, *args)

    def relative(self, X=None, Y=None):
        if X is None:
            return Y - self.y_min
        if Y is None:
            return X - self.x_min
        return X - self.x_min, Y - self.y_min

    def is_inside(self, X, Y):
        return (X > self.x_min) & (X < self.x_max) & (Y > self.y_min) & (Y < self.y_max)
    
    def is_inside_hecto(self, X, Y):
        return (X + 99 > self.x_min) & (X < self.x_max) & (Y + 99 > self.y_min) & (Y < self.y_max)
    
    def plot_interactive(self, bus_data = {}):
        min_lat, min_lon = self.to_lat_lon(self.x_min, self.y_min)[::-1]
        max_lat, max_lon = self.to_lat_lon(self.x_max, self.y_max)[::-1]

        m = folium.Map(location=self.to_lat_lon(*self.center)[::-1],
                       tiles="cartodb positron",
                       zoom_start=14,
                       min_lat = min_lat,
                       min_lon = min_lon,
                       max_lat = max_lat,
                       max_lon = max_lon,
                       max_bounds=True
        )
        
        folium.Rectangle(
            bounds=[(min_lat, min_lon), (max_lat, max_lon)]
        ).add_to(m)

        #cmap = mpl.colormaps["tab10"]
        #for line_name, line_data in bus_data.items():
        #    folium.PolyLine(locations=self.to_lat_lon(line_data[["POSITION_X","POSTION_Y"]]))
        #    folium.CircleMarker(
        #
        #    )
                    
        return m
    
    def save_data():
        pass



    
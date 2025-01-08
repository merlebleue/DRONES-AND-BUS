import os
import folium
from pyproj import CRS
from pyproj import Transformer

import datetime

import smopy
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from .download import DownloadManager

DATA_FOLDER = "data"

class Area:
    def __init__(self, x_min:int, x_max:int, y_min:int, y_max:int, download_manager = DownloadManager()):
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        
        # Conversion utilities
        self.crs = CRS.from_epsg(2056)
        self.to_lat_lon = Transformer.from_crs(self.crs, 4326, always_xy=True).transform
        self.to_lat_lon_bounds = Transformer.from_crs(self.crs, 4326, always_xy=True).transform_bounds
        self.to_MN95 = Transformer.from_crs(4326, self.crs).transform
        self.to_MN95_bounds = Transformer.from_crs(4326, self.crs).transform_bounds

        # Download Manager
        self.dl = download_manager



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
    
    def get_lat_lon_box(self):
         return *self.to_lat_lon(self.x_min, self.y_min)[::-1], *self.to_lat_lon(self.x_max, self.y_max)[::-1]
    
    def plot(self, *elements, background = "cartodb", figsize=(8,8), dpi=200, margin=0, layout="tight", plot_axes = True):
        # Create figure
        fig = plt.figure(figsize=figsize, dpi=dpi, layout = layout)
        ax = fig.subplots()

        # Add the background (using smopy library)
        if background is not None:
            cartodb_url = "https://basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}@2x.png"
            swisstopo_url = "https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.swisstlm3d-karte-grau/default/current/3857/{z}/{x}/{y}.png"

            if background == "cartodb":
                map = smopy.Map(self.get_lat_lon_box(), tileserver=cartodb_url, tilesize=512, margin=margin, verbose=False)
            elif background == "swisstopo":
                map = smopy.Map(self.get_lat_lon_box(), tileserver=swisstopo_url, margin=margin, verbose=False)
            else:
                raise ValueError("`background` argument must be either 'cartodb', 'swisstopo' or None")
            
            # Add map to the plot (keep units in MN95)
            (x_min, y_max), (x_max, y_min) = self.to_MN95(*smopy.num2deg(map.xmin, map.ymin, map.z)), self.to_MN95(*smopy.num2deg(max(map.box_tile[0], map.box_tile[2])+1, max(map.box_tile[1], map.box_tile[3])+1, map.z))
            map.show_mpl(ax=ax, extent=[x_min, x_max, y_min, y_max], zorder= -100)

        # If margin > 0, plot a rectangle with the area in the simulation
        size_x, size_y = self.x_max - self.x_min, self.y_max - self.y_min
        if margin > 0 and plot_axes:
            ax.add_patch(patches.Rectangle((self.x_min, self.y_min), size_x, size_y, linewidth=1, edgecolor='navy', facecolor='none'))

        # For anything in `elements`, call a .plot() method
        for e in elements:
            if type(e) is tuple:
                if type(e[1]) is dict:
                    e[0].plot(ax, **e[1])
                else:
                    e[0].plot(ax, *e[1:])
            else:
                e.plot(ax)

        # Personalise the plot
        ax.set_xlim(self.x_min-margin*size_x, self.x_max+margin*size_x)
        ax.set_ylim(self.y_min-margin*size_y, self.y_max+margin*size_y)
        if plot_axes:
            ax.xaxis.set_major_formatter('{x:,.0f}')
            ax.yaxis.set_major_formatter('{x:,.0f}')
            ax.grid(linestyle = ":",color="grey")
            ax.legend()
        else:
            ax.axis("off")
        ax.set_aspect("equal")


        return fig, ax



    
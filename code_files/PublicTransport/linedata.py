import os
import re

import numpy as np
import pandas as pd

from matplotlib.axes import Axes

from ..area import Area

class LineData:
    def __init__(self, id, name, parent_path, timetable=None, stops=None, routes = None, journeys=None, **kwargs):
        self.line_id = id
        self.line_name = name

        line_ref = re.sub(r'[^\w\d-]','_',id)
        self.path = os.path.join(parent_path, line_ref)        
        os.makedirs(self.path, exist_ok=True)

        if timetable is not None and stops is not None and journeys is not None:
            self.timetable = timetable
            self.stops = stops
            self.routes = routes
            self.journeys = journeys
        else:
            self.timetable, self.stops, self.journeys = self.get_data()

    def path_join (self, *args):
        return os.path.join(self.path, *args)
    
    def save_data (self):
        # Separate between "planned" (to the minute) and "real" (to the sec) data
        mask = self.timetable.index.get_level_values("EVENT").str[-4:] == "REAL"
        planned = self.timetable.loc[~mask]
        real = self.timetable.loc[mask]

        export_df = {
            "planned": planned,
            "real": real,
            "full": self.timetable,
            "stops": self.stops,
            "journeys": self.journeys,
            "routes": self.routes
        }
        
        for name, df in export_df.items():
            # Convert to string (preliminary to justifying the data)
            df_for_export = (df
                .reset_index()
                .convert_dtypes()
                .astype("string")
                .replace({"True": "Yes", "False":""}))
            # Justify the data
            max_len = df_for_export.astype(str).map(len).max()
            max_len = np.maximum(max_len, df_for_export.columns.str.len()) + 2
            (df_for_export
                .fillna(max_len.apply(lambda x: " "*x))
                .apply(lambda x: x.str.rjust(max_len[x.name]), axis=0)
                .to_csv(self.path_join(f"{self.line_name}_{name}.csv"), sep=";", index=False, header = df_for_export.columns.map(lambda x: x.center(max_len[x]))))
            
    def load_data(self):
        # Check files exist:
        assert os.path.isfile(self.path_join(f"{self.line_name}_stops.csv"))
        assert os.path.isfile(self.path_join(f"{self.line_name}_full.csv"))
        assert os.path.isfile(self.path_join(f"{self.line_name}_journeys.csv"))

        # Load the data
        self.stops = pd.read_csv(self.path_join(f"{self.line_name}_stops.csv"), sep="[ \t]*;[ \t]*", engine="python")
        self.routes = pd.read_csv(self.path_join(f"{self.line_name}_routes.csv"), sep="[ \t]*;[ \t]*", engine="python")
        self.timetable = pd.read_csv(self.path_join(f"{self.line_name}_full.csv"), sep="[ \t]*;[ \t]*", engine="python")
        self.journeys = pd.read_csv(self.path_join(f"{self.line_name}_journeys.csv"), sep="[ \t]*;[ \t]*", engine="python")

    def get_nearest_stops(self, x, y):
        x, y = x.reshape((-1, 1)), y.reshape((-1, 1))
        stops_x, stops_y = self.stops[["POSITION_X", "POSITION_Y"]].values.T
        stops_x, stops_y = stops_x.reshape((1, -1)), stops_y.reshape((1, -1))
        i = np.argmin(((x-stops_x)**2 + (y-stops_y)**2)**0.5, axis=1)
        return stops_x[0, i], stops_y[0, i]
    
    def get_min_max_coords(self):
        x_min, y_min = self.stops[['POSITION_X', 'POSITION_Y']].min()
        x_max, y_max = self.stops[['POSITION_X', 'POSITION_Y']].max()
        return x_min, x_max, y_min, y_max
    
    def get_area(self, margin= 500):
        x_min, y_min = self.stops[['POSITION_X', 'POSITION_Y']].min() - margin
        x_max, y_max = self.stops[['POSITION_X', 'POSITION_Y']].max() + margin
        return Area(x_min, x_max, y_min, y_max)

    def plot(self, ax: Axes = None, *args, routes = "all", **kwargs):
        if ax is None:
            fig, ax = self.get_area().plot()
            ax.set_title(f"Map for line {self.line_name}")

        if routes == "all":
            routes = self.stops.columns[self.stops.columns.str[:5] == "Route"]
        
        total_count = sum(self.routes["Count"][route] for route in routes)

        label = kwargs.pop("label", self.line_name)
        alpha = kwargs.pop("alpha", 1)
        kwargs["linewidth"] = kwargs.get("linewidth", 1)
        kwargs["markersize"] = kwargs.get("markersize", 3)
        kwargs["marker"] = kwargs.get("marker", "o")
        for route in routes:
            this_alpha = alpha * self.routes["Count"][route] / total_count
            lines2d = ax.plot("POSITION_X", "POSITION_Y", data=self.stops[self.stops[route]], *args, label=label, alpha=this_alpha, **kwargs)
            kwargs["c"] = lines2d[0].get_c()
            label="_"

class LinesData(dict):
    def __init__(self, *lines: LineData):
        self.name_to_id = {}
        self.key_to_id = {}
        super().__init__()

        for line in lines:
            self.add_line(line)
        
    def add_line(self, line: LineData):
        id = line.line_id
        name = str(line.line_name)
        if name in self.name_to_id:
            if type(self.name_to_id[name]) is set:
                self.name_to_id[name].append(id)
            elif type(self.name_to_id[name]) is str:
                if id != self.name_to_id[name] :
                    self.name_to_id[name] = {self.name_to_id[name], id}
        else:
            self.name_to_id[name] = id

        return super().__setitem__(id, line)

    def __setitem__(self, key: str, line: LineData):
        assert type(line) is LineData
        id = line.line_id
        self.key_to_id[key] = id

        return self.add_line(line)
    
    def __getitem__(self, key):
        key = str(key)
        #Try if key has previously been provided as key by setitem
        if key in self.key_to_id:
            id = self.key_to_id[key]
        # Try if key is a line id :
        elif key in self:
            id = key
        # Try if key is a line name
        elif key in self.name_to_id:
            id = self.name_to_id[key]
            if type(id) is set:
                # Multiple lines with the same name
                print("Warning ! Multiple lines with this name. Returning a LinesData object")
                lines = LinesData()
                for line_id in id:
                    lines.add_line(super().__getitem__(line_id))
                return lines
        else :
            e = KeyError(key)
            e.add_note(f"Key {key} has not been found in the lines of this object. Valid values:")
            e.add_note(f"Registered keys: {', '.join(self.key_to_id)}")
            e.add_note(f"Registered ids: {', '.join(self)}")
            e.add_note(f"Registered names: {', '.join(self.name_to_id)}")
            raise e
        return super().__getitem__(id)
    
    def __repr__(self):
        return f"""
LinesData object, with {len(self)} line{'' if len(self)==1 else 's'} registered
Registered line names : {', '.join(self.name_to_id)}
Registered line ids : {', '.join(self)}
Registered keys to access lines : {', '.join(map("'{}'".format, self.key_to_id))}
        """
    


    def get_area(self, margin = 500):
        coords = np.zeros((len(self), 4))
        for i, line in enumerate(self.values()):
            coords[i] = line.get_min_max_coords()
        x_min, y_min = coords.min(axis=0)[[0, 2]] - margin
        x_max, y_max = coords.max(axis=0)[[1, 3]] + margin
        return Area(x_min, x_max, y_min, y_max)


    def plot(self, ax: Axes = None, same_color = True, **kwargs):
        if ax is None:
            fig, ax = self.get_area().plot()
        label = kwargs.pop("label", "Transport lines" if same_color else "")
        for line_id, line in self.items():
            line.plot(ax=ax, label=label, **kwargs)
            if same_color:
                kwargs["c"] = ax.get_lines()[-1].get_c()
                label = ""
    
        
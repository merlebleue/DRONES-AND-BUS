import os
import re

import numpy as np
import pandas as pd

from matplotlib.axes import Axes

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

    def plot(self, ax: Axes, *args, routes = "all", **kwargs):
        if routes == "all":
            routes = self.stops.columns[self.stops.columns.str[:5] == "Route"]

        label = kwargs.pop("label", self.line_name)
        alpha = kwargs.pop("alpha", 1)
        kwargs["linewidth"] = kwargs.get("linewidth", 1)
        #kwargs["markersize"] = kwargs.get("markersize", 3)
        kwargs["marker"] = kwargs.get("marker", "o")
        for route in routes:
            this_alpha = alpha * self.routes["Count"][route] / self.routes["Count"]["Route_A"]
            lines2d = ax.plot("POSITION_X", "POSITION_Y", data=self.stops[self.stops[route]], *args, label=label, alpha=this_alpha, **kwargs)
            kwargs["c"] = lines2d[0].get_c()
            label="_"
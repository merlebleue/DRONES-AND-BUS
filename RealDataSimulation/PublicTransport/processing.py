import datetime
import os
import re

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

from ..download import DownloadManager
from ..area import Area
from .linedata import LineData, LinesData

TRANSPORT_FOLDER = "transport_data"
FILTERED_SUBFOLDER = "0_filtered_data"
TIMETABLE_FILE = "Timetable_{date}.csv"
STOPS_FILE = "Stops_{date}.csv"

DIDOK_URL =  "https://opentransportdata.swiss/fr/dataset/service-points-full/permalink"
TIMETABLE_URL = "https://opentransportdata.swiss/fr/dataset/istdaten/resource_permalink/{date}_istdaten.csv"

class TooFastError(Exception):
    def __init__(self, transport_data, needed_status):
        super().__init__("You're going too fast ! Try running previous steps first, or use `solve_too_fast = True` argument")
        current_status = transport_data.get_status()
        self.add_note(f"Needed status: {needed_status} ({transport_data.status_messages[needed_status]})")
        self.add_note(f"Actual status: {current_status} ({transport_data.status_messages[current_status]})")

class TransportData:
    status_messages = {
        -1 : "Unknown",
        0 : "Data not downloaded",
        1 : "Data downloaded",
        2 : "Data filtered",
        3 : "Line data generated"
    }

    def __init__(self, name : str, area: Area = None, line_id: str = None, date= datetime.datetime.today().date(), **kwargs):
        self.name = name


        if (by_area := (area is not None)):
            self.area = area
            self.dl: DownloadManager = kwargs.get("download_manager", area.dl)
        else:
            self.dl: DownloadManager = kwargs.get("download_manager", DownloadManager())
            if line_id is not None:
                self.line_id = line_id
            else :
                print("No area or line_id defined. Do not forget to define one when running .filter_data (use .search_lines to see the possibilities)")
                self.line_id = None
        self.by_area = by_area

        self.date = date
        if not isinstance(self.date, datetime.date):
            self.date = datetime.date(*self.date)

        self.transport_folder: str = kwargs.get("folder", TRANSPORT_FOLDER)
        self.filtered_folder: str = kwargs.get("filtered_folder", FILTERED_SUBFOLDER)
        self.path = os.path.join(self.transport_folder, self.date.strftime("%Y_%m_%d"))

        # Create folder
        os.makedirs(self.path, exist_ok=True)

        # Determine status
        self.get_status()

    def path_join (self, *args):
        return os.path.join(self.path, *args)

    def get_status(self):
        # Status unknows, determine status based on files
        # Try at status = 3
        # TODO

        # Try at status = 2
        filename = self.path_join(self.filtered_folder, self.name, "{df}.csv")
        if os.path.isfile(filename.format(df="lines")) and \
           os.path.isfile(filename.format(df="stops")) and \
           os.path.isfile(filename.format(df="timetable")):
            self.status = 2
            return 2

        # Try at status = 1
        if self.dl.is_file_downloaded(TIMETABLE_FILE.format(date=self.date)) and \
            self.dl.is_file_downloaded(STOPS_FILE.format(date=self.date)):

            self.status = 1
            return 1
        
        self.status = 0
        return 0

    def download_data(self, date_strict = True, stops_url = DIDOK_URL, timetable_url = TIMETABLE_URL, return_data = True):
        if not date_strict:
            date = self.dl.get_latest_date(timetable_url, self.date)
            if date != self.date:
                print(f"----\nChanged date to {date}\n----\n")
                self.date = date
                self.path = os.path.join(self.transport_folder, date.strftime("%Y_%m_%d"))
                os.makedirs(self.path, exist_ok=True)
        else:
            date = self.date

        # Download
        stops_file = self.dl.download_with_cache(stops_url, STOPS_FILE.format(date=date), zip=True)
        timetable_file = self.dl.download_with_cache(timetable_url.format(date=date), TIMETABLE_FILE.format(date=date))

        # Save
        self.stops_file, self.timetable_file = stops_file, timetable_file

        # Update status
        self.get_status()

        if return_data:
            # Return the files
            return stops_file, timetable_file
    
    def get_downloaded_filenames(self, solve_too_fast = False, date_strict = True):
        # Check that file has been downloaded :
        if hasattr(self, "stops_file") and hasattr(self, "timetable_file"):
            # All right
            stops_file, timetable_file = self.stops_file, self.timetable_file
        elif self.get_status() >= 1:
            # File had been downloaded previously
            stops_file = self.dl.get_path(STOPS_FILE.format(date=self.date))
            timetable_file = self.dl.get_path(TIMETABLE_FILE.format(date=self.date))
        elif solve_too_fast:
            # Download the files
            stops_file, timetable_file = self.download_data(date_strict=date_strict, return_data=True)
        else:
            raise TooFastError(self, 1)
        
        return stops_file, timetable_file
        
    def search_lines(self, line_name, solve_too_fast= True):
        stops_file, timetable_file = self.get_downloaded_filenames(solve_too_fast=solve_too_fast, date_strict = False)
        timetable_df = pd.read_csv(timetable_file, delimiter= ";", low_memory=False)

        return timetable_df[timetable_df.LINIEN_TEXT == line_name][["BETREIBER_ABK", "BETREIBER_NAME", "PRODUKT_ID", "LINIEN_ID", "LINIEN_TEXT", "VERKEHRSMITTEL_TEXT"]].drop_duplicates(subset = "LINIEN_ID")

    def filter_data(self, line_id = None, solve_too_fast = False, return_data = True):
        stops_file, timetable_file = self.get_downloaded_filenames(solve_too_fast=solve_too_fast)

        # Get DataFrames
        # --------------
        stops_df = pd.read_csv(stops_file, delimiter= ";", low_memory=False)
        timetable_df = pd.read_csv(timetable_file, delimiter= ";", low_memory=False)


        # Filter stops
        # ------------

        # Filter based on validity (keep stops valid at the date)
        stops_df = stops_df.loc[(stops_df.validFrom <= str(self.date)) & (stops_df.validTo >= str(self.date))]
        # Filter based on the fact it is a stop (stopPoint = true)
        stops_df = stops_df.loc[stops_df.stopPoint]
        # Only keep interesting columns
        stops_df = stops_df[['number', 'designationOfficial', 'lv95East', 'lv95North']]

        if self.by_area:
            # Get stops numbers in rectangle
            stops_numbers = stops_df[self.area.is_inside(stops_df['lv95East'], stops_df['lv95North'])]["number"]


        # Filter timetable_data
        # ---------------------

            # Select the lines that passes through our stops
            lines = timetable_df.LINIEN_ID[timetable_df.BPUIC.isin(stops_numbers)].unique()
        else :
            if (line_id := line_id or self.line_id):
                self.line_id = line_id
                lines = [line_id]
            else:
                raise ValueError(f"line_id not defined ? ({line_id}, {self.line_id})")
                
            
        # Filter the timetable for only those lines
        timetable_filtered = timetable_df[timetable_df.LINIEN_ID.isin(lines)]

        # Select all the stops (including outside from the rectangle) from those lines :
        stops_filtered = stops_df.loc[stops_df.number.isin(timetable_filtered.BPUIC.unique())]

        # Only keep interesting columns from timetable_df and rename them
        timetable_filtered = timetable_filtered[["LINIEN_ID", "LINIEN_TEXT", "BETREIBER_ABK", "PRODUKT_ID", "FAHRT_BEZEICHNER", "BPUIC", "FAELLT_AUS_TF", "ANKUNFTSZEIT", "AN_PROGNOSE", "AN_PROGNOSE_STATUS", "ABFAHRTSZEIT", "AB_PROGNOSE", "AB_PROGNOSE_STATUS"]].rename(columns={
            "FAHRT_BEZEICHNER" : "JOURNEY_ID",
            "BETREIBER_ABK" : "TRANSPORTER",
            "PRODUKT_ID" : "MEAN_OF_TRANSPORT",
            "LINIEN_ID" : "LINE_ID",
            "LINIEN_TEXT" : "LINE_NAME",
            "FAELLT_AUS_TF" : "CANCELLED",
            "BPUIC" : "STOP_NUMBER",
            "ANKUNFTSZEIT" : "ARRIVAL",
            "AN_PROGNOSE" : "ARRIVAL_REAL",
            "AN_PROGNOSE_STATUS" : "ARRIVAL_REAL_STATUS",
            "ABFAHRTSZEIT" : "DEPARTURE",
            "AB_PROGNOSE" : "DEPARTURE_REAL",
            "AB_PROGNOSE_STATUS" : "DEPARTURE_REAL_STATUS"
        })

        # Offload data about lines
        lines_df = timetable_filtered[["LINE_ID", "LINE_NAME", "TRANSPORTER", "MEAN_OF_TRANSPORT"]].drop_duplicates()

        # Export the filtered stops, timetable and line dataframes
        os.makedirs(self.path_join(self.filtered_folder, self.name), exist_ok=True)
        filename = self.path_join(self.filtered_folder, self.name, "{df}.csv")

        stops_filtered.to_csv(filename.format(df = "stops"), sep=";", index=False)
        timetable_filtered.to_csv(filename.format(df = "timetable"), sep=";", index=False)
        lines_df.to_csv(filename.format(df="lines"), sep=";", index=False)

        # Update status
        self.get_status()

        if return_data:
            # Return copies (to reduce impact) of the dataframes
            return stops_filtered.copy(deep=True), timetable_filtered.copy(deep=True), lines_df.copy(deep=True)

    def get_filtered_data(self, solve_too_fast = False):
        # Check that the data has already been filtered :
        if self.get_status() >= 2:
            # Data has been filtered previously : all good
            filename = self.path_join(self.filtered_folder, self.name, "{df}.csv")
            stops_df = pd.read_csv(filename.format(df = "stops"), sep = "[ \t]*;[ \t]*", engine="python")
            timetable_df = pd.read_csv(filename.format(df = "timetable"), sep = "[ \t]*;[ \t]*", engine="python")
            lines_df = pd.read_csv(filename.format(df = "lines"), sep = "[ \t]*;[ \t]*", engine="python")
        elif solve_too_fast:
            # Filter the data then get it
            stops_df, timetable_df, lines_df = self.filter_data(solve_too_fast=True, return_data=True)
        else:
            raise TooFastError(self, 2)
        
        return stops_df, timetable_df, lines_df
    
    def get_lines_data(self,
                       lines = "all",
                       modes = None,
                       correct_times = True,
                       threshold = 5,
                       verbose= 1,
                       solve_too_fast = False,
                       return_data = True):
        lines_df = self.get_filtered_data(solve_too_fast=solve_too_fast)[2]

        # Filter lines according to modes argument
        if modes is not None:
            pot_lines_df = lines_df.loc[lines_df.MEAN_OF_TRANSPORT.str.lower().isin([m.lower() for m in modes])]
            if len(pot_lines_df) == 0:
                raise ValueError(f"`modes` values is not found in the lines for this area.\nFound : {', '.join(lines_df.MEAN_OF_TRANSPORT.drop_duplicates().str.lower())}")
            else:
                lines_df = pot_lines_df
        # Determine which lines are asked
        if type(lines) is str:
            if lines == "all":
                # Get all lines
                lines_ids = lines_df.LINE_ID.unique().tolist()
            elif lines in lines_df.LINE_ID:
                lines_ids = [lines]
            elif lines in lines_df.LINE_NAME:
                line_id = lines_df.LINE_ID.loc[lines_df.LINE_NAME == lines][0]
                lines_ids = [line_id]
            else:
                raise ValueError(f"'{lines}' is not a valid value for `lines` argument. Valid values are (either alone or in a tuple):\n'all', {', '.join(lines_df.LINE_ID.astype(str))}, {', '.join(lines_df.LINE_NAME.astype(str))}")
        elif type(lines) is tuple:
            lines_ids = []
            for line in lines :
                if line in lines_df.LINE_ID:
                    lines_ids = [line]
                elif line in lines_df.LINE_NAME:
                    line_id = lines_df.LINE_ID.loc[lines_df.LINE_NAME == line][0]
                    lines_ids = [line_id]
                else:
                    raise ValueError(f"'{line}' is not a valid value for `lines` argument. Valid values are (either alone or in a tuple):\n'all', {', '.join(lines_df.LINE_ID.astype(str))}, {', '.join(lines_df.LINE_NAME.astype(str))}")
        else:
            raise TypeError("`lines` argument must be str or tuple")

        # Run over each line and compute the timetable
        # --------------------------------------------
        lines_data = LinesData()
        for line_id in lines_ids:
            lines_data.add_line(self.generate_timetable(line_id, 
                       correct_times = correct_times,
                       threshold = threshold,
                       verbose= verbose,
                       solve_too_fast = solve_too_fast,
                       return_data = True))
            
        if return_data:
            return lines_data
        
    def generate_timetable(self,
                           line_id = None,
                           correct_times = True,
                           threshold = 5,
                           verbose= 1,
                           solve_too_fast = False,
                           return_data = True):
        if line_id is None:
            line_id = self.line_id
        stops_df, timetable_df, lines_df = self.get_filtered_data(solve_too_fast=solve_too_fast)
        if verbose > 0:
            print(line_id)
        line_data = timetable_df.loc[timetable_df.LINE_ID == line_id, ["STOP_NUMBER", "JOURNEY_ID", "ARRIVAL", "ARRIVAL_REAL", "DEPARTURE", "DEPARTURE_REAL", "ARRIVAL_REAL_STATUS", "DEPARTURE_REAL_STATUS"]]
        line_name = lines_df.LINE_NAME.loc[lines_df.LINE_ID == line_id].iloc[0]

        # Remove duplicates (and try to select the lines with the most accurate status (so REAL instead of PROGNOSE))
        duplicates = (line_data
                        .sort_values(by=["ARRIVAL_REAL_STATUS", "DEPARTURE_REAL_STATUS"])
                        .duplicated(subset = ["STOP_NUMBER", "JOURNEY_ID"], keep="last")
                        )
        if duplicates.sum() > 0:
            if verbose > 0:
                print(f"Removing {duplicates.sum()} duplicates for line {line_name} ({line_id})")
            line_data = (line_data
                        .sort_values(by=["ARRIVAL_REAL_STATUS", "DEPARTURE_REAL_STATUS"])
                        .drop_duplicates(subset = ["STOP_NUMBER", "JOURNEY_ID"], keep="last")
                        )
        line_data = line_data.drop(columns = ["ARRIVAL_REAL_STATUS", "DEPARTURE_REAL_STATUS"])

        # Pivot timetable data for the bus line
        # ----------------------------------------
        line_timetable = (line_data
            .pivot(index="STOP_NUMBER", columns="JOURNEY_ID")
            .stack(level=0, future_stack=True)
            .apply(pd.to_datetime, format="mixed")
            )
        line_timetable.index.set_names("EVENT", level=-1, inplace=True)
        
        # ----
        # Analyse journeys
        # ----

        # Get the order in which each journey goes to each bus stop
        orders = (line_timetable
                    .loc[line_timetable.index.get_level_values("EVENT").str[-4:] == "REAL"]
                    .groupby("STOP_NUMBER", sort=False).first()
                    .apply(lambda x : x.dropna().sort_values().argsort(), axis=0)
                    .fillna(-1))
        
        # Count how many time each order appears
        order_counts = orders.T.value_counts().reset_index().astype("int").set_index("count").T
        order_counts = order_counts.sort_index(key=lambda x : x.map(order_counts.iloc[:, 0]))

        # ---
        # Create a "stops" df to get all the stops of the line in a correct order
        # ---

        stops = pd.merge(line_timetable.index.get_level_values("STOP_NUMBER").to_series(), 
                         stops_df[["designationOfficial", "lv95East", "lv95North"]].rename(columns = {"designationOfficial": "STOP_NAME", "lv95East": "POSITION_X", "lv95North": "POSITION_Y"}), 
                         how="left", 
                         right_on=stops_df["number"], 
                         left_index=True).drop("key_0", axis=1).set_index("STOP_NUMBER").drop_duplicates()

        # ---
        # Add a "distance" column to order the stops
        # ---

        # Select the order which appears the most
        order = order_counts.iloc[:, 0]

        # Compute the distance based on this order
        distance = ((stops[["POSITION_X", "POSITION_Y"]].loc[order>=0].sort_index(key=lambda x: x.map(order)).diff()**2).sum(axis=1)**0.5).cumsum()

        stops["DISTANCE"] = stops.index.map(distance)

        # Get full order of the stops by interpolation, over subsequent orders
        # ---

        # Iterate over other orders to interpolate the distances
        missing_distances = stops["DISTANCE"].isna().sum()
        for _, order in order_counts.iloc[:, 1:].items():
            if verbose > 1:
                print(missing_distances)
            
            distance = ((stops[["POSITION_X", "POSITION_Y"]].loc[order>=0].sort_index(key=lambda x: x.map(order)).diff()**2).sum(axis=1)**0.5).cumsum().rename("distance")

            distance_for_interp = stops["DISTANCE"].loc[distance.index].dropna()

            index=distance.index
            distance = interp1d(distance.loc[distance_for_interp.index].values, distance_for_interp.values, fill_value = "extrapolate", assume_sorted=False)(distance.values)
            distance = pd.Series(distance, index=index, name="distance")

            stops["DISTANCE"] = stops["DISTANCE"].fillna(distance)


            missing_distances = stops["DISTANCE"].isna().sum()
            if missing_distances == 0:
                break

        if missing_distances > 0:
            if verbose > 0:
                print(f"Still {missing_distances} distances values missing for line {line_name} ({line_id})")
                print(stops.loc[stops["DISTANCE"].isna()])
                print()
        
        # Sort the stops df
        stops = stops.sort_values("DISTANCE")
                
        # Add stop names to the timetable
        names = line_timetable.index.get_level_values("STOP_NUMBER").map(stops_df.set_index("number")["designationOfficial"]).rename("STOP_NAME")
        line_timetable = line_timetable.set_index([names, line_timetable.index])
        # Sort the timetable based on this distance
        def sort_function(x: pd.Index):
            if x.name == "STOP_NUMBER":
                return x.map(stops["DISTANCE"])
            else:
                return x
        line_timetable = line_timetable.sort_index(level=["STOP_NUMBER", "EVENT"], key = sort_function)

        # ----
        # Analyse routes
        # ----


        # Get whether journeys stops at each stop
        stop_mask = orders >= 0
        
        # Change stops index :
        stop_mask.index = stop_mask.index.map(stops["STOP_NAME"])
        stops = stops.reset_index().set_index("STOP_NAME")

        # Determine the different routes and add them to the "stops" df
        stop_mask = stop_mask.reindex(stops.index)
        routes = stop_mask.T.value_counts().rename("Count").reset_index()
        routes = routes.rename(index= lambda i: f"Route_{chr(65+i)}")
        stops = stops.merge(routes.T, how="left", left_on="STOP_NAME", right_index=True).sort_values("DISTANCE")

        # ----
        # Analyse journeys
        # ----

        # Create a `journeys` df to log journeys, their route and their direction
        journeys = line_data.JOURNEY_ID.drop_duplicates()

        # Determine the route :
        routes_map = routes.iloc[:, :-1].apply(lambda x : "".join(np.where(x, "Y", "N")), axis=1).rename("YN").reset_index().set_index("YN")["index"]
        journeys_routes = stop_mask.apply(lambda x : "".join(np.where(x, "Y", "N")), axis=0).map(routes_map).rename("Route")
        journeys = pd.DataFrame(journeys_routes, index = journeys)
        journeys["Number_of_stops"] = stop_mask.T.sum(axis=1)

        # Determine the direction :
        mask = line_timetable.index.get_level_values("EVENT").str[-4:] == "REAL"
        planned = line_timetable.loc[~mask]
        real = line_timetable.loc[mask]
        journeys["Direction"] = line_timetable.loc[line_timetable.index.get_level_values("EVENT") == "DEPARTURE_REAL"].diff().map(lambda x : np.where(x<pd.Timedelta(0), "R", "O"), na_action="ignore").mode().loc[0]

        # Add a direction to routes in the routes dataframe
        def get_direction(group):
            v = group.value_counts()
            return "".join(v.index)
        routes["Direction"] = journeys.groupby("Route")["Direction"].apply(get_direction)

        # Add start and end stops
        journeys["Start"] = real.droplevel(["STOP_NUMBER", "EVENT"]).idxmin(axis=0).T
        journeys["Start_time_Planned"] = planned.min(axis=0).T
        journeys["Start_time_Real"] = real.min(axis=0).T
        journeys["End"] = real.droplevel(["STOP_NUMBER", "EVENT"]).idxmax(axis=0).T
        journeys["End_time_Planned"] = planned.max(axis=0).T
        journeys["End_time_Real"] = real.max(axis=0).T

        # Sort journeys and line_timetable DataFrame
        journeys = journeys.sort_values("Start_time_Planned")
        line_timetable = line_timetable[journeys.index.tolist()]

        # ----
        # Correct the data
        # ----
        
        # Correct time data
        if correct_times:
            line_timetable.loc[mask, journeys.loc[journeys.Direction == "O"].index] = line_timetable.loc[mask, journeys.loc[journeys.Direction == "O"].index].apply(lambda col : pd.to_datetime(((col.dropna()- pd.Timestamp("1970-01-01")) // pd.Timedelta("1s")).expanding(1).max(), unit="s"), axis = 0)
            line_timetable.loc[mask, journeys.loc[journeys.Direction == "R"].index] = line_timetable.loc[mask, journeys.loc[journeys.Direction == "R"].index].apply(lambda col : pd.to_datetime(((col.dropna().iloc[::-1].reindex(["ARRIVAL_REAL", "DEPARTURE_REAL"], level=2)- pd.Timestamp("1970-01-01")) // pd.Timedelta("1s")).expanding(1).max(), unit="s"), axis = 0)

        # Drop the routes that share minimal number of stops with the "main" route
        if threshold > 0:
            only_routes = routes.drop(columns =["Count", "Direction"])
            route_similitude = (only_routes * only_routes.loc["Route_A"]).sum(axis=1)
            routes_to_drop = route_similitude.index[route_similitude < threshold]

            if len(routes_to_drop) > 0:
                print(f"Dropping routes {', '.join(routes_to_drop)} as their similitude with Route_A is smaller than the threshold ({threshold})")

                routes = routes.drop(index=routes_to_drop)
                stops = stops.drop(columns=routes_to_drop) # Remove the route
                stops = stops.loc[~stops.any(axis=1, bool_only=True)] # Remove stops where no route is going through it
                journeys_to_drop = journeys.index[journeys["Route"].isin(routes_to_drop)]
                print(f"Consequently, dropping journeys {', '.join(journeys_to_drop)}")
                journeys = journeys.drop(index=journeys_to_drop) # Remove concerned journeys from 'journeys' DataFrame
                line_timetable = line_timetable.drop(columns=journeys_to_drop) # Remove concerned journeys from the timetable
                line_timetable = line_timetable.dropna(how="all") # Remove stops where no journey is going through it
                print()

        # ----
        # Finalise and export
        # ----

        line_data = LineData(line_id, line_name, self.path, timetable = line_timetable, stops = stops, routes = routes, journeys= journeys)
        line_data.save_data()
        if return_data:
            return line_data
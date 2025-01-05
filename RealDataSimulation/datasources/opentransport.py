from datetime import datetime
import os
import re

import numpy as np
import pandas as pd

from .download import DownloadManager
from ..project import Project

TRANSPORT_FOLDER = "transport_data"
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
    def __init__(self, sim: Project, **kwargs):
        self.sim = sim

        self.date: datetime.date = kwargs.get("date", sim.t_start.date())
        self.dl: DownloadManager = kwargs.get("download_manager", sim.dl)
        self.transport_folder: str = kwargs.get("folder", TRANSPORT_FOLDER)

        # Create folder
        os.makedirs(sim.path_join(self.transport_folder), exist_ok=True)

        # Determine status
        self.get_status()

    def get_status(self):
        # Status unknows, determine status based on files
        # Try at status = 3
        # TODO

        # Try at status = 2
        filename = self.sim.path_join(self.transport_folder, "{df}.csv")
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
    
    def get_downloaded_filenames(self, solve_too_fast = False):
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
            stops_file, timetable_file = self.download_data(self, date_strict=True, return_data=True)
        else:
            raise TooFastError(self, 1)
        
        return stops_file, timetable_file
        
    def filter_data(self, solve_too_fast = False, return_data = True):
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

        # Get stops numbers in rectangle
        stops_numbers = stops_df[self.sim.is_inside(stops_df['lv95East'], stops_df['lv95North'])]["number"]


        # Filter timetable_data
        # ---------------------

        # Select the lines that passes through our stops
        lines = timetable_df.LINIEN_ID[timetable_df.BPUIC.isin(stops_numbers)].unique()
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
        filename = self.sim.path_join(self.transport_folder, "{df}.csv")

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
            filename = self.sim.path_join(self.transport_folder, "{df}.csv")
            stops_df = pd.read_csv(filename.format(df = "stops"), sep = "[ \t]*;[ \t]*", engine="python")
            timetable_df = pd.read_csv(filename.format(df = "timetable"), sep = "[ \t]*;[ \t]*", engine="python")
            lines_df = pd.read_csv(filename.format(df = "lines"), sep = "[ \t]*;[ \t]*", engine="python")
        elif solve_too_fast:
            # Filter the data then get it
            stops_df, timetable_df, lines_df = self.filter_data(solve_too_fast=True, return_data=True)
        else:
            raise TooFastError(self, 2)
        
        return stops_df, timetable_df, lines_df
    
    def generate_timetable(self, lines = "all", modes = None, solve_too_fast = False, return_data = True):
        stops_df, timetable_df, lines_df = self.get_filtered_data(solve_too_fast=solve_too_fast)

        # Filter lines according to modes argument
        if modes is not None:
            lines_df = lines_df.loc[lines_df.MEAN_OF_TRANSPORT.str.lower.isin([m.lower() for m in modes])]
            if len(lines_df) == 0:
                raise ValueError(f"`modes` values is not found in the lines for this area.\nFound : {', '.join(lines_df.MEAN_OF_TRANSPORT.astype(str))}")
        
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
        lines_timetables = {}
        for line_id in lines_ids:
            print(line_id)
            line_data = timetable_df.loc[timetable_df.LINE_ID == line_id, ["STOP_NUMBER", "JOURNEY_ID", "ARRIVAL", "ARRIVAL_REAL", "DEPARTURE", "DEPARTURE_REAL", "ARRIVAL_REAL_STATUS", "DEPARTURE_REAL_STATUS"]]
            line_name = lines_df.LINE_NAME.loc[lines_df.LINE_ID == line_id].iloc[0]

            # Remove duplicates (and try to select the lines with the most accurate status (so REAL instead of PROGNOSE))
            duplicates = (line_data
                            .sort_values(by=["ARRIVAL_REAL_STATUS", "DEPARTURE_REAL_STATUS"])
                            .duplicated(subset = ["STOP_NUMBER", "JOURNEY_ID"], keep="last")
                            )
            if duplicates.sum() > 0:
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
            
            # Add stop names
            names = line_timetable.index.get_level_values("STOP_NUMBER").map(stops_df.set_index("number")["designationOfficial"]).rename("STOP_NAME")
            line_timetable = line_timetable.set_index([names, line_timetable.index])
            
            # Add geodata
            index = line_timetable.index
            line_timetable = pd.merge(line_timetable, 
                                        stops_df[["lv95East", "lv95North"]].rename(columns = {"lv95East": "POSITION_X", "lv95North": "POSITION_Y"}), 
                                        how="left", 
                                        right_on=stops_df["number"], 
                                        left_on="STOP_NUMBER"
                                        ).drop(columns = "STOP_NUMBER")
            line_timetable.index = index

            # Select one of the journeys with the most stops
            journey = line_data.dropna()["JOURNEY_ID"].mode()[0]

            # Compute the distance based on this journey
            journey_data = (line_timetable
                            .loc[(line_timetable.index.get_level_values("EVENT").str[-4:] == "REAL"), [journey, "POSITION_X", "POSITION_Y"]]
                            .dropna(subset=journey)
                            .groupby("STOP_NUMBER")
                            .max()
                            .sort_values(journey)
                            )
            distance = ((journey_data[["POSITION_X", "POSITION_Y"]].diff()**2).sum(axis=1)**0.5).cumsum()

            line_timetable["DISTANCE"] = line_timetable.index.get_level_values("STOP_NUMBER").map(distance)
            line_timetable = line_timetable.sort_values(["DISTANCE", "EVENT"])

            # Get full order of the stops by interpolation
            # ---

            # Iterate over other journeys to interpolate the distances
            missing_distances = line_timetable["DISTANCE"].isna().sum()
            n_iter = 0
            while missing_distances > 0 and n_iter < 10:
                n_iter +=1
                print(missing_distances)
                # Find the journey with the most data on the stops for which we don't have the distance yet.
                journey = (line_timetable
                           .loc[(line_timetable.index.get_level_values("EVENT").str[-4:] == "REAL") * (line_timetable.DISTANCE.isna())]
                           .drop(["POSITION_X", "POSITION_Y" ,"DISTANCE"], axis=1, errors = "ignore")
                           .count(axis=0)
                           .idxmax())

                journey_data = (line_timetable
                                .loc[(line_timetable.index.get_level_values("EVENT").str[-4:] == "REAL"), [journey, "POSITION_X", "POSITION_Y", "DISTANCE"]]
                                .dropna(subset=journey).groupby("STOP_NUMBER")
                                .first()
                                .sort_values([journey]))

                distance = ((journey_data[["POSITION_X", "POSITION_Y"]].diff()**2).sum(axis=1)**0.5).cumsum().rename("distance")

                distance = journey_data.join(distance)["distance"]

                index=distance.index
                distance = np.interp(distance, distance.loc[journey_data["DISTANCE"].notna()], journey_data["DISTANCE"].dropna())
                distance = pd.Series(distance, index=index, name="distance")

                line_timetable["DISTANCE"] = line_timetable["DISTANCE"].fillna(line_timetable.join(distance)["distance"])


                missing_distances = line_timetable["DISTANCE"].isna().sum()
            if missing_distances > 0:
                print(f"Still {missing_distances} distances values missing for line {line_name} ({line_id})")

            line_timetable = line_timetable.sort_values(["DISTANCE", "EVENT"]) 

            # ----
            # Analyse journeys, to determine their direction and identify "strange" trajects
            # ----

            




            # ----
            # Finalise and export
            # ----

            # Separate between "planned" (to the minute) and "real" (to the sec) data
            mask = line_timetable.index.get_level_values("EVENT").str[-4:] == "REAL"
            planned = line_timetable.loc[~mask]
            real = line_timetable.loc[mask]

            lines_timetables[line_id] = {
                "planned": planned,
                "real": real,
                "full": line_timetable
            }

            # Export
            if lines_df.LINE_NAME.is_unique:
                # Use linenames to export
                line_ref = line_name
            else:
                # Use cleaned version of LINE_ID to export
                line_ref = re.sub(r'[^\w\d-]','_',line_id)
            
            os.makedirs(self.sim.path_join(self.transport_folder, str(line_ref)), exist_ok=True)
            for name, df in lines_timetables[line_id].items():
                df.to_csv(self.sim.path_join(self.transport_folder, str(line_ref), f"{line_ref}_{name}.csv"), sep=";", float_format="%.0f")

        return lines_timetables

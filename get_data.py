import pandas as pd
import matplotlib.pyplot as plt
import datetime
import os
import urllib.request, urllib.error
from zipfile import ZipFile

import seaborn as sns
import seaborn.objects as so

ZIP_FOLDER = os.path.join("data", "0_zip")
DOWNLOAD_FOLDER = os.path.join("data", "1_downloaded")
PRE_PROCESSED_FOLDER = os.path.join("data", "2_pre-processed")
PROCESSED_FOLDER = os.path.join("data", "3_processed")

def download_with_cache(url : str,
                   name: str,
                   date=datetime.datetime.today().date(),
                   zip = False,
                   verbose = 1,
                   download_folder = DOWNLOAD_FOLDER,
                   zip_folder = ZIP_FOLDER):
    """
    Downloads a file from a specified URL, with support for date formatting and optional handling of zip archives. 
    If the file already exists locally, the cached version is returned. Iterates backward through dates to find the file.

    Args:
        url (str): The URL template containing a `{date}` placeholder for dynamic date substitution.
        name (str): The filename template, including a `{date}` placeholder and file extension.
        date (datetime.date or tuple, optional): The starting date for file search. Defaults to today's date. Tuple must be in `(year, month, day)` format.
        zip (bool, optional): Whether the file is in a zip archive. Defaults to False.
        download_folder (str, optional): Directory where the file will be saved. Defaults to `DOWNLOAD_FOLDER`.
        zip_folder (str, optional): Directory where zip files are saved. Defaults to `ZIP_FOLDER`.

    Returns:
        tuple: 
            - save_path (str): The path to the saved file.
            - date (datetime.date): The date associated with the downloaded or cached file.
    """
    
    if not isinstance(date, datetime.date):
        date = datetime.date(*date)

    def generator(url, date):
        while date > datetime.date(1900, 1, 1):
            yield url.format(date=date), date
            date = date - datetime.timedelta(days=1)
    for try_url, date in generator(url, date):
        save_path = os.path.join(download_folder, name.format(date=date))
        zip_save_path = ""
        if zip :
            n, extension = name.rsplit(".", 1)
            zip_save_path = os.path.join(zip_folder, n.format(date=date) + "." + "zip")
            
        if os.path.isfile(save_path):
            return save_path, date
        
        if (zip and os.path.isfile(zip_save_path)):
            break

        request = urllib.request.Request(try_url, method='HEAD')
        try:
            with urllib.request.urlopen(request) as response:
                if response.status == 200:  # URL exists
                    # Proceed to download the file
                    # Create directories if they don't exist
                    os.makedirs(os.path.dirname(zip_save_path if zip else save_path), exist_ok=True)
                    # Download and save the file
                    urllib.request.urlretrieve(try_url, zip_save_path if zip else save_path)
                    break
        except urllib.error.HTTPError as e:
            if verbose >0 :
                print(f"File not found at {try_url} (404). Current date : {date}. Trying an earlier date.")
            continue
        
        
    if zip:
        with ZipFile(zip_save_path) as zip_file:

            files = zip_file.namelist()
            files2 = [f for f in files if f.endswith(extension)]
            if len(files2)>0:
                file = files2[0]
            else :
                file = files[0]
            zip_file.extract(file, download_folder)

        os.rename(os.path.join(download_folder, file), save_path)
        
    return save_path, date
    
def preprocess_TP_data(x_min, x_max, y_min, y_max, means_of_transport: tuple = ("all", ), date : datetime.date = datetime.datetime.today().date(), folder = PRE_PROCESSED_FOLDER):
    # Determine filename (to check if it exists)
    filename = os.path.join(folder, "_".join([str(i) for i in ("{df}", "{date}", "-".join(means_of_transport), x_min, x_max, y_min, y_max)]))

    # Check if files exist and if they exists load them and return them
    if os.path.isfile(filename.format(df = "stops", date=date)) & os.path.isfile(filename.format(df = "timetable", date=date)) :
        stops_filtered = pd.read_csv(filename.format(df = "stops", date=date))
        timetable_filtered = pd.read_csv(filename.format(df = "timetable", date=date))
    
        return stops_filtered, timetable_filtered

    # Download didok data
    didok_url = "https://opentransportdata.swiss/fr/dataset/service-points-full/permalink"
    didok_file, didok_date = download_with_cache(didok_url, "DIDOK_{date}.csv", zip=True, verbose=0)
    stops_df = pd.read_csv(didok_file, delimiter= ";", low_memory=False)

    # Update date if didok file is older
    if didok_date < date:
        print(f"Changing date to {didok_date} because most recent Didok data is older than {date}")
        date = didok_date
    
    # Download timetable data:
    timetable_url = "https://opentransportdata.swiss/fr/dataset/istdaten/resource_permalink/{date}_istdaten.csv"
    timetable_file, timetable_date= download_with_cache(timetable_url, "Timetable_{date}.csv", date, verbose=0)
    timetable_df = pd.read_csv(timetable_file, delimiter= ";", low_memory=False)

    # Update date if timetable file is older
    if timetable_date < date:
        print(f"Changing date to {timetable_date} because most recent timetable data is older than {date}")
        date = timetable_date

    # Given the possible change in date, check again
    if os.path.isfile(filename.format(df = "stops", date=date)) & os.path.isfile(filename.format(df = "timetable", date=date)) :
        stops_filtered = pd.read_csv(filename.format(df = "stops", date=date))
        timetable_filtered = pd.read_csv(filename.format(df = "timetable", date=date))
    
        return stops_filtered, timetable_filtered


    # Filter stops
    # ------------

    # Filter based on validity (keep stops valid at the date)
    stops_df = stops_df.loc[(stops_df.validFrom <= str(date)) & (stops_df.validTo >= str(date))]
    # Filter based on the fact it is a stop (stopPoint = true)
    stops_df = stops_df.loc[stops_df.stopPoint]
    # Only keep interesting columns
    stops_df = stops_df[['number', 'designationOfficial', 'lv95East', 'lv95North']]

    # Get stops numbers in rectangle
    stops_numbers = stops_df[stops_df['lv95East'].between(x_min, x_max) & stops_df['lv95North'].between(y_min, y_max)]["number"]


    # Filter timetable_data
    # ---------------------
    
    # Filter based on the transport means
    if "all" not in means_of_transport:
        timetable_df = timetable_df.loc[timetable_df.PRODUKT_ID.str.contains("|".join(means_of_transport)).fillna(False)]
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

    # Export the filtered stops and timetable dataframes
    stops_filtered.to_csv(filename.format(df = "stops", date=date), index=False)
    timetable_filtered.to_csv(filename.format(df = "timetable", date=date), index=False)

    # Return copies (to reduce impact) of the dataframes
    return stops_filtered.copy(deep=True), timetable_filtered.copy(deep=True)

def process_line_data(stops_df: pd.DataFrame, timetable_df = pd.DataFrame, complex=False, folder=PROCESSED_FOLDER):

    # Make a map LINE_ID -> LINE_NAME (for later)
    line_names = (timetable_df[["LINE_ID", "LINE_NAME"]]
                  .drop_duplicates()
                  .set_index("LINE_ID")
                  .to_dict()["LINE_NAME"]
                  )
    
    # Group by line and choose only some columns
    grouped = timetable_df.groupby("LINE_ID")[["STOP_NUMBER", "JOURNEY_ID", "ARRIVAL", "ARRIVAL_REAL", "DEPARTURE", "DEPARTURE_REAL", "ARRIVAL_REAL_STATUS", "DEPARTURE_REAL_STATUS"]]
    lines_data = {}
    simple_lines_data = {}
    for line_id, line_data in grouped:
        line_name = line_names[line_id]
        print(line_id, line_name)

        # Remove duplicates (and try to select the lines with the most accurate status (so REAL instead of PROGNOSE))
        duplicates = (line_data
                      .sort_values(by=["ARRIVAL_REAL_STATUS", "DEPARTURE_REAL_STATUS"])
                      .duplicated(subset = ["STOP_NUMBER", "JOURNEY_ID"], keep="last")
                      )
        if duplicates.sum() > 0:
            print(f"Removing {duplicates.sum()} duplicates for line {line_name} ({line_id})")
            line_data =line_data[~duplicates]
        line_data = line_data.drop(columns = ["ARRIVAL_REAL_STATUS", "DEPARTURE_REAL_STATUS"])

        # Refactor timetable data for the bus line
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
                                  stops_df[["lv95East", "lv95North"]].rename(columns = {"lv95East": "POSITION_X", "lv95North": "POSTION_Y"}), 
                                  how="left", 
                                  right_on=stops_df["number"], 
                                  left_on="STOP_NUMBER"
                                  ).drop(columns = "STOP_NUMBER")
        line_timetable.index = index

        # Select one of the journeys with the most stops
        journey = line_data["JOURNEY_ID"].dropna().mode()[0]

        # Compute the distance based on this journey
        journey_data = (line_timetable[[journey, "POSITION_X", "POSTION_Y"]]
                        .dropna(subset=journey)
                        .groupby("STOP_NUMBER")
                        .max()
                        .sort_values(journey)
                        )
        distance = ((journey_data[["POSITION_X", "POSTION_Y"]].diff()**2).sum(axis=1)**0.5).cumsum()

        line_timetable["DISTANCE"] = line_timetable.index.get_level_values("STOP_NUMBER").map(distance)
        line_timetable = line_timetable.sort_values(["DISTANCE", "EVENT"])
        
        # ----------------------------------------------------------
        # Compute travel time averages and then export "simple" data
        # ----------------------------------------------------------

        simple_lines_data[line_name] = {}
        for real_time in (False, True):
            mask = line_timetable.index.get_level_values("EVENT").str[-4:] == "REAL"
            if not real_time:
                mask = ~mask
            simple_line_data = (line_timetable[mask] # Select only real or planned times
                                .dropna(subset="DISTANCE") # Drop the stops at which our journey did not stop
                                )
            
            # Compute mean travel time
            def mean_travel_time(diff):
                df = (simple_line_data
                      .diff(diff)
                      .drop(columns=["DISTANCE", "POSITION_X", "POSTION_Y"])
                      ) * diff
                return (df[df>pd.Timedelta(seconds=0)] # Check sign to only have busses going that way
                        .mean(axis=1) # Compute mean accross the columns
                        .dt.seconds) # Return the seconds (easier to manipulate)
            previous_tt, next_tt = mean_travel_time(1), mean_travel_time(-1)
            simple_line_data["TIME_A"], simple_line_data["TIME_R"] = previous_tt, next_tt
            # Remove "_REAL" suffix for consistency
            if real_time:
                simple_line_data = simple_line_data.rename(index= lambda i : i[:-5],level="EVENT")
            # Invert the TIME_R between departure and arrival
            simple_line_data.loc[(slice(None), slice(None), "ARRIVAL"), "TIME_R"], simple_line_data.loc[(slice(None), slice(None), "DEPARTURE"), "TIME_R"] = simple_line_data.loc[(slice(None), slice(None), "DEPARTURE"), "TIME_R"].values, simple_line_data.loc[(slice(None), slice(None), "ARRIVAL"), "TIME_R"].values

            # Remove unused columns
            simple_line_data = simple_line_data[["DISTANCE", "TIME_A", "TIME_R", "POSITION_X", "POSTION_Y"]]
            # Remove first arrival and last departure lines
            simple_line_data = simple_line_data.dropna(subset = ["TIME_A", "TIME_R"], how="all")

            # Export and save
            os.makedirs(os.path.join(folder, "simple"), exist_ok=True)
            simple_line_data.to_csv(os.path.join(folder, "simple", f"{line_name}_{'real' if real_time else 'planned'}.csv"), float_format="%.0f")
            simple_lines_data[line_name]['real' if real_time else 'planned'] = simple_line_data
    return simple_lines_data


        
"""
        # Get full order of the stops by interpolation
        # ---

        # Iterate over other journeys to interpolate the distances
        missing_distances = line_timetable["Distance"].isna().sum()
        n_iter = 0
        while missing_distances > 0 and n_iter < 10:
            n_iter +=1
            print(missing_distances)
            # Find the journey with the most data on the stops for which we don't have the distance yet.
            journey = line_timetable.loc[line_timetable.Distance.isna()].drop(["lv95East", "lv95North" ,"Distance"], axis=1, errors = "ignore").count(axis=0).idxmax()

            journey_data = line_timetable[[journey, "lv95East", "lv95North", "Distance"]].dropna(subset=journey).groupby("STOP").first().sort_values([journey])

            distance = ((journey_data[["lv95East", "lv95North"]].diff()**2).sum(axis=1)**0.5).cumsum().rename("distance")

            distance = journey_data.join(distance)["distance"]

            index=distance.index
            distance = np.interp(distance, distance.loc[journey_data["Distance"].notna()], journey_data["Distance"].dropna())
            distance = pd.Series(distance, index=index, name="distance")

            line_timetable["Distance"] = line_timetable["Distance"].fillna(line_timetable.join(distance)["distance"])


            missing_distances = line_timetable["Distance"].isna().sum()
        if missing_distances > 0:
            print(f"Still {missing_distances} distances values missing for line {line_name} ({line_id})")

        # Separate between "planned" (to the minute) and "real" (to the sec) data
        planned = line_timetable.loc[(line_timetable.index.levels[0], line_timetable.index.levels[1], ["ANKUNFTSZEIT", "ABFAHRTSZEIT"]),].sort_values("Distance")
        real = line_timetable.loc[(line_timetable.index.levels[0], line_timetable.index.levels[1], ["AN_PROGNOSE", "AB_PROGNOSE"]),].sort_values("Distance")
        # Save
        os.makedirs(os.path.join(LINE_DATA_FOLDER, str(line_name)), exist_ok=True)
        planned.to_csv(os.path.join(LINE_DATA_FOLDER, str(line_name), f"{line_name}_planned.csv"), header=line_id)
        real.to_csv(os.path.join(LINE_DATA_FOLDER, str(line_name), f"{line_name}_real.csv"), header=line_id)

        lines_data[line_name] = {
            "planned" : planned,
            "real" : real,
            "timetable" : line_timetable
        }

    df = lines_data["705"]["real"]

    plt.figure(figsize=(10,5))                                                    
    for journey in journeys_per_line.get_group(line_id).unique():
        times = df[journey].sort_values()
        distance = df.sort_values(journey)["Distance"]
        plt.plot(times, distance, linewidth=1)
    #plt.yticks(df["Distance"], df.index.levels[0])
    #plt.xticks(pd.DateRange(start = date, end = date + datetime.timedelta(days=1), freq="1h"),rotation=25)
    plt.grid()
    plt.show()


    #     line_time_agg = line_timetable.diff()
    #     selected_bus_stops_data = pd.merge(line_data, stops_df, how="left", right_on="number", left_on="BPUIC")
    #     selected_bus_stops_data = selected_bus_stops_data[["number", "designationOfficial", "lv95East", "lv95North", "ANKUNFTSZEIT", "AN_PROGNOSE", "ABFAHRTSZEIT", "AB_PROGNOSE"]]
    #     selected_bus_stops_data.rename(columns={
    #         "number": "Number",
    #         "designationOfficial": "Name",
    #         "ANKUNFTSZEIT": "ArriveePrevue",
    #         "AN_PROGNOSE": "ArriveeReel",
    #         "ABFAHRTSZEIT": "DepartPrevu",
    #         "AB_PROGNOSE": "DepartReel"
    #     }, inplace=True)
    #     selected_bus_stops_data["InZone"] = -1
    #     mask_extended = selected_bus_stops_data.Number.isin(stops_numbers).rolling(3, 1, center=True).max().astype(bool)
    #     selected_bus_stops_data.loc[mask_extended, "InZone"] = 0
    #     selected_bus_stops_data.loc[selected_bus_stops_data.Number.isin(stops_numbers), "InZone"] = 1
    #     line_data[line_name] = selected_bus_stops_data
    #     selected_bus_stops_data.to_csv(f"line_data/{line_name}.csv", header=line_id)
    # display(selected_bus_stops_data)

    """
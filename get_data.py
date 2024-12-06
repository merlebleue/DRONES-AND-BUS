import pandas as pd
import matplotlib.pyplot as plt
import datetime
import os
import urllib.request, urllib.error
from zipfile import ZipFile

import seaborn as sns
import seaborn.objects as so

DOWNLOAD_FOLDER = "dataset"
DATARAW_FOLDER = "DATA_raw"
EXPORTS_FOLDER = "exports"

def download_cache(url : str,
                   name: str,
                   date=datetime.datetime.today().date(),
                   zip = False,
                   download_folder = DOWNLOAD_FOLDER,
                   zip_folder = DATARAW_FOLDER):
    """
    Downloads a file from a specified URL, with support for date formatting and optional handling of zip archives. 
    If the file already exists locally, the cached version is returned. Iterates backward through dates to find the file.

    Args:
        url (str): The URL template containing a `{date}` placeholder for dynamic date substitution.
        name (str): The filename template, including a `{date}` placeholder and file extension.
        date (datetime.date or tuple, optional): The starting date for file search. Defaults to today's date. Tuple must be in `(year, month, day)` format.
        zip (bool, optional): Whether the file is in a zip archive. Defaults to False.
        download_folder (str, optional): Directory where the file will be saved. Defaults to `DOWNLOAD_FOLDER`.
        zip_folder (str, optional): Directory where zip files are saved. Defaults to `DATARAW_FOLDER`.

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
    
if __name__ == '__main__':

    # Define rectangle boundaries
    x_min, x_max = 2531838.30, 2533571.35
    y_min, y_max = 1152042.99, 1153095.62

    # Download didok data
    didok_url = "https://opentransportdata.swiss/fr/dataset/service-points-full/permalink"
    didok_file, date = download_cache(didok_url, "DIDOK_{date}.csv", zip=True)

    stops_df = pd.read_csv(didok_file, delimiter= ";")

    # Download timetable data:
    timetable_url = "https://opentransportdata.swiss/fr/dataset/istdaten/resource_permalink/{date}_istdaten.csv"
    timetable_file, date= download_cache(timetable_url, "Timetable_{date}.csv", date)
    timetable_df = pd.read_csv(timetable_file, delimiter= ";")

    # Filter stops
    # ------------

    # Only keep interesting columns
    stops_df = stops_df[['lv95East', 'lv95North', 'validFrom', 'validTo', 'number', "designationOfficial"]]
    # Filter based on validity (keep stops valid at the date)
    stops_df = stops_df[(stops_df.validFrom <= str(date)) & (stops_df.validTo > str(date))]
    stops_df.drop(columns=['validFrom', 'validTo'])
    # Filter based on position
    stops_numbers = stops_df[stops_df['lv95East'].between(x_min, x_max) & stops_df['lv95North'].between(y_min, y_max)]["number"]

    # Deduce lines from timetable information
    # ---------------------------------------
    # Select the journeys that passes through our stops
    journeys = timetable_df.FAHRT_BEZEICHNER[timetable_df.BPUIC.isin(stops_numbers)]
    filtered = timetable_df[timetable_df.FAHRT_BEZEICHNER.isin(journeys)]

    # Make a map LINIEN_ID -> LINIEN_TEXT (for later)
    line_names = filtered[["LINIEN_ID", "LINIEN_TEXT"]].drop_duplicates().set_index("LINIEN_ID").to_dict()["LINIEN_TEXT"]
    
    #Group by line
    journeys_per_line = filtered.groupby("LINIEN_ID")["FAHRT_BEZEICHNER"]

    grouped = filtered.groupby("LINIEN_ID")[["BPUIC", "FAHRT_BEZEICHNER", "ANKUNFTSZEIT", "AN_PROGNOSE", "ABFAHRTSZEIT", "AB_PROGNOSE"]]
    lines_data = {}
    for line_id, line_data in grouped:
        line_name = line_names[line_id]
        print(line_id, line_name)
        
        n_duplicates = line_data.duplicated(subset = ["BPUIC", "FAHRT_BEZEICHNER"], keep="last").sum()
        if n_duplicates > 0:
            print(f"Removing {n_duplicates} duplicates for line {line_name} ({line_id})")
            line_data = line_data.drop_duplicates(subset = ["BPUIC", "FAHRT_BEZEICHNER"], keep="last")

        # Refactor timetable data for the bus line
        # ----------------------------------------
        line_timetable = line_data.pivot(index="BPUIC", columns="FAHRT_BEZEICHNER").stack(level=0, future_stack=True).apply(pd.to_datetime, format="mixed")
        line_timetable = line_timetable.reindex(line_timetable.index.levels[1][::-1], level=1)
        # Reorder : First on the min time for the first bus, and then for the stops without data, on the second bus in decreasing order (assuming it goes in the other direction).
        line_timetable = line_timetable.reindex(line_timetable.groupby("BPUIC").min().sort_values(line_timetable.columns[[0,1]].to_list(), ascending = [True, False]).index, level=0)
        # Add stop names
        names = line_timetable.index.get_level_values(0).map(stops_df.set_index("number")["designationOfficial"]).rename("Name")
        line_timetable = line_timetable.set_index([names, line_timetable.index])

        # Compute distance based on one journey with the most stops
        # ---
        index = line_timetable.index
        line_timetable = pd.merge(line_timetable, stops_df[["lv95East", "lv95North"]], how="left", right_on=stops_df["number"], left_on="BPUIC").drop(columns = "BPUIC")
        line_timetable.index = index

        journey = line_data["FAHRT_BEZEICHNER"].dropna().mode()[0]
        journey_data = line_timetable[[journey, "lv95East", "lv95North"]].dropna().sort_values(journey)

        distance = ((journey_data[["lv95East", "lv95North"]].diff()**2).sum(axis=1)**0.5).cumsum()
        journey_data["distance"] = distance

        line_timetable["Distance"] = journey_data["distance"]
        # -------
        # TODO : Add "simple" export based on one journey
        # -------

        # Now iterate over other journeys to add to interpolate the distances
        missing_distances = line_timetable["Distance"].isna().sum()
        n_iter = 0
        while missing_distances > 0 and n_iter < 10:
            n_iter +=1
            # Find the journey with the most data on the stops for which we don't have the distance yet.
            journey = line_timetable.loc[line_timetable.Distance.isna()].count(axis=0).idxmax()

            journey_data = line_timetable[[journey, "lv95East", "lv95North", "Distance"]].dropna(subset=journey).sort_values(journey)

            distance = ((journey_data[["lv95East", "lv95North"]].diff()**2).sum(axis=1)**0.5).cumsum()

            index=distance.index
            distance = np.interp(distance, distance.loc[journey_data["Distance"].notna()], journey_data["Distance"].dropna())
            distance = pd.Series(distance, index=index)

            line_timetable["Distance"] = line_timetable["Distance"].fillna(distance)


            missing_distances = line_timetable["Distance"].isna().sum()
        if missing_distances > 0:
            print(f"Still {missing_distances} distances values missing for line {line_name} ({line_id})")
        
        # ---
        # Add distance to the dataframe

        # Separate between "planned" (to the minute) and "real" (to the sec) data
        planned = line_timetable.loc[(line_timetable.index.levels[0], line_timetable.index.levels[1], ["ANKUNFTSZEIT", "ABFAHRTSZEIT"]),]
        real = line_timetable.loc[(line_timetable.index.levels[0], line_timetable.index.levels[1], ["AN_PROGNOSE", "AB_PROGNOSE"]),]
        # Save
        os.makedirs(os.path.join(EXPORTS_FOLDER, str(line_name)), exist_ok=True)
        planned.to_csv(os.path.join(EXPORTS_FOLDER, str(line_name), f"{line_name}_planned.csv"), header=line_id)
        real.to_csv(os.path.join(EXPORTS_FOLDER, str(line_name), f"{line_name}_real.csv"), header=line_id)
    
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
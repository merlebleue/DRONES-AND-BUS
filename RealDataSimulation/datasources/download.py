import pandas as pd
import datetime
import os
import urllib.request
import urllib.error
from zipfile import ZipFile, BadZipFile

ZIP_FOLDER = os.path.join("data", "0_zip")
DOWNLOAD_FOLDER = os.path.join("data", "1_downloaded")
PRE_PROCESSED_FOLDER = "Pre-processed"
SIMPLE_FOLDER = "TP_Simple"

class DownloadManager:
    def __init__(self, zip_folder = ZIP_FOLDER, download_folder = DOWNLOAD_FOLDER):
        self.zip_folder = zip_folder
        self.download_folder = download_folder

    def get_path(self, filename):
        return os.path.join(self.download_folder, filename)
    
    def is_file_downloaded(self, filename):
        return os.path.isfile(self.get_path(filename))
    
    def get_latest_downloaded(self, name, date = datetime.datetime.today().date): 
        if not isinstance(date, datetime.date):
            date = datetime.date(*date)

        def generator(name, date):
            while date > datetime.date(1900, 1, 1):
                yield name.format(date=date), date
                date = date - datetime.timedelta(days=1)
        for try_name, date in generator(name, date):
            save_path = os.path.join(self.download_folder, try_name)
            if os.path.isfile(save_path):
                return save_path, date
    
    def get_latest_date(self, url, date = datetime.datetime.today().date, method="HEAD", verbose = 1):
        if not isinstance(date, datetime.date):
            date = datetime.date(*date)

        def generator(url, date):
            while date > datetime.date(1900, 1, 1):
                yield url.format(date=date), date
                date = date - datetime.timedelta(days=1)

        for try_url, date in generator(url, date):
            request = urllib.request.Request(try_url, method=method)
            try:
                with urllib.request.urlopen(request) as response:
                    if response.status == 200:  # URL exists
                        return date
            except urllib.error.HTTPError as e:
                print(e)
                if verbose >0 :
                    print(f"File not found at {try_url} ({e}). Current date : {date}. Trying an earlier date.")
                continue

    def download_with_cache(self,
                            url : str,
                            name: str,
                            zip = False,
                            zip_file_name = None,
                            method = "HEAD"):     
        save_path = os.path.join(self.download_folder, name)
        zip_save_path = ""
        if zip :
            n, extension = name.rsplit(".", 1)
            zip_save_path = os.path.join(self.zip_folder, n + "." + "zip")
            
        if os.path.isfile(save_path):
            return save_path
        
        if not (zip and os.path.isfile(zip_save_path)):
            request = urllib.request.Request(url, method=method)
            with urllib.request.urlopen(request) as response:
                if response.status == 200:  # URL exists
                    # Proceed to download the file
                    # Create directories if they don't exist
                    os.makedirs(os.path.dirname(zip_save_path if zip else save_path), exist_ok=True)
                    # Download and save the file
                    urllib.request.urlretrieve(url, zip_save_path if zip else save_path)
            
        if zip:
            try:
                with ZipFile(zip_save_path) as zip_file:
                    files = zip_file.namelist()
                    if zip_file_name is None:
                        files2 = [f for f in files if f.endswith(extension)]
                        if len(files2)>0:
                            file = files2[0]
                        else :
                            file = files[0]
                    else:
                        files3 = [f for f in files if f.endswith(zip_file_name)]
                        if len(files3) == 0:
                            print(f"No file '{zip_file_name}' found in archive. Found : {files}")
                        file = files3[0]
                    try:    
                        zip_file.extract(file, self.download_folder)
                    except KeyError as e:
                        print(files)
                        raise e
            except BadZipFile as e:
                print(zip_save_path)
                raise e


            os.rename(os.path.join(self.download_folder, file), save_path)

            # Clean any remaining empty folder in `self.download_folder`
            for item in os.listdir(self.download_folder):
                item_path = os.path.join(self.download_folder,item)
                if os.path.isdir(item_path):
                    if not os.listdir(item_path):
                        os.removedirs(item_path)
            
        return save_path
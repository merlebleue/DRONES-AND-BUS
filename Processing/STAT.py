import pandas as pd
import numpy as np

from get_data import download_with_cache
from Area import Area

class STAT:
    def __init__(self, df: pd.DataFrame, default_weights = None):
        self.df = df
        self.default_weights = default_weights
    
    def generate_n(self, n:int, precision_in_meter = 100, seed=None, weights = None, **kwargs):
        if weights is None:
            weights = self.default_weights

        sample = self.df.sample(
            n = n,
            replace = True,
            weights = weights,
            random_state=seed,
            **kwargs
        )

        sample_array = sample[["POSITION_X", "POSITION_Y"]].to_numpy(copy=True)

        if precision_in_meter < 100:
            n_precision = 100 // precision_in_meter
            rng = np.random.default_rng(seed=seed)
            precision_array = rng.integers(n_precision, size=sample_array.shape) * precision_in_meter
        else:
            precision_array = np.full_like(sample_array, 50)

        return sample_array + precision_array


class STATPOP (STAT):
    def __init__(self, area: Area, year = 2023, asset_number = 32686751):
        filename, _ = download_with_cache(
            f"https://www.bfs.admin.ch/bfsstatic/dam/assets/{asset_number}/master",
            f"STATPOP{year}.csv",
            zip=True,
            zip_file_name=f"STATPOP{year}.csv",
            method="GET"
        )

        df = pd.read_csv(filename, sep=";")

        # Keep only hectares inside the area (i.e. with at least one square meter inside the area)
        df = df.loc[area.is_inside_hecto(X = df["E_KOORD"], Y = df["N_KOORD"])]

        # Reframe the dataframe, keep only interesting columsn and rename them
        df = df[["E_KOORD", "N_KOORD", "BBTOT"]].rename(columns = {
            "E_KOORD": "POSITION_X",
            "N_KOORD": "POSITION_Y",
            "BBTOT": "POPULATION"
        })

        # Save the dataframe by running the super() call to __init__ :
        super().__init__(df.copy(deep=True), "POPULATION")

    def generate_per_population(self, prob_per_population: float,  *args, weights=None,**kwargs):
        if weights is None:
            weights = self.default_weights
        return self.generate_n(int(prob_per_population * self.df[weights]), *args, weights=weights, **kwargs)


class STATENT(STAT):
    def __init__(self, area: Area, year = 2022, asset_number = 32258837):
        filename, _ = download_with_cache(
            f"https://www.bfs.admin.ch/bfsstatic/dam/assets/{asset_number}/master",
            f"STATENT{year}.csv",
            zip=True,
            zip_file_name=f"STATENT_{year}.csv",
            method="GET"
        )

        df = pd.read_csv(filename, sep=";")
        
        # Keep only hectares inside the area (i.e. with at least one square meter inside the area)
        df = df.loc[area.is_inside_hecto(X = df["E_KOORD"], Y = df["N_KOORD"])]

        # Reframe the dataframe, keep only interesting columsn and rename them
        df = df[["E_KOORD", "N_KOORD", "B0847AS", "B0847EMP", "B0847VZA", "B0847KB1", "B0847KB2", "B0847KB3", "B0847KB4"]].rename(columns = {
            "E_KOORD": "POSITION_X",
            "N_KOORD": "POSITION_Y",
            "B0847AS" : "SHOPS",
            "B0847EMP" : "SHOPS_EMP",
            "B0847VZA" : "SHOPS_ETP",
            "B0847KB1" : "SHOPS_0",
            "B0847KB2" : "SHOPS_10",
            "B0847KB3" : "SHOPS_50",
            "B0847KB4" : "SHOPS_250",
        })

        # Save the dataframe by running the super() call to __init__ :
        super().__init__(df.copy(deep=True), "SHOPS")
    

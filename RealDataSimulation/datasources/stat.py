import pandas as pd
import numpy as np

from .get_data import download_with_cache
from ..Simulation import Area

class STAT:
    def __init__(self, area: Area, df: pd.DataFrame, default_weights = None):
        self.df = df
        self.default_weights = default_weights
        self.area = area

    def jitter(self, precision, n, seed=None):
        shape = (n, 2)
        if precision < 100:
            n_precision = 100 // precision
            rng = np.random.default_rng(seed=seed)
            precision_array = (rng.integers(n_precision, size=shape)+0.5) * precision
        else:
            precision_array = np.full(shape, 50)

        return precision_array

    def generate_n(self, n:int, precision_in_meter = 100, seed=None, weights = None, **kwargs):
        if weights is None:
            weights = self.default_weights

        sample = self.df.sample(
            n = 2*n, # 2*n because after we remove some points outside of the area
            replace = True,
            weights = weights,
            random_state=seed,
            **kwargs
        )

        sample_array = sample[["POSITION_X", "POSITION_Y"]].to_numpy("float", copy=True)

        sample_array += self.jitter(precision_in_meter, 2*n, seed)

        # Remove points outside of area
        X, Y = sample_array.T
        sample_array = sample_array[self.area.is_inside(X, Y)]

        # Take n first points
        sample_array = sample_array[:n]

        return sample_array

    def generate_per_proportion(self, proportion: float,  *args, weights=None,**kwargs):
        if weights is None:
            weights = self.default_weights
        return self.generate_n(int(proportion * self.df[weights].sum()), *args, weights=weights, **kwargs)

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
        super().__init__(area, df.copy(deep=True), default_weights="POPULATION")


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
        super().__init__(area, df.copy(deep=True), default_weights="SHOPS")

    def get_entreprises(self, precision_in_meter = 100, seed=None): 
        sample_df = self.df.loc[self.df.index.repeat(self.df.SHOPS)].reset_index(drop=True).copy(deep=True)
        
        sample_df[["SHOPS_EMP", "SHOPS_ETP"]] = sample_df[["SHOPS_EMP", "SHOPS_ETP"]].div(sample_df["SHOPS"], axis="index")
        columns_to_keep = ["POSITION_X", "POSITION_Y", "SHOPS_EMP", "SHOPS_ETP"]
        sample_df = sample_df[columns_to_keep]

        sample_df[["POSITION_X", "POSITION_Y"]] += self.jitter(precision_in_meter, len(sample_df))

        # Remove those that are not in the area
        sample_df = sample_df.loc[self.area.is_inside(sample_df.POSITION_X, sample_df.POSITION_Y)]

        return STAT(self.area, sample_df, "SHOPS_ETP")
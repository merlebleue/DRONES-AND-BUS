import pandas as pd
import numpy as np

import itertools
import random

from get_data import download_with_cache
from Area import Area

class STAT:
    def __init__(self, df: pd.DataFrame, default_weights = None):
        self.df = df
        self.default_weights = default_weights

    def get_points(self, attributes=[]):
        return self.df[["POSITION_X", "POSITION_Y"]+attributes].to_numpy()
    
    def generate_n(self, n:int, seed=None, weights = None, **kwargs):
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

        return sample_array
    
    def generate_per_population(self, prob_per_population: float,  *args, weights=None,**kwargs):
        if weights is None:
            weights = self.default_weights
        return self.generate_n(int(prob_per_population * self.df[weights].sum()), *args, weights=weights, **kwargs)


class STATPOP (STAT):
    def __init__(self, area: Area, precision_in_meter = 100, seed=None, year = 2023, asset_number = 32686751):
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
        
        #Set RELI as index
        df = df.set_index("RELI")

        # We will generate households, but first we need to compute how many households of each size to add
        households_per_size = df[[f"HP0{i+1}" for i in range(6)]].rename(columns=lambda i : int(i[-1]))
        # But 3 is a placeholder for 1,2,3 : we need to take that into account. First, let's replace it by a 1
        households_per_size = households_per_size.where(households_per_size!=3, 1)
        # Then, for each row, add the missing numbers:
        diff = df["BBTOT"] - (households_per_size*households_per_size.columns).sum(axis=1)
        df["BBTOT_corrected"] = df["BBTOT"].copy()
        def correct_households_numbers(row):
            difference = diff.loc[row.name]
            availlable = row[row==1].index.to_list()
            if len(availlable) > 0:
                condition = (lambda x : x<=3) if df.loc[row.name, "BBTOT"] == 3 else (lambda x : x==difference)
                combinaisons = [seq for i in range(difference//min(availlable), 0, -1)
                                for seq in itertools.combinations_with_replacement(availlable, i)
                                if condition(sum(seq))]
            
                combinaison = ()
                if len(combinaisons) > 0:
                    combinaison = random.choice(combinaisons)
                else :
                    if df.loc[row.name, "BBTOT"] == 3:
                        df.loc[row.name, "BBTOT_corrected"] = sum(availlable)
                    elif row[6] >0 :
                        while len(combinaisons)==0 and difference > 1:
                            difference -= 1
                            combinaisons = [seq for i in range(difference//min(availlable), 0, -1)
                                            for seq in itertools.combinations_with_replacement(availlable, i)
                                            if sum(seq) == difference]
                        if len(combinaisons)>0:
                            combinaison = random.choice(combinaisons)
                
                for i in combinaison:
                    row[i] += 1
            return row
        households_per_size.apply(correct_households_numbers, axis=1)

        # Generate households of 1, 2, 3, 4 ,5 and > 6 people :
        hp_dfs = []
        for i in range(6):
            hp_dfs.append(df.loc[df.index.repeat(households_per_size[i+1])])
            hp_dfs[i]["POPULATION"] = i+1
        sparse_df = pd.concat(hp_dfs, ignore_index=True)

        # Correct number of households : add the difference to households of > 6
        diff = df["BBTOT_corrected"] - (households_per_size*households_per_size.columns).sum(axis=1)
        to_add = diff/households_per_size[6]
        to_add_15 = to_add.where(to_add < 15, 0)
        to_add_big = to_add - to_add_15
        sparse_df.loc[sparse_df["POPULATION"] == 6,"POPULATION"] += to_add_15 / sparse_df.loc[sparse_df["POPULATION"]==6].groupby("RELI")["POPULATION"].count()
        sparse_df.loc
        # Add jittering to the households
        n_precision = 100 // precision_in_meter
        rng = np.random.default_rng(seed=seed)
        precision_array = (rng.integers(n_precision, size=(len(sparse_df), 2))+0.5) * precision_in_meter
        sparse_df[["E_KOORD", "N_KOORD"]] += precision_array

        # Refilter on the area
        sparse_df = sparse_df.loc[area.is_inside(X = sparse_df["E_KOORD"], Y = sparse_df["N_KOORD"])]

        # Reframe the dataframe, keep only interesting columns and rename them
        columns_mapping = {
            "E_KOORD": "POSITION_X",
            "N_KOORD": "POSITION_Y",
            "POPULATION" : "POPULATION"
        }
        sparse_df = sparse_df[["E_KOORD", "N_KOORD", "POPULATION"]].rename(columns = columns_mapping)

        # Save the dataframe by running the super() call to __init__ :
        super().__init__(sparse_df.copy(deep=True), default_weights="POPULATION")


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
    

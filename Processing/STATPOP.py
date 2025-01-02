import pandas as pd

from get_data import download_with_cache
from Area import Area

class STATPOP:
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
        
        # Save the total population
        self.total_pop = df["POPULATION"].sum()
    
        # Replace population by the density (i.e. the population over the total population)
        df["DENSITY"] = df["POPULATION"] / self.total_pop
        df.drop(columns=["POPULATION"], inplace=True)

        self.density_df = df.copy(deep=True)

    def generate_n(self, n:int, **kwargs):
        sample = self.density_df.sample(
            n = n,
            replace = True,
            weights = "DENSITY",
            **kwargs
        )

        return sample[["POSITION_X", "POSITION_Y"]].to_numpy(copy=True)

    def generate_per_population(self, prob_per_population: float, **kwargs):
        return self.generate_n(int(prob_per_population * self.total_pop), **kwargs)

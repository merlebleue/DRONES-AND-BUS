import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from ..Simulation import Simulation
from ..datasources.stat import STATENT, STATPOP

class TaskManager:
    def __init__(self, sim: Simulation, precision_in_meters = 1, random_seed = None):
        self.sim = sim
        self.precision_in_meters = precision_in_meters

        # Generate shops
        statent = STATENT(sim)
        self.shops = statent.get_entreprises(precision_in_meters, seed=random_seed) # Generate entreprises with precision (random)

        # Generate customers
        self.customers = STATPOP(sim)

    def get_tasks(self, n, random_seed = None):
        demand = self.customers.generate_n(n, self.precision_in_meters, seed=random_seed) # Here precision serves to generate random customers
        supply = self.shops.generate_n(n, seed=random_seed) # No need to add a precision here, already done in __init__

        tasks = pd.DataFrame(np.hstack((supply, demand)), columns=["pickup_x", "pickup_y", "delivery_x", "delivery_y"])
        tasks["distance"] = ((tasks["delivery_x"] - tasks["pickup_x"])**2 + (tasks["delivery_y"] - tasks["pickup_y"])**2)**0.5

        return tasks
    
    def plot(self, ax = plt, tasks: pd.DataFrame = None):
        if tasks is None:
            # Plot a visualisation of the shops, and densities of customers
            ax.scatter(data=self.customers.df, x="POSITION_X", y="POSITION_Y", c="POPULATION", marker=(4,0,0), s=50, cmap="Blues", alpha=0.5, vmin=-self.customers.df["POPULATION"].quantile(0.5),vmax=self.customers.df["POPULATION"].quantile(0.95), label="Customer density")
            ax.scatter(data=self.shops.df, x="POSITION_X", y="POSITION_Y", c="SHOPS_ETP", marker="*", cmap="Oranges", s=20, vmin=-10, alpha=0.5, label="Shops, by jobs")
        else:
            # Plot the tasks with arrows
            ax.quiver(
                tasks["pickup_x"],
                tasks["pickup_y"],
                tasks["delivery_x"] - tasks["pickup_x"],
                tasks["delivery_y"] - tasks["pickup_y"],
                angles='xy', scale_units='xy', scale=1.01, color="silver", width=0.005, alpha=0.5
            )
            ax.scatter(tasks["pickup_x"], tasks["pickup_y"], c="C1", s=10, label="Pickup points")
            ax.scatter(tasks["delivery_x"], tasks["delivery_y"], c="C0", s=10, label="Delivery points")
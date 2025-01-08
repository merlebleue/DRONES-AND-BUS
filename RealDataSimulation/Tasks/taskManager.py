import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from ..area import Area
from .geostat import STATENT, STATPOP
from ..PublicTransport.linedata import LineData

class TaskManager:
    def __init__(self, area: Area, precision_in_meters = 1, random_seed = None):
        self.area = area
        self.precision_in_meters = precision_in_meters

        # Generate shops
        statent = STATENT(area)
        self.shops = statent.get_entreprises(precision_in_meters, seed=random_seed) # Generate entreprises with precision (random)

        # Generate customers
        self.customers = STATPOP(area)

    def get_tasks(self, n, random_seed = None):
        demand = self.customers.generate_n(n, self.precision_in_meters, seed=random_seed) # Here precision serves to generate random customers
        supply = self.shops.generate_n(n, seed=random_seed) # No need to add a precision here, already done in __init__

        tasks = pd.DataFrame(np.hstack((supply, demand)), columns=["pickup_x", "pickup_y", "delivery_x", "delivery_y"])
        tasks["distance"] = ((tasks["delivery_x"] - tasks["pickup_x"])**2 + (tasks["delivery_y"] - tasks["pickup_y"])**2)**0.5

        return tasks
    
    def plot(self, ax = None, tasks: pd.DataFrame = None, line: LineData = None):
        if ax is None:
            fig, ax = self.area.plot()
            
        if tasks is None:
            # Plot a visualisation of the shops, and densities of customers
            ax.scatter(data=self.customers.df, x="POSITION_X", y="POSITION_Y", c="POPULATION", marker=(4,0,0), s=50, cmap="Blues", alpha=0.5, vmin=-self.customers.df["POPULATION"].quantile(0.5),vmax=self.customers.df["POPULATION"].quantile(0.95), label="Customer density")
            ax.scatter(data=self.shops.df, x="POSITION_X", y="POSITION_Y", c="SHOPS_ETP", marker="*", cmap="Oranges", s=20, vmin=-self.shops.df["SHOPS_ETP"].quantile(0.5),vmax=self.shops.df["SHOPS_ETP"].quantile(0.95), alpha=0.75, label="Shops, by jobs")
        elif line is None:
            # Plot the tasks with arrows
            ax.quiver(
                tasks["pickup_x"],
                tasks["pickup_y"],
                tasks["delivery_x"] - tasks["pickup_x"],
                tasks["delivery_y"] - tasks["pickup_y"],
                angles='xy', scale_units='xy', scale=1.01, color="grey", width=0.002, alpha=0.5
            )
            ax.scatter(tasks["pickup_x"], tasks["pickup_y"], c="C1", s=10, label="Pickup points")
            ax.scatter(tasks["delivery_x"], tasks["delivery_y"], c="C0", s=10, label="Delivery points")
        else:
            # Plot the tasks, but to stops, not directly
            tasks["pickup_stop_x"], tasks["pickup_stop_y"] = line.get_nearest_stops(tasks.pickup_x.values, tasks.pickup_y.values)
            tasks["delivery_stop_x"], tasks["delivery_stop_y"] = line.get_nearest_stops(tasks.delivery_x.values, tasks.delivery_y.values)
            
            tasks["distance_transport"] = ((tasks["pickup_stop_x"] - tasks["pickup_x"])**2 + (tasks["pickup_stop_y"] - tasks["pickup_y"])**2)**0.5 \
                                            + ((tasks["delivery_stop_x"] - tasks["delivery_x"])**2 + (tasks["delivery_stop_y"] - tasks["delivery_y"])**2)**0.5
            improved_mask = tasks["distance_transport"] < tasks["distance"]

            tasks_improved = tasks.loc[improved_mask]
            tasks_not_improved = tasks.loc[~improved_mask]
            
            ax.quiver(
                tasks_improved["pickup_x"],
                tasks_improved["pickup_y"],
                tasks_improved["pickup_stop_x"] - tasks_improved["pickup_x"],
                tasks_improved["pickup_stop_y"] - tasks_improved["pickup_y"],
                angles='xy', scale_units='xy', scale=1.01, color="C1", width=0.002, alpha=0.5
            )
            ax.quiver(
                tasks_improved["delivery_stop_x"],
                tasks_improved["delivery_stop_y"],
                tasks_improved["delivery_x"] - tasks_improved["delivery_stop_x"],
                tasks_improved["delivery_y"] - tasks_improved["delivery_stop_y"],
                angles='xy', scale_units='xy', scale=1.01, color="C0", width=0.002, alpha=0.5
            )
            ax.quiver(
                tasks_not_improved["pickup_x"],
                tasks_not_improved["pickup_y"],
                tasks_not_improved["delivery_x"] - tasks_not_improved["pickup_x"],
                tasks_not_improved["delivery_y"] - tasks_not_improved["pickup_y"],
                angles='xy', scale_units='xy', scale=1.01, color="k", width=0.002, alpha=0.5
            )
            ax.scatter(tasks["pickup_x"], tasks["pickup_y"], c="C1", s=10, label="Pickup points")
            ax.scatter(tasks["delivery_x"], tasks["delivery_y"], c="C0", s=10, label="Delivery points")


        ax.plot([self.area.x_min], [self.area.y_max], alpha=0)
        ax.plot([self.area.x_min], [self.area.y_max], alpha=0)
        return ax
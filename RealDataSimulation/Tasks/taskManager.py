import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from ..area import Area
from .geostat import STATENT, STATPOP
from ..PublicTransport.linedata import LineData, LinesData

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
    
    def compute_improvement(self, tasks: pd.DataFrame, lines : LineData | LinesData):
        tasks = tasks.copy(deep=True)
        try :
            len(lines)
        except TypeError:
            lines = LinesData(lines)
        pickup_stop_x = np.zeros((len(tasks), len(lines)))
        pickup_stop_y = np.zeros((len(tasks), len(lines)))
        delivery_stop_x = np.zeros((len(tasks), len(lines)))
        delivery_stop_y = np.zeros((len(tasks), len(lines)))
        distance_transport = np.full((len(tasks), len(lines)), np.inf)
        line_names = np.zeros(len(lines), dtype=object)
        for i, line in enumerate(lines.values()):
            line_names[i] = str(line.line_name)
            pickup_stop_x[:, i], pickup_stop_y[:, i] = line.get_nearest_stops(tasks.pickup_x.values, tasks.pickup_y.values)
            delivery_stop_x[:, i], delivery_stop_y[:, i] = line.get_nearest_stops(tasks.delivery_x.values, tasks.delivery_y.values)
        
            distance_transport[:, i] = ((pickup_stop_x[:, i] - tasks["pickup_x"])**2 + (pickup_stop_y[:, i] - tasks["pickup_y"])**2)**0.5 \
                                        + ((delivery_stop_x[:, i] - tasks["delivery_x"])**2 + (delivery_stop_y[:, i] - tasks["delivery_y"])**2)**0.5
        idx = np.argmin(distance_transport, axis= 1)
        tasks["pickup_stop_x"] = pickup_stop_x[np.arange(len(tasks)), idx]
        tasks["pickup_stop_y"] = pickup_stop_y[np.arange(len(tasks)), idx]
        tasks["delivery_stop_x"] = delivery_stop_x[np.arange(len(tasks)), idx]
        tasks["delivery_stop_y"] = delivery_stop_y[np.arange(len(tasks)), idx]
        tasks["distance_transport"] = distance_transport[np.arange(len(tasks)), idx]
        
        tasks["improvement"] = tasks["distance"] - tasks["distance_transport"]
        tasks["line"] = line_names[idx]
        tasks["line"] = tasks["line"].where(tasks["improvement"] > 0, "Direct")

        return tasks

            
    
    def plot(self, ax = None, tasks: pd.DataFrame = None, with_lines = False):
        if ax is None:
            fig, ax = self.area.plot()
            
        if tasks is None:
            # Plot a visualisation of the shops, and densities of customers
            ax.scatter(data=self.customers.df, x="POSITION_X", y="POSITION_Y", c="POPULATION", marker=(4,0,0), s=50, cmap="Blues", alpha=0.5, vmin=-self.customers.df["POPULATION"].quantile(0.5),vmax=self.customers.df["POPULATION"].quantile(0.95), label="Customer density")
            ax.scatter(data=self.shops.df, x="POSITION_X", y="POSITION_Y", c="SHOPS_ETP", marker="*", cmap="Oranges", s=20, vmin=-self.shops.df["SHOPS_ETP"].quantile(0.5),vmax=self.shops.df["SHOPS_ETP"].quantile(0.95), alpha=0.75, label="Shops, by jobs")
        elif not with_lines:
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
            if "improvement" not in tasks:
                raise ValueError("with_lines is True but improvement has not been computed : use .compute_improvement()")
            improved_mask = tasks["improvement"] > 0

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
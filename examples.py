# %%
import matplotlib.pyplot as plt

# %% [markdown]
# # Examples

# %%
import RealDataSimulation as rds 
from RealDataSimulation import Area, TransportData, TaskManager, LinesData, LineData

# %% [markdown]
# ## Case study for line 705

# %%
tp705 = TransportData("705")
tp705.search_lines("705")

# %%
tp705.filter_data(line_id = "85:764:705", return_data=False)

# %%
l705 = tp705.generate_timetable()
area705 = l705.get_area(margin=500)

# %%
area705.plot(l705, margin=0.1)
plt.title("Bus line 705")
plt.savefig("fig/l705_area.png")

# %%
tm = TaskManager(area705, random_seed=2025)
area705.plot(tm, l705)
plt.title("Population density and shops generated around bus line 705")
plt.savefig("fig/l705_densities.png")

# %%
tasks = tm.get_tasks(100)
area705.plot((tm, tasks), l705, margin=0.05)
plt.legend(loc="upper left", shadow=True, fancybox=False)
plt.title("Tasks generated around bus line 705")
plt.savefig("fig/l705_tasks.png")

# %%
tasks = tm.compute_improvement(tasks, l705)
area705.plot((tm, tasks, True), l705, margin=0.05)
plt.legend(loc="upper left", shadow=True, fancybox=False)
plt.title("Tasks around bus line 705, using the bus line")
plt.savefig("fig/l705_tasks_bus.png")

improvement_705 = tasks["improvement"].values

# %%
_ = area705.plot((tm, tasks, True), l705, margin=0.05, plot_axes=False)
plt.savefig("fig/l705_clean.png")


# %% [markdown]
# ## Lausanne Area

# %%
lausanne = Area(2529839, 2542447, 1149986, 1157628)
lausanne.plot(margin=0.05)
plt.title("Lausanne area")
plt.savefig("fig/laus_area.png")

# %%
tl = TransportData("Lausanne", lausanne, date=(2025,1,7))
tl.filter_data(return_data=False)

# %%
lausanne_lines = tl.get_lines_data(modes=("bus", "metro"))

# %%
lausanne_lines

# %%
lausanne_lines[1].plot()
plt.savefig("fig/laus_l1.png")

# %%
_, ax = lausanne.plot((lausanne_lines, True), margin=0.05)
ax.get_legend().remove()
plt.title("Bus and metro lines around Lausanne")
plt.savefig("fig/laus_transport.png")

# %%
tm = TaskManager(lausanne, random_seed = 2025)
lausanne.plot(tm,(lausanne_lines, {"alpha": 0.5}), margin=0.05)
plt.title("Population density and shops generated in Lausanne area")
plt.savefig("fig/laus_density.png")

# %%
tasks = tm.get_tasks(25)
lausanne.plot((tm, tasks), (lausanne_lines, {"zorder": -1, "alpha": 0.05}), margin=0.05)
plt.legend(loc="lower left", shadow=True, fancybox=False)
plt.savefig("fig/laus_tasks25.png")

# %%
tasks = tm.compute_improvement(tasks, lausanne_lines)
used_lines = LinesData(*[lausanne_lines[l] for l in tasks.line.unique() if l != "Direct"])
print(used_lines)
lausanne.plot((tm, tasks, True), (lausanne_lines, {"zorder": -1, "alpha": 0.25, "c" : "grey"}), (used_lines, {"c" : "C2", "label": "Lines used"}), margin=0.05)
plt.legend(loc="lower left", shadow=True, fancybox=False)
plt.savefig("fig/laus_tasks25_bus.png")

# %%
tasks = tm.get_tasks(100)
tasks = tm.compute_improvement(tasks, lausanne_lines)
used_lines = LinesData(*[lausanne_lines[l] for l in tasks.line.unique() if l != "Direct"])
print(used_lines)
lausanne.plot((tm, tasks, True), (lausanne_lines, {"zorder": -1, "alpha": 0.25, "c" : "grey"}), (used_lines, {"c" : "C2", "label": "Lines used"}), margin=0.05, plot_axes=False)
plt.savefig("fig/laus_clean.png")

# %%
tasks = tm.get_tasks(100)
lausanne.plot((tm, tasks), (lausanne_lines, {"zorder": -1, "alpha": 0.05}), margin=0.05)
plt.legend(loc="lower left", shadow=True, fancybox=False)
plt.title("Tasks generated in Lausanne area")
plt.savefig("fig/laus_tasks100.png")

# %%
tasks = tm.compute_improvement(tasks, lausanne_lines)
used_lines = LinesData(*[lausanne_lines[l] for l in tasks.line.unique() if l != "Direct"])
print(used_lines)
lausanne.plot((tm, tasks, True), (lausanne_lines, {"zorder": -1, "alpha": 0.25, "c" : "grey"}), (used_lines, {"c" : "C2", "label": "Lines used"}), margin=0.05)
plt.legend(loc="lower left", shadow=True, fancybox=False)
plt.title("Tasks in Lausanne, using the bus and metro lines")
plt.savefig("fig/laus_tasks100_bus.png")

# %%
tasks = tm.get_tasks(1000)
lausanne.plot((tm, tasks), (lausanne_lines, {"zorder": -1, "alpha": 0.05}), margin=0.05)
plt.legend(loc="lower left", shadow=True, fancybox=False)
plt.title("Tasks generated in Lausanne area (1000)")
plt.savefig("fig/laus_tasks1000.png")

# %%
tasks = tm.compute_improvement(tasks, lausanne_lines)
used_lines = LinesData(*[lausanne_lines[l] for l in tasks.line.unique() if l != "Direct"])
print(used_lines)
lausanne.plot((tm, tasks, True), (lausanne_lines, {"zorder": -1, "alpha": 0.25, "c" : "grey"}), (used_lines, {"c" : "C2", "label": "Lines used"}), margin=0.05)
plt.legend(loc="lower left", shadow=True, fancybox=False)
plt.title("Tasks in Lausanne, using the bus and metro lines")
plt.savefig("fig/laus_tasks1000_bus.png")

improvement_lausanne = tasks["improvement"].values

# %% [markdown]
# ## Synthetic comparison

# %%
import pandas as pd

# %%
tasks = pd.read_csv("synthetic_tasks.csv", index_col=0)
tasks

# %%
bus_stops_df = pd.read_csv("synthetic_lines.csv", index_col=0)
bus_stops_df

# %%
bus_stops_df["Route_A"] = True
bus_stops_df["STOP_NAME"] = bus_stops_df.index.map("Stop{}".format)
bus_stops_df["STOP_NUMBER"] = bus_stops_df.index
bus_stops_df = bus_stops_df.set_index(["STOP_NAME"], drop=True)
bus_stops_df= bus_stops_df.rename(columns=lambda i : "POSITION_X" if i == "x" else "POSITION_Y" if i == "y" else i)
stops_1 = bus_stops_df.loc[bus_stops_df.line == "Line 1"].drop(columns="line")
stops_2 = bus_stops_df.loc[bus_stops_df.line == "Line 2"].drop(columns="line")
stops_1, stops_2

# %%
routes = pd.DataFrame(bus_stops_df["Route_A"]).T
route_1, route_2 = routes[stops_1.index], routes[stops_2.index]
route_1["Count"], route_2["Count"] = 10, 10

# %%
bus_lines = LinesData(LineData("1", "Line 1", "/synthetic/", -1, stops_1, route_1, -1), LineData("2", "Line 2", "/synthetic/", -2, stops_2, route_2, -2))

# %%
tm_synthetic= TaskManager(Area(0, 80, 0, 80))

# %%
plt.figure()
ax = plt.gca()
tm_synthetic.plot(ax, tasks=tasks)
bus_lines.plot(ax)
plt.legend(loc = "upper left")
plt.title("Synthetic bus lines and tasks")
plt.savefig("fig/synthetic_tasks.png")

# %%
tasks = tm_synthetic.compute_improvement(tasks, bus_lines)
ax = plt.gca()
tm_synthetic.plot(ax, tasks, True)
bus_lines.plot(ax)
plt.legend(loc = "upper left")
plt.title("Synthetic bus lines and tasks, using bus lines")
plt.savefig("fig/synthetic_tasks_bus.png")

improvement_synthetic = tasks["improvement"].values

# %% [markdown]
# ## Compare improvement

# %%
import seaborn as sns
import seaborn.objects as so

# %%
improvement_synthetic = pd.DataFrame(improvement_synthetic, columns=["Improvement"])
improvement_synthetic["Case"] = "Synthetic"

improvement_705 = pd.DataFrame(improvement_705, columns=["Improvement"])
improvement_705["Case"] = "705"

improvement_lausanne = pd.DataFrame(improvement_lausanne, columns=["Improvement"])
improvement_lausanne["Case"] = "Lausanne"

data = pd.concat((improvement_synthetic, improvement_705, improvement_lausanne))

data["has_improved"] = data["Improvement"]  > 0

data["Improvement_normalised"] = data.groupby("Case")["Improvement"].transform(lambda x: x / x.max())

# %%
data

# %%
improvement_percentage = data.groupby("Case")["has_improved"].mean()
sns.barplot(data=data, x="Case", y="has_improved", errorbar=None)
plt.title("Proportion of tasks using bus lines")
plt.ylabel("Improvement")
plt.savefig("fig/analyse_proportion.png")

# %%
plt.figure(figsize=(4,6))
sns.set_theme(style= "ticks")
sns.boxplot(data=data, x="Case", y="Improvement_normalised", ax= plt.gca())
plt.hlines([0], xmin=[-0.5], xmax=[2.5], colors="k")
plt.ylabel("Improvement (normalised)")
plt.title("Improvement, in terms of drone distance")
plt.savefig("fig/analyse_improvement.png")

# %%




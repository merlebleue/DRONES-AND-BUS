# Objectives of the project

## Project definition

> Adaptation of real-life public transport and socioeconomical data for incorporation into a simulation project.

### Main objectives
- Generate the bus data from real data and simplify it for select bus lines, in a format compatible with the current simulation(`bus_lines`, `bus_stations_df`).
  > **Deliverables :** `bus_lines`, `bus_stations_df`
- Generate a list of drone tasks based on :
  - Actual position of commerces
  - Habitation density / habitation 
  > **Deliverables :**  `task_df`
- "Combine the data" --> incorporate in the simulation


### Secondary (facultative) objectives
- Download and adapt timetable data to allow a future timetable-aware implementation.
- **Visualisation of a bus line on a time-space diagram.**
  - Possible uses / extension : consideration of which bus does which circulation
- Progressive adaptation of the `BusSystem` python class that simulates busses to include real life time considerations, with same endpoints as the current class.
  - Either variable speed OR average speed for entire cycle
  - Including adaptation of visualisation of the busses in a time-space diagram.
- Develop a comprehensive and robust python framework for accessing and processing the data availlable


## Personal learning objectives
- Familiarise myself with the data availlable about the transport in switzerland.
- Learn to solve difficuties that could arise from it : difference in encoding, ability to determine direction, ...

## Final deliverables
- Presentation for Nikolas : *Undefined* (first week of January we hope (06.01 - 10.01)) - 15 min Presentation - 15 min Q&A previous years
- Report : *Undefined* Introduction - Methodology - Results - Conclusion
- Code as well


_

_

_


# Current TODO

- Do Main Objective #1
- Update Bus System class to include visualisation
- Try Main Objective #2
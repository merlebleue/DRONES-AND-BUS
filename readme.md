# Real Data for a Drone-and-Bus Delivery System Scenario

A project done with EPFL's [LUTS laboratory](luts.epfl.ch) under the supervision of Minru Wang and Prof Geroliminis.

In this project, we manipulated real data about public transport lines in Switzerland, as well as created pairs of coordinates that associate (fictitious) shops and customers based on OFS public geostat (STATENT and STATPOP) data, for a drone-and-bus delivery system scenario. The code however can surely be used for other extends.

It implements a robust download manager that checks whether a file has already been downloaded and can also unzip files as well as check the latest available data (for example, with public transport data).

The public transport data comes from [opentransportdata.swiss](opentransportdata.swiss), in particular the ['Actual Data'](https://opentransportdata.swiss/en/dataset/istdaten) and the ['Service points'](https://opentransportdata.swiss/en/dataset/service-points-full) services.

## Repository

This repository countains :
- The final report of the project : [report.pdf](report.pdf)
- The code for generating the examples of the project : [examples.ipynb](examples.ipynb)
- A demo notebook for the different classes created in this project : [demo.ipynb](demo.ipynb)
- Output data examples for transport lines around Lausanne : [transport_data](transport_data)
- The code : [code_files](code_files)
- The latex of the report, and the related figures : [latex](latex) & [fig](fig)
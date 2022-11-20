# GEO4300_project
This readme contains description of files structure for project "Tidal characteristics along the Norwegian coast"  
## folders structrue ##
### harmonic analysis ###
The folder harmonic analysis contains the main jupyter notebook for the calculations and plotting in this project. It also contains two python modules used in the calculations and an Excel spreadsheet with information on tidal constituents.
### wave_height_distributions ###  
Folder wave_height_distributions contains 1 jupyter notebook and 1 gzipped data for 2021 calculating tidal wave height, its means and distributions for 4 chosen stations.
### reading data ###
Contains jupyter notebooks with example requests to get data from kartverket REST API.
Jupyter notebooks here are of educational value to download data and access them from the level of panda dataframe.
They were not direclty used in the project.
### reading_data/influx_db/ ###
The file: server_download_and_store.py contains all code for automatic download of data from kartverket API and store them in time series databas (influxDB), that we create to feed data to the dashboard.

kartverket api --------(REST API reqest) -----------> (INFLUX DATABASE) --------------> (GRAFANA DASHBOARD)

The main dashboard is avilable at address: 
http://bolge.vps.webdock.cloud:3000/d/1FHI8WnVz/tides?orgId=1
### reading_data/influx_db/ ###
contains python files to download data from kartverket and store them in influx
### reading_data/grafana_dashboard/ ###
contains dashboard file in form of json file


## project language ##
python 3.x
## major libraries ##
pandas 1.4.4  
numpy 1.21.6  
matplotlib 3.1.0  
scipy 1.6.2   
requests 2.22.0   
statmodels 0.13.2  
influxdb 5.3.1    

influx version 1.8  
https://docs.influxdata.com/influxdb/v1.8/  
grafana 9.2.3  
https://grafana.com/docs/grafana/latest/  



#Anna Wojciechowska, Oslo, November 2022

import pandas as pd
from datetime import datetime as dt
import time

import traceback
import json
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
import requests
import io

from influx_tools import *

import argparse




def store_measurement(df):
    measurement = 'tide_level'
    for i, row in df.iterrows():
        tagDict = {}
        #columns = ['timestamp', 'level', 'site', 'lat', 'lon', 'ref']
        tagDict['siteName'] = row['site']
        tagDict['referenceLevel'] = row['ref']
        fieldDict = {}
        fieldDict['level'] = row['level']
 
        insert_new_point(INFLUXDB_CLIENT, measurement, tagDict, fieldDict, LOGGER, row['timestamp'])
        
def extract_header_and_data(lines):
    header, data = [], 'timestamp  level\n'
    for line in lines:
        if line.startswith("#"):
            header.append(line)
        else:
            data += line + '\n'
    #pack header as dictionary
    header_dict = {}
    for line in header:
        if line.startswith('#'):
            line = line.strip('#')
            res = line.split(':')
            header_dict[res[0].strip()] = res[1].strip() 
    return header_dict, data

def parse_response(res):
    response_text = res.text.split('\r\n')
    header, data = extract_header_and_data(response_text)
    df = pd.read_csv(io.StringIO(data), sep='\s+', usecols = ['timestamp', 'level'])
    df['site'] = header['Site name']
    df['lat'] = header['Latitude']
    df['lon'] = header['Longitude']
    df['ref'] = header['Reference level']
    df['level'] = df['level'].fillna(0)
    df['timestamp'] = df['timestamp'].apply(lambda x: x.split('+')[0])
    df['timestamp'] = df['timestamp'].apply(lambda x: dt.strptime(x,"%Y-%m-%dT%H:%M:%S"))
    return df



basename = get_basename() + '.log'
log_dir = 'logs'
LOGGER = set_up_log(log_dir, basename)
LOGGER.info("start script")


INFLUXDB_AUTH = json.load(open(os.path.join(os.getcwd(), 'influxdb_credentials')))


INFLUXDB_CLIENT = InfluxDBClient(
    host='localhost', 
    username= INFLUXDB_AUTH['username'],
    password= INFLUXDB_AUTH['password'],
    port=8086,
    database='tide_info')


parser = argparse.ArgumentParser()
parser.add_argument('-d', '--dry-run', action='store_true', 
    help="does not write to database, just do dry rane")
args = parser.parse_args()

if args.dry_run:
    print("dry run")
else:
    print("normal run")
LOGGER.info("end script")




tide_stations = pd.read_csv('data/tide_stations_loc.csv')
start_date = '2022-01-01'
end_date = '2022-10-03'
data_type = 'OBS'
#url= url_template.format(lat, lon, datatype, place, start_date, end_date)
url_template = 'http://api.sehavniva.no/tideapi.php?tide_request=locationdata&lat={}&lon={}\
&datatype={}\
&file=txt&lang=en&place={}\
&dst=1&refcode=CD&fromtime={}&totime={}&interval=10'

urls = []

for i, row in tide_stations.iterrows():
    url = url_template.format(row['latitude'], row['longitude'], data_type, row['code'], start_date, end_date)
    urls.append(url)
    
columns = ['timestamp', 'level', 'site', 'lat', 'lon', 'ref']
df = pd.DataFrame(columns=columns)
i = 0
for url in urls:
    station_code = tide_stations['code'].iloc[i]
    i += 1
    LOGGER.info("getting data from: ".format(station_code))
    res = requests.get(url)
    if res.status_code != 200:
        print("ups, rquest error for ", url)
    else:
        temp_df = parse_response(res)
        df = pd.concat([df, temp_df])
df.reset_index(drop=True, inplace=True)

if not args.dry_run:
    store_measurement(df)

LOGGER.info("end  script")

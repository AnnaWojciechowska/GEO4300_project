#Anna Wojciechowska, Oslo, November 2022

import pandas as pd
from datetime import datetime as dt
from datetime import timedelta
import json
from influxdb import InfluxDBClient
import requests
import io
import os

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
        # 2 decimal places, float is safe
        fieldDict['level'] = float(row['level'])
 
        insert_new_point(INFLUXDB_CLIENT, measurement, tagDict, fieldDict, LOGGER, row['timestamp'])

def store_missing_data_info(df):
    measurement = 'missing_data'
    for i, row in df.iterrows():
        tagDict = {}
        #columns = ['timestamp', 'count_no', 'site', 'ref']
        tagDict['siteName'] = row['site']
        tagDict['referenceLevel'] = row['ref']
        fieldDict = {}
        fieldDict['count_no'] = 1
 
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

def parse_response(res, LOGGER, logs_dir):
    #res (ponse) is pandas dataframe
    correct_check = True
    response_text = res.text.split('\r\n')
    header, data = extract_header_and_data(response_text)
    df = pd.read_csv(io.StringIO(data), sep='\s+', usecols = ['timestamp', 'level'])
    df['site'] = header['Site name']
    df['lat'] = header['Latitude']
    df['lon'] = header['Longitude']
    df['ref'] = header['Reference level']
    # data is kept in  UTS, timezone shift can be discarrded
    df['timestamp'] = df['timestamp'].apply(lambda x: x.split('+')[0])
    df['timestamp'] = df['timestamp'].apply(lambda x: dt.strptime(x,"%Y-%m-%dT%H:%M:%S"))
  
    # dealing with nan values:
    # we extract them from main df and keep in seprate df
    nan_df = df[df['level'].isna()]

    if nan_df.shape[0] > 0:
        df.drop(nan_df.index.to_list(), inplace=True)
        nan_df.reset_index(inplace=True)

        # choose what is better way to handle: 
        nan_csv_filenamane = os.path.join(logs_dir, df.iloc[0]['site'] + ".csv")
        nan_df.to_csv(nan_csv_filenamane, index=False)
        LOGGER.info("Nan values: {}".format(nan_df.shape[0]))
        LOGGER.info(nan_df.to_csv())

    return df, nan_df



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

#automatic updates:
time_hour_ago = dt.utcnow() - timedelta(hours=1)
start_time = time_hour_ago.strftime('%Y-%m-%dT%H:00:00')
end_time = time_hour_ago.strftime('%Y-%m-%dT%H:50:00')

#tutaj remove me
#start_time = '2022-01-01T00:00:00'
#end_time = '2022-01-01T01:00:00'

data_type = 'OBS'
#url= url_template.format(lat, lon, datatype, place, start_date, end_date)
# we are using timezone=0 wich is UTC time
url_template = 'http://api.sehavniva.no/tideapi.php?tide_request=locationdata&lat={}&lon={}\
&datatype={}\
&file=txt&lang=en&place={}\
&dst=1&refcode=CD&fromtime={}&totime={}&tzone=0&interval=10'

urls = []

for i, row in tide_stations.iterrows():
    url = url_template.format(row['latitude'], row['longitude'], data_type, row['code'], start_time, end_time)
    #print(url)
    urls.append(url)
    
columns = ['timestamp', 'level', 'site', 'lat', 'lon', 'ref']
df = pd.DataFrame(columns=columns)
i = 0
for url in urls:
    station_code = tide_stations['code'].iloc[i]
    print("processing: {} {}".format(i, station_code))
    i += 1
    LOGGER.info("getting data from: {}".format(station_code))
    res = requests.get(url)
    if res.status_code != 200:
        print("ups, rquest error for ", url)
    else:
        data_df, missing_df = parse_response(res, LOGGER, log_dir)
       
        if not args.dry_run: 
            store_measurement(data_df)
            store_missing_data_info(missing_df)
        #df = pd.concat([df, temp_df])
#df.reset_index(drop=True, inplace=True)

LOGGER.info("end  script")

import pandas as pd
from datetime import datetime as dt
import logging
import time

import traceback
import json
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
import requests
import io

"""function inserting a datapoint to a measurement"""
def insert_new_point_with_timestamp(client, measurement, tag_dict, field_dict, timestamp):
    result = {
        'measurement': measurement,
        'tags': tag_dict,
        'fields': field_dict,
        # if time is not specified then the default timestamp is used
        'time': timestamp,
    }
    
    exceptions_counter = 0
    while True:
        try:
            client.write_points([result], time_precision="ms")
            break
        except (InfluxDBClientError, InfluxDBServerError):
            exceptions_counter += 1
            LOGGER.info('Unexpected error: %s', str(exceptions_counter))
            LOGGER.info(traceback.format_exc())
            # in case of 503 Service Unavailable error the service usually
            # restart itself - it takes about 4 minutes
            time.sleep(4 * 60)
        except (ValueError):
            exceptions_counter += 1
            # most likely just a connection error, just retry
            LOGGER.info('Unexpected error: %s', str(exceptions_counter))
            LOGGER.info(traceback.format_exc())
        except Exception:
            exceptions_counter += 1
            LOGGER.exception('Unexpected exception, "just" fix the script.')
        if exceptions_counter > 20:
            LOGGER.info('Fail to write after 20 trials. Giving up ')
            break

def store_measurement(df):
    measurement = 'tide_level'
    for i, row in df.iterrows():
        tagDict = {}
        #columns = ['timestamp', 'level', 'site', 'lat', 'lon', 'ref']
        tagDict['siteName'] = row['site']
        #tagDict['lat'] = row['lat']
        #tagDict['lon'] = row['lon']
        tagDict['referenceLevel'] = row['ref']
        fieldDict = {}
        fieldDict['level'] = row['level']
        #fieldDict['lat'] = row['lat']
        #fieldDict['lon'] = row['lon']

        insert_new_point_with_timestamp(influx_client, measurement, tagDict, fieldDict, row['timestamp'])
        
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

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
FILE_HANDLER = logging.FileHandler('./tides_to_influx.log')
FILE_HANDLER.setFormatter(logging.Formatter(fmt='%(asctime)s [%(levelname)s] %(message)s', datefmt='%a, %d %b %Y %H:%M:%S'))
LOGGER = logging.getLogger()
LOGGER.addHandler(FILE_HANDLER)
LOGGER.setLevel(logging.INFO)


LOGGER.info("start script")
LOGGER.info(dt.now())


influx_client = InfluxDBClient(
    host='localhost', 
    username= 'writer',
    password='test',
    port=8086,
    database='tide_info')

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


store_measurement(df)

LOGGER.info("end  script")
LOGGER.info(dt.now())


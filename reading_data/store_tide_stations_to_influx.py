import pandas as pd
from datetime import datetime as dt
import logging
import time

import traceback
import json
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError

"""function inserting a datapoint to a measurement"""
def insert_new_point_with_timestamp(client, measurement, tag_dict, field_dict, *timestamp):
    result = {
        'measurement': measurement,
        'tags': tag_dict,
        'fields': field_dict,
    }
    # if time is not specified  at writing time, the current datetime is used
    if timestamp:
        result['time'] = timestamp
    
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

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
FILE_HANDLER = logging.FileHandler('./tides_to_influx.log')
FILE_HANDLER.setFormatter(logging.Formatter(fmt='%(asctime)s [%(levelname)s] %(message)s', datefmt='%a, %d %b %Y %H:%M:%S'))
LOGGER = logging.getLogger()
LOGGER.addHandler(FILE_HANDLER)
LOGGER.setLevel(logging.INFO)


INFLUX_CLIENT = InfluxDBClient(
    host='localhost', 
    username= 'writer',
    password='test',
    port=8086,
    database='tide_info')

tdf = pd.read_table("data/tide_stations_loc.csv", sep = ',')

string_cols = ['code','type']
for i, row in tdf.iterrows():
    tag_dict = {}
    for col in string_cols:
        tag_dict[col] = row[col]
    # for some reason name seems to be keyword in influx
    tag_dict['station_name'] = row['name']
    field_dict = {}
    field_dict['lat'] = float(row['latitude'])
    field_dict['lon'] = float(row['longitude'])
    insert_new_point_with_timestamp(INFLUX_CLIENT, "tide_stations", tag_dict, field_dict)
    print("inserted")

print("done")

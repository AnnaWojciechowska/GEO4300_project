#Anna Wojciechowska, Oslo, October 2022
#I prefer to keep this file than the whole library
# here are some of the influx functions I often use
#version 0.1

from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
import time
import traceback
import os, sys

import logging



def set_up_log(log_dir, log_filename):
    script_run_dir = os.getcwd()
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    #check if log dir exist, create both log dir and log file if necessary
    if not os.path.isdir(os.path.join(script_run_dir, log_dir)):
        os.mkdir(os.path.join(script_run_dir, log_dir))
    file_handler = logging.FileHandler(os.path.join(script_run_dir, log_dir, log_filename), mode='a')
    file_handler.setFormatter(logging.Formatter(fmt='%(asctime)s [%(levelname)s] %(message)s', datefmt='%a, %d %b %Y %H:%M:%S'))
    logger = logging.getLogger()
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)
    return logger

def get_basename():
    script_path = sys.argv[0]
    path_elems = script_path.split('/')
    script_name = path_elems[len(path_elems) - 1]
    res = script_name.split('.py')
    return res[0]



"""function inserting a datapoint to a measurement"""
def insert_new_point(CLIENT,  measurement, tag_dict, field_dict, LOGGER = None, timestamp = None):
    result = {
        'measurement': measurement,
        'tags': tag_dict,
        'fields': field_dict,
    }
    # if time is not specified  at writing time, default date is used
    if timestamp:
        result['time'] = timestamp
    

    exceptions_counter = 0
    while True:
        try:
            CLIENT.write_points([result], time_precision="ms")
            break
        except (InfluxDBClientError, InfluxDBServerError):
            exceptions_counter += 1
            if (LOGGER):
                LOGGER.info('Unexpected error: %s', str(exceptions_counter))
                LOGGER.info(traceback.format_exc())
            # in case of 503 Service Unavailable error the service usually
            # restart itself - it takes about 4 minutes
            time.sleep(4 * 60)
        except (ValueError):
            exceptions_counter += 1
            # most likely just a connection error, just retry
            if (LOGGER):
                LOGGER.info('Unexpected error: %s', str(exceptions_counter))
                LOGGER.info(traceback.format_exc())
        except Exception:
            exceptions_counter += 1
            if (LOGGER):
                LOGGER.exception('Unexpected exception, "just" fix the script.')
        if exceptions_counter > 20:
            if (LOGGER):
                LOGGER.info('Fail to write after 20 trials. Giving up ')
            break

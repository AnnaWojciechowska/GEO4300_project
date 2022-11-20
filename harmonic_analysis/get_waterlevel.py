"""
Documentation
"""

import requests
import pandas as pd
import io  
from datetime import datetime as dt

def extract_header_and_data(lines):
    
    header = []
    data = 'Timestamp  Level\n'
    for line in lines:
        if line.startswith("#"):
            # Header lines start with a '#'.
            header.append(line)
        else:
            # The rest of the lines are the actual water level data.
            data += line + '\n'
    return header, data


def download_waterlevel(
    start_date, end_date, station_code, station_lat, station_lon, interval=10):
    """ Download water level data from the Norwegian Mapping Authority's API.
    
    Parameters
    ----------
    start_date : str
        First day for which to download water level data.
    end_date : str
        Last day for which to download water level data.
    station_name : str
        Three letter code for the water level station.
    station_lat : str or float
        Latitude of the water level station.
    station_lon : str or float
        Longitude of the water level station.
    interval : {10, 60}, optional (default 10)
        Observation interval in minutes.
    """

    print(f'Downloading water level data for station: {station_code}')

    # Make a list of the years for which we will get water level data.
    years = pd.date_range(
        pd.Timestamp(start_date), pd.Timestamp(end_date), freq='YS'
    )

    # Initialize a DataFrame that will hold the downloaded data
    df = pd.DataFrame()

    # We can only get data for one year at a time from the API, so loop over
    # all the years we want data for, and download it sequentially.
    for year in years:
        print(f' Year: {year.year}')
        # Define the start and end dates for our request to the API.
        start_date_api = year.strftime('%Y-%m-%d')
        end_year = year.year + 1
        end_date_apt = f'{end_year}-01-01'
        # Define the url for the API request.
        url = (
            f'http://api.sehavniva.no/tideapi.php?tide_request=locationdata'
            f'&lat={station_lat}&lon={station_lon}&datatype=OBS&file=txt'
            f'&lang=en&place={station_code}&dst=0&tzone=0&refcode=CD'
            f'&fromtime={start_date_api}&totime={end_date_apt}'
            f'&interval={interval}')
        # Get the water level data from the API for the given year.
        res = requests.get(url)
        response_text = res.text.split('\r\n')
        header, data = extract_header_and_data(response_text)
        # Store the data to a DataFrame.
        df_temp = pd.read_csv(
            io.StringIO(data), sep='\s+', usecols = ['Timestamp', 'Level']
        )
        # Format the Timestamp.
        df_temp['Timestamp'] = df_temp['Timestamp'].apply(
            lambda x: dt.strptime(x,"%Y-%m-%dT%H:%M:%S+00:00")
        )
        # Make the Timestamp into the index of the DataFrame, and remove the 
        # 'Timestamp' column to avoid duplicate.
        df_temp.index = df_temp['Timestamp']
        df_temp.drop(labels='Timestamp', axis=1, inplace=True)
        # Drop the last entry since that is the first date of the next year.
        df_temp = df_temp[:-1]
        # Add this years data to the total.
        df = pd.concat([df, df_temp])

    # Save the data to a csv file.
    outfile = f'{station_code}_waterlevel.csv'
    print(f'Writing file: {outfile}')
    df.to_csv(outfile, index_label='Time (UTC)')

    return
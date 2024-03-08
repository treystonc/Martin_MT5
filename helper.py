import datetime as dt
import MetaTrader5 as mt
import pandas as pd
import requests
import json
import pytz


def load_economic_calendar():
    print("Loading economic calendar...")

    url = 'https://economic-calendar.tradingview.com/events'

    today = pd.Timestamp.today().normalize()
    payload = {
        'from': (today + pd.offsets.Hour(1)).isoformat() + '.000Z',
        'to': (today + pd.offsets.Day(7) + pd.offsets.Hour(22)).isoformat() + '.000Z',
        'countries': ','.join(['US', 'EU'])
    }
    response = requests.get(url, params=payload)
    data = response.json()

    selected_columns = ['title', 'country', 'indicator', 'category', 'period', 'importance', 'currency', 'date']
    extracted_data = [{col: entry.get(col) for col in selected_columns} for entry in data.get('result', [])]
    df_cal = pd.DataFrame(extracted_data)
    # Define a list of keywords
    keywords = ['Nonfarm Payrolls', 'Unemployment Rate', 'Interest Rate Decision', 'CPI', 'ADP']
    # Create a regular expression pattern to match any of the keywords
    pattern = '|'.join(keywords)
    # Filter the DataFrame based on the pattern
    filtered_df_cal = df_cal[df_cal['title'].str.contains(pattern, case=False, na=False, regex=True)]
    unique_dates = filtered_df_cal['date'].unique()

    important_dates = []
    for date in unique_dates.tolist():
        timezone = pytz.timezone('Etc/GMT-2')  # UTC+2 timezone
        converted_datetime = dt.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%fZ').\
            replace(tzinfo=pytz.utc).astimezone(timezone)
        start = pd.Timestamp(converted_datetime) - dt.timedelta(hours=12)
        end = pd.Timestamp(converted_datetime) + dt.timedelta(hours=4)
        important_dates.append((start, end))

    print("Economic calendar loaded completely.")
    print(f"{len(important_dates)} dates identified.")

    return important_dates
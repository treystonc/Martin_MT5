import datetime as dt
import MetaTrader5 as mt
import pandas as pd
import requests
import json
import pytz


import datetime

def print_with_timestamp(message):
    timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    print(f"{timestamp} {message}")

def load_economic_calendar(currencies):
    print_with_timestamp("Loading economic calendar...")

    url = 'https://economic-calendar.tradingview.com/events'
    
    countries = []
    for currency in currencies:
        if currency == "EURUSD":
            countries.append('US')
            countries.append('EU')
        elif currency == "AUDCAD":
            countries.append('AU')
            countries.append('CA')

    today = pd.Timestamp.today().normalize()
    payload = {
        'from': (today + pd.offsets.Hour(1)).isoformat() + '.000Z',
        'to': (today + pd.offsets.Day(14) + pd.offsets.Hour(22)).isoformat() + '.000Z',
        'countries': ','.join(countries)
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

    # important_dates = []
    # unique_dates = filtered_df_cal['date'].unique()
    # for date in unique_dates.tolist():
    # 
    #     timezone = pytz.timezone('Etc/GMT-2')  # UTC+2 timezone
    #     converted_datetime = dt.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%fZ').\
    #         replace(tzinfo=pytz.utc).astimezone(timezone)
    #     start = pd.Timestamp(converted_datetime) - dt.timedelta(hours=12)
    #     end = pd.Timestamp(converted_datetime) + dt.timedelta(hours=4)
    #     important_dates.append((start, end))

    important_news = []
    # if not load_dates_only:
    for index, news in filtered_df_cal.iterrows():
        timezone = pytz.timezone('Etc/GMT-2')  # UTC+2 timezone
        converted_datetime = dt.datetime.strptime(news['date'], '%Y-%m-%dT%H:%M:%S.%fZ'). \
            replace(tzinfo=pytz.utc).astimezone(timezone)
        important_news.append([news['title'], news['country'], converted_datetime])


    print_with_timestamp("Economic calendar loaded completely.")
    print_with_timestamp(f"{len(important_news)} news identified.")

    return important_news
    
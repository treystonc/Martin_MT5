import datetime as dt
import sys
import time
import MetaTrader5 as mt
import pandas as pd
import requests
from trading import TradeSession
from algorithm import Strategy
import threading
import PySimpleGUI as sg
import json


class MartinApp():
    def __init__(self):
        option_label_column = [
            [sg.Text("Installation")],
            [sg.Text("Account")],
            [sg.Text("Profile")],
        ]

        with open('data.json', 'r') as data_file:
            data = json.load(data_file)

        self.accounts = data['ACCOUNTS']
        self.profiles = data['PROFILES']

        logins = [account['LOGIN'] for account in self.accounts]
        profiles = [profile['NAME'] for profile in self.profiles]

        option_column = [
            [sg.Combo(["C:\\Program Files\\FBS MetaTrader 5\\terminal64.exe"],
                      default_value="C:\\Program Files\\FBS MetaTrader 5\\terminal64.exe",
                      key="-INS-OPTIONS-")],
            [sg.Combo(logins, default_value=logins[0], key="-ACCOUNT-OPTIONS-")],
            [sg.Combo(profiles, default_value=profiles[0], key="-PROFILE-OPTIONS-")],
        ]

        self.layout = [
            [sg.Column(option_label_column), sg.Column(option_column)],
            [sg.Button("Start", key="-STARTSTOP-")],
            [sg.Multiline(size=(100, 50), key="-LOGS-", autoscroll=True, reroute_stdout=True)]
        ]

        self.window = sg.Window("MARTIN App", self.layout)

        sg.theme("Reddit")

        self.running = False
        self.process_thread = []

    # def load_economic_calendar(self):
    #     print("Loading economic calendar...")
    #
    #     url = 'https://economic-calendar.tradingview.com/events'
    #
    #     today = pd.Timestamp.today().normalize()
    #     payload = {
    #         'from': (today + pd.offsets.Hour(23)).isoformat() + '.000Z',
    #         'to': (today + pd.offsets.Day(7) + pd.offsets.Hour(22)).isoformat() + '.000Z',
    #         'countries': ','.join(['US', 'EU'])
    #     }
    #     response = requests.get(url, params=payload)
    #     data = response.json()
    #
    #     selected_columns = ['title', 'country', 'indicator', 'category', 'period', 'importance', 'currency', 'date']
    #     extracted_data = [{col: entry.get(col) for col in selected_columns} for entry in data.get('result', [])]
    #     df_cal = pd.DataFrame(extracted_data)
    #     # Define a list of keywords
    #     keywords = ['Nonfarm Payrolls', 'Unemployment Rate', 'Interest Rate Decision', 'CPI', 'ADP']
    #     # Create a regular expression pattern to match any of the keywords
    #     pattern = '|'.join(keywords)
    #     # Filter the DataFrame based on the pattern
    #     filtered_df_cal = df_cal[df_cal['title'].str.contains(pattern, case=False, na=False, regex=True)]
    #     unique_dates = filtered_df_cal['date'].unique()
    #
    #     important_dates = []
    #     for date in unique_dates.tolist():
    #         start = pd.Timestamp(date) - dt.timedelta(hours=12)
    #         end = pd.Timestamp(date) + dt.timedelta(hours=4)
    #         important_dates.append((start, end))
    #
    #     print("Economic calendar loaded completely.")
    #     print(f"{len(important_dates)} dates identified.")
    #
    #     return important_dates

    def start_stop(self):
        if not self.running:
            self.running = True
            self.window['-STARTSTOP-'].update("Stop")
            self.process_thread = threading.Thread(target=self.run_auto_trading)
            self.process_thread.start()
        else:
            self.running = False
            self.window['-STARTSTOP-'].update("Start")
            print("Auto trading stopped.")

    def run_auto_trading(self):
        selected_account_id = self.window['-ACCOUNT-OPTIONS-'].get()
        selected_account = next((account for account in self.accounts
                                 if account['LOGIN'] == selected_account_id), None)

        selected_profile_name = self.window['-PROFILE-OPTIONS-'].get()
        selected_profile = next((profile for profile in self.profiles
                                 if profile['NAME'] == selected_profile_name), None)

        selected_installation = self.window['-INS-OPTIONS-'].get()
        
        session = TradeSession(selected_account, selected_profile, selected_installation)
        session.start()
        # selected_installation = self.window['-INS-OPTIONS-'].get()
        # selected_account_id = self.window['-ACCOUNT-OPTIONS-'].get()
        # 
        # initialize = mt.initialize(selected_installation)
        # if initialize:
        #     print("MetaTrader initialized successfully.")
        # else:
        #     print("MetaTrader initialized failed.")
        #     self.running = False
        #     self.window['-STARTSTOP-'].update("Start")
        # 
        # if initialize:
        #     selected_account = next((account for account in self.accounts
        #                              if account['LOGIN'] == selected_account_id), None)
        # 
        #     LOGIN = selected_account["LOGIN"]
        #     SERVER = selected_account["SERVER"]
        #     PASSWORD = selected_account["PASSWORD"]
        # 
        #     login = mt.login(login=LOGIN, server=SERVER, password=PASSWORD)
        # 
        #     if login:
        #         print(f"Account: {LOGIN} logged on to Meta Trader successfully.")
        #         print(f"Server = {SERVER}")
        # 
        #     self.load_economic_calendar()
        #     self.run_logic()

    # def run_logic(self):
    #         columns = ['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'Spread', 'Real Volume']
    #
    #         selected_profile_name = self.window['-PROFILE-OPTIONS-'].get()
    #         selected_profile = next((profile for profile in self.profiles
    #                                  if profile['NAME'] == selected_profile_name), None)
    #
    #         print(f"Loaded profile - {selected_profile_name}")
    #         print("Profile configurations:")
    #         print("-----------------------")
    #         for key, value in selected_profile.items():
    #             print(f"{key}: {value}")
    #
    #         SYMBOL = selected_profile["SYMBOL"]
    #         POINT = mt.symbol_info(SYMBOL).point
    #
    #         # Generate trade signals
    #         session = TradeSession(POINT, selected_profile)
    #         strategy = Strategy(POINT, selected_profile, mt.POSITION_TYPE_BUY, mt.POSITION_TYPE_SELL)
    #
    #         print("Auto trading started.")
    #
    #         while self.running:
    #             rates = mt.copy_rates_from_pos(SYMBOL, mt.TIMEFRAME_M1, 0, 1440)
    #
    #             df = pd.DataFrame.from_records(rates, columns=columns)
    #             df['time'] = pd.to_datetime(df['time'], unit='s')
    #             signals = strategy.generate_trade_signal(df)
    #
    #             last_signal = signals.iloc[-1]
    #
    #             result = strategy.process_signal(last_signal)
    #
    #             if result and result['start_new_trade']:
    #                 session.send_order(result)
    #
    #             time.sleep(1)

    def on_close(self):
        self.running = False  # Stop the background process
        if self.process_thread:
            self.process_thread.join()  # Wait for the background thread to join
        self.window.close()  # Close the PySimpleGUI window
        sys.exit()  # Exit the program

    def run(self):
        while True:
            event, values = self.window.read()
            if event == sg.WINDOW_CLOSED:
                self.on_close()
                break
            elif event == '-STARTSTOP-':
                self.start_stop()



pd.set_option('display.max_columns', None)

app = MartinApp()
app.run()


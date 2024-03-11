import datetime as dt
import sys
import threading
import time
import MetaTrader5 as mt
import pandas as pd
import requests
from trading import TradeSession
from algorithm import Strategy
import PySimpleGUI as sg
import json
import logging
from helper import *


SERVER_TIMEZONE = pytz.timezone('Australia/Melbourne')

class MartinApp():
    def __init__(self):
        with open('data.json', 'r') as data_file:
            data = json.load(data_file)

        self.accounts = {}
        for account in data['ACCOUNTS']:
            key = account['LOGIN']
            self.accounts[key] = account

        self.profiles = {}
        for profile in data['PROFILES']:
            key = profile['NAME']
            self.profiles[key] = profile

        self.installations = {}
        for installation in data['INSTALLATIONS']:
            key = installation['NAME']
            self.installations[key] = installation

        self.sessions = {}
        self.selected_account = None
        self.important_news = []
        self.thread = threading.Thread(target=self.daemon_load_economic_calendar)
        self.running = False

        logins = [instance['LOGIN'] for instance in self.accounts.values()]
        profiles = [instance['NAME'] for instance in self.profiles.values()]
        installations = [instance['NAME'] for instance in self.installations.values()]

        option_label_column = [
            [sg.Text("Installation")],
            [sg.Text("Account")],
            [sg.Text("Profile")],
        ]

        option_column = [
            [sg.Combo(installations,
                      default_value=installations[0],
                      key="-INS-OPTIONS-")],
            [sg.Combo(logins, default_value=logins[0], enable_events=True, key="-ACCOUNT-OPTIONS-"),
             sg.Button("CREATE", key="-CREATE-")],
            [sg.Combo(profiles, default_value=profiles[0], enable_events=True, key="-PROFILE-OPTIONS-")],
        ]

        self.layout = [
            [sg.Column(option_label_column), sg.Column(option_column)],
            [sg.HorizontalSeparator()],
            [sg.Text("Trade sessions")],
            [sg.Listbox(self.sessions, key="-SESSIONS-", enable_events=True, size=(40,5)),
             sg.Listbox({}, key="-NEWS-", size=(60,5))],
            [sg.Button("START", key="-STARTSTOP-", disabled=True),
             sg.Button("PAUSE", key="-PAUSE-", disabled=True),
             sg.Button("CLEAR LOG", key="-CLEAR-")],
            [sg.Text(text='', key="-STATUS-")],
            [sg.Multiline(size=(100, 50), key="-LOGS-", autoscroll=True, reroute_stdout=True)]
        ]

        self.window = sg.Window("MARTIN App", self.layout)

        sg.theme("Reddit")

    def get_current_selections(self):
        selected_account_id = self.window['-ACCOUNT-OPTIONS-'].get()
        selected_profile_name = self.window['-PROFILE-OPTIONS-'].get()

        return selected_account_id, selected_profile_name

    def run_auto_trading(self):
        account_id, profile_name = self.get_current_selections()

        selected_account = self.accounts[account_id]
        selected_profile = self.profiles[profile_name]

        session_key = str(selected_account['LOGIN']) + " - " + selected_profile['SYMBOL'] + selected_profile['NAME']
        session = self.sessions.get(session_key)


        if session is None:
            installation_key = self.window['-INS-OPTIONS-'].get()
            installation = self.installations[installation_key]

            session = TradeSession(selected_account, selected_profile, installation['PATH'])
            self.sessions[session.key] = session
            
            if session.start():
                self.window['-STARTSTOP-'].update('STOP')
                # self.window['-SELECT-'].update(disabled=True)
                self.window['-PAUSE-'].update(disabled=False)
                self.window['-STATUS-'].update('SESSION STARTED.')
        else:
            if session.running:
                session.stop()
                self.window['-STARTSTOP-'].update('START')
                # self.window['-SELECT-'].update(disabled=False)
                self.window['-PAUSE-'].update(disabled=True)
                self.window['-STATUS-'].update('SESSION STOPPED.')
            else:
                if session.start():
                    self.window['-STARTSTOP-'].update('STOP')
                    # self.window['-SELECT-'].update(disabled=True)
                    self.window['-PAUSE-'].update(disabled=False)
                    self.window['-STATUS-'].update('SESSION STARTED.')

    def create_session(self):
        account_id, profile_name = self.get_current_selections()

        selected_account = self.accounts[account_id]
        selected_profile = self.profiles[profile_name]

        session_key = str(selected_account['LOGIN']) + " - " + selected_profile['SYMBOL'] + selected_profile['NAME']
        session = self.sessions.get(session_key)

        if session is None:
            installation_key = self.window['-INS-OPTIONS-'].get()
            installation = self.installations[installation_key]

            session = TradeSession(selected_account, selected_profile, installation['PATH'])
            self.sessions[session.key] = session

            self.update_news_dashboard(selected_profile['SYMBOL'])

    def on_close(self):
        self.running = False
        self.window.close()  # Close the PySimpleGUI window
        self.thread.join()
        sys.exit()  # Exit the program

    def run(self):
        self.running = True
        self.thread.start()

        while True:
            event, values = self.window.read()
            if event == sg.WINDOW_CLOSED:
                self.on_close()
                break
            elif event == "-ACCOUNT-OPTIONS-" or event  == "-PROFILE-OPTIONS-":
                account_id, profile_name = self.get_current_selections()

                selected_account = self.accounts[account_id]
                selected_profile = self.profiles[profile_name]

                session_key = str(selected_account['LOGIN']) + " - " + selected_profile['SYMBOL'] + selected_profile[
                    'NAME']
                session = self.sessions.get(session_key)

                if session is None:
                    self.window['-STARTSTOP-'].update('START')

            elif event == '-CREATE-':
                self.create_session()
                self.window['-SESSIONS-'].update(values=self.sessions)

            elif event == '-SESSIONS-':
                session_key = self.window["-SESSIONS-"].get()
                if session_key is not None:
                    session = self.sessions[session_key[0]]
                    if session.running:
                        if session.paused:
                            self.window['-PAUSE-'].update('RESUME')
                            self.window['-STATUS-'].update('SESSION PAUSED.')
                        else:
                            self.window['-PAUSE-'].update('PAUSE')
                            self.window['-STARTSTOP-'].update('STOP')
                            self.window['-STARTSTOP-'].update(disabled=False)
                            self.window['-STATUS-'].update('SESSION RUNNING.')
                    else:
                        self.window['-STARTSTOP-'].update('START')
                        self.window['-STARTSTOP-'].update(disabled=False)
                        self.window['-PAUSE-'].update(disabled=True)
                        self.window['-STATUS-'].update('SESSION STOPPED.')

                    self.update_news_dashboard(session.SYMBOL)
                else:
                    self.window['-STATUS-'].update('')

            elif event == '-STARTSTOP-':
                self.run_auto_trading()

            elif event == '-PAUSE-':
                if session.paused:
                    session.resume()
                    self.window['-PAUSE-'].update('PAUSE')
                    self.window['-STATUS-'].update('SESSION RESUMED.')
                    print_with_timestamp(f"Session for {session.key} has been resumed.")
                else:
                    session.pause()
                    self.window['-PAUSE-'].update('RESUME')
                    self.window['-STATUS-'].update('SESSION PAUSED.')
                    print_with_timestamp(f"Session for {session.key} has been paused.")

            elif event == '-CLEAR-':
                self.window['-LOGS-'].update('')

    def daemon_load_economic_calendar(self):
        gap_counter = 60
        while self.running:
            if gap_counter == 60:
                symbols = []
                for session in self.sessions.values():
                    symbols.append(session.SYMBOL)

                if len(symbols) > 0:
                    self.important_news = load_economic_calendar(symbols)

                gap_counter = 0

            gap_counter += 1
            time.sleep(1)

    def get_news_for_symbol(self, symbol):
        countries = []
        if symbol == "EURUSD":
            countries.append('US')
            countries.append('EU')
        elif symbol == "AUDCAD":
            countries.append('AU')
            countries.append('CA')

        important_news = [instance for instance in self.important_news if instance[1] in countries ]
        return important_news

    def update_news_dashboard(self, symbol):
        important_news = self.get_news_for_symbol(symbol)
        formatted_dates = []
        for news in important_news:
            local_date = news[2].astimezone(SERVER_TIMEZONE)
            formatted_dates.append(str(local_date) + " - " + news[1] + " - " +
                                   str(news[0]))
        self.window['-NEWS-'].update(values=formatted_dates)


pd.set_option('display.max_columns', None)
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

app = MartinApp()
app.run()


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
            [sg.Combo(logins, default_value=logins[0], enable_events=True, key="-ACCOUNT-OPTIONS-")],
            [sg.Combo(profiles, default_value=profiles[0], enable_events=True, key="-PROFILE-OPTIONS-")],
        ]

        self.layout = [
            [sg.Column(option_label_column), sg.Column(option_column)],
            [sg.Button("START", key="-STARTSTOP-")],
            [sg.Multiline(size=(100, 50), key="-LOGS-", autoscroll=True, reroute_stdout=True)]
        ]

        self.window = sg.Window("MARTIN App", self.layout)

        sg.theme("Reddit")

        self.sessions = []


    def run_auto_trading(self):
        selected_account_id = self.window['-ACCOUNT-OPTIONS-'].get()
        selected_profile_name = self.window['-PROFILE-OPTIONS-'].get()

        session_exists = False
        for session in self.sessions:
            if session.account['LOGIN'] == selected_account_id \
                    and session.configurations['NAME'] == selected_profile_name:
                if session.running:
                    self.window['-STARTSTOP-'].update('STOP')
                else:
                    self.window['-STARTSTOP-'].update('START')

                session_exists = True
                break

        if not session_exists:
            selected_profile = next((profile for profile in self.profiles
                                     if profile['NAME'] == selected_profile_name), None)
            selected_account = next((account for account in self.accounts
                                     if account['LOGIN'] == selected_account_id), None)
            selected_installation = self.window['-INS-OPTIONS-'].get()
        
            session = TradeSession(selected_account, selected_profile, selected_installation)
            self.sessions.append(session)
            session.start()
            self.window['-STARTSTOP-'].update('STOP')
        else:
            if session.running:
                if session.paused:
                    session.resume()
                    self.window['-STARTSTOP-'].update('STOP')
                else:
                    session.pause()
                    self.window['-STARTSTOP-'].update('START')
            else:
                session.start()
                self.window['-STARTSTOP-'].update('STOP')

    def on_close(self):
        self.window.close()  # Close the PySimpleGUI window
        sys.exit()  # Exit the program

    def run(self):
        while True:
            event, values = self.window.read()
            if event == sg.WINDOW_CLOSED:
                self.on_close()
                break
            elif event == "-ACCOUNT-OPTIONS-" or event  == "-PROFILE-OPTIONS-":
                selected_account_id = self.window['-ACCOUNT-OPTIONS-'].get()
                selected_profile_name = self.window['-PROFILE-OPTIONS-'].get()

                session_exists = False
                for session in self.sessions:
                    if session.account['LOGIN'] == selected_account_id \
                            and session.configurations['NAME'] == selected_profile_name:
                        if session.running:
                            self.window['-STARTSTOP-'].update('STOP')
                        else:
                            self.window['-STARTSTOP-'].update('START')

                        session_exists = True
                        break

                if not session_exists:
                    self.window['-STARTSTOP-'].update('START')

            elif event == '-STARTSTOP-':
                self.run_auto_trading()



pd.set_option('display.max_columns', None)

app = MartinApp()
app.run()


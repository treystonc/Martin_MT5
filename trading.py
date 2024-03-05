import MetaTrader5 as mt
import pandas as pd
import time
from helper import *
from algorithm import *
import threading

class TradeSession:
    def __init__(self, account, configurations, installation):
        self.account = account
        self.installation = installation
        self.SYMBOL = configurations['SYMBOL']
        self.MAGIC_NUMBER = configurations["MAGIC_NUMBER"]
        self.configurations = configurations
        
        self.running = False
        self.paused = False
        self.thread = threading.Thread(target=self.run)
        
        self.SYMBOL_POINT = 0
        self.TP_PIPS = configurations["DEFAULT_TP_PIPS"]
        self.ATR_THRESHOLD = configurations['ATR_THRESHOLD']
        self.ATR_APPLY = configurations['ATR_APPLY']
        self.ATR_MIN_PIPS_MULTIPLIER = configurations['ATR_MIN_PIPS_MULTIPLIER']
        self.ATR_VOLUME_MULTIPLIER = configurations['ATR_VOLUME_MULTIPLIER']
        self.ATR_TP_MULTIPLIER = configurations["ATR_TP_MULTIPLIER"]

        self.strategy = Strategy(self.configurations, mt.POSITION_TYPE_BUY, mt.POSITION_TYPE_SELL)
        self.important_dates = []

    def modify_position(self, order_number, new_stop_loss, new_take_profit):
        # Create the request
        request = {
            "action": mt.TRADE_ACTION_SLTP,
            "tp": new_take_profit,
            "position": order_number
        }
    
        result = mt.order_send(request)
        if result[0] == mt.TRADE_RETCODE_DONE:
            print(f"Order modified: {order_number}. New take profit price = {new_take_profit}")
        else:
            print(f"Order {order_number} failed to modify")

    def adjust_positions_tp(self, order_type, atr):
        positions = mt.positions_get(SYMBOL=self.SYMBOL)
    
        position_columns = ['ticket', 'time', 'time_msc', 'time_update', 'time_update_msc', 'type', 'magic', 'identifier',
                            'reason', 'volume', 'price_open', 'sl', 'tp', 'price_current', 'swap', 'profit', 'symbol',
                            'comment', 'external_id']
        
        df_position = pd.DataFrame.from_records(positions, columns=position_columns)
        open_positions = df_position[df_position['type'] == order_type]
    
        average_cost = 0
        if len(open_positions) > 0:
            total_cost = (open_positions.price_open * open_positions.volume).sum()
            total_volume = (open_positions.volume).sum()
            average_cost = round(total_cost / total_volume, 5)
    
        adjust_value = self.TP_PIPS * self.SYMBOL_POINT
        if self.ATR_APPLY:
            if atr >= self.ATR_THRESHOLD:
                adjust_value = adjust_value * self.ATR_TP_MULTIPLIER
    
        new_tp = average_cost + adjust_value
        if order_type == mt.POSITION_TYPE_SELL:
            new_tp = average_cost - adjust_value
    
        for index, row in open_positions.iterrows():
            self.modify_position(row.ticket, 0, new_tp)

    def send_order(self, trade):
        request = {
            "action": mt.TRADE_ACTION_DEAL,
            "symbol": trade['symbol'],
            "volume": trade['volume'],
            "type": trade['action_type'],
            "price": trade['open_price'],
            "tp": trade['tp'],
            "magic": self.MAGIC_NUMBER,  # Unique identifier for your trades
            "type_time": mt.ORDER_TIME_GTC,  # Good till canceled
            "type_filling": mt.ORDER_FILLING_FOK,
            "comment": trade['comment']
        }
    
        result = mt.order_send(request)
    
        print(f'Order: {trade["action_type"]} Volume: {trade["volume"]} Price: {trade["open_price"]} TP: {trade["tp"]}'
              f' Result: re{result[0]}')
    
        if result and result[0] == mt.TRADE_RETCODE_DONE:
            print(f"Order executed: {result[2]}")
            self.adjust_positions_tp(trade["action_type"], trade["atr"])

    def start(self):
        initialize = mt.initialize(self.installation)
        if initialize:
            print("MetaTrader initialized successfully.")
        else:
            print("MetaTrader initialized failed.")

        if initialize:
            LOGIN = self.account["LOGIN"]
            SERVER = self.account["SERVER"]
            PASSWORD = self.account["PASSWORD"]

            login = mt.login(login=LOGIN, server=SERVER, password=PASSWORD)

            if login:
                print(f"Account: {LOGIN} logged on to Meta Trader successfully.")
                print(f"Server = {SERVER}")

            self.SYMBOL_POINT = mt.symbol_info(self.SYMBOL).point

            self.important_dates =  load_economic_calendar()
            self.running = True
            self.thread.start()

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def stop(self):
        self.running = False

    def run(self):
        columns = ['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'Spread', 'Real Volume']

        while self.running:
            if not self.paused:
                rates = mt.copy_rates_from_pos(self.SYMBOL, mt.TIMEFRAME_M1, 0, 1440)

                df = pd.DataFrame.from_records(rates, columns=columns)
                df['time'] = pd.to_datetime(df['time'], unit='s')
                signals = self.strategy.generate_trade_signal(df)

                last_signal = signals.iloc[-1]

                result = self.strategy.process_signal(last_signal, self.important_dates)

                if result and result['start_new_trade']:
                    self.send_order(result)

                time.sleep(1)
            else:
                time.sleep(0.1)
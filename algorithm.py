import datetime as dt
import MetaTrader5 as mt
import pandas as pd
import talib

class Strategy:
    def __init__(self, configs, mt_buy_indicator, mt_sell_indicator):
        self.SYMBOL = configs['SYMBOL']
        self.SYMBOL_POINT = 0
        self.DEFAULT_VOLUME = configs['DEFAULT_VOLUME']
        self.DEFAULT_VOLUME_MULTIPLIER = configs['DEFAULT_VOLUME_MULTIPLIER']
        self.MIN_PIPS_FROM_LAST_ORDER = configs['MIN_PIPS_FROM_LAST_ORDER']
        self.TP_PIPS = configs['DEFAULT_TP_PIPS']
        self.RSI_PERIOD = configs['RSI_PERIOD']
        self.RSI_BAR_TO_COMPARE = configs['RSI_BAR_TO_COMPARE']
        self.ST_MA_TYPE = configs['MA_SHORT_TYPE']
        self.ST_MA_PERIOD = configs['MA_SHORT_PERIOD']
        self.LT_MA_TYPE = configs['MA_LONG_TYPE']
        self.LT_MA_PERIOD = configs['MA_LONG_PERIOD']
        self.ATR_PERIOD = configs['ATR_PERIOD']
        self.MT5_BUY_INDICATOR = mt_buy_indicator
        self.MT5_SELL_INDICATOR = mt_sell_indicator
        self.ATR_THRESHOLD = configs['ATR_THRESHOLD']
        self.ATR_APPLY = configs['ATR_APPLY']
        self.ATR_MIN_PIPS_MULTIPLIER = configs['ATR_MIN_PIPS_MULTIPLIER']
        self.ATR_VOLUME_MULTIPLIER = configs['ATR_VOLUME_MULTIPLIER']
        self.MAX_SPREAD_ALLOWED = configs['MAX_SPREAD_ALLOWED']


    def generate_trade_signal(self, df):
        # Calculate RSI
        df['RSI'] = talib.RSI(df['close'], timeperiod=self.RSI_PERIOD)
    
        # Calculate Moving Average (MA)
        if self.ST_MA_TYPE == "SMA":
            df['MA_SHORT'] = talib.SMA(df['close'], timeperiod=self.ST_MA_PERIOD)
        elif self.ST_MA_TYPE == "EMA":
            df['MA_SHORT'] = talib.EMA(df['close'], timeperiod=self.ST_MA_PERIOD)
         
        if self.ST_MA_TYPE == "SMA":
            df['MA_LONG'] = talib.SMA(df['close'], timeperiod=self.LT_MA_PERIOD)
        elif self.ST_MA_TYPE == "EMA":
            df['MA_LONG'] = talib.EMA(df['close'], timeperiod=self.LT_MA_PERIOD)

        # Calculate Average True Range (ATR)
        df['ATR'] = talib.ATR(df.high, df.low, df.close, timeperiod=self.ATR_PERIOD)
    
        # Generate trade signals
        signals = []
        for i in range(len(df)):
            if (df['RSI'][i] > 30 and
                    all(df['RSI'][i] > df['RSI'][i - j] for j in range(1, self.RSI_BAR_TO_COMPARE)) and
                    df['MA_SHORT'][i] >= df['MA_LONG'][i]):
                signals.append('BUY')
            elif (df['RSI'][i] < 70 and
                  all(df['RSI'][i] < df['RSI'][i - j] for j in range(1, self.RSI_BAR_TO_COMPARE)) and
                  df['MA_SHORT'][i] <= df['MA_LONG'][i]):
                signals.append('SELL')
            else:
                signals.append('')
    
        df['Signal'] = signals
    
        return df


    def adjust_for_weekend(start_time):
        # Check if the start time falls on a Saturday (6) or Sunday (0)
        if start_time.weekday() >= 5:  # Saturday or Sunday
            # Calculate the number of days to shift back to Friday
            days_to_shift = start_time.weekday() - 4  # 4 is Friday's weekday number
            # Adjust the start time to the last minute of the previous Friday
            start_time -= dt.timedelta(days=days_to_shift,
                                       hours=start_time.hour, minutes=start_time.minute, seconds=start_time.second)
    
        return start_time


    def process_signal(self, data, important_dates):
        is_buy = False
        is_sell = False
        order_sequence = 1
        volume = self.DEFAULT_VOLUME
        
        if self.SYMBOL_POINT == 0:
            self.SYMBOL_POINT = mt.symbol_info(self.SYMBOL).point

        position_columns = ['ticket', 'time', 'time_msc', 'time_update', 'time_update_msc', 'type', 'magic',
                            'identifier',
                            'reason', 'volume', 'price_open', 'sl', 'tp', 'price_current', 'swap', 'profit', 'symbol',
                            'comment', 'external_id']
    
    
        positions = mt.positions_get(SYMBOL=self.SYMBOL)
        df_position = pd.DataFrame.from_records(positions, columns=position_columns)
    
        # Check has important news based on imported economic calendar
        has_important_news = False
        for dates in important_dates:
            start, end = dates
            data_time = data['time'].tz_localize('UTC')
            has_important_news = has_important_news or (data_time >= start and data_time <= end)
    
        is_max_trade_reached = False

        # First, collect all opened positions
        # If it has opened position:
        # Check if its last opened position's open price is X pips from the current price
        # Apply ATR factor (volatility) on the minimum pips gap and multiplier on the new trade volume
        if (data['Signal']) == "BUY":
            open_positions = df_position[df_position['type'] == self.MT5_BUY_INDICATOR]
            has_no_position = len(open_positions) == 0
            if not has_no_position:
                last_position = open_positions.iloc[-1]
                min_pips = self.MIN_PIPS_FROM_LAST_ORDER * self.SYMBOL_POINT
                if self.ATR_APPLY and data.ATR >= self.ATR_THRESHOLD:
                    min_pips = data.ATR * self.ATR_MIN_PIPS_MULTIPLIER
                is_buy = (last_position.price_open - min_pips) > data['close']
                
                volume_multiplier = self.DEFAULT_VOLUME_MULTIPLIER
                if data.ATR >= self.ATR_THRESHOLD:
                    volume_multiplier = self.ATR_VOLUME_MULTIPLIER
                volume = round(last_position.volume * volume_multiplier, 2)
            else:
                is_buy = not has_important_news
            order_sequence = len(open_positions) + 1
        elif (data['Signal']) == "SELL":
            open_positions = df_position[df_position['type'] == self.MT5_SELL_INDICATOR]
            has_no_position = len(open_positions) == 0
            if not has_no_position:
                last_position = open_positions.iloc[-1]
                min_pips = self.MIN_PIPS_FROM_LAST_ORDER * self.SYMBOL_POINT
                if self.ATR_APPLY and data.ATR >= self.ATR_THRESHOLD:
                    min_pips = data.ATR * self.ATR_MIN_PIPS_MULTIPLIER
                is_sell = (last_position.price_open + min_pips) < data['close']
                volume_multiplier = self.DEFAULT_VOLUME_MULTIPLIER
                if data.ATR >= self.ATR_THRESHOLD:
                    volume_multiplier = self.ATR_VOLUME_MULTIPLIER
                volume = round(last_position.volume * volume_multiplier, 2)
            else:
                is_sell = not has_important_news
            order_sequence = len(open_positions) + 1
        
        is_new_trade = False
        tp = 0
        comment = ''
        action_type = 0
        open_price = data.close
        
        if not is_max_trade_reached and data.spread <= self.MAX_SPREAD_ALLOWED:
            if is_buy:
                is_new_trade = True
                tp = open_price + self.TP_PIPS * self.SYMBOL_POINT
                comment = "Buy - " + str(order_sequence)
                action_type = self.MT5_BUY_INDICATOR

    
            elif is_sell:
                is_new_trade = True
                tp = open_price - self.TP_PIPS * self.SYMBOL_POINT
                comment = "Sell - " + str(order_sequence)
                action_type = self.MT5_SELL_INDICATOR

        new_trade = {
            "start_new_trade": is_new_trade,
            "symbol": self.SYMBOL,
            "open_price": open_price,
            "action_type": action_type,
            "tp": tp,
            "sl": 0,
            "volume": volume,
            "comment": comment,
            "atr": data.ATR
        }
        
        return new_trade
import numpy as np
from pandas import DataFrame
import talib.abstract as ta

from .trading_env import TradingEnv, Actions, Positions


class CryptoEnv(TradingEnv):

    def __init__(self, df, window_size, frame_bound):
        assert len(frame_bound) == 2

        self.frame_bound = frame_bound
        super().__init__(df, window_size)

        self.trade_fee_bid_percent = 0.01  # unit
        self.trade_fee_ask_percent = 0.005  # unit
        self.rsi_window = 14

    def _process_data(self):
        assert self.frame_bound[0] >= self.window_size
        
        self.df = self.populate_indicators(self.df)
        
        prices = self.get_frame(self.df.loc[:, 'close']).to_numpy()
        # prices = prices[self.frame_bound[0]-self.window_size:self.frame_bound[1]]
        
        
        #rsi = self.get_frame(ta.RSI(self.df, timeperiod=14)).to_numpy()
        #difference = self.get_frame(self.df['diff']).to_numpy()
        
        #signal_features = np.column_stack((prices, difference, rsi))
        signal_features = self.get_frame(self.df).to_numpy()
        pricesdf = self.get_frame(self.df).loc[:,'close'].to_numpy()
        print(signal_features)
        return prices, signal_features

    #TODO: get indicators from strategy
    def populate_indicators(self, df:DataFrame):
        df['diff'] = df['close'].diff()
        df['rsi'] = ta.RSI(self.df, timeperiod=14)
        macd = ta.MACD(df)
        df['macd'] = macd['macd']
        df['macdsignal'] = macd['macdsignal']
        df['macdhist'] = macd['macdhist']
        
        #TODO: Replace hardcoded index by number of Nan rows
        df = df.iloc[35:]
        print(df.head())
        return df[['close', 'diff', 'rsi', 'macdsignal']]
    
    
    def get_frame(self, df):
        return df[self.frame_bound[0]-self.window_size:self.frame_bound[1]]

    def _calculate_reward(self, action):
        step_reward = 0

        trade = False
        if ((action == Actions.Buy.value and self._position == Positions.Short) or
            (action == Actions.Sell.value and self._position == Positions.Long)):
            trade = True

        if trade:
            current_price = self.prices[self._current_tick]
            last_trade_price = self.prices[self._last_trade_tick]
            price_diff = current_price - last_trade_price

            if self._position == Positions.Long:
                step_reward += price_diff
            
            elif self._position == Positions.Short:
                step_reward += -price_diff
            

        return step_reward


    def _update_profit(self, action):
        trade = False
        if ((action == Actions.Buy.value and self._position == Positions.Short) or
            (action == Actions.Sell.value and self._position == Positions.Long)):
            trade = True

        if trade or self._done:
            current_price = self.prices[self._current_tick]
            last_trade_price = self.prices[self._last_trade_tick]

            if self._position == Positions.Long:
                shares = (self._total_profit * (1 - self.trade_fee_ask_percent)) / last_trade_price
                self._total_profit = (shares * (1 - self.trade_fee_bid_percent)) * current_price
            

    def max_possible_profit(self):
        current_tick = self._start_tick
        last_trade_tick = current_tick - 1
        profit = 1.

        while current_tick <= self._end_tick:
            position = None
            if self.prices[current_tick] < self.prices[current_tick - 1]:
                while (current_tick <= self._end_tick and
                       self.prices[current_tick] < self.prices[current_tick - 1]):
                    current_tick += 1
                position = Positions.Short
            else:
                while (current_tick <= self._end_tick and
                       self.prices[current_tick] >= self.prices[current_tick - 1]):
                    current_tick += 1
                position = Positions.Long

            if position == Positions.Long:
                current_price = self.prices[current_tick - 1]
                last_trade_price = self.prices[last_trade_tick]
                shares = profit / last_trade_price
                profit = shares * current_price
            last_trade_tick = current_tick - 1

        return profit

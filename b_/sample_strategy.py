from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import talib.abstract as ta



class MyStrategy(IStrategy):
    INTERFACE_VERSION = 2
    
    # Strategy parameters
    minimal_roi = {
        "0": 0.01  # Minimum ROI at any time.
    }
    stoploss = -0.1  # Default stoploss, which can be overridden by custom_stoploss

    # Trailing stop
    trailing_stop = False
    trailing_stop_positive = 0.005
    trailing_stop_positive_offset = 0.015
    trailing_only_offset_is_reached = True

    # Hyperparameters
    RISK_LEVEL = 0.02
    LEVERAGE = 10
    
    def populate_indicators(self, dataframe: DataFrame) -> DataFrame:
        # Bollinger Bands
        dataframe['bb_lowerband'] = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)[2]
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=5)
        # ATR
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame) -> DataFrame:
        conditions = []
        # Condition: Target bearish candle
        conditions.append(
            (dataframe['close'] < dataframe['open']) &  # Bearish candle
            (dataframe['low'] < dataframe['bb_lowerband']) &  # Lowest price below lower BBand
            (dataframe['close'] < dataframe['bb_lowerband']) &  # Closing price below lower BBand
            (dataframe['rsi'] < 30)  # RSI less than 30
        )
        
        if conditions:
            # Only consider the first bullish candle after the bearish candle
            dataframe.loc[
                (dataframe['close'] > dataframe['open']) &
                (dataframe['close'].shift(1) < dataframe['open'].shift(1)) &
                conditions[-1], 'buy'] = 1

        return dataframe

    def custom_stoploss(self, dataframe: DataFrame, trade: 'Trade', current_time: 'datetime', current_rate: float, current_profit: float, **kwargs) -> float:
        stop_loss_trigger = -0.5 * dataframe['atr'].iloc[-1]
        return stop_loss_trigger

    def custom_stake_amount(self, balance: float, entry_price: float, stop_loss_price: float) -> float:
        price_difference = abs(entry_price - stop_loss_price)
        stake_amount = (balance * self.RISK_LEVEL) / price_difference
        return stake_amount * self.LEVERAGE

    def populate_sell_trend(self, dataframe: DataFrame) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['close'] > dataframe['buy_price'] + dataframe['atr'] * 1.0)  # Take profit condition
            ), 'sell'] = 1
        return dataframe

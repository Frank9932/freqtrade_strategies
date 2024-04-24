from freqtrade.strategy.interface import IStrategy
from freqtrade.persistence import Trade
from pandas import DataFrame
import talib.abstract as ta

class MyStrategy(IStrategy):
    INTERFACE_VERSION = 3  # Updated interface version to V3

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

    def populate_entry_trend(self, dataframe: DataFrame) -> DataFrame:
        conditions = (
            (dataframe['close'] < dataframe['open']) &  # Bearish candle
            (dataframe['low'] < dataframe['bb_lowerband']) &  # Lowest price below lower BBand
            (dataframe['close'] < dataframe['bb_lowerband']) &  # Closing price below lower BBand
            (dataframe['rsi'] < 30)  # RSI less than 30
        )
        
        dataframe.loc[
            conditions &
            (dataframe['close'].shift(-1) > dataframe['open'].shift(-1)), 'enter_long'] = 1  # Enter long on the next candle if it is bullish

        return dataframe

    def custom_stoploss(self, trade: Trade, current_time: 'datetime', current_rate: float, current_profit: float, **kwargs) -> float:
        # Retrieve the ATR value from the dataframe at the trade's open candle
        atr = trade.open_df['atr'].iloc[-1] if 'atr' in trade.open_df else 0
        return -0.5 * atr

    def custom_stake_amount(self, pair: str, current_time: 'datetime', current_rate: float, **kwargs) -> float:
        balance = self.wallets.get_free(pair.split('/')[0])
        stop_loss_price = current_rate - (0.5 * self.dp.get_analyzed_dataframe(pair)['atr'].iloc[-1])
        price_difference = abs(current_rate - stop_loss_price)
        stake_amount = (balance * self.RISK_LEVEL) / price_difference
        return stake_amount * self.LEVERAGE

    def populate_exit_trend(self, dataframe: DataFrame) -> DataFrame:
        dataframe.loc[
            (dataframe['close'] > dataframe['buy_price'] + dataframe['atr'] * 1.0), 'exit_long'] = 1  # Take profit condition
        return dataframe

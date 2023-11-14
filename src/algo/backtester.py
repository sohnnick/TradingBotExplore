import yfinance as yf
import numpy as np
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta

# CLASS: initialize data pulls, key technical indicators, obtain latest recommendation, & backtest results
class SMABacktester:
    
    # INITIALIZATION
    def __init__(self, name, dt_prior, dt_latest):
        self.ticker = name
        self.obj = yf.Ticker(name)
        self.data = self.obj.history(start=dt_prior, end=dt_latest)\
            .reset_index().sort_values('Date', ascending=True)
        self.data.Date = pd.to_datetime(self.data.Date)
        self.data = self.data.set_index('Date')
        self.info = self.obj.info
    
    # SET moving average parameters
    def set_parameters(self, sma_low, sma_high):
        self.sma_low = sma_low
        self.sma_high = sma_high
        self.data['SMA_Low'] = self.data['Open'].rolling(sma_low).mean()
        self.data['SMA_High'] = self.data['Open'].rolling(sma_high).mean()
        self.data.dropna(inplace=True) # drop data if it doesn't have all SMAs
    
    # RUN historical strategies
    def run_strategy(self):
        # get returns
        self.data['returns'] = np.log(self.data['Open'] / self.data['Open'].shift(1))

        # get strategy POSITION
        self.data['position'] = np.where(self.data['SMA_Low'] > self.data['SMA_High'], 1, 0)

        # get log returns of strategy
        self.data['strategy_returns'] = self.data['position'].shift(1) * self.data['returns']

        # get cumulative returns
        self.data['strategy_cumret'] = self.data['strategy_returns'].cumsum().apply(np.exp)

        # get cumulative max up until a certain point
        self.data['strategy_cummax'] = self.data['strategy_cumret'].cummax()

    def get_latest_recommendation(self):
        # INITIALIZE current date
        current_date = datetime.date.today().strftime('%Y-%m-%d')

        # COLLECT latest record and its latest position
        latest_record = self.data.sort_index(axis=0, ascending=True)[-1:]
        latest_date = latest_record.index[0].to_pydatetime().strftime('%Y-%m-%d')
        latest_dict = latest_record.to_dict('records')[0]

        # FORMAT for return
        latest_rec_dict = dict()
        latest_rec_dict['date'] = latest_date

        # if latest record is today & we have the open price available
        if latest_date == current_date and latest_dict['Open'] != None:
            latest_rec_dict['position'] = latest_dict['position']
            latest_rec_dict['SMA_Low'] = latest_record['SMA_Low'].values[0]
            latest_rec_dict['SMA_High'] = latest_record['SMA_High'].values[0]
            latest_rec_dict['status'] = 'SUCCESS'
            latest_rec_dict['reason'] = 'NA'
        # otherwise return error
        else:
            latest_rec_dict['position'] = None
            latest_rec_dict['SMA_Low'] = None
            latest_rec_dict['SMA_High'] = None
            latest_rec_dict['status'] = 'FAIL'
            latest_rec_dict['reason'] = 'Could not pull open price data or latest record does not match current date.'

        return latest_rec_dict
    
    # BACKTEST strategy returns, standard deviation, max drawdown
    def get_backtest_metrics(self):
        metrics = dict()
        
        # get cumulative returns
        metrics['cum_returns'] = np.exp(self.data['returns'].sum())-1
        metrics['strategy_cum_returns'] = np.exp(self.data['strategy_returns'].sum())-1

        # get annualized returns
        metrics['annualized_returns'] = np.exp(self.data['returns'].mean()*252)-1
        metrics['annualized_strategy_returns'] = np.exp(self.data['strategy_returns'].mean()*252)-1

        # get get annualized standard deviation
        metrics['annualized_std'] = (self.data['returns'].apply(np.exp)-1).std()*252**0.5
        metrics['annualized_strategy_std'] = (self.data['strategy_returns'].apply(np.exp)-1).std()*252**0.5

        # max drawdown
        drawdown = self.data.strategy_cummax - self.data.strategy_cumret
        metrics['max_drawdown'] = drawdown.max()

        # longest drawdown
        zero_drawdown = drawdown[drawdown == 0]
        # get periods by shifting the drawdown dates over one and subtracting it from the prior
        periods = (zero_drawdown.index[1:].to_pydatetime() - zero_drawdown.index[:-1].to_pydatetime()) 
        metrics['longest_drawdown'] = periods.max() # get the longest period

        # return data
        return metrics
import os
import sys
import time
import requests
import datetime
from dateutil.relativedelta import relativedelta
from configparser import ConfigParser

from algo import *

if __name__ == "__main__":

    # INITIALIZE Alpaca Client
    config = ConfigParser()
    config.read('../config.ini')

    ALPACA_API_KEY = config['APIKeys']['alpaca_key'] # initialize alpaca keys
    ALPACA_API_SECRET = config['APIKeys']['alpaca_secret']

    client = TradingClient(ALPACA_API_KEY, ALPACA_API_SECRET, paper=True) # initialize Alpaca client

    # INITIALIZE date range to backtest
    DT_LATEST = datetime.datetime.now()
    DT_PRIOR = DT_LATEST - relativedelta(years=5) # prior x years

    # SET Ticker of choice
    TICKER = 'SPY'

    # RUN algo
    run_algo_execution(client, TICKER, DT_PRIOR, DT_LATEST)

    # client.close_all_positions(cancel_orders=True)
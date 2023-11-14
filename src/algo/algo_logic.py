import os
import sys
import pathlib
import time
import requests
import datetime
from dateutil.relativedelta import relativedelta
from configparser import ConfigParser

# alpaca libraries
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.stream import TradingStream
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.enums import AssetClass

# import relevant libraries
from .backtester import *

# FUNCTION: execute order
def execute_order(ticker, notional_amt):

    order_details = MarketOrderRequest(
        symbol= ticker,
        notional=notional_amt,
        side = OrderSide.BUY,
        time_in_force = TimeInForce.DAY
    )

    try:
        order = client.submit_order(order_data=order_details)
    except:
        print(f'ORDER NOT FILLED for {ticker} of ${notional_amt:.2f}: API error...')
        return

    # if order could not be filled, print failure
    if order.filled_at == None:
        print(f'ORDER NOT FILLED for {ticker} of ${notional_amt:.2f}: check if markets are open...')
    
    # if success
    else:
        print(f'ORDER FILLED for {ticker} of ${notional_amt:.2f}: success!')

# FUNCTION: trading algorithm logic
def run_algo_execution(client, ticker, dt_prior, dt_latest):

    STR_PAD = '#'*7 

    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
    # Initialize Tick Obj & Clock
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

    # get market clock
    clock = client.get_clock()

    # INITIALIZE backtester and run strategy 
    ticker_obj = SMABacktester(ticker, dt_prior, dt_latest)
    ticker_obj.set_parameters(60, 252)
    ticker_obj.run_strategy()

    # get backtest results & recommendation
    backtest_results = ticker_obj.get_backtest_metrics()
    latest_recommendation = ticker_obj.get_latest_recommendation()

    # print(latest_recommendation)

    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
    # PULL accounts and positions
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

    # account details
    account = dict(client.get_account())
    moolah = float(account['cash'])
    non_margin_buying_power = float(account['non_marginable_buying_power'])

    # open / active position
    all_positions = client.get_all_positions()
    ticker_positions = list(filter( lambda x: x.symbol == ticker, all_positions ))

    # market is open & we have a successful recommendation return -> apply trading logic
    if latest_recommendation['status'] == 'SUCCESS' and clock.is_open:

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
        # IF no existing positions -> place an order for 50% of market value
        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 


        if not ticker_positions:
            print(STR_PAD, 'No existing positions... we will try to execute your first position.', STR_PAD)

            notional_amt = non_margin_buying_power/2

            # execute position only if it is a buy recommendation & buying power > 0 
            if latest_recommendation['position'] == 1 and non_margin_buying_power > 0:
                execute_order(ticker, notional_amt)
            # do nothing if sell recommendation
            else:
                if non_margin_buying_power <= 0:
                    print(f'ORDER NOT REQUESTED: insufficient buying power...')
                else:
                    print(f'ORDER NOT REQUESTED: no buy recommendation for today...')


        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
        # IF POSITION EXISTS -> sell if sell recommendation, otherwise buy or hold
        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 


        else:
            print(STR_PAD, 'Based on your existing position, we will apply our algorithm.', STR_PAD)

            # liquidate everything if sell recommendation
            if latest_recommendation['position'] == 0:
                try:
                    client.close_position(ticker)
                except:
                    print('ERROR: cannot close position since no position exists.')
            
            # if recommendation is a buy
            else:

                # get relative difference between SMA low and SMA high
                rel_diff = latest_recommendation['SMA_Low']/latest_recommendation['SMA_High']-1

                # scale the relative difference out with respect to 30% relative difference max
                # i.e. if relative difference exceeds 30%, its scaled relative diff caps at 100%
                scaled_rel_diff = min(rel_diff/.3, 1)

                # get notional order amount
                notional_amt = (1-scaled_rel_diff)*non_margin_buying_power/2

                execute_order(ticker, notional_amt)

    else:
        print('Market not open!')
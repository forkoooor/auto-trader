#!/usr/bin/env python

import pandas as pd
import pytz

from backtesting import Backtest, Strategy
from datetime import datetime
from numpy import arange
import pandas_datareader as web

# TODO: Implement strategy that waits a certain number of bars before exceuting a stop loss order.
    # Right now, even with an 8% stop loss, one could get wicked out of operation with a single trade.
# TODO: Implement strategy that waits a certain number of bars before exceuting a buy order.

class VolatilityStrategy(Strategy):
    max_idle_period = 10
    stop_limit_basis_points = 250
    trade_goal_basis_points = 250
    confirmations_required = 2

    def init(self):
        self.bars_since_move = 0

        self.holding = True
        self.last_buy_price = self.current_price
        self.target_price = self.data.Close[0] + (self.data.Close[0] * self.trade_goal)

        self.confirmations = [0,0]

    @property
    def current_price(self):
        return self.data.Close[-1]

    @property
    def trade_goal(self):
        return self.trade_goal_basis_points / 10000

    @property
    def stop_loss_price(self):
        return self.last_buy_price - (self.last_buy_price * (self.stop_limit_basis_points / 10000))

    def next(self):
        self.bars_since_move += 1

        force_buy = False
        force_sell = False

        # determine if this bar is up or down from the previous one
        if self.data.Close[-1] > self.data.Close[-2]:
            self.confirmations[0] += 1
            self.confirmations[1] = 0
        elif self.data.Close[-1] < self.data.Close[-2]:
            self.confirmations[1] += 1
            self.confirmations[0] = 0

        if self.holding:
            force_sell = self.current_price <= self.stop_loss_price and self.confirmations[1] >= self.confirmations_required

            if self.current_price >= self.target_price or force_sell:
                self.bars_since_move = 0
                self.holding = False
                self.target_price = self.current_price - (self.current_price * self.trade_goal)

                self.sell()
        else:
            force_buy = self.bars_since_move >= self.max_idle_period and self.confirmations[0] >= self.confirmations_required

            if self.current_price <= self.target_price or force_buy:
                self.bars_since_move = 0
                self.holding = True
                self.target_price = self.current_price + (self.current_price * self.trade_goal)
                self.last_buy_price = self.current_price

                self.buy(
                    tp=self.target_price,
                    sl=self.stop_loss_price
                )

def get_data():
    start=datetime(2022, 1, 1, 0, 0, 0, tzinfo=pytz.timezone('UTC'))
    end=datetime(2022, 8, 26, 0, 0, 0, tzinfo=pytz.timezone('UTC'))

    PAIR = web.DataReader('ETH-USD', 'yahoo', start, end)

    return PAIR

def main():
    PAIR = get_data()

    backtest = Backtest(PAIR, VolatilityStrategy)

    results = backtest.optimize(
        stop_limit_basis_points=range(50, 500, 50),
        trade_goal_basis_points=range(50, 500, 50),
        max_idle_period=range(6, 288, 6),
        maximize='Equity Final [$]')

    print(results)

    backtest.plot(results=results)


if __name__ == '__main__':
    main()
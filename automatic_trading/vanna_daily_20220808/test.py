import os
import pandas as pd
import numpy as np
from scipy.stats import percentileofscore
import warnings
import datetime
import time
import math
import talib as ta
import tcoreapi_mq as t
from matplotlib import pyplot as plt
from tabulate import tabulate
from pylab import mpl
from matplotlib import ticker

mpl.rcParams['font.sans-serif'] = ['SimHei']
mpl.rcParams['axes.unicode_minus'] = False
warnings.simplefilter('ignore')
core = t.TCoreZMQ(quote_port="51864", trade_port="51834")
BrokerID = 'M2_PAPERTRADE'
Account = 'y000-mvtuat09'

orders_obj = {
    "Symbol": 'TC.O.SSE.510050.202209.C.2.75',
    "BrokerID": BrokerID,
    "Account": Account,
    "TimeInForce": "1",
    "Side": "1",
    "OrderType": "15",
    "OrderQty": "50",
    'Synthetic': '1',
    "PositionEffect": "4",
    "SelfTradePrevention": "3",
    'ChasePrice': '1T|5|1|C'
}
ordid = core.NewOrder(orders_obj)



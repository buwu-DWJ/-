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
from dwj_tools.Lib_OptionCalculator import CalVannaCall
from dwj_tools.Lib_OptionCalculator import CalVannaPut
from dwj_tools.Lib_OptionCalculator import CalIVPut
from dwj_tools.Lib_OptionCalculator import CalDeltaPut
from dwj_tools.Lib_OptionCalculator import CalIVCall
from dwj_tools.Lib_OptionCalculator import CalDeltaCall
from dwj_tools.Lib_OptionCalculator import CalThetaCall
from dwj_tools.Lib_OptionCalculator import CalThetaPut
from dwj_tools.Lib_OptionCalculator import CalVegaCall
from dwj_tools.Lib_OptionCalculator import CalVegaPut
from pylab import mpl
from matplotlib import ticker

mpl.rcParams['font.sans-serif'] = ['SimHei']
mpl.rcParams['axes.unicode_minus'] = False
warnings.simplefilter('ignore')
core = t.TCoreZMQ(quote_port="51864", trade_port="51834")
thisDir = os.path.dirname(__file__)

tradingday = pd.read_hdf('tradingday.h5')
all_day = list(tradingday['date'])
def update():
    interval = '1K'
    try:
        old_df = pd.read_hdf('df_min.h5')
        start_idx = all_day.index(old_df.index[-1]) + 1
    except:
        old_df = False
        start_idx = 4846
    for i in all_day[start_idx:]:
        csd_date = i.strftime('%Y%m%d')
        option_symbols = core.QueryAllInstrumentInfo('Options', csd_date)
        while option_symbols['Success'] != 'OK':
            option_symbols = core.QueryAllInstrumentInfo('Options', csd_date)
        for month in [0, 1, 2, 3]:
            tau = int(option_symbols['Instruments']['Node'][0]
                      ['Node'][0]['Node'][2+month]['Node'][0]['TradeingDays'][0])
            for j, crt_symbol in enumerate(option_symbols['Instruments']['Node'][0]['Node'][0]['Node'][2+month]['Node'][0]['Contracts']):
                new_option_data = pd.DataFrame(core.SubHistory(
                    crt_symbol, interval, csd_date+'00', csd_date+'07'))
                temp_date = len(new_option_data) * [csd_date]
                flag = len(new_option_data) * ['C']
                new_option_data['date'] = temp_date
                new_option_data['flag'] = flag
                new_option_data['tau'] = tau
                if j == 0 and month == 0:
                    df = new_option_data
                else:
                    df = df.append(new_option_data)
            for k in option_symbols['Instruments']['Node'][0]['Node'][0]['Node'][2+month]['Node'][1]['Contracts']:
                new_option_data = pd.DataFrame(core.SubHistory(
                    k, interval, csd_date+'00', csd_date+'07'))
                temp_date = len(new_option_data) * [csd_date]
                flag = len(new_option_data) * ['P']
                new_option_data['date'] = temp_date
                new_option_data['flag'] = flag
                new_option_data['tau'] = tau
                df = df.append(new_option_data)
        close = np.array(pd.to_numeric(df['Close']))
        df['Close'] = close


c = list(tradingday['date'])



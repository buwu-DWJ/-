#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   dwj_utils.py
@Time    :   2022/12/02 11:19:39
@Author  :   DingWenjie
@Contact :   359582058@qq.com
@Doc    :    辅助函数:
                 
'''


import sys
import os
import pandas as pd
import numpy as np
import warnings
import datetime
import time
import math
import talib as ta
import tcoreapi_mq as t
from matplotlib import pyplot as plt
from pylab import mpl
sys.path.append("..")
from automatic_trading import *


mpl.rcParams['font.sans-serif'] = ['SimHei']
mpl.rcParams['axes.unicode_minus'] = False
thisDir = os.path.dirname(__file__)
warnings.simplefilter('ignore')
core = t.TCoreZMQ(quote_port="51864", trade_port="51834")
tradingday = pd.read_excel(r'C:\Users\dingwenjie\Desktop\demo\备份\-\automatic_trading\vanna_daily_20220808\tradingday.xlsx')['date']
tradingday_list = [a.strftime('%Y%m%d') for a in tradingday]


def get_und_str(symbol, type_='und'):
    if symbol=='510050':
        if type_=='und':
            symbol_str = 'TC.S.SSE.510050'
        else:
            symbol_str = 'TC.F.U_SSE.510050.'
    elif symbol=='510300':
        if type_=='und':
            symbol_str = 'TC.S.SSE.510300'
        else:
            symbol_str = 'TC.F.U_SSE.510300.'
    elif symbol=='510500':
        if type_=='und':
            symbol_str = 'TC.S.SSE.510050'
        else:
            symbol_str = 'TC.F.U_SSE.510500.'
    elif symbol=='159915':
        if type_=='und':
            symbol_str = 'TC.S.SZSE.159915'
        else:
            symbol_str = 'TC.F.U_SZSE.159915.'
    return symbol_str


def cpt_hv_given_date(symbol, crt_date, month=0, interval='5K', crt_idx=0):
    '''计算同期hv
    Args:
        interval: '5K','1K'
    '''
    option_info = core.QueryAllInstrumentInfo('Options', crt_date)
    while option_info['Success'] != 'OK':
        option_info = core.QueryAllInstrumentInfo('Options', crt_date)
    csd_month = option_info['Instruments']['Node'][0]['Node'][0]['Node'][2+month]['CHS']
    tau = int(option_info['Instruments']['Node'][0]['Node'][0]['Node'][2+month]['Node'][0]['TradeingDays'][0])
    end_idx = tradingday_list.index(crt_date)
    start_idx = end_idx-tau
    start_date = tradingday_list[start_idx]
    df = pd.DataFrame(core.SubHistory(get_und_str(symbol), interval, start_date+'00', crt_date+'07'))
    close = np.log(pd.to_numeric(df['Close']).pct_change()+1)
    hv = np.sqrt(((close[1+crt_idx:1+48*tau+crt_idx].values)**2).sum()/tau*240)
    return hv
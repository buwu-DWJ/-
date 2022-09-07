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
BrokerID = 'MVT_SIM2'
Account = '1999_2-0070889'






strike_list = list(np.arange(2.0, 2.95, 0.05)) + \
        list(np.arange(3.0, 4.0, 0.1))
strike_list = [round(a, 2) for a in strike_list]
crt_position_only = core.QryPosition(BrokerID+'-'+Account)
strike_of_position = []
month_of_position = []
for position in crt_position_only:
    if round(float(position['StrikePrice']), 2) not in strike_of_position:
        strike_of_position += [round(float(position['StrikePrice']), 2)]
    if int(position['Month']) not in month_of_position:
        month_of_position += [int(position['Month'])]
old_min_id = strike_list.index(min(strike_of_position))
old_max_id = strike_list.index(max(strike_of_position))
csd_strike_list = strike_list[old_min_id:old_max_id+1]
old_min_id = strike_list.index(min(strike_of_position))
month_of_position.sort()
position_array = np.zeros(
    (2*len(month_of_position), len(csd_strike_list)))
position_array = pd.DataFrame(position_array).replace(0, '-')
for position in crt_position_only:
    month_index = month_of_position.index(int(position['Month']))
    if position['CallPut'] == 'C':
        row_id = 2 * month_index
    else:
        row_id = 2 * month_index + 1
    column_id = csd_strike_list.index(
        round(float(position['StrikePrice']), 2))
    position_tag = 0
    if position['Side'] == '1':
        position_tag = 1
    else:
        position_tag = -1
    position_array.iloc[row_id, column_id] = str(
        position_tag * int(position['Quantity']))
index_ = []
for i, csd_month in enumerate(month_of_position):
    index_ += [str(csd_month)+'call', str(csd_month)+'put']
df_position = pd.DataFrame(position_array)
df_position.index = index_
df_position.columns = csd_strike_list
today = datetime.date.today()
today_str = today.strftime('%Y%m%d')
code_call25, code_call65, code_put25, code_put65 = 0, 0, 0, 0
size_call25, size_call_65, size_put25, size_put65 = 0, 0, 0, 0
get_codecall25, get_codecall65, get_codeput25, get_codeput65 = False, False, False, False
i = 0
while True:
    temp_month = df_position.index[i][:6]
    try:
        crt_synf = core.SubHistory(f'TC.F.U_SSE.510050.{temp_month}', '5K', today_str+'00', today_str+'07')
        crt_synf = float(list(pd.DataFrame(crt_synf)['Close'])[-1])
    except:
        print('读取合成期货数据失败,重试')
        time.sleep(3)
        crt_synf = core.SubHistory(f'TC.F.U_SSE.510050.{temp_month}', '5K', today_str+'00', today_str+'07')
        crt_synf = float(list(pd.DataFrame(crt_synf)['Close'])[-1])
    for j in csd_strike_list:
        if df_position[j][i] != '-' and j<=crt_synf and code_call65==0 and not get_codecall65:
            code_call65 = f'TC.O.SSE.510050.{temp_month}.C.{j}'
            size_call_65 = int(df_position[j][i])
        if df_position[j][i] != '-' and j>crt_synf and not get_codecall25:
            code_call25 = f'TC.O.SSE.510050.{temp_month}.C.{j}'
            size_call25 = int(df_position[j][i])
        if df_position[j][i+1] != '-' and j<=crt_synf and code_put25==0 and not get_codeput25:
            code_put25 = f'TC.O.SSE.510050.{temp_month}.P.{j}'
            size_put25 = int(df_position[j][i+1])
        if df_position[j][i+1] != '-' and j>crt_synf and not get_codeput65:
            code_put65 = f'TC.O.SSE.510050.{temp_month}.P.{j}'
            size_put65 = int(df_position[j][i+1])
    i += 2
    if i>=len(df_position):
        break
    elif i>=2:
        if code_call25!=0:
            get_codecall25 = True
        if code_call65!=0:
            get_codecall65 = True
        if code_put25!=0:
            get_codeput25 = True
        if code_put65!=0:
            get_codeput65 = True




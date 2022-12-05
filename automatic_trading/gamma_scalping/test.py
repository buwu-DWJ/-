import sys
import os
import pandas as pd
import numpy as np
from scipy.stats import percentileofscore
from func_timeout import func_set_timeout
import warnings
import datetime
import time
import math
import talib as ta
import dwj_tools.read_hdf as r
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
    df = pd.DataFrame(core.SubHistory('TC.S.SSE.510050', interval, start_date+'00', crt_date+'07'))
    close = np.log(pd.to_numeric(df['Close']).pct_change()+1)
    hv = np.sqrt(((close[1+crt_idx:1+48*tau+crt_idx].values)**2).sum()/tau*240)
    return hv


def get_option_code(true_option_call, true_option_put):
    '''
    获取当前时刻中|delta|为0.5和-0.5的合约
    Args:
        true_option_call: 当前时刻call
        true_option_put: 当前时刻put
    Return:
        code_call_25, code_call_65, code_put_25, code_put_65
        get_data: 实值合约delta是否超出0.65给定的范围, 若超出-False, 反之-True
    '''
    tol = 0.1
    id_call_50 = np.abs(true_option_call['delta']-0.5).argmin()
    id_put_50 = np.abs(true_option_put['delta']+0.5).argmin()
    code_call_50 = true_option_call['symbol'][id_call_50]
    code_put_50 = true_option_put['symbol'][id_put_50]
    return code_call_50, code_put_50


def get_size(df, code_list, etf_close, flag, cash_vega=30000):
    '''计算各个合约手数
    Args:
        df: 期权数据
        code_list: 合约列表, 分别为call_50, put_50
    '''
    x = Symbol('x')  # call50
    y = Symbol('y')  # put50
    df_call50 = df.iloc[list(df['symbol'] == code_list[0]), :]
    df_put50 = df.iloc[list(df['symbol'] == code_list[1]), :]
    if flag=='short':
        cash_gamma = -0.05 * 10000000
    elif flag=='long':
        cash_gamma = 0.05 * 10000000
    a = solve(
        [float(df_call50['delta'])*x+float(df_put50['delta'])*y,
         float(df_call50['gamma'])*x+float(df_put50['gamma'])*y-cash_gamma/10000/etf_close
         ],
        [x, y]
    )
    size_call50 = math.ceil(a[x])
    size_put50 = math.ceil(a[y])
    return size_call50, size_put50


def get_price_list(df, code_list):
    '''获取code_list中合约当前的价格
    '''
    print(df)
    print(code_list)
    price_list = []
    for csd_code in code_list:
        price_list += [float(df.iloc[list(df['symbol']
                                          == csd_code), :]['close'])]
    return price_list


def open_position(cash, code_dict, all_df, df, time_idx, flag, with_commission):
    '''开仓
    Args:
        value:  净值list
        df_50/300:  当日所有期权数据
        time_idx:  当前时刻
        flag:  多空方向
        with_commission:  是否考虑手续费
    Return:
        code_dict:  开仓合约size及开仓价格的dataframe
        value:  更新后的净值list
    '''
    csd_month = 0
    csd_df = df[df.index == time_idx].reset_index(drop=True)
    csd_tau = csd_df['tau'].drop_duplicates().values[csd_month]
    csd_df = csd_df.iloc[csd_df.index[csd_df['tau'] == csd_tau], :]
    true_option_call = csd_df.loc[list(
        csd_df['flag'] == 'C'), :].reset_index(drop=True)
    true_option_put = csd_df.loc[list(
        csd_df['flag'] == 'P'), :].reset_index(drop=True)
    code_call, code_put = get_option_code(true_option_call, true_option_put)
    code_list = [code_call, code_put]
    print(code_list)
    size_call, size_put = get_size(csd_df, code_list, cash_vega=target_cash_vega-crt_cash_vega)
    size_list = [size_call, size_put]
    print(f'call {size_list[0]}手, put {size_list[1]}手')
    price_list = get_price_list(csd_df, code_list)
    while True in np.isnan(price_list):
        print('\n'*1000+'当前收盘价有问题')
        time_idx += 1
        csd_df = all_df[all_df.index == time_idx].reset_index(drop=True)
        csd_tau = csd_df['tau'].drop_duplicates().values[csd_month]
        csd_df = csd_df.iloc[csd_df.index[csd_df['tau'] == csd_tau], :]
        price_list = get_price_list(csd_df, code_list)
    print('目前检测开仓中持仓变化')
    print('open_position变换仓位前持仓为')
    print(code_dict)
    for i, temp_code in enumerate(code_list):
        in_it = False
        if type(code_dict)!=int:
            for j, temp_symbol in enumerate(code_dict['symbol'].values):
                if temp_code==temp_symbol:
                    in_it = True
                    code_dict['size'][j] = code_dict['size'][j] + size_list[i]
                    break
        else:
            code_dict = pd.DataFrame()
        if not in_it:
            new_df = pd.DataFrame([str(temp_code), float(price_list[i]), float(size_list[i])]).T
            new_df.columns = ['symbol', 'price', 'size']
            code_dict = code_dict.append(new_df)
    print('open_position变换仓位后持仓为')
    print(f'当前价格为{price_list}')
    print(code_dict)
    code_dict.reset_index(drop=True, inplace=True)
    print(code_dict)
    cash = cash - np.array(size_list).dot(np.array(price_list)*10000-2)
    return code_dict, cash


def change_position(cash, code_dict, all_df, df, time_idx, flag, target_cash_vega, with_commission):
    csd_df = df[df.index == time_idx].reset_index(drop=True)
    csd_month = 0
    csd_tau = csd_df['tau'].drop_duplicates().values[csd_month]
    csd_df = csd_df.iloc[csd_df.index[csd_df['tau'] == csd_tau], :]
    true_option_call = csd_df.loc[list(
        csd_df['flag'] == 'C'), :].reset_index(drop=True)
    true_option_put = csd_df.loc[list(
        csd_df['flag'] == 'P'), :].reset_index(drop=True)
    code_call, code_put = get_option_code(true_option_call, true_option_put)
    code_list = [code_call, code_put]
    print('调仓所用的合约为')
    print(code_list)
    size_call, size_put = get_size(csd_df, code_list, target_cash_vega)
    size_list = [size_call, size_put]
    print(f'调仓,目标仓位 call {size_list[0]}手, put {size_list[1]}手')
    print(code_dict)
    for i, temp_code in enumerate(code_list):
        in_it = False
        for j, temp_symbol in enumerate(code_dict['symbol'].values):
            if temp_code==temp_symbol:
                in_it = True
                code_dict['size'][j] = code_dict['size'][j] - size_list[i]
                break
        if not in_it:
            new_df = pd.DataFrame([str(temp_code), 0, -float(size_list[i])]).T
            new_df.columns = ['symbol', 'price', 'size']
            code_dict = code_dict.append(new_df)
        print(code_dict)
    code_dict.reset_index(drop=True, inplace=True)
    price_list = get_price_list(csd_df, code_dict['symbol'].values)
    while True in np.isnan(price_list):
        print('\n'*1000+'当前收盘价有问题')
        time_idx += 1
        csd_df = all_df[all_df.index == time_idx].reset_index(drop=True)
        csd_tau = csd_df['tau'].drop_duplicates().values[csd_month]
        csd_df = csd_df.iloc[csd_df.index[csd_df['tau'] == csd_tau], :]
        price_list = get_price_list(csd_df, code_dict['symbol'].values)
    code_dict['price'] = price_list
    print('调仓最后所用的code_dict为')
    print(code_dict)
    for i in range(len(code_dict)):
        cash += code_dict['size'].values[i]*(code_dict['price'].values[i]*10000-2)
    code_dict = pd.DataFrame()
    code_dict['symbol'] = code_list
    price_list = get_price_list(csd_df, code_dict['symbol'].values)
    code_dict['price'] = price_list
    code_dict['size'] = size_list
    print(code_dict)
    return code_dict, cash


def close_position(value, all_df, df, cash, code_dict=0, time_idx=0, with_commission=1, jump_tag=False):
    '''平仓或计算净值
    Args:
        jump_tag: 日内有交易则jumptag=True, 用以判断是否加入手续费
    Return:
        value:
        cash:
    '''
    value_copy = copy.deepcopy(value)
    csd_df = df[df.index == time_idx].reset_index(drop=True)
    if not jump_tag:
        csd_df = df[df.index == 235].reset_index(drop=True)
    price_list = get_price_list(csd_df, list(code_dict['symbol']))
    temp_code_dict = code_dict.copy(deep=True)
    temp_code_dict['crt_close'] = price_list
    print('当前收盘价')
    while True in np.isnan(price_list):
        print('\n'*1000+'当前收盘价有问题')
        time_idx += 1
        csd_df = all_df[all_df.index == time_idx].reset_index(drop=True)
        price_list = get_price_list(csd_df, list(code_dict['symbol']))
        temp_code_dict['crt_close'] = price_list
    print(np.array(price_list))
    print('上次收盘价')
    print(np.array(temp_code_dict['price'].values))
    cash = cash + float((np.array(list(temp_code_dict['size'].values))*(
        np.array(list(temp_code_dict['crt_close'].values)))*10000).sum())
    if jump_tag:
        cash = cash - \
            float(np.abs(temp_code_dict['size']).sum()*2) * with_commission
    value_copy += [cash]
    temp_code_dict['price'] = temp_code_dict['crt_close']
    return value_copy, cash, temp_code_dict


def bt_gamma(start_date, end_date):
    '''
    Args:
    Return:
    '''
    cash = 10000000
    code_dict = 0
    value = [cash]
    having_position = False
    flag = 0
    tradingday = pd.read_excel(r'C:\Users\dingwenjie\Desktop\demo\备份\-\automatic_trading\vanna_daily_20220808\tradingday.xlsx')['date']
    date_list = [i.strftime('%Y%m%d') for i in tradingday]
    start_idx = date_list.index(start_date)
    end_idx = date_list.index(end_date)
    csd_time_horizon = date_list[start_idx:end_idx]
    firmed_csd_range = [int((i+1)*30-1) for i in range(7)] + [235]
    start_etf_close = 0
    target_cash_gamma = 0
    for i, crt_date in enumerate(csd_time_horizon):
        forced_close = False
        print(f'\n\n\n\n当前日期{crt_date}')
        all_df, _, _ = r.read_data_dogsk('510050', str(crt_date))
        df, und, synf = r.read_data_dogsk('510050', str(crt_date), firmed_csd_range)
        crt_tau = df['tau'].drop_duplicates(keep='first').tolist()[0]
        print(f'今日tau为:{crt_tau}')
        if crt_tau == 0:  # 强制平仓
            print(f'到期日,强制平仓')
            if flag != 0:
                value, cash, _ = close_position(
                        value, all_df, df, cash, code_dict, crt_range, 1, jump_tag=True)
            else:
                value += [value[-1]]
                print(f'今日value:{value[-1]}')
                flag = 0
                code_dict = 0
                having_position = False
                print(f'\n今日强制平仓,value:{value[-1]}')
                continue
        for j, crt_range in enumerate(firmed_csd_range[:-1]):
            if having_position and flag=='long':
                if :  # 判断出场

                elif:  # 判断平delta

            elif having_position and flag=='short':
                if :  # 判断平delta


            elif not having_position and crt_tau>5:
                if :  # 判断开仓

            elif not having_position and 0<crt_tau<=5:
                # 进行开仓


        if not having_position:
            value += [cash]
        else:
            print('今日结束时的持仓情况为:')
            print(code_dict)
            value, _, _ = close_position(
                    value, all_df, df, cash, code_dict, crt_range, 1, jump_tag=False)
            print(f'今日value:{value[-1]}')



                code_dict, cash = open_position(cash, code_dict, all_df, df, crt_range, flag, crt_cash_vega, target_cash_vega,  1)
                print(f'开仓后cash变为: {cash:.0f}')
                print('开仓后持仓变为')
                print(code_dict)
            elif (np.abs(crt_cash_vega)<np.abs(target_cash_vega)*scale) and scale!=1:
                code_dict, cash = change_position(cash, code_dict, all_df, df, crt_range, flag, target_cash_vega, 1)





    date = csd_time_horizon
    data = value[1:]
    index_j = np.argmax(np.maximum.accumulate(data) - data)  # 结束位置
    index_i = np.argmax(data[:index_j])  # 开始位置
    d = data[index_j]/data[index_i]-1  # 最大回撤
    print(len(date))
    print(len(data))
    print(index_i)
    print(index_j)
    print(
        f'最大回撤开始时间为{date[index_i-1]},结束时间为{date[index_j-1]},\n最大回撤为{d*100:.2f}%,')
    rtn = pd.DataFrame()
    rtn['close'] = data
    rtn.index = date
    daily_rtn = rtn['close'].pct_change()
    daily_rtn.dropna(inplace=True)
    sharp = daily_rtn.mean()/daily_rtn.std()*np.sqrt(245)
    annual_return = (value[-1]/10000000 - 1)/len(date) * 245
    print(f'年化{annual_return*100:.1f}%')
    return value, date, d, annual_return, sharp, count


















































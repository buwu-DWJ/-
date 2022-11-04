#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   kurtosis_20221104.py
@Time    :   2022/11/04 11:13:13
@Author  :   DingWenjie
@Contact :   359582058@qq.com
@Desc    :   峰度策略, 仅供测试
             50, 300次月峰度均值回复, 买卖两边的strangle(或加入straddle)
'''


import sys
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
thisDir = os.path.dirname(__file__)
warnings.simplefilter('ignore')
core = t.TCoreZMQ(quote_port="51864", trade_port="51834")


def get_crt_timescale():
    '''
    获得当前时间下最新数据在Subhistory时间节点中对应的起始结束字符串
    '''
    hour = time.localtime().tm_hour
    if hour<=9:
        start_str, end_str = '00', '02'
    elif hour==10:
        start_str, end_str = '02', '03'
    elif hour==11:
        start_str, end_str = '03', '04'
    elif hour==13:
        start_str, end_str = '05', '06'
    elif hour>=14:
        start_str, end_str = '06', '07'
    return start_str, end_str


def get_option_data(is_test=False):
    '''获取给定日期的期权数据
    Args:
        interval: 数据间隔, 默认五分钟
    Return:
        df
    '''
    interval='DOGSK'
    today = datetime.date.today()
    csd_date = today.strftime('%Y%m%d')
    option_symbols = core.QueryAllInstrumentInfo('Options', csd_date)
    len_of_df = 0
    start_str, end_str = get_crt_timescale()
    if is_test:
        start_str, end_str = '00', '07'
    while option_symbols['Success'] != 'OK':
        option_symbols = core.QueryAllInstrumentInfo('Options', csd_date)
    for month in [0, 1, 2, 3]:
        print(f'当前month {month}')
        tau = int(option_symbols['Instruments']['Node'][0]
                  ['Node'][0]['Node'][2+month]['Node'][0]['TradeingDays'][0])
        for j, crt_symbol in enumerate(option_symbols['Instruments']['Node'][0]['Node'][0]['Node'][2+month]['Node'][0]['Contracts']):
            new_option_data = pd.DataFrame(core.SubHistory(
                crt_symbol, interval, csd_date+start_str, csd_date+end_str))
            temp_date = len(new_option_data) * [csd_date]
            flag = len(new_option_data) * ['C']
            new_option_data['date'] = temp_date
            new_option_data['flag'] = flag
            new_option_data['tau'] = tau
            if j == 0 and month == 0:
                df = new_option_data
                len_of_df = len(df)
            else:
                df = df.append(new_option_data.iloc[:len_of_df,:])
        for k in option_symbols['Instruments']['Node'][0]['Node'][0]['Node'][2+month]['Node'][1]['Contracts']:
            new_option_data = pd.DataFrame(core.SubHistory(
                k, interval, csd_date+start_str, csd_date+end_str))
            temp_date = len(new_option_data) * [csd_date]
            flag = len(new_option_data) * ['P']
            new_option_data['date'] = temp_date
            new_option_data['flag'] = flag
            new_option_data['tau'] = tau
            df = df.append(new_option_data.iloc[:len_of_df,:])
        print(len(df))
    df.rename(columns={'de': 'delta','p': 'Close','ve':'vega','th':'theta'}, inplace=True)
    close = np.array(pd.to_numeric(df['Close']))
    df['Close'] = close
    delta = np.array(pd.to_numeric(df['delta']))/100
    df['delta'] = delta
    vega = np.array(pd.to_numeric(df['vega']))
    df['vega'] = vega
    theta = np.array(pd.to_numeric(df['theta']))
    df['theta'] = theta
    return df


def choose_option_given_month(option, month=0):
    '''根据get_option_data得到的原始期权数据筛选给定月份的call与put的最新时刻数据
    Args:
        option: 原始期权数据
        Month: 目标月份
    Return:
        true_option_call: 带有希腊值数据的call
        true_option_put: ...
    '''
    crt_tau = option['tau'].drop_duplicates(keep='first').tolist()[month]
    newest_index = option.index.drop_duplicates(keep='first').tolist()[-1]
    true_option = option.iloc[(option.index == newest_index).tolist()]
    true_option = true_option.iloc[list(true_option['tau'] == crt_tau)]
    true_option_call = true_option.loc[list(
        true_option['flag'] == 'C'), :].reset_index(drop=True)
    true_option_put = true_option.loc[list(
        true_option['flag'] == 'P'), :].reset_index(drop=True)
    return true_option_call, true_option_put


def get_option_code(true_option_call, true_option_put):
    '''
    获取当前时刻中|delta|为0.25和0.65的合约
    Args:
        true_option_call: 当前时刻call
        true_option_put: 当前时刻put
    Return:
        code_call_25, code_call_65, code_put_25, code_put_65
        get_data: 实值合约delta是否超出0.65给定的范围, 若超出-False, 反之-True
    '''
    tol = 0.15
    id_call_25 = np.abs(true_option_call['delta']-0.25).argmin()
    id_call_65 = np.abs(true_option_call['delta']-0.65).argmin()
    id_put_25 = np.abs(true_option_put['delta']+0.25).argmin()
    id_put_65 = np.abs(true_option_put['delta']+0.65).argmin()
    code_call_25 = true_option_call['Symbol'][id_call_25]
    code_call_65 = true_option_call['Symbol'][id_call_65]
    code_put_25 = true_option_put['Symbol'][id_put_25]
    code_put_65 = true_option_put['Symbol'][id_put_65]
    if np.abs(true_option_call['delta']-0.65).min() > tol or np.abs(true_option_put['delta']+0.65).min() > tol:
        get_data = False
    else:
        get_data = True
    return code_call_25, code_call_65, code_put_25, code_put_65, get_data


def get_crt_account_cashvanna(BrokerID='MVT_SIM2', Account='1999_2-0070624', log=False):
    '''
    获取当前资金账户的cashvanna值
    '''
    having_position = False
    crt_position = core.QryPositionTracker()
    crt_cash_vanna = 0
    for csd_data in crt_position['Data']:
        if csd_data['BrokerID'] == BrokerID and csd_data['Account'] == Account and csd_data['SubKey'] == 'Total':
            having_position = True
            crt_cash_vanna = float(csd_data['1%$Vanna'])
            if log:
                print(f'当前cashvanna为{crt_cash_vanna:.0f}')
            break
    return crt_cash_vanna, having_position


def open_position_given_cash_vanna(option, crt_cash_vanna, target_cash_vanna, log, BrokerID, Account, a, b, forced_next=False, theta_vega_positive=3, theta_vega_negative=4.5):
    '''开仓, 一直做到给定的cashvanna
    Args:
        crt_cash_vanna: 当前账户的cashvanna
        target_cash_vanna: 目标cashvanna
        a, b: a为每次交易一组期权中实值的手数, b为一组中虚值的手数
        forced_next: bool, 是否强制使用次月进行开仓(如到期日需要换月的情形)
        theta_vega_positive/negative: 近月平值的|theta/vega|超出该值时, 换用次月合约进行开仓
    '''
    if forced_next:
        true_option_call, true_option_put = choose_option_given_month(
            option=option, month=1)
        code_call_25, code_call_65, code_put_25, code_put_65, get_data = get_option_code(
            true_option_call, true_option_put)
    else:
        true_option_call, true_option_put = choose_option_given_month(
            option=option, month=0)
        code_call_25, code_call_65, code_put_25, code_put_65, get_data = get_option_code(
            true_option_call, true_option_put)
        iiidd = np.abs(np.array(true_option_call['Close'])
                       - np.array(true_option_put['Close'])).argmin()
        vega_atm = float(
            true_option_call['vega'][iiidd]+true_option_put['vega'][iiidd])/2
        theta_atm = float(
            true_option_call['theta'][iiidd]+true_option_put['theta'][iiidd])/2
        if vega_atm==0:
            vega_atm = 0.00001
        if log:
            print(
                f'当前平值vega为{vega_atm:.5f},平值theta为{theta_atm:.5f},比值为{np.abs(theta_atm/vega_atm):.1f}')
        if (target_cash_vanna > 0 and np.abs(theta_atm/vega_atm) > theta_vega_positive) or (target_cash_vanna < 0 and np.abs(theta_atm/vega_atm) > theta_vega_negative):
            if log:
                print('theta/vega超出限制,改用次月合约')
            true_option_call, true_option_put = choose_option_given_month(
                option, month=1)
        elif not get_data:
            if log:
                print('近月期权delta不在范围内,考虑次月期权')
            true_option_call, true_option_put = choose_option_given_month(
                option, month=1)
        code_call_25, code_call_65, code_put_25, code_put_65, get_data = get_option_code(
            true_option_call, true_option_put)
    code_list = [code_put_25, code_call_65, code_call_25, code_put_65]
    size_list = [b, a, b, a]
    if log:
        print(
            f'今日要做的目标期权分别为\ndelta25处的call:{code_call_25}\ndelta65处的call:{code_call_65}\ndelta25处的put:{code_put_25}\ndelta65处的put:{code_put_65}')
    do_trading = input('是否要进行下单,如果要继续请输入1:')
    if do_trading!='1':
        sys.exit('停止脚本')
    if target_cash_vanna > 0:
        side_list = [2, 2, 1, 1]
    else:
        side_list = [1, 1, 2, 2]
    while np.abs(crt_cash_vanna) < np.abs(target_cash_vanna):
        # 下单顺序, 先虚值再实值, 先call后put
        # 虚值单, 用中间价追价
        orders_obj_call_25 = {
            "Symbol": code_list[0],
            "BrokerID": BrokerID,
            "Account": Account,
            "TimeInForce": "1",
            "Side": f"{side_list[0]}",
            "OrderType": "11",
            'Synthetic': '1',
            "OrderQty": f"{size_list[0]}",
            "PositionEffect": "4",
            "SelfTradePrevention": "3",
            'ChasePrice': '1T|3|2|M'
        }
        orders_obj_put_25 = {
            "Symbol": code_list[2],
            "BrokerID": BrokerID,
            "Account": Account,
            "TimeInForce": "1",
            "Side": f"{side_list[2]}",
            "OrderType": "11",
            'Synthetic': '1',
            "OrderQty": f"{size_list[2]}",
            "PositionEffect": "4",
            "SelfTradePrevention": "3",
            'ChasePrice': '1T|3|2|M'
        }
        ordid_call_25 = core.NewOrder(orders_obj_call_25)
        ordid_put_25 = core.NewOrder(orders_obj_put_25)
        not_finish_call_25 = True
        not_finish_put_25 = True
        while True:
            if core.getorderinfo(ordid_call_25) and core.getorderinfo(ordid_put_25):
                if core.getorderinfo(ordid_call_25)['ExecType'] == '3' and not_finish_call_25:
                    orders_obj_call_65 = {
                        "Symbol": code_list[1],
                        "BrokerID": BrokerID,
                        "Account": Account,
                        "TimeInForce": "1",
                        "Side": f"{side_list[1]}",
                        "OrderType": "15",
                        'Synthetic': '1',
                        "OrderQty": f"{size_list[1]}",
                        "PositionEffect": "4",
                        "SelfTradePrevention": "3",
                        'ChasePrice': '1T|3|1|M'
                    }
                    ordid_call_65 = core.NewOrder(orders_obj_call_65)
                    not_finish_call_25 = False
                if core.getorderinfo(ordid_put_25)['ExecType'] == '3' and not_finish_put_25:
                    orders_obj_put_65 = {
                        "Symbol": code_list[3],
                        "BrokerID": BrokerID,
                        "Account": Account,
                        "TimeInForce": "1",
                        "Side": f"{side_list[3]}",
                        "OrderType": "15",
                        'Synthetic': '1',
                        "OrderQty": f"{size_list[3]}",
                        "PositionEffect": "4",
                        "SelfTradePrevention": "3",
                        'ChasePrice': '1T|3|1|M'
                    }
                    ordid_put_65 = core.NewOrder(orders_obj_put_65)
                    not_finish_put_25 = False
                if (not not_finish_call_25) and (not not_finish_put_25):
                    break
                time.sleep(0.1)
        while True:
            if core.getorderinfo(ordid_call_65) and core.getorderinfo(ordid_put_65):
                if core.getorderinfo(ordid_call_65)['ExecType']=='3' and core.getorderinfo(ordid_put_65)['ExecType']=='3':
                    break
                time.sleep(0.1)
        crt_cash_vanna, _ = get_crt_account_cashvanna(
            BrokerID=BrokerID, Account=Account)
        if log:
            print(f'当前cashvanna为{crt_cash_vanna:.0f}')
    return


def close_position(BrokerID, Account, log=False, tag='all'):
    '''平仓
    Args:
        tag: 平哪个月份的仓位, 'all'-全平, 'near'-平近月
    '''
    do_trading = input(f'即将进行平仓操作,平仓合约tag为{tag}\n如果要继续平仓,请输入1:')
    if do_trading!='1':
        return
    option_info = core.QueryAllInstrumentInfo('Options')
    hot_month = option_info['Instruments']['Node'][0]['Node'][0]['Node'][2]['CHS']
    pos = core.QryPosition(BrokerID+'-'+Account)
    for csd_position in pos:
        if tag == 'near' and csd_position['Month'] != hot_month:
            continue
        symbol = csd_position['Symbol']
        quantity = csd_position['Quantity']
        if csd_position['Side'] == '1':
            side = '2'
        else:
            side = '1'
        while int(quantity)!=0:
            if int(quantity)>100:
                temp_quantity = '100'
            else:
                temp_quantity = quantity
            orders_obj = {
                "Symbol": symbol,
                "BrokerID": BrokerID,
                "Account": Account,
                "TimeInForce": "1",
                "Side": side,
                "OrderType": "15",
                "OrderQty": temp_quantity,
                "PositionEffect": "4",
                'Synthetic': '1',
                "SelfTradePrevention": "3",
                'ChasePrice': '1T|3|3|M'
            }
            ordid = core.NewOrder(orders_obj)
            while True:
                if core.getorderinfo(ordid):
                    if core.getorderinfo(ordid)['ExecType'] == '3':
                        break
                    time.sleep(0.5)
            quantity = str(int(quantity)-int(temp_quantity))
    if log:
        print('平仓完毕')
    return


def get_skew_hist(log=False):
    '''获取分钟级别历史skew数据,采用权分析合成期货每日去除收盘前5分钟的skew数据
    Args:
        None
    Return:
        在当前路径生成.h5文件
    '''
    etf_hist = core.SubHistory(
        'TC.S.SSE.510050', 'DK', '2020010200', '2030010100')
    date = pd.DataFrame(etf_hist)['Date'].tolist()[:-1]
    for csd_symbol in ['510050', '510300']:
        skew_array = np.zeros((len(date)*235, 8))
        date_list = []
        for i, crt_date in enumerate(date):
            if log:
                print(crt_date)
            option_info = core.QueryAllInstrumentInfo('Options', crt_date)
            while option_info['Success'] != 'OK':
                option_info = core.QueryAllInstrumentInfo('Options', crt_date)
            for j in range(4):
                if log:
                    print(j)
                csd_month = option_info['Instruments']['Node'][0]['Node'][0]['Node'][j+2]['CHS']
                syn_f = core.SubHistory(
                    f'TC.F.U_SSE.{csd_symbol}.{csd_month}', 'DOGSK', crt_date+'00', crt_date+'07')
                syn_f = pd.DataFrame(syn_f)
                skew_array[i*235:i*235+235, j] = (pd.to_numeric(syn_f['cskew'])[:-5])*100
                skew_array[i*235:i*235+235, j+4] = (pd.to_numeric(syn_f['pskew'])[:-5])*100
            date_list += [crt_date] * 235
        df = pd.DataFrame(skew_array)
        df.columns = ['call_skew_0', 'call_skew_1', 'call_skew_2',
                      'call_skew_3', 'put_skew_0', 'put_skew_1', 'put_skew_2', 'put_skew_3']
        df.index = date_list
        df.to_hdf('skew_hist.h5', key=csd_symbol)
    return


def update_skew_hdf(log=False):
    '''
    更新路径下的skew历史数据至上一个交易日, 若无文件则创建'skew_hist.h5'
    '''
    try:
        skew_hist = pd.read_hdf('skew_hist.h5', key='510050')
    except:
        print('当前路径下未发现历史skew数据,现在开始创立')
        get_skew_hist(log=True)
        return
    etf_hist = pd.DataFrame(core.SubHistory(
        'TC.S.SSE.510050', 'DK', skew_hist.index[-1]+'00', '2030010100'))
    if len(etf_hist) <= 2:
        print('当前skew历史数据已经是最新, 无需更新')
        return
    else:
        date = etf_hist['Date'][1:-1]
        for csd_symbol in ['510050', '510300']:
            skew_hist = pd.read_hdf('skew_hist.h5', key=csd_symbol)
            skew_array = np.zeros((len(date)*235, 8))
            date_list = []
            for i, crt_date in enumerate(date):
                if log:
                    print(crt_date)
                option_info = core.QueryAllInstrumentInfo('Options', crt_date)
                while option_info['Success'] != 'OK':
                    option_info = core.QueryAllInstrumentInfo('Options', crt_date)
                for j in range(4):
                    if log:
                        print(j)
                    csd_month = option_info['Instruments']['Node'][0]['Node'][0]['Node'][j+2]['CHS']
                    syn_f = core.SubHistory(
                        f'TC.F.U_SSE.510050.{csd_month}', 'DOGSK', crt_date+'00', crt_date+'07')
                    syn_f = pd.DataFrame(syn_f)
                    skew_array[i*235:i*235+235, j] = float(pd.to_numeric(syn_f['cskew'])[:-5])*100
                    skew_array[i*235:i*235+235, j+4] = float(pd.to_numeric(syn_f['pskew'])[:-5])*100
                date_list += [crt_date]*235
            new_df = pd.DataFrame(skew_array)
            new_df.columns = ['call_skew_0', 'call_skew_1', 'call_skew_2',
                              'call_skew_3', 'put_skew_0', 'put_skew_1', 'put_skew_2', 'put_skew_3']
            new_df.index = date_list
            new_skew_hist = skew_hist.append(new_df)
            new_skew_hist.to_hdf('skew_hist.h5', key=csd_symbol)
        return


def get_crt_skew():
    '''
    获取当前50和300etf近月平值期权的skew
    '''
    option_info = core.QueryAllInstrumentInfo('Options')
    while option_info['Success'] != 'OK':
        option_info = core.QueryAllInstrumentInfo('Options')
    today = datetime.date.today()
    today_str = today.strftime('%Y%m%d')
    hot_month = option_info['Instruments']['Node'][0]['Node'][0]['Node'][2]['CHS']
    start_str, end_str = get_crt_timescale()
    syn_f = core.SubHistory(
        f'TC.F.U_SSE.510050.{hot_month}', 'DOGSK', today_str+start_str, today_str+end_str)
    syn_f = pd.DataFrame(syn_f)
    return float(syn_f['cskew'].tolist()[-1])*100, float(syn_f['pskew'].tolist()[-1])*100


def get_cashdelta_cashvega(BrokerID, Account):
    '''
    获取当前账户的cashvega及cashdelta
    '''
    crt_position = core.QryPositionTracker()
    crt_cash_delta = 0
    crt_cash_vega = 0
    for csd_data in crt_position['Data']:
        if csd_data['BrokerID'] == BrokerID and csd_data['Account'] == Account and csd_data['SubKey'] == 'Total':
            crt_cash_delta = float(csd_data['$Delta'])
            crt_cash_vega = float(csd_data['$Vega'])
            break
    return crt_cash_delta, crt_cash_vega


def save_origon_cashvanna(cashvanna):
    '''
    保存策略开仓/加仓时做的cashvanna, 而非对冲后剩余的cashvanna
    '''
    today = datetime.date.today()
    new_df = pd.DataFrame([int(cashvanna)])
    new_df.index = [today]
    try:
        df = pd.read_hdf('summary/cashvanna.h5')
        if today in df.index:
            df = df.drop([today])
        new_df = df.append(new_df)
    except:
        pass
    new_df.to_hdf('summary/cashvanna.h5', key='1')


def simulator(log=False, maxqty=3, BrokerID='MVT_SIM2', Account='1999_2-0070624', is_test=False, test_cash_vanna=0.02, test_month=1):
    '''模拟交易主程序
    Args:
        maxqty: 每次下单最大手数
        is_test: 测试用
        test
    '''
    # 获取账户当前仓位
    cash = 10000000
    b = maxqty
    a = round(maxqty*0.25/0.65)
    forced_next = False
    crt_cash_vanna, having_position = get_crt_account_cashvanna(
        BrokerID=BrokerID, Account=Account, log=log)
    if log:
        print('开始获取期权数据')
    try:
        option = get_option_data(is_test)
    except:
        if log:
            print('获取期权数据时报错, 重试一次')
        time.sleep(2)
        option = get_option_data(is_test)
    while len(option) < 2:
        try:
            option = get_option_data(is_test)
        except:
            if log:
                print('获取期权数据时报错, 重试一次')
            time.sleep(2)
            option = get_option_data(is_test)
    if log:
        print('获取期权数据成功,计算目标cashvanna')
    if option['tau'].drop_duplicates(keep='first').tolist()[0] == 0:
        if log:
            print('今天到期日')
        forced_next = True
    if is_test and test_month == 1:
        print('测试到期日情形中')
        forced_next = True
    target_cash_vanna = 1
    if is_test:
        target_cash_vanna = test_cash_vanna * cash
        print(f'测试使用{test_cash_vanna*100}%的cashvanna进行开仓')
    if log:
        print(f'今天要做的目标cashvanna为{target_cash_vanna:.0f}')
    '''
        开始进行交易
    '''
    if crt_cash_vanna == 0 and target_cash_vanna != 0:  # 若未持仓 进行开仓
        if time.localtime().tm_hour < 11 or is_test:  # 只用在上午进行判断
            if log:
                print('当前刚开盘,进行开仓')
            open_position_given_cash_vanna(option=option, crt_cash_vanna=crt_cash_vanna, target_cash_vanna=target_cash_vanna,
                                       log=log, a=a, b=b, BrokerID=BrokerID, Account=Account, forced_next=forced_next)
            if Account=='1999_2-0070889':
                save_origon_cashvanna(target_cash_vanna)
    elif crt_cash_vanna != 0 and crt_cash_vanna*target_cash_vanna <= 0:  # 目标cashvanna为零或者与当前账户cashvanna反向
        # 进行平仓
        if target_cash_vanna==0 and (15>time.localtime().tm_hour>=14 or is_test or forced_next):  # 若目标cashvanna为零，且在两点后，进行平仓
            if log:
                print('当前收盘前,目标cashvanna为零,进行平仓')
            close_position(BrokerID=BrokerID, Account=Account, log=log, tag='all')
            if Account=='1999_2-0070889':
                save_origon_cashvanna(0)
        elif target_cash_vanna != 0 or is_test:  # 若目标cashvanna与当前反向, 且在9点, 先平后开
            if log:
                print('目标cashvanna反向,先平后开')
            close_position(BrokerID=BrokerID, Account=Account, log=log, tag='all')
            if 15>time.localtime().tm_hour>=14:
                if log:
                    print('当前收盘前,虽然反向cashvanna,只需平仓')
                if Account=='1999_2-0070889':
                    save_origon_cashvanna(0)
                return
            crt_cash_vanna, having_position = get_crt_account_cashvanna(
                BrokerID=BrokerID, Account=Account, log=log)
            open_position_given_cash_vanna(option=option, crt_cash_vanna=crt_cash_vanna, target_cash_vanna=target_cash_vanna,
                                           log=log, a=a, b=b, BrokerID=BrokerID, Account=Account, forced_next=forced_next)
            if Account=='1999_2-0070889':
                save_origon_cashvanna(target_cash_vanna)
    elif crt_cash_vanna != 0:
        # 补做cashvanna
        crt_cash_vanna, having_position = get_crt_account_cashvanna(
            BrokerID=BrokerID, Account=Account, log=log)
        if forced_next:
            if log:
                print('今日到期,先平掉账户中近月合约')
            close_position(BrokerID=BrokerID,
                           Account=Account, log=log, tag='near')
            if time.localtime().tm_hour<11 or is_test:
                if log:
                    print('当前开盘时间,重新用次月合约开对应的cashvanna')
                open_position_given_cash_vanna(option=option, crt_cash_vanna=0, target_cash_vanna=crt_cash_vanna,
                                           log=log, a=a, b=b, BrokerID=BrokerID, Account=Account, forced_next=forced_next)
        if np.abs(target_cash_vanna) > np.abs(crt_cash_vanna) and (time.localtime().tm_hour<11 or is_test):
            if log:
                print('当前开盘时间,补做cashvanna')
            open_position_given_cash_vanna(option=option, crt_cash_vanna=crt_cash_vanna, target_cash_vanna=target_cash_vanna,
                                           log=log, a=a, b=b, BrokerID=BrokerID, Account=Account, forced_next=forced_next)
            if Account=='1999_2-0070889':
                save_origon_cashvanna(target_cash_vanna)
    else:
        if Account=='1999_2-0070889':
            return
            save_origon_cashvanna(0)


def get_position_code_for_hedge(true_option_call, true_option_put):
    '''
    获取当前持仓中四个合约代码call25,call65,put25,put65
    csd_synf: 是否考虑合成期货位置
    '''
    id_call_50= np.abs(true_option_call['delta']-0.5).argmin()
    id_put_50 = np.abs(true_option_put['delta']+0.5).argmin()
    code_call_50 = true_option_call['Symbol'][id_call_50]
    code_put_50 = true_option_put['Symbol'][id_put_50]
    return code_call_50, code_put_50


def judge_size(crt_hedge_size):
    '''
    判断当前剩余仓位是否可以继续对冲,若不能则直接停止程序
    '''
    if crt_hedge_size==0:
        print('当前用作对冲的合约未持仓')
        sys.exit('停止脚本')


def hedge_vega_delta(target_delta, target_vega, tol_delta, tol_vega, origin_cashvanna, cash=10000000, BrokerID='MVT_SIM2', Account='1999_2-0070624', log=False, is_test=False, forced_market=False, maxqty=3, forced_target_cashvanna=False):
    '''收盘对冲delta以及vega
    Args:
        target_delta: 目标要对冲到的cash_delta值,例如target_delta=0.01,表示百分之一的cash_delta即cash*0.01
        target_vega: 目标要对冲到的cash_vega
        tol_delta: 目标cashdelta上下容忍范围,也是小数
        tol_vega: 目标cashvega上下容忍范围
        forced_market: 强制用市价对冲
        forced_target_cashvanna: 强制使用给定的origin_cashvanna进行对冲
    Return:
        None
    '''
    if Account=='1999_2-0070889' and not forced_target_cashvanna:
        origin_cashvanna = float(pd.read_hdf('summary/cashvanna.h5').values[-1])
    # otm_size = maxqty * 2
    # universe_itm_size = round(maxqty*0.25/0.65) * 2
    if (time.localtime().tm_hour<14 or (time.localtime().tm_hour==14 and time.localtime().tm_min<45)) and not is_test:
        if log:
            print('未到收盘前，不对冲')
        return
    crt_cash_vanna, having_position = get_crt_account_cashvanna(
        BrokerID=BrokerID, Account=Account, log=log)
    if crt_cash_vanna == 0:
        if log:
            print('当前未持仓, 无需对冲')
        return
    crt_cash_delta, crt_cash_vega = get_cashdelta_cashvega(BrokerID, Account)
    if log:
        print(f'当前cashdelta为{crt_cash_delta:.0f},cashvega为{crt_cash_vega:.0f}')
        print(f'cashdelta容忍范围为{tol_delta*100:.1f}%,cashvega容忍范围为{tol_vega*100:.3f}%')
    if np.abs(crt_cash_delta-target_delta*cash)<tol_delta*cash and np.abs(crt_cash_vega-target_vega*cash)<tol_vega*cash:
        if log:
            print('当前cashdelta与cashvega均在容忍范围内,无需对冲')
        return
    if log:
        print('开始获取期权数据')
    try:
        option = get_option_data(is_test)
    except:
        if log:
            print('获取期权数据时报错, 重试一次')
        time.sleep(2)
        option = get_option_data(is_test)
    while len(option) < 2:
        try:
            option = get_option_data(is_test)
        except:
            if log:
                print('获取期权数据时报错, 重试一次')
            time.sleep(2)
            option = get_option_data(is_test)
    crt_tau = option['tau'].drop_duplicates(keep='first').tolist()[0]
    forced_next = False
    if crt_tau<=5:
        forced_next = True
    if forced_next:
        true_option_call, true_option_put = choose_option_given_month(
            option=option, month=1)
    else:
        true_option_call, true_option_put = choose_option_given_month(
            option=option, month=0)
    code_call_50, code_put_50 = get_position_code_for_hedge(true_option_call, true_option_put)
    do_trading = input(f'对冲选取的合约为\ncall50:{code_call_50},\nput50:{code_put_50},\n如果要继续对冲,请输入1:')
    if do_trading!='1':
        return
    count = 0
    universe_itm_size = 3
    while np.abs(crt_cash_delta-target_delta*cash) > tol_delta*cash/10 or np.abs(crt_cash_vega-target_vega*cash) > tol_vega*cash/10:
        if np.abs(crt_cash_vega-target_vega*cash) > tol_vega*cash/10:
            temp_order_size = 6
        else:
            temp_order_size = universe_itm_size
        if crt_cash_vega >= target_vega*cash and crt_cash_delta >= target_delta*cash:
            side = 2
            code = code_call_50
        elif crt_cash_vega >= target_vega*cash and crt_cash_delta < target_delta*cash:
            side = 2
            code = code_put_50
        elif crt_cash_vega < target_vega*cash and crt_cash_delta >= target_delta*cash:
            side = 1
            code = code_put_50
        else:
            side = 1
            code = code_call_50
        if forced_market:
            orders_obj = {
                "Symbol": code,
                "BrokerID": BrokerID,
                "Account": Account,
                "TimeInForce": "1",
                "Side": f"{side}",
                "OrderType": "1",
                "OrderQty": f"{temp_order_size}",
                "PositionEffect": "4",
                "SelfTradePrevention": "3"
            }
        else:
            orders_obj = {
                "Symbol": code,
                "BrokerID": BrokerID,
                "Account": Account,
                "TimeInForce": "1",
                "Side": f"{side}",
                "OrderType": "11",
                "OrderQty": f"{temp_order_size}",
                "PositionEffect": "4",
                "SelfTradePrevention": "3",
                'Synthetic': '1',
                'ChasePrice': '1T|3|1|M'
            }
        ordid = core.NewOrder(orders_obj)
        while True:
            if core.getorderinfo(ordid):
                if core.getorderinfo(ordid)['ExecType'] == '3':
                    break
                time.sleep(0.1)
        crt_cash_delta, crt_cash_vega = get_cashdelta_cashvega(
            BrokerID, Account)
        crt_cash_vanna, having_position = get_crt_account_cashvanna(
            BrokerID=BrokerID, Account=Account, log=log)
        count += 1
        if log and (not count % 2):
            print(
                f'持续对冲中, 当前cashdelta为{crt_cash_delta:.0f}, cashvega为{crt_cash_vega:.0f}')
    print('对冲完毕')


def get_pnl_h5_and_draw_pic(BrokerID, Account, equity_adjust=0):
    '''
    更新账户市值权益数据并计算年化收益以及最大回撤, 然后导出图
    '''
    today = datetime.date.today()
    crt_margin = core.QryMargin(BrokerID+'-'+Account)
    crt_mktprem = float(crt_margin['Margins'][0]['MarketPremium'])+equity_adjust
    new_df = pd.DataFrame([crt_mktprem])
    new_df.index = [today]
    try:
        df = pd.read_hdf('summary/pnl.h5')
        if today in df.index:
            df = df.drop([today])
        new_df = df.append(new_df)
    except:
        pass
    new_df.to_hdf('summary/pnl.h5', key='1')
    data = list(new_df[0])
    try:
        index_j = np.argmax(np.maximum.accumulate(data) - data)  # 结束位置
        index_i = np.argmax(data[:index_j])  # 开始位置
        d = data[index_j]/data[index_i]-1  # 最大回撤
    except ValueError:
        d = 0
    rtn = pd.DataFrame()
    rtn['close'] = data
    rtn.index = new_df.index
    daily_rtn = rtn['close'].pct_change()
    daily_rtn.dropna(inplace=True)
    try:
        sharp = daily_rtn.mean()/daily_rtn.std()*np.sqrt(240)
    except:
        sharp = 0
    annual_return = (data[-1]/10000000 - 1)/(len(data)) * 240
    return new_df.index, data, d, annual_return, sharp


def write_summary_md(BrokerID='MVT_SIM2', Account='1999_2-0070624', equity_adjust=0):
    folder_path = os.path.join(thisDir, 'summary')
    if not os.path.exists(folder_path):
        os.mkdir(folder_path)
    today = datetime.date.today()
    today_str = today.strftime('%Y-%m-%d')
    today_str_vanilla = today.strftime('%Y%m%d')
    md_str = '# 日级别vanna模拟交易' + today_str + '概览\n' + '## 今日损益\n'
    crt_position_tracker = core.QryPositionTracker()
    crt_position_only = core.QryPosition(BrokerID+'-'+Account)
    crt_margin = core.QryMargin(BrokerID+'-'+Account)
    total_position_tracker = 0
    print('正在做净值统计')
    for i in crt_position_tracker['Data']:
        if i['Account'] == Account and i['SubKey'] == 'Total':
            total_position_tracker = i
            break
    if total_position_tracker == 0:
        pnl = {
            '模拟账户名': Account,
            '日期': today_str,
            '市值权益': int(crt_margin['Margins'][0]['MarketPremium'])+equity_adjust
        }
    else:
        crt_month_sum_commission = 0  # 当月总手续费
        crt_month_sum_intraday_pnl = 0  # 当月总日内
        crt_month_sum_pnl = 0  # 当月总损益
        commission = float(crt_margin['Margins'][0]['Commissions'])
        intraday_pnl = int(round(float(i['TdPnL']), 0))
        total_pnl = int(round(float(i['PnL'])-float(crt_margin['Margins'][0]['Commissions']), 0))
        new_df = pd.DataFrame([commission, intraday_pnl, total_pnl]).T
        new_df.index = [today]
        try:
            df = pd.read_hdf('summary/crt_month_pnl.h5')
            if today in df.index:
                df = df.drop([today])
            new_df = df.append(new_df)
        except:
            pass
        new_df.to_hdf('summary/crt_month_pnl.h5', key='1')
        for ii, csd_date in enumerate(new_df.index):
            if csd_date.year==new_df.index[-1].year and csd_date.month==new_df.index[-1].month:
                crt_month_sum_commission += new_df.iloc[ii,0]
                crt_month_sum_intraday_pnl += new_df.iloc[ii,1]
                crt_month_sum_pnl += new_df.iloc[ii,2]
        pnl = {
            '模拟账户名': Account,
            '日期': today_str,
            '市值权益': int(float(crt_margin['Margins'][0]['MarketPremium']))+equity_adjust,
            '今日损益(含手续费)': str(int(round(float(i['PnL'])-float(crt_margin['Margins'][0]['Commissions']), 0)))+' ('+str(round(((float(i['PnL'])-float(crt_margin['Margins'][0]['Commissions']))/(float(crt_margin['Margins'][0]['MarketPremium'])-float(i['PnL'])))*100, 3))+'%)',
            '昨持损益': str(int(round(float(i['YdPnL']), 0)))+' ('+str(round(float(i['YdPnL'])/100000,3))+'%)',
            '日内损益': str(int(round(float(i['TdPnL']), 0)))+' ('+str(round(float(i['TdPnL'])/100000,3))+'%)',
            '手续费': crt_margin['Margins'][0]['Commissions']+' ('+str(round(float(crt_margin['Margins'][0]['Commissions'])/100000,3))+'%)',
            '总持仓': i['TotalPosition'],
            '净持仓': i['NetPosition'],
            '本月总计收益': int(crt_month_sum_pnl),
            '本月总计日内': int(crt_month_sum_intraday_pnl),
            '本月总计手续费': int(crt_month_sum_commission)
        }
    md_str += pd.Series(pnl, name='模拟账户损益统计').to_markdown() + \
        '\n\n' + '## 持仓统计\n'
    print('正在做持仓统计')
    strike_list = list(np.arange(2.0, 2.95, 0.05)) + \
        list(np.arange(3.0, 4.0, 0.1))
    strike_list = [round(a, 2) for a in strike_list]

    if not crt_position_only:
        md_str += '**今日最终未持仓**' + '\n\n'
        having_final_position = False
    else:
        having_final_position = True
        md_str += '**最终持仓统计**' + '\n\n'
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
        md_str += df_position.to_markdown() + '\n\n'
    temp_filled_rep = core.QryFillReport()
    if not temp_filled_rep:
        md_str += '**今日日内未交易**' + '\n\n'
    else:
        final_qry_index = temp_filled_rep[-1]['QryIndex']
        while core.QryFillReport(qryIndex=final_qry_index):
            temp_filled_rep += core.QryFillReport(qryIndex=final_qry_index)
            final_qry_index = temp_filled_rep[-1]['QryIndex']
        temp_filled_rep = [crt_rep for crt_rep in temp_filled_rep if crt_rep['Account']==Account]
        if len(temp_filled_rep)==0:
            md_str += '**今日日内未交易**' + '\n\n'
        else:
            md_str += '**日内持仓变化**' + '\n\n'
            strike_of_position = []
            month_of_position = []
            for rep in temp_filled_rep:
                try:
                    a, b = rep['Symbol'].split('.C.')
                except:
                    a, b = rep['Symbol'].split('.P.')
                if round(float(b), 2) not in strike_of_position:
                    strike_of_position += [round(float(b), 2)]
                if a.split('.')[-1] not in month_of_position:
                    month_of_position += [int(a.split('.')[-1])]
            if not having_final_position:
                csd_strike_list = strike_list[strike_list.index(
                    min(strike_of_position)):strike_list.index(max(strike_of_position))+1]
            else:
                csd_strike_list = strike_list[min(strike_list.index(
                    min(strike_of_position)),old_min_id):max(strike_list.index(max(strike_of_position)),old_max_id)+1]
            month_of_position.sort()
            month_of_position = pd.Series(month_of_position)
            month_of_position.drop_duplicates(inplace=True)
            month_of_position = list(month_of_position)
            position_array = np.zeros(
                (2*len(month_of_position), len(csd_strike_list)))
            position_array = pd.DataFrame(position_array).replace(0, '-')
            for rep in temp_filled_rep:
                flag = 0
                position_tag = 0
                try:
                    a, b = rep['Symbol'].split('.C.')
                    flag = 'C'
                except:
                    a, b = rep['Symbol'].split('.P.')
                    flag = 'P'
                month_index = month_of_position.index(int(a.split('.')[-1]))
                if flag == 'C':
                    row_id = 2 * month_index
                else:
                    row_id = 2 * month_index + 1
                column_id = csd_strike_list.index(
                    round(float(b), 2))
                if rep['Side'] == '1':
                    position_tag = 1
                else:
                    position_tag = -1
                if position_array.iloc[row_id, column_id] == '-':
                    position_array.iloc[row_id,
                                        column_id] = position_tag * int(rep['MatchedQty'])
                else:
                    position_array.iloc[row_id, column_id] = position_array.iloc[row_id,
                                                                                 column_id] + position_tag * int(rep['MatchedQty'])
            index_ = []
            for i, csd_month in enumerate(month_of_position):
                index_ += [str(csd_month)+'call', str(csd_month)+'put']
            df_position = pd.DataFrame(position_array)
            df_position.index = index_
            df_position.columns = csd_strike_list
            md_str += df_position.to_markdown() + '\n\n'
    print('正在做cashgreeks统计')
    md_str += '## cashgreeks统计\n'
    month_of_position = []
    for i in crt_position_tracker['Data']:
        if i['Account'] == Account and i['SubKey'] != 'Total' and i['SubKey'] not in month_of_position:
            month_of_position += [int(i['SubKey'])]
    td_cashgreeks = []
    final_cashgreeks = []
    month_of_position.sort()
    final_cashgreeks_df = 0
    td_cashgreeks_df = 0
    for i, csd_month in enumerate(month_of_position):
        for j in crt_position_tracker['Data']:
            if j['SubKey'] == str(csd_month) and j['Account'] == Account:
                new_final_cashgreeks = [j['$Delta'], j['$Gamma'], j['$Vega'],
                                        j['1%$Vanna'], j['$Theta'], j['$Charm'], j['$Speed'], j['$Vomma']]
                new_final_cashgreeks = [int(float(a))
                                        for a in new_final_cashgreeks]
                final_cashgreeks += new_final_cashgreeks
                new_td_cashgreeks = [j['Td$Delta'], j['Td$Gamma'], j['Td$Vega'],
                                     j['1%Td$Vanna'], j['Td$Theta'], j['Td$Charm'], j['Td$Speed'], j['Td$Vomma']]
                new_td_cashgreeks = [int(float(a)) for a in new_td_cashgreeks]
                td_cashgreeks += new_td_cashgreeks
                if i == 0:
                    final_cashgreeks_df = pd.DataFrame(final_cashgreeks).T
                    td_cashgreeks_df = pd.DataFrame(td_cashgreeks).T
                else:
                    final_cashgreeks_df = final_cashgreeks_df.append(
                        pd.DataFrame(final_cashgreeks).T)
                    td_cashgreeks_df = td_cashgreeks_df.append(
                        pd.DataFrame(td_cashgreeks).T)
                final_cashgreeks = []
                td_cashgreeks = []
    for j in crt_position_tracker['Data']:
        if j['SubKey'] == 'Total' and j['Account'] == Account:
            new_final_cashgreeks = [j['$Delta'], j['$Gamma'], j['$Vega'],
                                    j['1%$Vanna'], j['$Theta'], j['$Charm'], j['$Speed'], j['$Vomma']]
            new_final_cashgreeks = [int(float(a))
                                    for a in new_final_cashgreeks]
            new_final_cashgreeks[0] = str(new_final_cashgreeks[0])+'('+str(round(new_final_cashgreeks[0]*100/10000000,1))+'%)'
            new_final_cashgreeks[2] = str(new_final_cashgreeks[2])+'('+str(round(new_final_cashgreeks[2]*100/10000000,3))+'%)'
            new_final_cashgreeks[3] = str(new_final_cashgreeks[3])+'('+str(round(new_final_cashgreeks[3]*100/10000000,1))+'%)'
            final_cashgreeks += new_final_cashgreeks
            new_td_cashgreeks = [j['Td$Delta'], j['Td$Gamma'], j['Td$Vega'],
                                 j['1%Td$Vanna'], j['Td$Theta'], j['Td$Charm'], j['Td$Speed'], j['Td$Vomma']]
            new_td_cashgreeks = [int(float(a)) for a in new_td_cashgreeks]
            td_cashgreeks += new_td_cashgreeks
            final_cashgreeks_df = final_cashgreeks_df.append(
                pd.DataFrame(final_cashgreeks).T)
            td_cashgreeks_df = td_cashgreeks_df.append(
                pd.DataFrame(td_cashgreeks).T)
            break
    index_ = month_of_position + ['总计']
    columns = ['\$Delta', '\$Gamma', '\$Vega', '\$Vanna',
               '\$Theta', '\$Charm', '\$Speed', '\$Vomma']
    if type(final_cashgreeks_df) == int:
        md_str += '\n无cashgreeks信息\n'
    else:
        final_cashgreeks_df.index = index_
        td_cashgreeks_df.index = index_
        final_cashgreeks_df.columns = columns
        td_cashgreeks_df.columns = columns
        md_str += '\n**总体cashgreeks**\n' + tabulate(final_cashgreeks_df, headers=final_cashgreeks_df.columns, tablefmt='pipe', disable_numparse=True) + '\n\n' + \
            '**日内cashgreeks**' + '\n\n' + \
            tabulate(td_cashgreeks_df, headers=td_cashgreeks_df.columns,
                     tablefmt='pipe', disable_numparse=True) + '\n\n'
    date_, value, d, annual_return, sharp = get_pnl_h5_and_draw_pic(
        BrokerID=BrokerID, Account=Account, equity_adjust=equity_adjust)
    plt.plot(date_, value, label='总资产')
    plt.legend(fontsize=12)
    plt.xticks(fontsize=10, rotation=22)
    plt.yticks(fontsize=12)
    plt.title(
        f'年化收益{annual_return*100:.1f}%,最大回撤{d*100:.1f}%,夏普比率{sharp:.2f}', fontsize=15)
    plt.grid()
    plt.gca().xaxis.set_major_locator(ticker.MultipleLocator(math.ceil(len(date_)/8)))
    plt.tight_layout()
    plt.savefig(f'summary/netvalue{today_str_vanilla}.png', dpi=500)
    md_str += '## 总资产曲线图\n\n' + f'![](netvalue{today_str_vanilla}.png)'
    md_str = md_str.replace('|--','|:--').replace('--|','--:|')
    output_path = os.path.join(thisDir, f'summary\\{today_str_vanilla}.md')
    if os.path.exists(output_path):
        os.remove(output_path)
    with open(output_path, 'w', encoding='utf-8') as file:
        file.writelines(md_str)
    file.close()


if __name__ == '__main__':
    maxqty = 3
    # BrokerID = 'MVT_SIM2'
    # Account = '1999_2-0070889'
    # BrokerID = 'DCore_SIM_SS2'
    # Account = 'mvtuat09'
    # Account = 'simtest1'
    # get_crt_account_cashvanna(BrokerID=BrokerID, Account=Account, log=True)
    # if time.localtime().tm_hour < 15:
    #     simulator(log=True, maxqty=maxqty, BrokerID=BrokerID, Account=Account)
    #     hedge_vega_delta(target_delta=0, target_vega=0, log=True, origin_cashvanna=-1080000, forced_target_cashvanna=False, forced_market=False,
    #                       tol_delta=0.1, tol_vega=0.0005, BrokerID=BrokerID, Account=Account, maxqty=maxqty)
    # else:
    #     write_summary_md(BrokerID=BrokerID, Account=Account, equity_adjust=28921)


'''
以下测试用
'''
# BrokerID = core.QryAccount()['Accounts'][0]['BrokerID']
# Account = core.QryAccount()['Accounts'][0]['Account']
# write_summary_md(BrokerID=BrokerID, Account=Account, equity_adjust=28921)

# hedge_vega_delta(target_delta=0, target_vega=0, log=True, origin_cashvanna=-1080000,
#                           tol_delta=0.01, tol_vega=0.0001, BrokerID='MVT_SIM2', Account='1999_2-0070599', is_test=True)
# hedge_vega_delta(target_delta=0, target_vega=0, log=True, origin_cashvanna=-1, forced_target_cashvanna=True,
#                           tol_delta=0.01, tol_vega=0.0001, BrokerID=BrokerID, Account=Account, is_test=True)
# simulator(log=True, maxqty=maxqty, BrokerID=BrokerID, Account=Account, is_test=True, test_month=0)
# close_position(BrokerID, Account, log=True)


# option_info = core.QueryAllInstrumentInfo('Options')
# while option_info['Success'] != 'OK':
#     option_info = core.QueryAllInstrumentInfo('Options')
# csd_month = option_info['Instruments']['Node'][0]['Node'][0]['Node'][3]['CHS']
# print(f'当前次月为{csd_month}')
# core.SubGreeks(f'TC.F.U_SSE.510050.{csd_month}')
# core.SubGreeks(f'TC.F.U_SSE.510300.{csd_month}')
# his_0 = core.SubHistory(f'TC.F.U_SSE.510050.{csd_month}', 'DOGSK', time.strftime('%Y%m%d', time.localtime())+'00', time.strftime('%Y%m%d', time.localtime())+'07')
# his_1 = core.SubHistory(f'TC.F.U_SSE.510300.{csd_month}', 'DOGSK', time.strftime('%Y%m%d', time.localtime())+'00', time.strftime('%Y%m%d', time.localtime())+'07')
# barlen = 0
# print('获取历史数据成功')
# while True:
#     message = core.mdupdate()
#     if message and message['DataType']=='GREEKS':
#         print('1')
#         his_0 = core.barupdate2('DOGSK', his_0, message)
#         his_1 = core.barupdate2('DOGSK', his_1, message)
#         print(len(his_0), len(his_1))
#         if len(his_0)>barlen and barlen!=0:
#             print(time.localtime())
#             print(his_0)
#             print('\n'*20)
#             print(his_1)
#             print('\n'*100)
#     barlen = len(his_0)

# core.UnsubGreeks(f'TC.F.U_SSE.510050.{csd_month}')
# core.UnsubGreeks(f'TC.F.U_SSE.510300.{csd_month}')

















#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   gamma_scalping_20221117.py
@Time    :   2022/11/17 13:17:13
@Author  :   DingWenjie
@Contact :   359582058@qq.com
@Desc    :   gamma_scalping, 仅供测试
             5分钟级,
             最简单情形：当前分钟hv超过历史75分位值则开仓, 小于45则平仓
             中性delta, vega
'''


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


def open_position_given_cashgamma(option, crt_cash_vanna, target_cash_vanna, log, BrokerID, Account, a, b, forced_next=False, theta_vega_positive=3, theta_vega_negative=4.5):
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


def get_hv_hist(log=False, interval=5):
    '''获取分钟级别hv历史数据
    Args:
        None
    Return:
        在当前路径生成.h5文件
    '''
    etf_hist = pd.DataFrame(core.SubHistory(
        'TC.S.SSE.510050', '1K', '2020010200', '2030010100'))
    close = np.log(pd.to_numeric(etf_hist['Close']).pct_change()+1)
    date_len = round(len(close)/240-interval)
    # etf_hist = etf_hist.iloc[:date_len*240,:]
    hv_list = []
    for csd_date in range(date_len):
        close_list = close.values[csd_date*240:(csd_date+interval)*240]
        hv_list += [np.sqrt( (close_list**2).sum() * 240/interval )]
    date = etf_hist['Date'][240*interval:].drop_duplicates()
    return hv_list


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
            if log:
                print(f'开始获取{csd_symbol}')
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
                    skew_array[i*235:i*235+235, j] = (pd.to_numeric(syn_f['cskew'])[:-5])*100
                    skew_array[i*235:i*235+235, j+4] = (pd.to_numeric(syn_f['pskew'])[:-5])*100
                date_list += [crt_date]*235
            new_df = pd.DataFrame(skew_array)
            new_df.columns = ['call_skew_0', 'call_skew_1', 'call_skew_2',
                              'call_skew_3', 'put_skew_0', 'put_skew_1', 'put_skew_2', 'put_skew_3']
            new_df.index = date_list
            new_skew_hist = skew_hist.append(new_df)
            new_skew_hist.to_hdf('skew_hist.h5', key=csd_symbol)
        return


@func_set_timeout(10)
def get_crt_skew(smoothed=True):
    '''
    获取当前50和300etf近月期权的skew
    Return:
        list: [cskew_50, pskew_50, cskew_300, pskew_300]
    '''
    option_info = core.QueryAllInstrumentInfo('Options')
    while option_info['Success'] != 'OK':
        option_info = core.QueryAllInstrumentInfo('Options')
    today = datetime.date.today()
    today_str = today.strftime('%Y%m%d')
    hot_month = option_info['Instruments']['Node'][0]['Node'][0]['Node'][2]['CHS']
    # start_str, end_str = get_crt_timescale()
    syn_f_50 = core.SubHistory(
        f'TC.F.U_SSE.510050.{hot_month}', 'DOGSK', today_str+'00', today_str+'07')
    syn_f_50 = pd.DataFrame(syn_f_50)
    syn_f_300 = core.SubHistory(
        f'TC.F.U_SSE.510300.{hot_month}', 'DOGSK', today_str+'00', today_str+'07')
    syn_f_300 = pd.DataFrame(syn_f_300)
    if smoothed:
        skew_list = [
            np.median(pd.to_numeric(syn_f_50['cskew']).values[1:][-5:])*10000,
            np.median(pd.to_numeric(syn_f_50['pskew']).values[1:][-5:])*10000,
            np.median(pd.to_numeric(syn_f_300['cskew']).values[1:][-5:])*10000,
            np.median(pd.to_numeric(syn_f_300['pskew']).values[1:][-5:])*10000
            ]
    else:
        skew_list = [
            pd.to_numeric(syn_f_50['cskew']).values[-1]*10000,
            pd.to_numeric(syn_f_50['pskew']).values[-1]*10000,
            pd.to_numeric(syn_f_300['cskew']).values[-1]*10000,
            pd.to_numeric(syn_f_300['pskew']).values[-1]*10000
            ]
    return skew_list


def save_origon_cashgamma(cashvanna):
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


def simulator(log=False, BrokerID='DCore_SIM_SS2', Account='simtest3', is_test=False, equity_adjust=0):
    '''模拟交易主程序
    Args:
        maxqty: 每次下单最大手数
        is_test: 测试用
        test
    '''
    # 获取账户当前仓位
    cash = 10000000
    forced_next = False
    while True:
        crt_time = time.localtime()
        if (crt_time.tm_hour<9 or (crt_time.tm_hour==9 and crt_time.tm_min<=30)) and not is_test:
            print('当前未开盘, 结束程序')
            return
        elif crt_time.tm_hour>=15 and not is_test:
            write_summary = input('当前已收盘, 是否写summary?\n')
            if write_summary==1:
                get_pnl_h5_and_draw_pic(BrokerID, Account, equity_adjust)
            return

        if log:
            print('开始获取期权数据')
        option = get_option_data(is_test)
        while len(option) < 2:
            option = get_option_data(is_test)
            time.sleep(2)
        if log:
            print('获取期权数据成功')
        if option['tau'].drop_duplicates(keep='first').tolist()[0] == 0:
            if log:
                print('今天到期日')
            forced_next = True
        if is_test and test_month == 1:
            print('测试到期日情形中')
            forced_next = True
        if is_test:
            print(f'测试开仓')
        '''
            开始进行交易
        '''
        while time.localtime().tm_hour<15 and (time.localtime().tm_hour<14 or time.localtime().tm_min<51):
            if not time.localtime().tm_min%5:
                print(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())))
                crt_position_only = core.QryPosition(BrokerID+'-'+Account)
                if not crt_position_only:
                    print('当前未持仓, 判断开仓条件')
                    skew_list = get_crt_skew()
                    if 1:
                        open_position_given_cash_vanna(option, crt_cash_vanna, target_cash_vanna, log, BrokerID, Account, a, b)
                    else:
                        pass



    # if crt_cash_vanna == 0 and target_cash_vanna != 0:  # 若未持仓 进行开仓
    #     if time.localtime().tm_hour < 11 or is_test:  # 只用在上午进行判断
    #         if log:
    #             print('当前刚开盘,进行开仓')
    #         open_position_given_cash_vanna(option=option, crt_cash_vanna=crt_cash_vanna, target_cash_vanna=target_cash_vanna,
    #                                    log=log, a=a, b=b, BrokerID=BrokerID, Account=Account, forced_next=forced_next)
    #         if Account=='1999_2-0070889':
    #             save_origon_cashvanna(target_cash_vanna)
    # elif crt_cash_vanna != 0 and crt_cash_vanna*target_cash_vanna <= 0:  # 目标cashvanna为零或者与当前账户cashvanna反向
    #     # 进行平仓
    #     if target_cash_vanna==0 and (15>time.localtime().tm_hour>=14 or is_test or forced_next):  # 若目标cashvanna为零，且在两点后，进行平仓
    #         if log:
    #             print('当前收盘前,目标cashvanna为零,进行平仓')
    #         close_position(BrokerID=BrokerID, Account=Account, log=log, tag='all')
    #         if Account=='1999_2-0070889':
    #             save_origon_cashvanna(0)
    #     elif target_cash_vanna != 0 or is_test:  # 若目标cashvanna与当前反向, 且在9点, 先平后开
    #         if log:
    #             print('目标cashvanna反向,先平后开')
    #         close_position(BrokerID=BrokerID, Account=Account, log=log, tag='all')
    #         if 15>time.localtime().tm_hour>=14:
    #             if log:
    #                 print('当前收盘前,虽然反向cashvanna,只需平仓')
    #             if Account=='1999_2-0070889':
    #                 save_origon_cashvanna(0)
    #             return
    #         crt_cash_vanna, having_position = get_crt_account_cashvanna(
    #             BrokerID=BrokerID, Account=Account, log=log)
    #         open_position_given_cash_vanna(option=option, crt_cash_vanna=crt_cash_vanna, target_cash_vanna=target_cash_vanna,
    #                                        log=log, a=a, b=b, BrokerID=BrokerID, Account=Account, forced_next=forced_next)
    #         if Account=='1999_2-0070889':
    #             save_origon_cashvanna(target_cash_vanna)
    # elif crt_cash_vanna != 0:
    #     # 补做cashvanna
    #     crt_cash_vanna, having_position = get_crt_account_cashvanna(
    #         BrokerID=BrokerID, Account=Account, log=log)
    #     if forced_next:
    #         if log:
    #             print('今日到期,先平掉账户中近月合约')
    #         close_position(BrokerID=BrokerID,
    #                        Account=Account, log=log, tag='near')
    #         if time.localtime().tm_hour<11 or is_test:
    #             if log:
    #                 print('当前开盘时间,重新用次月合约开对应的cashvanna')
    #             open_position_given_cash_vanna(option=option, crt_cash_vanna=0, target_cash_vanna=crt_cash_vanna,
    #                                        log=log, a=a, b=b, BrokerID=BrokerID, Account=Account, forced_next=forced_next)
    #     if np.abs(target_cash_vanna) > np.abs(crt_cash_vanna) and (time.localtime().tm_hour<11 or is_test):
    #         if log:
    #             print('当前开盘时间,补做cashvanna')
    #         open_position_given_cash_vanna(option=option, crt_cash_vanna=crt_cash_vanna, target_cash_vanna=target_cash_vanna,
    #                                        log=log, a=a, b=b, BrokerID=BrokerID, Account=Account, forced_next=forced_next)
    #         if Account=='1999_2-0070889':
    #             save_origon_cashvanna(target_cash_vanna)
    # else:
    #     if Account=='1999_2-0070889':
    #         return
    #         save_origon_cashvanna(0)


def judge_size(crt_hedge_size):
    '''
    判断当前剩余仓位是否可以继续对冲,若不能则直接停止程序
    '''
    if crt_hedge_size==0:
        print('当前用作对冲的合约未持仓')
        sys.exit('停止脚本')


def hedge(target_delta, target_vega, tol_delta, tol_vega, origin_cashvanna, cash=10000000, BrokerID='DCore_SIM_SS2', Account='simtest3', log=False, is_test=False, forced_market=False, maxqty=3, forced_target_cashvanna=False):
    '''对冲delta,vega并补gamma
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


if __name__ == '__main__':
    maxqty = 3
    BrokerID = 'DCore_SIM_SS2'
    Account = 'simtest3'
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

















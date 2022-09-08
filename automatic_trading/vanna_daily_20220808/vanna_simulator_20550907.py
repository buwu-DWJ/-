'''
@File    :   vanna_simulator_20220902.py
@Time    :   2022/09/02
@Author  :   DingWenjie
@Contact :   359582058@qq.com
@Desc    :   日级别vanna策略模拟交易脚本, 需上午下午各运行一次, 自动进行开仓以及对冲,
             收盘后运行则导出损益表
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
warnings.simplefilter('ignore')
core = t.TCoreZMQ(quote_port="51864", trade_port="51834")
thisDir = os.path.dirname(__file__)


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
    elif hour==14:
        start_str, end_str = '06', '07'
    return start_str, end_str


def get_option_data(interval='DOGSK'):
    '''获取给定日期的期权数据
    Args:
        interval: 数据间隔, 默认五分钟
    Return:
        df
    '''
    today = datetime.date.today()
    csd_date = today.strftime('%Y%m%d')
    option_symbols = core.QueryAllInstrumentInfo('Options', csd_date)
    len_of_df = 0
    start_str, end_str = get_crt_timescale()
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


def cpt_position_vanilla(symbol='TC.S.SSE.510050', timeperiod=20, std=2, up_limit=1.4, down_limit=-0.4):
    '''计算position, 最简单的情形, 用以进一步计算cashvanna
    Args:
        symbol: 标的
        timeperiod: 布林带时间范围
        std: 布林带宽度
        up_limit: position上限
        down_limit: position下限
    Return:
        position: 当前价格在历史20天2std布林带中的分位值
    '''
    today = datetime.date.today()
    today_str = today.strftime('%Y%m%d')
    hist = pd.DataFrame(core.SubHistory(
        symbol, '5K', '2022060200', today_str+'00'))
    close_hist = [float(a) for i, a in enumerate(
        hist['Close']) if (i+1) % 48 == 47]
    upper, middle, lower = ta.BBANDS(
        np.array(close_hist), timeperiod=timeperiod, nbdevup=std, nbdevdn=std)
    upper = upper[-1]
    lower = lower[-1]
    crt_close_list = pd.DataFrame(core.SubHistory(
        symbol, '1K', today_str+'00', today_str+'07'))
    try:
        crt_close = float(list(crt_close_list['Close'])[-1])
    except:
        print('获取不到今日第五分钟收盘价')
        sys.exit('停止脚本')
    position = min(max((crt_close-lower)/(upper-lower), down_limit), up_limit)
    return position


def cpt_cash_vanna(cash, crt_cash_vanna, basic_vanna=0.1, open_position_positive=1, open_position_negative=0, callskew_threhold=0.7, callskew_multiplier=0.7, putskew_threhold=0.7, putskew_multiplier=1, skew_timehorizon=120, with_hangqing=True, hangqing_his_lenth_positive=40, hangqing_his_lenth_negative=50, with_volume=True, symbol='TC.S.SSE.510050', log=False, close_position_positive=0.7, close_position_negative=0.5):
    '''
    根据在布林带的位置计算要做的cashvanna
    Args:
        cash: 总资金
        crt_cash_vanna: 当前账户中持有的cashvanna
        basic_vanna: 总vanna的基础值
        open_position_positive/negative: 正/负vanna入场条件
        call/putskew_threhold: 根据call/putskew进行打折参考的历史分位值, 超过则打
        call/putskew_multiplier: 打折倍数
        with_hangqing: 是否加入行情条件
        hangwing_hist_lenth_positive/negative: 做正/负vanna时行情参考的历史范围
        with_volume: 是否加入成交量条件
        close_position_positive/negative: 做正负vanna平仓对应的position阈值
    Return:
        cash_vanna
    '''
    update_skew_hdf()
    skew_hist = pd.read_hdf('skew_hist.h5')
    call_skew_hist = np.array(skew_hist['call_skew_0'])
    put_skew_hist = np.array(skew_hist['put_skew_0'])
    crt_cskew, crt_pskew = get_crt_skew()
    vanilla_position = cpt_position_vanilla(
        timeperiod=10, std=1)
    today = datetime.date.today()
    today_str = today.strftime('%Y%m%d')
    if vanilla_position >= 0.5:  # 判断做正vanna
        position = cpt_position_vanilla(timeperiod=5, std=1)
        if crt_cash_vanna > 0 and open_position_negative < position <= close_position_positive:
            if log:
                print(
                    f'当前持有正vanna,position为{position:.2f},低于平仓阈值{close_position_positive},高于负vanna开仓阈值{open_position_negative},故全平')
            cash_vanna = 0
            return cash_vanna
        elif crt_cash_vanna < 0 and open_position_positive > position >= close_position_negative:
            if log:
                print(
                    f'当前持有负vanna,position为{position:.2f},高于平仓阈值{close_position_negative},低于正vanna开仓阈值{open_position_positive},故全平')
            cash_vanna = 0
            return cash_vanna
        elif crt_cash_vanna == 0 and position < open_position_positive:
            if log:
                print(
                    f'当前未持仓,position为{position:.2f},低于正vanna开仓阈值{open_position_positive},今日不做')
            cash_vanna = 0
            return cash_vanna
        vanna_percent = basic_vanna * (position-0.5)
        cash_vanna = vanna_percent * cash
        callskew_pctile = percentileofscore(
            call_skew_hist[-skew_timehorizon:], crt_cskew)
        if log:
            print(
                f'今日做正vanna,position为{position:.2f},cashvanna基值为{cash_vanna:.0f}, 当前callskew为{crt_cskew*100:.1f}%, 分位值为{callskew_pctile:.0f}%')
        if callskew_pctile/100 > callskew_threhold:
            cash_vanna = cash_vanna * callskew_multiplier
            if log:
                print(
                    f'超出阈值, cashvanna变为{cash_vanna:.0f}')
    else:  # 判断负vanna
        position = cpt_position_vanilla(timeperiod=10, std=1)
        if crt_cash_vanna > 0 and open_position_negative < position <= close_position_positive:
            if log:
                print(
                    f'当前持有正vanna,position为{position:.2f},低于平仓阈值{close_position_positive},高于负vanna开仓阈值{open_position_negative},故全平')
            cash_vanna = 0
            return cash_vanna
        elif crt_cash_vanna < 0 and open_position_positive > position >= close_position_negative:
            if log:
                print(
                    f'当前持有负vanna,position为{position:.2f},高于平仓阈值{close_position_negative},低于正vanna开仓阈值{open_position_positive},故全平')
            cash_vanna = 0
            return cash_vanna
        elif crt_cash_vanna == 0 and position > open_position_negative:
            if log:
                print(
                    f'当前未持仓,position为{position:.2f},高于负vanna开仓阈值{open_position_negative},今日不做')
            cash_vanna = 0
            return cash_vanna
        vanna_percent = basic_vanna * (position-0.5)
        cash_vanna = vanna_percent * cash
        putskew_pctile = percentileofscore(
            put_skew_hist[-skew_timehorizon:], crt_pskew)
        if log:
            print(
                f'今日做负vanna,position为{position:.2f},cashvanna基值为{cash_vanna:.0f}, 当前putskew为{crt_pskew*100:.1f}%, 分位值为{putskew_pctile:.0f}%')
        if putskew_pctile/100 > putskew_threhold:
            cash_vanna = cash_vanna * putskew_multiplier
            if log:
                print(
                    f'超出阈值, cashvanna变为{cash_vanna:.0f}')
    if with_hangqing or with_volume:
        etf_data = pd.DataFrame(core.SubHistory(
            symbol, 'DK', '2022060200', today_str+'00'))
        if with_hangqing:
            close_yes = float(list(etf_data['Close'])[-2])
            if cash_vanna >= 0:
                high_hist = list(pd.to_numeric(
                    etf_data['High'][-hangqing_his_lenth_positive-2:-2]))
            else:
                high_hist = list(pd.to_numeric(
                    etf_data['High'][-hangqing_his_lenth_negative-2:-2]))
            if close_yes > max(high_hist):
                cash_vanna = cash_vanna * 1.2
                if log:
                    print(
                        f'昨日收盘价为{close_yes:.3f}, 历史高位为{max(high_hist):.3f}, cashvanna变为{cash_vanna:.0f}')
        if with_volume:
            volume_yes = float(list(etf_data['Volume'])[-2])
            volume_before = float(list(etf_data['Volume'])[-3])
            if volume_yes > volume_before*1.2:
                cash_vanna = cash_vanna * 1.2
                if log:
                    print(
                        f'昨日成交量为{volume_yes:.0f}, 前日成交量为{volume_before:.0f}, 超过1.2倍, cashvanna变为{cash_vanna:.0f}')
    return cash_vanna


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
                "OrderType": "1",
                "OrderQty": temp_quantity,
                "PositionEffect": "4",
                "SelfTradePrevention": "3"
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
    '''获取510050历史skew数据,采用权分析合成期货每日收盘前5分钟的skew数据
    Args:
        None
    Return:
        在当前路径生成.h5文件
    '''
    etf_hist = core.SubHistory(
        'TC.S.SSE.510050', 'DK', '2020010200', '2030010100')
    date = pd.DataFrame(etf_hist)['Date'].tolist()[-140:-1]
    skew_array = np.zeros((len(date), 8))
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
            skew_array[i, j] = float(syn_f['cskew'].tolist()[-5])*100
            skew_array[i, j+4] = float(syn_f['pskew'].tolist()[-5])*100
    df = pd.DataFrame(skew_array)
    df.columns = ['call_skew_0', 'call_skew_1', 'call_skew_2',
                  'call_skew_3', 'put_skew_0', 'put_skew_1', 'put_skew_2', 'put_skew_3']
    df.index = date
    df.to_hdf('skew_hist.h5', key='1')
    return


def update_skew_hdf(log=False):
    '''
    更新路径下的skew历史数据至上一个交易日, 若无文件则创建'skew_hist.h5'
    '''
    try:
        skew_hist = pd.read_hdf('skew_hist.h5')
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
        skew_array = np.zeros((len(date), 8))
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
                skew_array[i, j] = float(syn_f['cskew'].tolist()[-5])*100
                skew_array[i, j+4] = float(syn_f['pskew'].tolist()[-5])*100
        new_df = pd.DataFrame(skew_array)
        new_df.columns = ['call_skew_0', 'call_skew_1', 'call_skew_2',
                          'call_skew_3', 'put_skew_0', 'put_skew_1', 'put_skew_2', 'put_skew_3']
        new_df.index = date
        new_skew_hist = skew_hist.append(new_df)
        new_skew_hist.to_hdf('skew_hist.h5', key='1')
        return


def get_crt_skew():
    '''
    获取当前50etf近月平值期权的skew
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
        option = get_option_data()
    except:
        if log:
            print('获取期权数据时报错, 重试一次')
        time.sleep(2)
        option = get_option_data()
    while len(option) < 2:
        try:
            option = get_option_data()
        except:
            if log:
                print('获取期权数据时报错, 重试一次')
            time.sleep(2)
            option = get_option_data()
    if log:
        print('获取期权数据成功,计算目标cashvanna')
    if option['tau'].drop_duplicates(keep='first').tolist()[0] == 0:
        if log:
            print('今天到期日')
        forced_next = True
    if is_test and test_month == 1:
        print('测试到期日情形中')
        forced_next = True
    target_cash_vanna = cpt_cash_vanna(
        cash=cash, log=log, crt_cash_vanna=crt_cash_vanna)
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
            save_origon_cashvanna(target_cash_vanna)
    elif crt_cash_vanna != 0 and crt_cash_vanna*target_cash_vanna <= 0:  # 目标cashvanna为零或者与当前账户cashvanna反向
        # 进行平仓
        if target_cash_vanna==0 and (15>time.localtime().tm_hour>=14 or is_test):  # 若目标cashvanna为零，且在两点后，进行平仓
            if log:
                print('当前收盘前,目标cashvanna为零,进行平仓')
            close_position(BrokerID=BrokerID, Account=Account, log=log, tag='all')
            save_origon_cashvanna(0)
        elif target_cash_vanna != 0 and (time.localtime().tm_hour<11 or is_test):  # 若目标cashvanna与当前反向, 且在9点, 先平后开
            if log:
                print('当前开盘,目标cashvanna反向,先平后开')
            close_position(BrokerID=BrokerID, Account=Account, log=log, tag='all')
            crt_cash_vanna, having_position = get_crt_account_cashvanna(
                BrokerID=BrokerID, Account=Account, log=log)
            open_position_given_cash_vanna(option=option, crt_cash_vanna=crt_cash_vanna, target_cash_vanna=target_cash_vanna,
                                           log=log, a=a, b=b, BrokerID=BrokerID, Account=Account, forced_next=forced_next)
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
            if time.localtime().tm_hour==14 or is_test:
                if log:
                    print('当前收盘前,重新用次月合约开对应的cashvanna')
                open_position_given_cash_vanna(option=option, crt_cash_vanna=0, target_cash_vanna=crt_cash_vanna,
                                           log=log, a=a, b=b, BrokerID=BrokerID, Account=Account, forced_next=forced_next)
                return
        if np.abs(target_cash_vanna) > np.abs(crt_cash_vanna) and (time.localtime().tm_hour<11 or is_test):
            if log:
                print('当前开盘时间,补做cashvanna')
            open_position_given_cash_vanna(option=option, crt_cash_vanna=crt_cash_vanna, target_cash_vanna=target_cash_vanna,
                                           log=log, a=a, b=b, BrokerID=BrokerID, Account=Account, forced_next=forced_next)
            save_origon_cashvanna(target_cash_vanna)
    else:
        save_origon_cashvanna(0)


def get_position_code_for_hedge(BrokerID, Account):
    '''
    获取当前持仓中四个合约代码call25,call65,put25,put65
    '''
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
            time.sleep(2)
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
    return code_call25, code_call65, code_put25, code_put65, int(size_call25), int(size_call_65), int(size_put25), int(size_put65)


def judge_size(crt_hedge_size):
    '''
    判断当前剩余仓位是否可以继续对冲,若不能则直接停止程序
    '''
    if crt_hedge_size==0:
        print('当前用作对冲的合约未持仓')
        sys.exit('停止脚本')


def hedge_vega_delta(target_delta, target_vega, tol_delta, tol_vega, origin_cashvanna, cash=10000000, BrokerID='MVT_SIM2', Account='1999_2-0070624', log=False, is_test=False, forced_market=False, maxqty=3):
    '''收盘对冲delta以及vega
    Args:
        target_delta: 目标要对冲到的cash_delta值,例如target_delta=0.01,表示百分之一的cash_delta即cash*0.01
        target_vega: 目标要对冲到的cash_vega
        tol_delta: 目标cashdelta上下容忍范围,也是小数
        tol_vega: 目标cashvega上下容忍范围
    Return:
        None
    '''
    otm_size = maxqty * 2
    itm_size = round(maxqty*0.25/0.65) * 2
    if time.localtime().tm_hour<14 and not is_test:
        if log:
            print('未到收盘前，不对冲')
        return
    # origin_cashvanna = float(pd.read_hdf('summary/cashvanna.h5').values[-1])
    crt_cash_vanna, having_position = get_crt_account_cashvanna(
        BrokerID=BrokerID, Account=Account, log=log)
    if crt_cash_vanna == 0:
        if log:
            print('当前未持仓, 无需对冲')
        return
    # origin_cashvanna = float(pd.read_hdf('summary/cashvanna.h5').values[-1])
    crt_cash_delta, crt_cash_vega = get_cashdelta_cashvega(BrokerID, Account)
    if log:
        print(f'当前cashdelta为{crt_cash_delta:.0f},cashvega为{crt_cash_vega:.0f}')
        print(f'cashdelta容忍范围为{tol_delta*100:.1f}%,cashvega容忍范围为{tol_vega*100:.3f}%')
    if np.abs(crt_cash_delta-target_delta*cash)<tol_delta*cash and np.abs(crt_cash_vega-target_vega*cash)<tol_vega*cash:
        if log:
            print('当前cashdelta与cashvega均在容忍范围内,无需对冲')
        return
    try:
        option = get_option_data()
    except:
        if log:
            print('获取期权数据时报错, 重试一次')
        time.sleep(2)
        option = get_option_data()
    while len(option) < 2:
        try:
            option = get_option_data()
        except:
            if log:
                print('获取期权数据时报错, 重试一次')
            time.sleep(2)
            option = get_option_data()
    # 根据当前持仓中是否有次月合约判断对冲合约的选取
    option_info = core.QueryAllInstrumentInfo('Options')
    while option_info['Success'] != 'OK':
        option_info = core.QueryAllInstrumentInfo('Options')

    code_call_25, code_call_65, code_put_25, code_put_65, size_call_25, size_call_65, size_put_25, size_put_65 = get_position_code_for_hedge(
        BrokerID=BrokerID, Account=Account)
    do_trading = input(f'对冲选取的合约为\ncall25:{code_call_25},\ncall65:{code_call_65},\nput25:{code_put_25},\nput65:{code_put_65},\n如果要继续对冲,请输入1:')
    if do_trading!='1':
        return
    count = 0
    while np.abs(crt_cash_delta-target_delta*cash) > tol_delta*cash or np.abs(crt_cash_vega-target_vega*cash) > tol_vega*cash:
        if crt_cash_vega >= target_vega*cash and crt_cash_delta >= target_delta*cash:
            side = 2
            if origin_cashvanna>crt_cash_vanna > 0 or crt_cash_vanna<origin_cashvanna<0:  # 做正vanna,卖call65
                code = code_call_65
            else:  # 卖call25
                code = code_call_25
        elif crt_cash_vega >= target_vega*cash and crt_cash_delta < target_delta*cash:
            side = 2
            if origin_cashvanna>crt_cash_vanna > 0 or crt_cash_vanna<origin_cashvanna<0:  # 做正vanna,卖put25
                code = code_put_25
            else:  # 卖put65
                code = code_put_65
        elif crt_cash_vega < target_vega*cash and crt_cash_delta >= target_delta*cash:
            side = 1
            if origin_cashvanna>crt_cash_vanna > 0 or crt_cash_vanna<origin_cashvanna<0:  # 做正vanna,买put65
                code = code_put_65
            else:  # 买put25
                code = code_put_25
        else:
            side = 1
            if origin_cashvanna>crt_cash_vanna > 0 or crt_cash_vanna<origin_cashvanna<0:  # 做正vanna,买call25
                code = code_call_25
            else:  # 买call65
                code = code_call_65
        if code==code_call_25:
            judge_size(size_call_25)
        elif code==code_call_65:
            judge_size(size_call_65)
        elif code==code_put_25:
            judge_size(size_put_25)
        else:
            judge_size(size_put_65)
        if code==code_call_25 or code==code_put_25:
            if (code==code_call_25 and ( (side==2 and size_call_25>=otm_size) or (side==1 and size_call_25<=-otm_size) )) or (code==code_put_25 and ((side==2 and size_put_25>=otm_size) or (side==1 and size_put_25<=-otm_size))):
                temp_order_size = otm_size
                if code==code_call_25:
                    size_call_25 = size_call_25 + int(temp_order_size*(side-1.5)*(-2))
                else:
                    size_put_25 = size_put_25 + int(temp_order_size*(side-1.5)*(-2))
            elif (code==code_call_25 and ( (side==2 and 0<size_call_25<otm_size) or (side==1 and 0>size_call_25>-otm_size) )) or (code==code_put_25 and ((side==2 and 0<size_put_25<otm_size) or (side==1 and 0>size_put_25>-otm_size))):
                if log:
                    print('剩余仓位低于给定单次反向操作的手数,全平')
                if code==code_call_25:
                    temp_order_size = np.abs(size_call_25)
                    size_call_25 = 0
                else:
                    temp_order_size = np.abs(size_put_25)
                    size_put_25 = 0
            else:
                print('当前有方向不对的仓位,无法自动对冲,请手动调整后再运行')
                sys.exit('停止脚本')
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
                    'ChasePrice': '1T|3|2|M'
                }
        else:
            if (code==code_call_65 and ( (side==2 and size_call_65>=itm_size) or (side==1 and size_call_65<=-itm_size) )) or (code==code_put_65 and ((side==2 and size_put_65>=itm_size) or (side==1 and size_put_65<=-itm_size))):  # 剩余仓位满足反向的对冲操作
                temp_order_size = itm_size
                if code==code_call_65:
                    size_call_65 = size_call_65 + int(temp_order_size*(side-1.5)*(-2))
                else:
                    size_put_65 = size_put_65 + int(temp_order_size*(side-1.5)*(-2))
            elif (code==code_call_65 and ( (side==2 and 0<size_call_65<itm_size) or (side==1 and 0>size_call_65>-itm_size) )) or (code==code_put_65 and ((side==2 and 0<size_put_65<itm_size) or (side==1 and 0>size_put_65>-itm_size))):  # 剩余仓位不够进行反向操作, 直接用剩余仓位对冲后重新获取代码
                if log:
                        print('剩余仓位低于给定单次反向操作的手数,全平')
                if code==code_call_65:
                    temp_order_size = np.abs(size_call_65)
                    size_call_65 = 0
                else:
                    temp_order_size = np.abs(size_put_65)
                    size_put_65 = 0
            else:
                print('当前有方向不对的仓位,无法自动对冲,请手动调整后再运行')
                sys.exit('停止脚本')
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
                    "OrderType": "15",
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
        if (code==code_call_25 and size_call_25==0) or (code==code_call_65 and size_call_65==0) or (code==code_put_25 and size_put_25==0) or (code==code_put_65 and size_put_65==0):
            if log:
                print('目标合约仓位已为零,重新寻找对冲目标合约')
            code_call_25, code_call_65, code_put_25, code_put_65, size_call_25, size_call_65, size_put_25, size_put_65 = get_position_code_for_hedge(
                    BrokerID=BrokerID, Account=Account)
    print('对冲完毕')


def get_pnl_h5_and_draw_pic(BrokerID, Account):
    '''
    更新账户市值权益数据并计算年化收益以及最大回撤, 然后导出图
    '''
    today = datetime.date.today()
    crt_margin = core.QryMargin(BrokerID+'-'+Account)
    crt_mktprem = float(crt_margin['Margins'][0]['MarketPremium'])+8000
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


def write_summary_md(BrokerID='MVT_SIM2', Account='1999_2-0070624'):
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
            '市值权益': int(crt_margin['Margins'][0]['MarketPremium'])+8000
        }
    else:
        pnl = {
            '模拟账户名': Account,
            '日期': today_str,
            '市值权益': int(float(crt_margin['Margins'][0]['MarketPremium']))+8000,
            '今日收益': str(round(((float(i['PnL'])-float(crt_margin['Margins'][0]['Commissions']))/(float(crt_margin['Margins'][0]['MarketPremium'])-float(i['PnL'])))*100, 3))+'%',
            '今日损益': int(round(float(i['PnL'])-float(crt_margin['Margins'][0]['Commissions']), 0)),
            '昨持损益': str(int(round(float(i['YdPnL']), 0)))+'('+str(round(float(i['YdPnL'])/100000,2))+'%)',
            '日内损益': str(int(round(float(i['TdPnL']), 0)))+'('+str(round(float(i['TdPnL'])/100000,2))+'%)',
            '手续费': crt_margin['Margins'][0]['Commissions']+'('+str(round(float(crt_margin['Margins'][0]['Commissions'])/100000,2))+'%)',
            '总持仓': i['TotalPosition'],
            '净持仓': i['NetPosition']
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
        BrokerID=BrokerID, Account=Account)
    plt.plot(date_, value, label='总资产')
    plt.legend(fontsize=12)
    plt.xticks(fontsize=12, rotation=25)
    plt.yticks(fontsize=12)
    plt.title(
        f'年化收益{annual_return*100:.1f}%,最大回撤{d*100:.1f}%,夏普比率{sharp:.2f}', fontsize=15)
    plt.grid()
    plt.gca().xaxis.set_major_locator(ticker.MultipleLocator(math.ceil(len(date_)/8)+1))
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
    BrokerID = 'MVT_SIM2'
    Account = '1999_2-0070599'
    # if time.localtime().tm_hour < 15:
    #     simulator(log=True, maxqty=maxqty, BrokerID=BrokerID, Account=Account)
    #     hedge_vega_delta(target_delta=0, target_vega=0, log=True, origin_cashvanna=-1080000,
    #                       tol_delta=0.1, tol_vega=0.0005, BrokerID=BrokerID, Account=Account, maxqty=maxqty)
    # else:
    #     write_summary_md(BrokerID=BrokerID, Account=Account)

# write_summary_md(BrokerID=BrokerID, Account=Account)

# hedge_vega_delta(target_delta=0, target_vega=0, log=True, origin_cashvanna=-1080000,
#                           tol_delta=0.1, tol_vega=0.0005, BrokerID='MVT_SIM2', Account='1999_2-0070599', is_test=True)

simulator(log=True, maxqty=maxqty, BrokerID=BrokerID, Account=Account, is_test=True, test_month=0)
# close_position(BrokerID, Account, log=True)











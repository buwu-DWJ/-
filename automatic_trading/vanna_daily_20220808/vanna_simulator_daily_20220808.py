import pandas as pd
import numpy as np
from scipy.stats import percentileofscore
import warnings
import datetime
import time
import talib as ta
import tcoreapi_mq as t
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
# from pylab import mpl

# mpl.rcParams['font.sans-serif'] = ['SimHei']
# mpl.rcParams['axes.unicode_minus'] = False
warnings.simplefilter('ignore')
core = t.TCoreZMQ(quote_port="51864", trade_port="51834")


def get_option_data(interval='5K'):
    '''获取给定日期的期权数据
    Args:
        interval: 数据间隔, 默认五分钟
    Return:
        df
    '''
    today = datetime.date.today()
    csd_date = today.strftime('%Y%m%d')
    option_symbols = core.QueryAllInstrumentInfo('Options', csd_date)
    if option_symbols['Success'] != 'OK':
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
    return df


def cpt_greeks(call_option, put_option, tau):
    '''计算希腊值
    Args:
        call/put_option: call/put 原始数据
        tau: 年化后的到期时间, 记得输入时除以240
    Return:
        call/put_option
    '''
    K = []
    iv = []
    delta = []
    vanna = []
    vega = []
    theta = []
    r = np.log(1.018)
    if len(call_option) < len(put_option) and float(call_option['Symbol'][0].split('.C.')[1]) == float(put_option['Symbol'][0].split('.P.')[1]):
        put_option = put_option.iloc[:-1, :]
    elif len(call_option) < len(put_option) and float(call_option['Symbol'][0].split('.C.')[1]) != float(put_option['Symbol'][0].split('.P.')[1]):
        put_option = put_option.iloc[1:, :]
    elif len(call_option) > len(put_option) and float(call_option['Symbol'][0].split('.C.')[1]) == float(put_option['Symbol'][0].split('.P.')[1]):
        call_option = call_option.iloc[:-1, :]
    elif len(call_option) > len(put_option) and float(call_option['Symbol'][0].split('.C.')[1]) != float(put_option['Symbol'][0].split('.P.')[1]):
        call_option = call_option.iloc[1:, :]
    for i in range(len(call_option)):
        cc = call_option['Symbol'][i]
        K += [float(cc.split('.C.')[1])]
    K = np.array(K, dtype='float64')
    iiidd = np.abs(np.array(call_option['Close'])
                   - np.array(put_option['Close'])).argmin()
    stock_price = (np.array(call_option['Close'])
                   + K*np.exp(-tau*r)
                   - np.array(put_option['Close']))[iiidd]
    for k in range(len(call_option)):
        implied_vol = CalIVCall(
            S=stock_price, K=K[k], T=tau, r=r, c=call_option['Close'].iloc[k])
        iv = iv + [implied_vol]
        delta = delta + \
            [CalDeltaCall(S=stock_price, K=K[k],
                          T=tau, r=r, iv=implied_vol)]
        vanna = vanna + \
            [CalVannaCall(S=stock_price, K=K[k],
                          T=tau, r=r, iv=implied_vol)]
        vega = vega + \
            [CalVegaCall(S=stock_price, K=K[k],
                         T=tau, r=r, iv=implied_vol)]
        theta = theta + \
            [CalThetaCall(S=stock_price, K=K[k],
                          T=tau, r=r, iv=implied_vol)]
    call_option['delta'] = delta
    call_option['iv'] = iv
    call_option['vanna'] = vanna
    call_option['theta'] = theta
    call_option['vega'] = vega
    iv = []
    delta = []
    vanna = []
    vega = []
    theta = []
    for k in range(len(put_option)):
        implied_vol = CalIVPut(
            S=stock_price, K=K[k], T=tau, r=r, p=put_option['Close'].iloc[k])
        iv = iv + [implied_vol]
        delta = delta + \
            [CalDeltaPut(S=stock_price, K=K[k],
                         T=tau, r=r, iv=implied_vol)]
        vanna = vanna + \
            [CalVannaPut(S=stock_price, K=K[k],
                         T=tau, r=r, iv=implied_vol)]
        vega = vega + \
            [CalVegaPut(S=stock_price, K=K[k],
                        T=tau, r=r, iv=implied_vol)]
        theta = theta + \
            [CalThetaPut(S=stock_price, K=K[k],
                         T=tau, r=r, iv=implied_vol)]
    put_option['delta'] = delta
    put_option['iv'] = iv
    put_option['vanna'] = vanna
    put_option['theta'] = theta
    put_option['vega'] = vega
    call_option['strike'] = K
    put_option['strike'] = K
    return call_option, put_option


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
    # date_flag = 3
    # while date_flag!=0 or date_flag!=1:
    #     date_flag = input('是使用今日的收盘价还是昨日的收盘价来计算position(今日请输入0, 昨日请输入1):\n')
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
    crt_close = float(list(crt_close_list['Close'])[-1])
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
        # if (crt_cash_vanna>0 and open_position_negative<position<=close_position_positive) or (crt_cash_vanna<0 and open_position_positive>position>=close_position_negative):
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
                f'今日做正vanna, cashvanna基值为{cash_vanna:.0f}, 当前callskew为{crt_cskew*100:.1f}%, 分位值为{callskew_pctile:.0f}%')
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
                f'今日做负vanna, cashvanna基值为{cash_vanna:.0f}, 当前putskew为{crt_pskew*100:.1f}%, 分位值为{putskew_pctile:.0f}%')
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
    true_option_call, true_option_put = cpt_greeks(
        true_option_call, true_option_put, crt_tau/240)
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
            crt_cash_vanna = float(csd_data['$Vanna'])
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
    code_list = [code_call_25, code_put_25, code_call_65, code_put_65]
    size_list = [b, b, a, a]
    if log:
        print(
            f'今日要做的目标期权分别为\ndelta25处的call:{code_call_25}\ndelta65处的call:{code_call_65}\ndelta25处的put:{code_put_25}\ndelta65处的put:{code_put_65}')
    if target_cash_vanna > 0:
        side_list = [1, 2, 2, 1]
    else:
        side_list = [2, 1, 1, 2]
    while np.abs(crt_cash_vanna) < np.abs(target_cash_vanna):
        # 下单顺序, 先虚值再实值, 先call后put
        for i, csd_symbol in enumerate(code_list):
            orders_obj = {
                "Symbol": csd_symbol,
                "BrokerID": BrokerID,
                "Account": Account,
                "TimeInForce": "1",
                "Side": f"{side_list[i]}",
                "OrderType": "1",
                "OrderQty": f"{size_list[i]}",
                            "PositionEffect": "4",
                            "SelfTradePrevention": "3"
            }
            ordid = core.NewOrder(orders_obj)
            while True:
                if core.getorderinfo(ordid):
                    if core.getorderinfo(ordid)['ExecType'] == '3':
                        break
                    time.sleep(0.5)
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
        orders_obj = {
            "Symbol": symbol,
            "BrokerID": BrokerID,
            "Account": Account,
            "TimeInForce": "1",
            "Side": side,
            "OrderType": "1",
            "OrderQty": quantity,
            "PositionEffect": "4",
            "SelfTradePrevention": "3"
        }
        ordid = core.NewOrder(orders_obj)
        while True:
            if core.getorderinfo(ordid):
                if core.getorderinfo(ordid)['ExecType'] == '3':
                    break
                time.sleep(0.5)
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
    syn_f = core.SubHistory(
        f'TC.F.U_SSE.510050.{hot_month}', 'DOGSK', today_str+'00', today_str+'07')
    syn_f = pd.DataFrame(syn_f)
    return float(syn_f['cskew'].tolist()[-5])*100, float(syn_f['pskew'].tolist()[-5])*100


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


def simulator(log=False, maxqty=3, BrokerID='MVT_SIM2', Account='1999_2-0070624'):
    '''模拟交易主程序
    Args:
        maxqty: 每次下单最大手数
    '''
    # 获取账户当前仓位
    cash = 10000000
    b = maxqty
    a = round(maxqty*0.25/0.65)
    forced_next = False
    crt_cash_vanna, having_position = get_crt_account_cashvanna(
        BrokerID=BrokerID, Account=Account, log=log)
    try:
        option = get_option_data()
    except:
        if log:
            print('获取期权数据时报错, 重试一次')
        time.sleep(3)
        option = get_option_data()
    if log:
        print('获取期权数据成功,计算目标cashvanna')
    if option['tau'].drop_duplicates(keep='first').tolist()[0] == 0:
        if log:
            print('今天到期日')
        forced_next = True
    target_cash_vanna = cpt_cash_vanna(
        cash=cash, log=log, crt_cash_vanna=crt_cash_vanna)
    if log:
        print(f'今天要做的目标cashvanna为{target_cash_vanna:.0f}')
    '''
        开始进行交易
    '''
    if crt_cash_vanna == 0 and target_cash_vanna != 0:  # 若未持仓 进行开仓
        open_position_given_cash_vanna(option=option, crt_cash_vanna=crt_cash_vanna, target_cash_vanna=target_cash_vanna,
                                       log=log, a=a, b=b, BrokerID=BrokerID, Account=Account, forced_next=forced_next)
    elif crt_cash_vanna != 0 and crt_cash_vanna*target_cash_vanna <= 0:  # 目标cashvanna为零或者与当前账户cashvanna反向
        # 进行平仓
        close_position(BrokerID=BrokerID, Account=Account, log=log, tag='all')
        if target_cash_vanna != 0:
            crt_cash_vanna, having_position = get_crt_account_cashvanna(
                BrokerID=BrokerID, Account=Account, log=log)
            open_position_given_cash_vanna(option=option, crt_cash_vanna=crt_cash_vanna, target_cash_vanna=target_cash_vanna,
                                           log=log, a=a, b=b, BrokerID=BrokerID, Account=Account, forced_next=forced_next)
    elif crt_cash_vanna != 0:
        # 补做cashvanna
        if np.abs(target_cash_vanna) > np.abs(crt_cash_vanna):
            if forced_next:
                if log:
                    print('今日到期,先平掉账户中近月合约')
                close_position(BrokerID=BrokerID,
                               Account=Account, log=log, tag='near')
            open_position_given_cash_vanna(option=option, crt_cash_vanna=crt_cash_vanna, target_cash_vanna=target_cash_vanna,
                                           log=log, a=a, b=b, BrokerID=BrokerID, Account=Account, forced_next=forced_next)


def hedge_vega_delta(target_delta, target_vega, tol_delta, tol_vega, cash=10000000, BrokerID='MVT_SIM2', Account='1999_2-0070624', log=False):
    '''收盘对冲delta以及vega
    Args:
        target_delta: 目标要对冲到的cash_delta值,例如target_delta=0.01,表示百分之一的cash_delta即cash*0.01
        target_vega: 目标要对冲到的cash_vega
        tol_delta: 目标cashdelta上下容忍范围,也是小数
        tol_vega: 目标cashvega上下容忍范围
    Return:
        None
    '''
    use_next = False
    crt_cash_vanna, having_position = get_crt_account_cashvanna(
        BrokerID=BrokerID, Account=Account, log=log)
    if crt_cash_vanna == 0:
        if log:
            print('当前未持仓, 无需对冲')
        return
    try:
        option = get_option_data()
    except:
        if log:
            print('获取期权数据时报错, 重试一次')
        time.sleep(3)
        option = get_option_data()
    # 根据当前持仓中是否有次月合约判断对冲合约的选取
    option_info = core.QueryAllInstrumentInfo('Options')
    while option_info['Success'] != 'OK':
        option_info = core.QueryAllInstrumentInfo('Options')
    next_month = option_info['Instruments']['Node'][0]['Node'][0]['Node'][3]['CHS']
    pos = core.QryPosition(BrokerID+'-'+Account)
    for csd_position in pos:
        if csd_position['Month'] == next_month:
            use_next = True
            break
    if use_next:
        if log:
            print('查询到当前持仓中含有次月合约, 所以平仓直接选用次月合约')
        true_option_call, true_option_put = choose_option_given_month(
            option, month=1)
    else:
        true_option_call, true_option_put = choose_option_given_month(
            option, month=0)
    code_call_25, code_call_65, code_put_25, code_put_65, get_data = get_option_code(
        true_option_call, true_option_put)
    if (not get_data) and (not use_next):
        if log:
            print('近月合约delta不在范围内,考虑次月合约')
        true_option_call, true_option_put = choose_option_given_month(
            option, month=1)
        code_call_25, code_call_65, code_put_25, code_put_65, get_data = get_option_code(
            true_option_call, true_option_put)
    crt_cash_delta, crt_cash_vega = get_cashdelta_cashvega(BrokerID, Account)
    if log:
        print(f'当前cashdelta为{crt_cash_delta:.0f},cashvega为{crt_cash_vega:.0f}')
    count = 0
    while np.abs(crt_cash_delta-target_delta*cash) > tol_delta*cash or np.abs(crt_cash_vega-target_vega*cash) > tol_vega*cash:
        if crt_cash_vega >= target_vega*cash and crt_cash_delta >= target_delta*cash:
            side = 2
            if crt_cash_vanna > 0:  # 卖call65
                code = code_call_65
            else:  # 卖call25
                code = code_call_25
        elif crt_cash_vega >= target_vega*cash and crt_cash_delta < target_delta*cash:
            side = 2
            if crt_cash_vanna > 0:  # 卖put25
                code = code_put_25
            else:  # 卖put65
                code = code_put_65
        elif crt_cash_vega < target_vega*cash and crt_cash_delta >= target_delta*cash:
            side = 1
            if crt_cash_vanna > 0:  # 买put65
                code = code_put_65
            else:  # 买put25
                code = code_put_25
        else:
            side = 1
            if crt_cash_vanna > 0:  # 买call25
                code = code_call_25
            else:  # 买call65
                code = code_call_65
        orders_obj = {
            "Symbol": code,
            "BrokerID": BrokerID,
            "Account": Account,
            "TimeInForce": "1",
            "Side": f"{side}",
            "OrderType": "1",
            "OrderQty": "1",
                        "PositionEffect": "4",
                        "SelfTradePrevention": "3"
        }
        ordid = core.NewOrder(orders_obj)
        while True:
            if core.getorderinfo(ordid):
                if core.getorderinfo(ordid)['ExecType'] == '3':
                    break
                time.sleep(0.5)
        crt_cash_delta, crt_cash_vega = get_cashdelta_cashvega(
            BrokerID, Account)
        count += 1
        if log and (not count % 4):
            print(
                '持续对冲中, 当前cashdelta为{crt_cash_delta:.0f}, cashvega为{crt_cash_vega:.0f}')
    print('对冲完毕')


if __name__ == '__main__':
    maxqty = 3
    BrokerID = 'MVT_SIM2'
    Account = '1999_2-0070624'
    if time.localtime().tm_hour < 12:
        simulator(log=True, maxqty=maxqty, BrokerID=BrokerID, Account=Account)
    else:
        hedge_vega_delta(target_delta=0, target_vega=0, log=True,
                         tol_delta=0.02, tol_vega=0.0001, BrokerID=BrokerID, Account=Account)

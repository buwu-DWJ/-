import pandas as pd
import numpy as np
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
from pylab import mpl

mpl.rcParams['font.sans-serif'] = ['SimHei']
mpl.rcParams['axes.unicode_minus'] = False
warnings.simplefilter('ignore')
core = t.TCoreZMQ(quote_port="51864", trade_port="51834")


def get_option_data(interval='5K'):
    '''获取给定日期的期权数据
    Args:
        interval: 数据间隔, 默认五分钟
    Return:
        df:
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


def Rsquared(y, y_hat):
    sse = ((y - y_hat)**2).sum()
    sst = ((y - y.mean())**2).sum()
    return 1-sse/sst


def get_iv(data, month, target_de, force_linear=False):
    r_regulated = True  # if month_idx <= 1 else False

    def fit(data, target_de, degree, r_regulated=False):
        '''
            data的delta列名为'de',
            data的iv列名为'iv',
        '''
        data1 = data.copy()
        data1['diff'] = abs(abs(data1.de)-abs(target_de))
        if degree == 1:
            upper = data1[data1.de > target_de]
            lower = data1[data1.de <= target_de]
            if len(upper) >= 1 and len(lower) >= 1:
                data2 = pd.concat(
                    [upper.iloc[-1, :], lower.iloc[0, :]], axis=1).T
            else:
                data2 = data1.sort_values('diff')[:3] if len(
                    data1) >= 3 else data1.sort_values('diff')[:2]
            x = data2.de.values.astype('float')
            y = data2.iv.values.astype('float')
            f = np.polyfit(x, y, 1)
            return f, x, y, np.polyval(f, target_de)
        elif degree == 2:
            data2 = data1[(abs(data1.de) < 0.95) &
                          (abs(data1.de) > 0.05)].copy()
            if len(data2) >= 3:
                data2 = data2.sort_values('diff')[:4]
                x = data2.de.values.astype('float')
                y = data2.iv.values.astype('float')
                f = np.polyfit(x, y, 2)
                y_hat = np.polyval(f, x)  # 拟合y值
                r = Rsquared(y, y_hat)  # R方
                if r_regulated and r < 0.9:
                    data2 = data2.sort_values('diff')[:3]
                    x = data2.de.values.astype('float')
                    y = data2.iv.values.astype('float')
                    f = np.polyfit(x, y, 2)
            else:
                data2 = data1[(abs(data1.de) < 0.99) &
                              (abs(data1.de) > 0.01)].copy()
                data2 = data2.sort_values('diff')[:3]
                x = data2.de.values.astype('float')
                y = data2.iv.values.astype('float')
                f = np.polyfit(x, y, 2)
            return f, x, y, np.polyval(f, target_de)
    if force_linear:
        _, _, _, est_iv = fit(data, target_de, degree=1)
    else:
        _, _, _, est_iv = fit(data, target_de, degree=2,
                              r_regulated=r_regulated)
    return est_iv


def cpt_skew(option, month=0):
    '''
        计算给定期权历史数据的每日峰度：(callskew+putskew)/(2 * atm_iv)
    args:
        df: 期权数据
        date: 日期数据
        month: 计算哪个月份,[0,1,2,3]
    return:
        kurtosis: 峰度的新列表
    '''
    tau = option['tau'].drop_duplicates(keep='first').tolist()
    tau.sort()
    # if (0 in option['tau'].drop_duplicates(keep='first').tolist()) or (0 in option['tau'].drop_duplicates(keep='first').tolist()):
    #     true_option = option.loc[list(
    #         option['maturity'] == maturity[month+1]), :].sort_values(by='strike')
    # else:
    true_option = option.loc[list(
        option['tau'] == tau[month]), :].sort_values(by='strike')
    true_option_call = true_option.loc[list(
        true_option['flag'] == 'C'), :]
    true_option_call = true_option_call.rename(columns={'delta': 'de'})
    true_option_put = true_option.loc[list(
        true_option['flag'] == 'P'), :]
    true_option_put = true_option_put.rename(columns={'delta': 'de'})
    # 二次拟合
    civ50 = get_iv(true_option_call, month, 0.50)
    piv50 = get_iv(true_option_put, month, -0.50)
    iv50 = (civ50+piv50)/2
    # 线性拟合
    civ50_linear = get_iv(true_option_call, month, 0.50, force_linear=True)
    piv50_linear = get_iv(true_option_put, month, -0.50, force_linear=True)
    iv50_linear = (civ50_linear+piv50_linear)/2
    if (np.array([iv50, civ50, piv50]) < 0).any() or (np.array([iv50, civ50, piv50]) > 1).any() or abs(civ50 - piv50) > 0.10:
        poorfit = True
    else:
        poorfit = False
    # cskew iv拟合
    civ25 = get_iv(true_option_call, month, 0.25, force_linear=True)
    # piv75 = get_iv(true_option_put, month, -0.75, force_linear=True)
    # cskew_iv = (civ25+piv75)/2
    cskew_iv = civ25
    # pskew iv拟合
    # civ75 = get_iv(true_option_call, month, 0.75, force_linear=True)
    piv25 = get_iv(true_option_put, month, -0.25, force_linear=True)
    # pskew_iv = (civ75+piv25)/2
    pskew_iv = piv25
    # 计算skew
    cskew = (cskew_iv/iv50 - 1) if not poorfit else (cskew_iv/iv50_linear - 1)
    pskew = (pskew_iv/iv50 - 1)if not poorfit else (pskew_iv/iv50_linear - 1)
    return cskew, pskew


def cpt_greeks(call_option, put_option, tau):
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
        close_hist: 历史一定时间内的收盘前五分钟收盘价序列
        crt_close: 当前收盘价
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
    return position, np.array(close_hist), crt_close


def cpt_cash_vanna(option, cash, crt_cash_vanna, basic_vanna=0.1, open_position_positive=1, open_position_negative=0, callskew_threhold=0.7, callskew_multiplier=0.7, putskew_threhold=0.7, putskew_multiplier=1, with_hangqing=True, hangqing_his_lenth_positive=40, hangqing_his_lenth_negative=50, with_volume=True, symbol='TC.S.SSE.510050', log=False, close_position_positive=0.7, close_position_negative=0.5):
    '''
    根据在布林带的位置计算要做的cashvanna
    Args:
        option: 当前时刻的期权数据
        cash: 总资金
        basic_vanna: 总vanna的基础值
        open_position_positive: 正vanna入场条件
        open_position_negative:
        callskew_threhold:
        callskew_multiplier:
        putskew_threhold:
        putskew_multiplier:
        theta_vega_positive:
        theta_vega_negative:
        with_hangqing:
        hangwing_hist_lenth:
        with_volume:
    Return:
        cash_vanna
    '''
    vanilla_position, close_hist, crt_close = cpt_position_vanilla()
    today = datetime.date.today()
    today_str = today.strftime('%Y%m%d')
    if vanilla_position >= 0.5:  # 判断做正vanna
        position, _, _ = cpt_position_vanilla(timeperiod=5, std=1)
        if (crt_cash_vanna>0 and open_position_negative<position<=close_position_positive) or (crt_cash_vanna<0 and open_position_positive>position>=close_position_negative):
            cash_vanna = 0
            return cash_vanna
        vanna_percent = basic_vanna * (position-0.5)
        cash_vanna = vanna_percent * cash
        callskew, _ = cpt_skew(option)
        if log:
            print(f'今日做正vanna, cashvanna基值为{cash_vanna:.0f}')
        if callskew > callskew_threhold:
            cash_vanna = cash_vanna * callskew_multiplier
            if log:
                print(
                    f'当前callskew为{callskew:.2f}, 超出阈值, cashvanna变为{cash_vanna:.0f}')
    else:  # 判断负vanna
        if (crt_cash_vanna>0 and position<=close_position_positive) or (crt_cash_vanna<0 and position>=close_position_negative):
            cash_vanna = 0
            return cash_vanna
        position, _, _ = cpt_position_vanilla(timeperiod=10, std=1)
        vanna_percent = basic_vanna * (position-0.5)
        cash_vanna = vanna_percent * cash
        _, putskew = cpt_skew(option)
        if log:
            print(f'今日做负vanna, cashvanna基值为{cash_vanna:.0f}')
        if putskew > putskew_threhold:
            cash_vanna = cash_vanna * putskew_multiplier
            if log:
                print(
                    f'当前putskew为{putskew:.2f}, 超出阈值, cashvanna变为{cash_vanna:.0f}')
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
            if volume_yes > volume_before:
                cash_vanna = cash_vanna * 1.2
                if log:
                    print(
                        f'昨日成交量为{volume_yes:.0f}, 前日成交量为{volume_before:.0f}, cashvanna变为{cash_vanna:.0f}')
    return cash_vanna


def choose_option_given_month(option, month=0):
    '''根据get_option_data得到的原始期权数据筛选给定月份的call与put
    Args:
        option: 原始期权数据
        Month: 目标月份
    Return:
        true_option_call:
        true_option_put:
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
        true_option_call, true_option_put, crt_tau)
    return true_option_call, true_option_put


def get_option_code(true_option_call, true_option_put):
    '''
    获取当前时刻中|delta|为0.25和0.65的合约
    Args:
        true_option_call: 当前时刻call
        true_option_put: 当前时刻put
    Return:
        code_call_25, code_call_65, code_put_25, code_put_65
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
    '''获取当前资金账户的cashvanna值
    Args:
        core:
    Return:
        cash_vanna
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


def open_position_given_cash_vanna(option, true_option_call, true_option_put, crt_cash_vanna, target_cash_vanna, log, BrokerID, Account, a, b):
    code_call_25, code_call_65, code_put_25, code_put_65, get_data = get_option_code(
            true_option_call, true_option_put)
    if not get_data:
        if log: print('近月期权delta不在范围内,考虑次月期权')
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
                            "OrderType":"1",
                            "OrderQty":f"{size_list[i]}",
                            "PositionEffect":"4",
                            "SelfTradePrevention":"3"
                        }
            ordid = core.NewOrder(orders_obj)
            while True:
                if core.getorderinfo(ordid):
                    if core.getorderinfo(ordid)['ExecType']=='3':
                        break
                    time.sleep(0.5)
        crt_cash_vanna, _ = get_crt_account_cashvanna(
            BrokerID=BrokerID, Account=Account)
        if log: print(f'当前cashvanna为{crt_cash_vanna:.0f}')



def close_all_position(BrokerID, Account, log=False):
    '''平掉所有仓位
    Args:
        BrokerID:
        Account:
    '''
    pos = core.QryPosition(BrokerID+'-'+Account)
    for csd_position in pos:
        symbol = csd_position['Symbol']
        quantity = csd_position['Quantity']
        if csd_position['Side']=='1':
            side = '2'
        else:
            side = '1'
        orders_obj = {
                        "Symbol": symbol,
                        "BrokerID": BrokerID,
                        "Account": Account,
                        "TimeInForce": "1",
                        "Side": side,
                        "OrderType":"1",
                        "OrderQty": quantity,
                        "PositionEffect": "4",
                        "SelfTradePrevention": "3"
                    }
        ordid = core.NewOrder(orders_obj)
        while True:
            if core.getorderinfo(ordid):
                if core.getorderinfo(ordid)['ExecType']=='3':
                    break
                time.sleep(0.5)
    if log: print('平仓完毕')


def simulator(log=False, maxqty=3):
    '''模拟交易主程序
    Args:

    '''
    # 获取账户当前仓位
    BrokerID = 'MVT_SIM2'
    Account = '1999_2-0061366'
    cash = 10000000
    b = maxqty
    a = round(maxqty*0.25/0.65)
    crt_cash_vanna, having_position = get_crt_account_cashvanna(
        BrokerID=BrokerID, Account=Account, log=log)
    try:
        option = get_option_data()
        true_option_call, true_option_put = choose_option_given_month(
            option, month=0)
    except:
        if log:
            print('获取期权数据时报错, 重试一次')
        time.sleep(3)
        option = get_option_data()
        true_option_call, true_option_put = choose_option_given_month(
            option, month=0)
    if log:
        print('获取期权数据成功,计算目标cashvanna')
    target_cash_vanna = cpt_cash_vanna(
        option=true_option_call.append(true_option_put), cash=cash, log=log, crt_cash_vanna=crt_cash_vanna)
    '''
        开始进行交易
    '''
    if crt_cash_vanna==0 and target_cash_vanna!=0:  # 若未持仓 进行开仓
        open_position_given_cash_vanna(option=option, true_option_call=true_option_call, true_option_put=true_option_put, crt_cash_vanna=crt_cash_vanna, target_cash_vanna=target_cash_vanna, log=log, a=a, b=b, BrokerID=BrokerID, Account=Account)
    elif crt_cash_vanna!=0 and crt_cash_vanna*target_cash_vanna<=0:  # 目标cashvanna为零或者与当前账户cashvanna反向
        # 进行平仓
        close_all_position(BrokerID, Account, log)
        if target_cash_vanna!=0:
            crt_cash_vanna, having_position = get_crt_account_cashvanna(
        BrokerID=BrokerID, Account=Account, log=log)
            open_position_given_cash_vanna(option=option, true_option_call=true_option_call, true_option_put=true_option_put, crt_cash_vanna=crt_cash_vanna, target_cash_vanna=target_cash_vanna, log=log, a=a, b=b, BrokerID=BrokerID, Account=Account)
    elif crt_cash_vanna!=0:
        # 若delta出现偏移

        # 补做cashvanna
        if np.abs(target_cash_vanna)>np.abs(crt_cash_vanna):
            open_position_given_cash_vanna(option=option, true_option_call=true_option_call, true_option_put=true_option_put, crt_cash_vanna=crt_cash_vanna, target_cash_vanna=target_cash_vanna, log=log, a=a, b=b, BrokerID=BrokerID, Account=Account)


if __name__ == '__main__':
    simulator(log=True)

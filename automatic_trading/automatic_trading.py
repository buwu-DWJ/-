#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   automatic_trading.py
@Time    :   2022/11/30 10:58:53
@Author  :   DingWenjie
@Contact :   359582058@qq.com
@Desc    :   定义automatic_trading函数
'''


import os
import pandas as pd
import numpy as np
import warnings
import datetime
import time
import math
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


def get_option_data(is_test=False, month_list=[0,1]):
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
    for month in month_list:
        print(f'当前获取month {month}')
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
    df.rename(columns={'de': 'delta','p': 'Close','ve':'vega','th':'theta','ga':'gamma'}, inplace=True)
    close = np.array(pd.to_numeric(df['Close']))
    df['Close'] = close
    delta = np.array(pd.to_numeric(df['delta']))/100
    df['delta'] = delta
    vega = np.array(pd.to_numeric(df['vega']))
    df['vega'] = vega
    theta = np.array(pd.to_numeric(df['theta']))
    df['theta'] = theta
    gamma = np.array(pd.to_numeric(df['gamma']))
    df['gamma'] = gamma
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


def get_option_code(true_option_call, true_option_put, delta_list):
    '''
    获取当前时刻delta_list中delta对应的合约
    Args:
        true_option_call: 当前时刻call
        true_option_put: 当前时刻put
        delta_list: 所需要的delta列表
    Return:
        code_list:
        get_data: 实值合约delta是否超出给定的范围tol, 若超出-False, 反之-True
    '''
    tol = 0.15
    code_list = []
    delta_diff = []
    get_data = True
    for csd_delta in delta_list:
        if csd_delta>0:
            temp_idx = np.abs(true_option_call['delta']-csd_delta).argmin()
            code_list += [true_option_call['Symbol'][temp_idx]]
            delta_diff += [np.abs(true_option_call['delta']-csd_delta).min()]
        else:
            temp_idx = np.abs(true_option_put['delta']-csd_delta).argmin()
            code_list += [true_option_put['Symbol'][temp_idx]]
            delta_diff += [np.abs(true_option_put['delta']-csd_delta).min()]
    if np.array(delta_diff).max()>tol:
        get_data = False
    return code_list, get_data


def get_crt_account_cashgreeks(BrokerID='DCore_SIM_SS2', Account='simtest3'):
    '''
    获取当前资金账户的cashdelta, cashvega, cashgamma, cashvanna, cashtheta值
    '''
    having_position = False
    crt_position = core.QryPositionTracker()
    cash_greeks = {}
    for csd_data in crt_position['Data']:
        if csd_data['BrokerID'] == BrokerID and csd_data['Account'] == Account and csd_data['SubKey'] == 'Total' and csd_data['Symbol']=='TC.S.SSE.510050':
            having_position = True
            cash_greeks['cashvanna'] = float(csd_data['1%$Vanna'])
            cash_greeks['cashdelta'] = float(csd_data['$Delta'])
            cash_greeks['cashvega'] = float(csd_data['$Vega'])
            cash_greeks['cashgamma'] = float(csd_data['1%$Gamma'])
            cash_greeks['cashtheta'] = float(csd_data['$Theta'])
            break
    return cash_greeks, having_position


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
                'ChasePrice': '1T|3|1|M'
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


def write_summary_md(BrokerID='DCore_SIM_SS2', Account='simtest3', equity_adjust=0):
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


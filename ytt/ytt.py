#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   ytt.py
@Time    :   2022/11/22 09:40:32
@Author  :   DingWenjie
@Contact :   359582058@qq.com
@Desc    :   计算昨持损益归因, 日内交易损益归因
             昨持损益需要每天收盘后保存 core.QryPosition
             日内交易需要当天的 core.QryFillReport
'''


import os
import pandas as pd
import numpy as np
import warnings
import datetime
import tcoreapi_mq as t
from tqdm import tqdm
from pylab import mpl


mpl.rcParams['font.sans-serif'] = ['SimHei']
mpl.rcParams['axes.unicode_minus'] = False
thisDir = os.path.dirname(__file__)
warnings.simplefilter('ignore')
core = t.TCoreZMQ(quote_port="51864", trade_port="51834")
BrokerID = 'DCore_SIM_SS2'
Account = 'simtest3'
tradingday = pd.read_excel(r'C:\Users\dingwenjie\Desktop\demo\demo\dwj_tools\dwj_tools\get_dogsk_data\tradingday.xlsx')['date']
tradingday_list = [a.strftime('%Y%m%d') for a in tradingday]
today = datetime.datetime.today().strftime('%Y%m%d')
today_idx = tradingday_list.index(today)
yst = tradingday_list[today_idx-1]


def get_filled_report(Account):
    temp_filled_rep = core.QryFillReport()
    final_qry_index = temp_filled_rep[-1]['QryIndex']
    while core.QryFillReport(qryIndex=final_qry_index):
        temp_filled_rep += core.QryFillReport(qryIndex=final_qry_index)
        final_qry_index = temp_filled_rep[-1]['QryIndex']
    temp_filled_rep = [crt_rep for crt_rep in temp_filled_rep if crt_rep['Account']==Account]
    filled_rep = pd.DataFrame(temp_filled_rep)
    filled_rep = filled_rep[['Symbol', 'ReportID','TransactDate', 'TransactTime', 'Side', 'MatchedQty', 'MatchedPrice']]
    filled_rep['MatchedPrice'] = pd.to_numeric(filled_rep['MatchedPrice'])
    filled_rep['MatchedQty'] = pd.to_numeric(filled_rep['MatchedQty'])
    filled_rep['Side'] = pd.to_numeric(filled_rep['Side'])
    filled_rep.columns = ['symbol', 'report_id','date', 'filled_time', 'side', 'size', 'price']
    type_ = []
    und = []
    month = []
    und_f_str = []
    multi = []
    for symbol in filled_rep['symbol'].values:
        temp_instrumentinfo = core.QueryInstrumentInfo(symbol)['Info']['.'.join(symbol.split('.')[:4])]
        if '.O.' in symbol:
            und_f_str += [temp_instrumentinfo['Underlying.F'] + '.' + symbol.split('.')[4]]
        else:
            und_f_str += [symbol[:-7]]
        multi += [int(temp_instrumentinfo['Weight'])]
        type_ += [symbol.split('.')[1]]
        und += [symbol.split('.')[3]]
        month += [symbol.split('.')[4]]
    filled_rep['type'] = type_
    filled_rep['und'] = und
    filled_rep['month'] = month
    filled_rep['side'] = 3-2*filled_rep['side']
    filled_rep['und_f'] = und_f_str
    filled_rep['multi'] = multi
    return filled_rep


def get_today_position(BrokerID, Account):
    position = core.QryPosition(BrokerID+'-'+Account)
    position = pd.DataFrame(position)
    position = position[['Symbol', 'SecurityType', 'Exchange', 'Security', 'Month', 'TransactDate', 'Side', 'Quantity']]
    position['Side'] = pd.to_numeric(position['Side'])
    position['Quantity'] = pd.to_numeric(position['Quantity'])
    position.columns = ['symbol', 'type', 'exchange', 'und', 'month', 'date', 'side', 'size']
    position['side'] = 3-2*position['side']
    und_f_str = []
    multi = []
    for symbol in position['symbol'].values:
        temp_instrumentinfo = core.QueryInstrumentInfo(symbol)['Info']['.'.join(symbol.split('.')[:4])]
        if '.O.' in symbol:
            und_f_str += [temp_instrumentinfo['Underlying.F'] + '.' + symbol.split('.')[4]]
        else:
            und_f_str += [symbol[:-7]]
        multi += [int(temp_instrumentinfo['Weight'])]
    position['und_f'] = und_f_str
    position['multi'] = multi
    position.to_hdf('daily_position.h5', key=today+'_'+Account)
    return position


def cpt_daily_pnl_total(BrokerID, Account):
    '''
    昨持盈亏归因, 总计版
    '''
    today_position = get_today_position(BrokerID, Account)
    try:
        yst_position = pd.read_hdf('daily_position.h5', key=yst+'_'+Account)
    except KeyError:
        print('没有昨持仓位数据!\n')
        return
    end_idx = 0  # 计算期权盈亏的截止时间, 即当前时刻与日盘收盘时刻取小
    pnl_list = []
    for i, csd_rep in tqdm(enumerate(today_position['symbol'])):
        temp_pnl = {}
        temp_rep = today_position.iloc[i, :]
        temp_symbol = temp_rep['symbol']
        crt_exchange = temp_symbol.split('.')[2]
        if (crt_exchange!='SSE' and crt_exchange!='SZSE') or temp_rep['type']!='O':
            continue
        und_f_str = temp_rep['und_f']
        multi = temp_rep['multi']
        try:
            locals()[und_f_str+'_yst']
        except KeyError:
            locals()[und_f_str+'_yst'] = pd.DataFrame(core.SubHistory(und_f_str, 'DOGSK', yst+'00', yst+'07'))
            locals()[und_f_str+'_today'] = pd.DataFrame(core.SubHistory(und_f_str, 'DOGSK', today+'00', today+'07'))
        if not end_idx:
            end_idx = len(locals()[und_f_str+'_today'])-1
        if end_idx>=235:
            end_idx = 234
        try:
            locals()[f'{temp_symbol}_yst']
        except KeyError:
            locals()[f'{temp_symbol}_yst'] = pd.DataFrame(core.SubHistory(temp_symbol, 'DOGSK', yst+'00', yst+'20'))
            locals()[f'{temp_symbol}_today'] = pd.DataFrame(core.SubHistory(temp_symbol, 'DOGSK', today+'00', today+'20'))
        locals()[und_f_str+'_today'] = locals()[und_f_str+'_today'].iloc[:end_idx+1,:]
        locals()[und_f_str+'_yst'] = locals()[und_f_str+'_yst'].iloc[:235,:]
        locals()[f'{temp_symbol}_yst'] = locals()[f'{temp_symbol}_yst'].iloc[:235,:]
        locals()[f'{temp_symbol}_today'] = locals()[f'{temp_symbol}_today'].iloc[:end_idx+1,:]
        temp_pnl['symbol'] = temp_symbol
        iv_diff = float(locals()[und_f_str+'_today']['iv'].values[end_idx])-float(locals()[und_f_str+'_yst']['iv'].values[234])
        price_diff_pct = float(locals()[und_f_str+'_today']['p'].values[end_idx])/float(locals()[und_f_str+'_yst']['p'].values[234])-1
        cashgreeks_multi = temp_rep['side']*temp_rep['size']*multi
        temp_pnl['total'] = cashgreeks_multi*(float(locals()[f'{temp_symbol}_today']['p'].values[end_idx])-float(locals()[f'{temp_symbol}_yst']['p'].values[234]))
        cash_delta = cashgreeks_multi*float(locals()[f'{temp_symbol}_yst']['de'].values[234])/100 * float(locals()[und_f_str+'_yst']['p'].values[234])
        temp_pnl['size'] = temp_rep['side']*temp_rep['size']
        temp_pnl['delta'] = cash_delta * price_diff_pct
        cash_vega = cashgreeks_multi*float(locals()[f'{temp_symbol}_yst']['ve'][234])
        temp_pnl['vega'] = cash_vega*iv_diff
        cash_gamma = cashgreeks_multi/100*float(locals()[und_f_str+'_yst']['p'].values[234])**2
        temp_pnl['gamma'] = 0.5*cash_gamma*price_diff_pct**2*100
        cash_vanna = cashgreeks_multi*float(locals()[f'{temp_symbol}_yst']['va'][234])*float(locals()[und_f_str+'_yst']['p'].values[234])
        temp_pnl['vanna'] = cash_vanna*price_diff_pct*iv_diff
        cash_theta = cashgreeks_multi*float(locals()[f'{temp_symbol}_yst']['th'][234])
        temp_pnl['theta'] = cash_theta*(end_idx+6)/240
        # cash_charm = cashgreeks_multi*float(locals()[f'{temp_symbol}']['ch'][start_idx])*float(locals()[und_f_str]['p'].values[start_idx])
        # temp_pnl['charm_pnl'] = cash_charm*price_diff_pct
        # cash_vomma = cashgreeks_multi*float(locals()[f'{temp_symbol}']['vo'][start_idx])
        # temp_pnl['vomma_pnl'] = 0.5*cash_vomma*iv_diff**2
        # cash_speed = cashgreeks_multi*float(locals()[f'{temp_symbol}']['spe'][start_idx])*float(locals()[und_f_str]['p'].values[start_idx])
        # temp_pnl['speed_pnl'] = 0.5*cash_speed*price_diff_pct*(price_diff_pct*100)**2
        # cash_zomma = cashgreeks_multi*float(locals()[f'{temp_symbol}']['zo'][start_idx])*float(locals()[und_f_str]['p'].values[start_idx])
        # temp_pnl['zomma_pnl'] = cash_zomma*iv_diff/100*(0.5*100*price_diff_pct)
        pnl_list += [temp_pnl]
    pnl_df = pd.DataFrame(pnl_list).round()
    all_pnl = pnl_df.copy(deep=True)
    allund = pnl_df['symbol']
    allund_with_month = allund.apply(lambda x: '.'.join(x.split('.')[:5]))
    allund_without_month = allund.apply(lambda x: '.'.join(x.split('.')[:4]))
    pnl_month = pd.DataFrame()
    pnl_no_month = pd.DataFrame()
    for csd_und in allund_with_month.drop_duplicates().values:
        temp_df = pnl_df.loc[csd_und == allund_with_month,:].sum().to_frame().T
        temp_df['symbol'] = csd_und
        pnl_month = pnl_month.append(temp_df)
    for csd_und in allund_without_month.drop_duplicates().values:
        temp_df = pnl_df.loc[csd_und == allund_without_month,:].sum().to_frame().T
        temp_df['symbol'] = csd_und
        pnl_no_month = pnl_no_month.append(temp_df)
    return all_pnl.set_index('symbol',drop=True), pnl_month.set_index('symbol',drop=True), pnl_no_month.set_index('symbol',drop=True)


def cpt_intraday_pnl_total(Account):
    '''
    日内期权盈亏分析, 总计版
    '''
    end_idx = 0  # 计算期权盈亏的截止时间, 即当前时刻与日盘收盘时刻取小
    filled_rep = get_filled_report(Account)
    pnl_list = []
    for i, csd_rep in tqdm(enumerate(filled_rep['symbol'])):
        temp_pnl = {}
        temp_rep = filled_rep.iloc[i, :]
        temp_symbol = temp_rep['symbol']
        crt_exchange = temp_symbol.split('.')[2]
        if (crt_exchange!='SSE' and crt_exchange!='SZSE') or temp_rep['type']!='O':
            continue
        und_f_str = temp_rep['und_f']
        multi = temp_rep['multi']
        try:
            locals()[und_f_str]
        except KeyError:
            locals()[und_f_str] = pd.DataFrame(core.SubHistory(und_f_str, 'DOGSK', today+'00', today+'07'))
        if not end_idx:
            end_idx = len(locals()[und_f_str])-1
        if end_idx>=235:
            end_idx = 234
        try:
            locals()[f'{temp_symbol}']
        except KeyError:
            locals()[f'{temp_symbol}'] = pd.DataFrame(core.SubHistory(temp_symbol, 'DOGSK', today+'00', today+'20'))
        locals()[und_f_str] = locals()[und_f_str].iloc[:end_idx+1,:]
        locals()[f'{temp_symbol}'] = locals()[f'{temp_symbol}'].iloc[:end_idx+1,:]
        filled_time = temp_rep['filled_time'][:3]
        start_idx = (np.array([int(a[:-5]) for a in locals()[f'{temp_symbol}']['t']])<int(filled_time)).sum()  # 该单成交时间id, 以该时间为起始时刻
        temp_pnl['symbol'] = temp_symbol
        temp_pnl['report_id'] = temp_rep['report_id']
        temp_pnl['filled_time'] = temp_rep['filled_time']
        iv_diff = float(locals()[und_f_str]['iv'].values[end_idx])-float(locals()[und_f_str]['iv'].values[start_idx])
        price_diff_pct = float(locals()[und_f_str]['p'].values[end_idx])/float(locals()[und_f_str]['p'].values[start_idx])-1
        cashgreeks_multi = temp_rep['side']*temp_rep['size']*multi
        temp_pnl['total'] = cashgreeks_multi*(float(locals()[f'{temp_symbol}']['p'].values[end_idx])-temp_rep['price'])
        cash_delta = cashgreeks_multi*float(locals()[f'{temp_symbol}']['de'].values[start_idx])/100 * float(locals()[und_f_str]['p'].values[start_idx])
        temp_pnl['size'] = temp_rep['side']*temp_rep['size']
        temp_pnl['delta'] = cash_delta * price_diff_pct
        cash_vega = cashgreeks_multi*float(locals()[f'{temp_symbol}']['ve'][start_idx])
        temp_pnl['vega'] = cash_vega*iv_diff
        cash_gamma = cashgreeks_multi/100*float(locals()[und_f_str]['p'].values[start_idx])**2
        temp_pnl['gamma'] = 0.5*cash_gamma*price_diff_pct**2*100
        cash_vanna = cashgreeks_multi*float(locals()[f'{temp_symbol}']['va'][start_idx])*float(locals()[und_f_str]['p'].values[start_idx])
        temp_pnl['vanna'] = cash_vanna*price_diff_pct*iv_diff
        cash_theta = cashgreeks_multi*float(locals()[f'{temp_symbol}']['th'][start_idx])
        temp_pnl['theta'] = cash_theta*(end_idx-start_idx)/240
        # cash_charm = cashgreeks_multi*float(locals()[f'{temp_symbol}']['ch'][start_idx])*float(locals()[und_f_str]['p'].values[start_idx])
        # temp_pnl['charm_pnl'] = cash_charm*price_diff_pct
        # cash_vomma = cashgreeks_multi*float(locals()[f'{temp_symbol}']['vo'][start_idx])
        # temp_pnl['vomma_pnl'] = 0.5*cash_vomma*iv_diff**2
        # cash_speed = cashgreeks_multi*float(locals()[f'{temp_symbol}']['spe'][start_idx])*float(locals()[und_f_str]['p'].values[start_idx])
        # temp_pnl['speed_pnl'] = 0.5*cash_speed*price_diff_pct*(price_diff_pct*100)**2
        # cash_zomma = cashgreeks_multi*float(locals()[f'{temp_symbol}']['zo'][start_idx])*float(locals()[und_f_str]['p'].values[start_idx])
        # temp_pnl['zomma_pnl'] = cash_zomma*iv_diff/100*(0.5*100*price_diff_pct)
        pnl_list += [temp_pnl]
    pnl_df = pd.DataFrame(pnl_list).round()
    all_pnl = pnl_df.copy(deep=True)
    del pnl_df['report_id']
    del pnl_df['filled_time']
    allund = pnl_df['symbol']
    allund_with_month = allund.apply(lambda x: '.'.join(x.split('.')[:5]))
    allund_without_month = allund.apply(lambda x: '.'.join(x.split('.')[:4]))
    pnl_month = pd.DataFrame()
    pnl_no_month = pd.DataFrame()
    for csd_und in allund_with_month.drop_duplicates().values:
        temp_df = pnl_df.loc[csd_und == allund_with_month,:].sum().to_frame().T
        temp_df['symbol'] = csd_und
        pnl_month = pnl_month.append(temp_df)
    for csd_und in allund_without_month.drop_duplicates().values:
        temp_df = pnl_df.loc[csd_und == allund_without_month,:].sum().to_frame().T
        temp_df['symbol'] = csd_und
        pnl_no_month = pnl_no_month.append(temp_df)
    return all_pnl.set_index('symbol',drop=True), pnl_month.set_index('symbol',drop=True), pnl_no_month.set_index('symbol',drop=True)


def get_md():
    folder_path = os.path.join(thisDir, 'summary')
    if not os.path.exists(folder_path):
        os.mkdir(folder_path)
    md_str = '# 模拟交易损益归因\n\n## 日内损益归因\n'
    all_pnl, pnl_month, pnl_no_month = cpt_intraday_pnl_total(Account)
    md_str += '### 分月份损益\n' + pnl_month.to_markdown() + '\n### 合并月份损益\n' + pnl_no_month.to_markdown() + '\n## 昨持损益归因\n'
    all_pnl, pnl_month, pnl_no_month = cpt_daily_pnl_total(BrokerID, Account)
    md_str += '### 分月份损益\n' + pnl_month.to_markdown() + '\n### 合并月份损益\n' + pnl_no_month.to_markdown()
    md_str = md_str.replace('|--','|:--').replace('--|','--:|')
    output_path = os.path.join(thisDir, f'summary\\{today}.md')
    if os.path.exists(output_path):
        os.remove(output_path)
    with open(output_path, 'w', encoding='utf-8') as file:
        file.writelines(md_str)
    file.close()


get_md()
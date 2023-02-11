#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   cta.py
@Time    :   2023/01/03 14:25:31
@Author  :   DingWenjie
@Contact :   359582058@qq.com
@Desc    :   cta automatic_trading utilities
'''


from icetcore import TCoreAPI, OrderStruct
import pandas as pd
import os
import numpy as np
import warnings
import time
import datetime
import sys
import tkinter as tk
from tkinter import ttk


warnings.simplefilter('ignore')
thisDir = os.path.dirname(__file__)
api = TCoreAPI()
re = api.connect()
tradingday = pd.read_excel(os.path.join(
    thisDir, 'tradingday.xlsx'), index_col=0)
date_str_list = [csd_date.strftime('%Y%m%d') for csd_date in tradingday.index]
TODAY_STR = datetime.date.today().strftime('%Y%m%d')
YESTERDAY_STR = date_str_list[date_str_list.index(TODAY_STR)-1]


class Automatic_Trading_CTA():
    '''
    Args:
        strategy_list:
        strategy_name:
    Funcs:
        runfile_and_get_position:
        get_today_position:
    '''

    def __init__(self, strategy_name, ACCOUNT, BROKERID):
        self.strategy_name = strategy_name
        self.ACCOUNT = ACCOUNT
        self.BROKERID = BROKERID
        self.strategy_len = len(strategy_name)

    @staticmethod
    def __get_exchange_given_und(und):
        if 'TC.F.' in und:
            return '.'.join(und.split('.')[2:4])
        elif und.upper() in ['AP', 'CF', 'CJ', 'CY', 'FG', 'JR', 'LR', 'MA', 'OI', 'PF',
                             'PK', 'PM', 'RI', 'RM', 'RS', 'SA', 'SF', 'SM', 'SR', 'TA',
                             'UR', 'WH', 'ZC']:
            return 'CZCE.'+und.upper()
        elif und.upper() in ['AG', 'AL', 'AU', 'BU', 'CU', 'FU', 'HC', 'NI', 'PB',
                             'RB', 'RU', 'SN', 'SP', 'SS', 'ZN', 'WR']:
            return 'SHFE.'+und.lower()
        elif und.upper() in ['BC', 'LU', 'NR', 'SC']:
            return 'INE.'+und.lower()
        elif und.upper() in ['A', 'B', 'BB', 'C', 'CS', 'EB', 'EG', 'FB', 'I', 'J',
                             'JD', 'JM', 'L', 'LH', 'M', 'P', 'PG', 'PP', 'RR', 'V', 'Y']:
            return 'DCE.'+und.lower()
        else:
            sys.exit('品种代号有问题, 停止脚本')

    # def __runfile_and_get_position_from_py(self):
    #     '''run .py to get positions of the strategies, return dataframe'''
    #     pos_dict = {}
    #     for i, strategy in enumerate(self.strategy_list):
    #         globals()[f'strategy_{i}'] = __import__(strategy, fromlist=True)
    #         temp_pos_dict = globals()[f'strategy_{i}'].pos
    #         for csd_und in list(temp_pos_dict.keys()):
    #             csd_und_with_exchange = self.__get_exchange_given_und(csd_und)
    #             temp_hot_month = api.gethotmonth(
    #                 'TC.F.'+csd_und_with_exchange+'.HOT', strdate=TODAY_STR, strtime='00')
    #             temp_pos_dict[list(temp_hot_month.values())[
    #                 0]] = temp_pos_dict.pop(csd_und)
    #         pos_dict[self.strategy_name[i]] = temp_pos_dict
    #     pos_df = pd.DataFrame.from_dict(
    #         pos_dict, orient='index')
    #     return pos_df.sort_index(axis=1)

    def __get_position_from_excel(self, date_type='today'):
        pos_df = pd.DataFrame()
        for i, csd_strategy in enumerate(self.strategy_name):
            print(csd_strategy)
            if date_type == 'today':
                temp_df = pd.read_excel(os.path.join(thisDir,
                                                     f'position/{csd_strategy}_position.xlsx'))
            elif date_type == 'yesterday':
                temp_df = pd.read_excel(os.path.join(thisDir,
                                                     f'position/{csd_strategy}_position_old.xlsx'))
            for csd_und in list(temp_df.columns):
                csd_und_with_exchange = self.__get_exchange_given_und(csd_und)
                temp_hot_month = api.gethotmonth(
                    'TC.F.'+csd_und_with_exchange+'.HOT', strdate=TODAY_STR, strtime='00')
                temp_df = temp_df.rename(
                    columns={csd_und: list(temp_hot_month.values())[0]})
            if date_type == 'today':
                temp_df.to_excel(os.path.join(thisDir,
                                              f'position/{csd_strategy}_position.xlsx'), index=False)
            elif date_type == 'yesterday':
                temp_df.to_excel(os.path.join(thisDir,
                                              f'position/{csd_strategy}_position_old.xlsx'), index=False)
            pos_df = pos_df.append(temp_df)
        pos_df.index = self.strategy_name
        return pos_df.sort_index(axis=1)

    # def save_today_position(self):
    #     '''save today position into .hdf'''
    #     pos_df = self.__get_position_from_excel()
    #     # pos_df = self.__runfile_and_get_position()
    #     # with pd.HDFStore('position.h5') as store:
    #     #     pos_keys = store.keys
    #     pos_df.to_hdf('position.h5', key='position_'+TODAY_STR)
    #     return pos_df

    def get_theory_intraday_position(self):
        ''''''
        intraday_dict = {}
        today_pos = self.__get_position_from_excel(date_type='today')
        yesterday_pos = self.__get_position_from_excel(date_type='yesterday')
        for i, csd_strategy in enumerate(self.strategy_name):
            today_position = today_pos.loc[csd_strategy, :].T.dropna()
            yesterday_position = yesterday_pos.loc[csd_strategy, :].T.dropna()
            concat_position = pd.concat(
                [today_position, yesterday_position], axis=1)
            concat_position.columns = ['a', 'b']
            intraday_position = concat_position['a'].fillna(
                0) - concat_position['b'].fillna(0)
            intraday_position.drop(
                intraday_position[intraday_position == 0].index, inplace=True)
            intraday_dict[csd_strategy] = dict(intraday_position)
        intraday_pos_df = pd.DataFrame.from_dict(intraday_dict, orient='index')
        return intraday_pos_df.sort_index(axis=1), today_pos.sort_index(axis=1), yesterday_pos.sort_index(axis=1)

    def get_real_intraday_position(self, today_pos, crt_pos):
        today_total = today_pos.sum()
        today_total.drop(today_total[today_total == 0].index, inplace=True)
        if type(crt_pos) == int:
            return pd.DataFrame(today_total).T
        else:
            crt_total = crt_pos.sum()
            concat_total = pd.concat([today_total, crt_total], axis=1)
            concat_total.columns = ['a', 'b']
            intraday_position = concat_total['a'].fillna(
                0) - concat_total['b'].fillna(0)
            intraday_position = intraday_position.drop(
                intraday_position[intraday_position == 0].index)
            intraday_pos_df = pd.DataFrame(intraday_position).T
            return intraday_pos_df.sort_index(axis=1)

    def get_crt_position_given_account(self):
        crt_position_only = api.getposition(self.BROKERID+'-'+self.ACCOUNT)
        if not crt_position_only:
            return 0
        else:
            crt_position = pd.DataFrame()
            for csd_und in crt_position_only:
                if csd_und['SymbolA'] == '':
                    if csd_und['Symbol'] not in crt_position.columns:
                        crt_position[csd_und['Symbol']] = [
                            csd_und['Quantity']*(3-csd_und['Side']*2)]
                    else:
                        crt_position[csd_und['Symbol']] = [crt_position[csd_und['Symbol']] +
                                                           csd_und['Quantity']*(3-csd_und['Side']*2)]
                else:
                    if csd_und['SymbolA'] not in crt_position.columns:
                        crt_position[csd_und['SymbolA']] = [
                            csd_und['Quantity']*(3-csd_und['Side1']*2)]
                    else:
                        crt_position[csd_und['SymbolA']] = [crt_position[csd_und['SymbolA']] +
                                                            csd_und['Quantity']*(3-csd_und['Side1']*2)]
                    if csd_und['SymbolB'] not in crt_position.columns:
                        crt_position[csd_und['SymbolB']] = [
                            csd_und['Quantity']*(3-csd_und['Side2']*2)]
                    else:
                        crt_position[csd_und['SymbolB']] = [crt_position[csd_und['SymbolB']] +
                                                            csd_und['Quantity']*(3-csd_und['Side2']*2)]
            return crt_position.sort_index(axis=1)

    def show_intraday_position(self):
        '''
        Tkinter gui to show intraday_position and do trading and save_data
        '''
        intraday_df, today_df, yesterday_df = self.get_theory_intraday_position()
        window = tk.Tk()
        window.title('品种仓位')
        for i, csd_strategy in enumerate(self.strategy_name):
            tk.Label(window, text='品种:').grid(row=i*5, column=1)
            tk.Label(window, text=csd_strategy+':').grid(row=i*5+1, column=0)
            tk.Label(window, text='今日仓位:').grid(row=i*5+1, column=1)
            tk.Label(window, text='昨日仓位:').grid(row=i*5+2, column=1)
            tk.Label(window, text='日内交易:').grid(row=i*5+3, column=1)
            # csd_intraday_position = intraday_df.loc[csd_strategy, :].dropna()
            try:
                csd_intraday_position = intraday_df.loc[csd_strategy, :].dropna(
                )
            except KeyError:
                csd_intraday_position = pd.Series([0])
                csd_intraday_position.index = ['TC.F.CZCE.MA.202305']
            csd_today_position = today_df.loc[csd_strategy, :].dropna()
            csd_yesterday_position = yesterday_df.loc[csd_strategy, :].dropna()
            concat_position = pd.concat(
                [csd_today_position, csd_yesterday_position, csd_intraday_position], axis=1)
            concat_position.columns = ['a', 'b', 'c']
            concat_position = concat_position.T.fillna(0)
            for j, csd_und in enumerate(concat_position.columns):
                tk.Label(window, text='.'.join(
                    csd_und.split('.')[-2:])).grid(row=i*5, column=2+j)
                for k in range(3):
                    tk.Label(window, text=str(int(concat_position.iloc[k, j]))).grid(
                        row=i*5+1+k, column=2+j)
            tk.Label(window, text='').grid(row=i*5+4, column=0)
        intraday_total = intraday_df.sum()
        today_total = today_df.sum()
        today_total.drop(today_total[today_total == 0].index, inplace=True)
        tk.Label(window, text='理论目标仓位:').grid(row=i*5+6, column=1)
        for j, csd_und in enumerate(today_total.index):
            tk.Label(window, text='.'.join(csd_und.split(
                '.')[-2:])).grid(row=i*5+5, column=2+j)
            tk.Label(window, text=str(int(today_total.values[j]))).grid(
                row=i*5+6, column=2+j)
        crt_position = self.get_crt_position_given_account()
        tk.Label(window, text='当前总仓位:').grid(row=i*5+8, column=1)
        if type(crt_position) == int:
            tk.Label(window, text='当前无仓位').grid(row=i*5+7, column=2+j)
            tk.Label(window, text='当前无仓位').grid(
                row=i*5+8, column=2+j)
        else:
            for j, csd_und in enumerate(crt_position.columns):
                tk.Label(window, text='.'.join(csd_und.split(
                    '.')[-2:])).grid(row=i*5+7, column=2+j)
                tk.Label(window, text=str(int(crt_position[csd_und]))).grid(
                    row=i*5+8, column=2+j)
        tk.Label(window, text='').grid(row=i*5+9, column=0)
        tk.Label(window, text='理论日内合计:').grid(row=i*5+11, column=1)
        for j, csd_und in enumerate(intraday_total.index):
            tk.Label(window, text='.'.join(csd_und.split(
                '.')[-2:])).grid(row=i*5+10, column=2+j)
            tk.Label(window, text=str(int(intraday_total.values[j]))).grid(
                row=i*5+11, column=2+j)
        real_intraday_position = self.get_real_intraday_position(
            today_df, crt_position)
        real_intraday = real_intraday_position.copy(deep=True)
        tk.Label(window, text='实际日内合计:').grid(row=i*5+13, column=1)
        for j, csd_und in enumerate(real_intraday_position.columns):
            tk.Label(window, text='.'.join(csd_und.split(
                '.')[-2:])).grid(row=i*5+12, column=2+j)
            tk.Label(window, text=str(int(real_intraday_position[csd_und]))).grid(
                row=i*5+13, column=2+j)
        tk.Label(window, text='').grid(row=i*5+14, column=0)

        def do_trading_given_intraday_position():
            if do_trading.get() == '否':
                return
            elif do_trading.get() == '是':
                df = real_intraday
                for i, csd_und in enumerate(df):
                    csd_qty = np.abs(int(df[csd_und].values))
                    csd_side = int(1.5-np.sign(df[csd_und].values)/2)
                    while csd_qty > 0:
                        if csd_qty > int(get_max_qty.get()):
                            temp_qty = int(get_max_qty.get())
                        else:
                            temp_qty = csd_qty
                        # order = OrderStruct(ACCOUNT=self.ACCOUNT,
                        #                     BROKERID=self.BROKERID,
                        #                     Symbol=csd_und,
                        #                     Side=csd_side,
                        #                     OrderQty=temp_qty,
                        #                     OrderType=1,
                        #                     TimeInForce=2,
                        #                     PositionEffect=4,
                        #                     SelfTradePrevention=3,
                        #                     )
                        order = OrderStruct(Account=self.ACCOUNT,
                                            BrokerID=self.BROKERID,
                                            Symbol=csd_und,
                                            Side=csd_side,
                                            OrderQty=temp_qty,
                                            OrderType=10,
                                            TimeInForce=1,
                                            PositionEffect=4,
                                            SelfTradePrevention=3,
                                            Synthetic=1,
                                            ChasePrice="1T|3|3|M"  # 加价, 追几次, 每次追几秒, 最终市价M或删单C
                                            )
                        orderkey = api.neworder(order)
                        csd_qty -= temp_qty
                        time.sleep(0.5)
                do_trading.current(1)

        def save_data_():
            for j, csd_strategy in enumerate(self.strategy_name):
                temp_df = pd.read_excel(os.path.join(thisDir,
                                                     f'position/{csd_strategy}_position.xlsx'))
                temp_df.to_excel(os.path.join(thisDir,
                                              f'position/{csd_strategy}_position_old.xlsx'), index=False)
            save_data.current(1)
            tk.Label(window, text='保存完毕!').grid(row=i*5+17, column=3)
            return

        def go_0(*args):
            print(do_trading.get())

        def go_1(*args):
            print(get_max_qty.get())

        def go_2(*args):
            print(save_data.get())
        tk.Label(window, text='最长交易时间:').grid(row=i*5+15, column=0)
        get_max_qty = ttk.Combobox(
            window, textvariable=tk.StringVar(), width=5)
        get_max_qty['values'] = ('10', '20', '30', '40', '50', '60')
        get_max_qty.current(3)
        get_max_qty.bind('<<ComboboxSelected>>', go_1)
        get_max_qty.grid(row=i*5+15, column=1)
        tk.Label(window, text='是否进行交易:').grid(row=i*5+16, column=0)
        do_trading = ttk.Combobox(
            window, textvariable=tk.StringVar(), width=5)
        do_trading['values'] = ('是', '否')
        do_trading.current(1)
        do_trading.bind('<<ComboboxSelected>>', go_0)
        do_trading.grid(row=i*5+16, column=1)
        tk.Button(window, text="开始交易", width=10, command=do_trading_given_intraday_position).grid(
            row=i*5+16, column=2, padx=1, pady=1)
        tk.Label(window, text='是否覆盖数据:').grid(row=i*5+17, column=0)
        save_data = ttk.Combobox(window, textvariable=tk.StringVar(), width=5)
        save_data['values'] = ('是', '否')
        save_data.current(1)
        save_data.bind('<<ComboboxSelected>>', go_2)
        save_data.grid(row=i*5+17, column=1)
        tk.Button(window, text='保存数据', width=10, command=save_data_).grid(
            row=i*5+17, column=2, padx=1, pady=1)
        tk.Label(window, text='保存只可在日盘收盘后进行!').grid(
            row=i*5+18, column=0, columnspan=2)

        window.mainloop()

'''
    df.h5:    und_option_dogsk_YYYYMMDD, 期权dogsk原始数据
              und_dogsk_YYYYMMDD, 标的dogsk原始数据
              und_iv_YYYYMMDD, 计算得到的iv,skew等数据

'''


import pandas as pd
import numpy as np
from icetcore import TCoreAPI, BarType, GreeksType, SymbolType
import os
import warnings
import datetime
import multiprocessing
import json
import time
from numba import jit
from tqdm import tqdm
from scipy.stats import percentileofscore
from matplotlib import pyplot as plt
from pylab import mpl


mpl.rcParams['font.sans-serif'] = ['SimHei']
mpl.rcParams['axes.unicode_minus'] = False
warnings.simplefilter('ignore')
thisDir = os.path.dirname(__file__)
api = TCoreAPI()
re = api.connect()
TRADINGDAY_START_IDX = 1219
# TRADINGDAY_START_IDX = 1400
TDAYS_PER_YEAR = 240
TODAY_STR = datetime.datetime.today().strftime('%Y%m%d')
trading_day = pd.read_excel(
    r'C:\Users\dingwenjie\Desktop\demo\demo\dwj_tools\dwj_tools\get_dogsk_data\tradingday.xlsx', index_col=0).index
trading_day = [a.strftime('%Y%m%d') for a in trading_day]
if time.localtime().tm_hour < 15:
    TODAY_STR = trading_day[trading_day.index(TODAY_STR)-1]
YESTERDAY_STR = trading_day[trading_day.index(TODAY_STR)-1]
END_IDX = trading_day.index(TODAY_STR)
if not os.path.exists(os.path.join(thisDir, f'data/{TODAY_STR}')):
    os.mkdir(os.path.join(thisDir, f'data/{TODAY_STR}'))


class CTA_DATA_PROCESSING():
    def __init__(self, und_list):
        self.close_df = {}
        self.und_list = und_list
        self.undf_symbol = {}
        self.iv = {}
        self.iv_history = {}
        self.vol_df = {}
        self.tau = {}
        self.maturity = {}

    def get_fadj_data_given_hotmonth(self):
        fadj_dict = json.load(
            open(os.path.join(thisDir, f'data/{YESTERDAY_STR}/fadj.json')))
        new_fadj_dict = {}
        for und in self.und_list:
            print(und)
            df = pd.read_json(fadj_dict[und])
            hotmonth = pd.read_excel(os.path.join(
                thisDir, 'data.xlsx'), sheet_name='hotmonth_'+und.split('.')[1], index_col=0)  # .drop_duplicates(subset=['hot'])
            hotmonth_str = hotmonth['hot'].values[-1]
            subhotmonth_str = hotmonth['subhot'].values[-1]
            self.undf_symbol[und+'_hot'] = f'TC.F.{und}.{hotmonth_str}'
            self.undf_symbol[und+'_subhot'] = f'TC.F.{und}.{subhotmonth_str}'
            self.iv[und+'_hot'] = api.getgreekshistory(
                GreeksType.DOGSK, 1, self.undf_symbol[und+'_hot'], TODAY_STR+'00', TODAY_STR+'23')[-5]['IV']
            self.iv[und+'_subhot'] = api.getgreekshistory(
                GreeksType.DOGSK, 1, self.undf_symbol[und+'_subhot'], TODAY_STR+'00', TODAY_STR+'23')[-5]['IV']
            start_idx = trading_day.index(
                str(df.index[-1]))+1
            for i, date in tqdm(enumerate(trading_day[start_idx:END_IDX+1])):
                current_hotmonth = hotmonth['hot'][hotmonth.index[hotmonth.index <= int(
                    trading_day[start_idx+i])][-1]]
                if int(date) in hotmonth.index:
                    last_hotmonth = hotmonth['hot'][hotmonth.index[hotmonth.index <= int(
                        trading_day[start_idx+i-1])][-1]]
                    fadj_factor = api.getquotehistory(
                        BarType.DK, 1, f'TC.F.{und}.{current_hotmonth}', trading_day[start_idx+i-1]+'00', trading_day[start_idx+i-1]+'23')[0]['Close']/api.getquotehistory(
                        BarType.DK, 1, f'TC.F.{und}.{last_hotmonth}', trading_day[start_idx+i-1]+'00', trading_day[start_idx+i-1]+'23')[0]['Close']
                    df = df * fadj_factor
                try:
                    temp_df = pd.DataFrame(api.getquotehistory(
                        BarType.DK, 1, f'TC.F.{und}.{current_hotmonth}', trading_day[start_idx+i]+'00', trading_day[start_idx+i]+'23'))[['Open', 'High', 'Low', 'Close']]
                except KeyError:
                    print(f'{date}:{und}quotehistory数据为空')
                    temp_df = pd.DataFrame(df.iloc[-1, :]).T
                temp_df.index = [int(date)]
                temp_df.columns = ['open', 'high', 'low', 'close']
                df = df.append(temp_df)
            self.close_df[und] = df
            new_fadj_dict[und] = df.to_json()
        with open(os.path.join(thisDir, f'data/{TODAY_STR}/fadj.json'), 'w') as f:
            f.write(json.dumps(new_fadj_dict))

    def get_iv_and_tau_history(self):
        self.tau = json.load(
            open(os.path.join(thisDir, f'data/{YESTERDAY_STR}/tau_history.json')))
        self.iv_history = json.load(
            open(os.path.join(thisDir, f'data/{YESTERDAY_STR}/iv_history.json')))
        self.maturity = json.load(
            open(os.path.join(thisDir, f'data/{YESTERDAY_STR}/maturity_history.json')))
        for und in self.und_list:
            print(f'当前获取{und}的历史iv以及到期日信息')
            # self.iv_history[und] = {}
            # self.tau[und+'_hot'] = {}
            # self.tau[und+'_subhot'] = {}
            # self.maturity[und+'_hot'] = {}
            # self.maturity[und+'_subhot'] = {}
            hotmonth = pd.read_excel(os.path.join(
                thisDir, 'data.xlsx'), sheet_name='hotmonth_'+und.split('.')[1], index_col=0)  # .drop_duplicates(subset=['hot'])
            for i, date in tqdm(enumerate(trading_day[TRADINGDAY_START_IDX:END_IDX+1])):
                if date in self.iv_history[self.und_list[0]]:
                    continue
                crt_hotmonth = hotmonth['hot'][hotmonth.index[hotmonth.index <= int(
                    date)][-1]]
                crt_subhotmonth = hotmonth['subhot'][hotmonth.index[hotmonth.index <= int(
                    date)][-1]]
                symbol_history = api.getsymbolhistory(
                    SymbolType.Options, date)
                if not symbol_history:
                    symbol_history = api.getsymbolhistory(
                        SymbolType.Options, date)
                for temp_ in symbol_history['Node']:
                    if temp_['ENG'].split('(')[0] == und.split('.')[0]:
                        for temp__ in temp_['Node']:
                            if temp__['Node'][0]['Node'][0]['Contracts'][0].split('.')[3] == und.split('.')[1]:
                                for temp___ in temp__['Node']:
                                    if temp___['ENG'] != 'HOT' and temp___['ENG'] == str(crt_hotmonth):
                                        self.tau[und+'_hot'][date] = int(
                                            temp___['Node'][0]['TradeingDays'][0])
                                        self.maturity[und+'_hot'][date] = temp___[
                                            'Node'][0]['ExpirationDate'][0]
                                    elif temp___['ENG'] != 'HOT' and temp___['ENG'] == str(crt_subhotmonth):
                                        self.tau[und+'_subhot'][date] = int(
                                            temp___['Node'][0]['TradeingDays'][0])
                                        self.maturity[und+'_subhot'][date] = temp___[
                                            'Node'][0]['ExpirationDate'][0]
                                break
                        break
                try:
                    self.iv_history[und][date] = api.getgreekshistory(
                        GreeksType.DOGSK, 1, f'TC.F.{und}.{crt_hotmonth}', date+'00', date+'23')[-5]['IV']
                except TypeError:
                    print(f'{und}:{date}dogsk数据有问题')
                    self.iv_history[und][date] = self.iv_history[und][trading_day[TRADINGDAY_START_IDX:END_IDX+1][i-1]]
        with open(os.path.join(thisDir, f'data/{TODAY_STR}/tau_history.json'), 'w') as f:
            f.write(json.dumps(self.tau))
        with open(os.path.join(thisDir, f'data/{TODAY_STR}/iv_history.json'), 'w') as f:
            f.write(json.dumps(self.iv_history))
        with open(os.path.join(thisDir, f'data/{TODAY_STR}/maturity_history.json'), 'w') as f:
            f.write(json.dumps(self.maturity))

    @staticmethod
    @jit(nopython=True)
    def cal_yz(temp_array):
        sig = np.zeros(temp_array.shape[0]-1)
        sig_yz = np.zeros(temp_array.shape[0]-1)
        length = temp_array.shape[0]
        open_array = temp_array[:, 0]
        high_array = temp_array[:, 1]
        low_array = temp_array[:, 2]
        close_array = temp_array[:, 3]
        preclose_array = temp_array[:, 4]
        for i in range(length-1):
            temp_open = open_array[-i-2:]
            temp_high = high_array[-i-2:]
            temp_low = low_array[-i-2:]
            temp_close = close_array[-i-2:]
            temp_pre_close = preclose_array[-i-2:]
            sig_overnight = np.log(temp_open/temp_pre_close).var()
            sig_open_to_close = np.log(temp_close/temp_open).var()
            sig[i] = np.log(temp_close/temp_pre_close).std() * \
                np.sqrt(TDAYS_PER_YEAR)
            sig_rs = (np.log(temp_high/temp_close)*np.log(temp_high /
                                                          temp_open)+np.log(temp_low/temp_close)*np.log(temp_low/temp_open)).mean()
            k = 0.34/(1.34 + (len(temp_close)+1)/(len(temp_close)-1))
            sig_yz[i] = np.sqrt(k*sig_open_to_close + sig_overnight +
                                (1-k)*sig_rs)*np.sqrt(TDAYS_PER_YEAR)
        return sig*100, sig_yz*100

    def calculate_yz(self):
        self.get_fadj_data_given_hotmonth()
        for und in self.und_list:
            print(und)
            self.close_df[und]['preclose'] = self.close_df[und]['close'].shift(
                1)
            self.close_df[und].dropna(inplace=True)
            total_len = len(self.close_df[und])
            hv_array = np.zeros((total_len, total_len))
            yz_array = np.zeros((total_len, total_len))
            for i, date in tqdm(enumerate(self.close_df[und].index)):
                if i != 0:
                    temp_array = np.array(self.close_df[und].iloc[:i+1, :])
                    re_sig, re_yz = self.cal_yz(temp_array)
                    hv_array[i, 1:i+1] = re_sig
                    yz_array[i, 1:i+1] = re_yz
            hv_df = pd.DataFrame(hv_array)
            hv_df.index = self.close_df[und].index
            hv_df.columns = range(total_len)
            yz_df = pd.DataFrame(yz_array)
            yz_df.index = self.close_df[und].index
            yz_df.columns = range(total_len)
            self.vol_df[f'{und}_hv'] = hv_df
            self.vol_df[f'{und}_yz'] = yz_df

    def draw_volcone(self):
        percentile_list = [10, 25, 50, 75, 90]
        fig = plt.figure(
            figsize=(8, 3*len(self.und_list)))
        for i, und in enumerate(self.und_list):
            tau_hotmonth = self.tau[und+'_hot'][TODAY_STR]
            tau_subhotmonth = self.tau[und+'_subhot'][TODAY_STR]
            len_fig = max(tau_hotmonth, tau_subhotmonth)+2
            iv_hotmonth = self.iv[und+'_hot']
            iv_subhotmonth = self.iv[und+'_subhot']
            ax = fig.add_subplot(len(self.und_list), 1, i+1)
            for vol_type in ['yz']:
                df = self.vol_df[und+'_'+vol_type]
                for percentile in percentile_list:
                    locals()[f'pct_{percentile}'] = []
                for i in range(len_fig):
                    csd_array = df[i+1].values[i+1:]
                    for percentile in percentile_list:
                        locals()[
                            f'pct_{percentile}'] += [np.percentile(csd_array, percentile)]
                for percentile in percentile_list:
                    plt.plot(df.columns[1:len_fig+1], locals()[
                             f'pct_{percentile}'], label=str(percentile))
                if iv_hotmonth:
                    percentile_hotmonth = percentileofscore(
                        df[tau_hotmonth].dropna().values, iv_hotmonth)
                    plt.annotate(f'{iv_hotmonth}({percentile_hotmonth:.0f})', xy=(
                        tau_hotmonth, iv_hotmonth), xytext=(tau_hotmonth, iv_hotmonth+2))
                    plt.scatter([tau_hotmonth], [iv_hotmonth])
                if iv_subhotmonth:
                    percentile_subhotmonth = percentileofscore(
                        df[tau_subhotmonth].dropna().values, iv_subhotmonth)
                    plt.annotate(f'{iv_subhotmonth}({percentile_subhotmonth:.0f})', xy=(
                        tau_subhotmonth, iv_subhotmonth), xytext=(tau_subhotmonth, iv_subhotmonth+2))
                    plt.scatter([tau_subhotmonth], [iv_subhotmonth])
                plt.title(und+'_'+vol_type, fontsize=15)
                plt.legend()
                plt.grid()
                plt.tight_layout()
                plt.xticks(fontsize=12)
                plt.yticks(fontsize=12)
        fig.savefig(os.path.join(
            thisDir, f'data/{TODAY_STR}/波动率锥_{TODAY_STR}.png'), dpi=300)

    def update_iv_data(self):
        for i, und in enumerate(und_list):
            hot_month = pd.read_excel(
                os.path.join(thisDir, 'data.xlsx'), sheet_name='hotmonth_'+und.split('.')[1], index_col=0)
            print(f'{und}: 当前开始获取期权原始dogsk数据')
            for j, csd_date in enumerate(trading_day[END_IDX-5:END_IDX]):
                if j == 0:
                    continue
                try:
                    pd.read_hdf(os.path.join(thisDir, 'df.h5'),
                                key=f'{und}_option_dogsk_{csd_date}')
                except KeyError:
                    print(f'当前日期为{csd_date}, 检测到无数据, 开始获取')
                    # 获取合约列表
                    contract_list = []
                    df_list = []
                    temp_hot_month = hot_month[hot_month.index <= int(
                        csd_date)].iloc[-1, :]
                    temp_hot_month = [str(a) for a in temp_hot_month]
                    symbol_history = api.getsymbolhistory(
                        SymbolType.Options, csd_date)
                    for temp_ in symbol_history['Node']:
                        if temp_['ENG'].split('(')[0] == und.split('.')[0]:
                            for temp__ in temp_['Node']:
                                if temp__['Node'][0]['Node'][0]['Contracts'][0].split('.')[3] == und.split('.')[1]:
                                    for temp___ in temp__['Node']:
                                        if temp___['ENG'] != 'HOT' and temp___['ENG'] in temp_hot_month:
                                            contract_list += temp___['Node'][0]['Contracts']+temp___[
                                                'Node'][1]['Contracts']
                                    break
                            break
                    # 根据合约列表获取所有dogsk数据
                    for csd_symbol in contract_list:
                        a = api.getgreekshistory(
                            GreeksType.DOGSK, 1, csd_symbol, trading_day[trading_day.index(csd_date)-1]+'07', csd_date+'07')
                        temp_df = pd.DataFrame(a)
                        temp_df['maturity'] = [
                            api.getexpirationdate(a[0]['Symbol'])]*len(temp_df)
                        if temp_hot_month.index(a[0]['Symbol'].split('.')[4]) == 0:
                            temp_df['month'] = [0]*len(temp_df)
                        else:
                            temp_df['month'] = [1]*len(temp_df)
                        temp_df.index = [csd_date]*len(temp_df)
                        df_list += [temp_df]
                    dogsk_df = pd.concat(df_list)
                    # dogsk_df.to_hdf(os.path.join(thisDir, 'df.h5'),
                    #                 key=f'{csd_und}_option_dogsk_{csd_date}')


        # # 根据volume排名保存数据
        # for csd_und in und_list:
        #     position_data = pd.read_excel(os.path.join(
        #         thisDir, 'data.xlsx'), sheet_name=csd_und.split('.')[1], index_col=0)
        #     position_data.index = [a.strftime('%Y%m%d') for a in position_data.index]
        #     li = list(position_data.index)
        #     new_li = list(set(li))
        #     new_li.sort(key=li.index)
        #     df = pd.DataFrame()
        #     for date in new_li:
        #         csd_df = position_data[position_data.index == date]
        #         csd_df = csd_df.sort_values(by='volume', ascending=False)
        #         df = df.append(csd_df.iloc[:3, [2, 3, 10]])
        #     df.to_excel(os.path.join(thisDir, f'hotmonth_volume_{csd_und}.xlsx'))
        #     df = pd.DataFrame()
        #     for date in new_li:
        #         csd_df = position_data[position_data.index == date]
        #         csd_df = csd_df.sort_values(by='position', ascending=False)
        #         df = df.append(csd_df.iloc[:3, [2, 3, 10]])
        #     df.to_excel(os.path.join(thisDir, f'hotmonth_position_{csd_und}.xlsx'))
if __name__ == "__main__":
    und_list = ['CZCE.TA', 'CZCE.MA', 'DCE.i',  'DCE.m']
    # und_list = ['DCE.i']
    my_cdp = CTA_DATA_PROCESSING(und_list)
    my_cdp.get_iv_and_tau_history()
    my_cdp.calculate_yz()
    my_cdp.draw_volcone()
    a_iv = my_cdp.iv_history
    a_tau = my_cdp.tau
    a_yz = my_cdp.vol_df
    a_maturity = my_cdp.maturity
    a_undf = my_cdp.undf_symbol
    a_close = my_cdp.close_df
    # fig = plt.figure(figsize=(8, 3*len(und_list)))
    # for i, und in enumerate(und_list):
    #     ax = fig.add_subplot(len(und_list), 1, i+1)
    #     yz = a_yz[und+'_yz']
    #     iv = a_iv[und]
    #     tau = a_tau[und+'_hot']
    #     x = []
    #     y = []
    #     for date in tqdm(trading_day[TRADINGDAY_START_IDX:END_IDX+1]):
    #         if type(iv[date]) != float:
    #             continue
    #         x += [tau[date]]
    #         y += [iv[date]-yz.loc[int(date), x[-1]]]
    #     plt.title(f'{und}历史同期(iv-yz)波动率散点图', fontsize=15)
    #     plt.grid()
    #     plt.scatter(x, y)
    #     plt.xticks(fontsize=12)
    #     plt.yticks(fontsize=12)
    #     plt.tight_layout()
    # fig = plt.figure(figsize=(8, 3*len(und_list)))
    # for i, und in enumerate(und_list):
    #     ax = fig.add_subplot(len(und_list), 1, i+1)
    #     yz = a_yz[und+'_yz']
    #     iv = a_iv[und]
    #     tau = a_tau[und+'_hot']
    #     x = []
    #     y = []
    #     for date in tqdm(trading_day[TRADINGDAY_START_IDX:END_IDX+1]):
    #         if type(iv[date]) != float:
    #             continue
    #         x += [tau[date]]
    #         y += [iv[date]-yz.loc[int(date), x[-1]]]
    #     a = und.split('.')[1]
    #     globals()[f'{a}_dict'] = {}
    #     for i, j in enumerate(x):
    #         try:
    #             globals()[f'{a}_dict'][j] += [y[i]]
    #         except:
    #             globals()[f'{a}_dict'][j] = [y[i]]
    #     x = []
    #     y = []
    #     for i in globals()[f'{a}_dict']:
    #         x += [i]
    #         y += [np.mean(np.array(globals()[f'{a}_dict'][i]))]
    #     plt.title(f'{und}历史同期(iv-yz)波动率均值', fontsize=15)
    #     plt.grid()
    #     plt.scatter(x, y)
    #     plt.xticks(fontsize=12)
    #     plt.yticks(fontsize=12)
    #     plt.tight_layout()

# with open(os.path.join(thisDir, 'data/a.json'), 'w') as f:
#     f.write(json.dumps(a))

# c = json.load(open(os.path.join(thisDir, 'data/a.json')))
# c['ss'] = ['ggg']
# with open(os.path.join(thisDir, 'data/a.json'), 'w') as f:
#     f.write(json.dumps(c))

# # fadj 数据
# # iv 数据
# # yz 数据
# #

# iv_history = a_iv
# with open(os.path.join(thisDir, f'data/{TODAY_STR}/iv_history.json'), 'w') as f:
#     f.write(json.dumps(iv_history))

# tau_history = a_tau
# with open(os.path.join(thisDir, f'data/{TODAY_STR}/tau_history.json'), 'w') as f:
#     f.write(json.dumps(tau_history))

# maturity_history = a_maturity
# with open(os.path.join(thisDir, f'data/{TODAY_STR}/maturity_history.json'), 'w') as f:
#     f.write(json.dumps(maturity_history))


# yz_history = a_yz
# for i in yz_history:
#     yz_history[i] = yz_history[i].to_json()
# with open(os.path.join(thisDir, 'data/yz_history.json'), 'w') as f:
#     f.write(json.dumps(yz_history))

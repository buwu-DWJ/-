#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   test.py
@Time    :   2022/11/21 11:06:09
@Author  :   DingWenjie
@Contact :   359582058@qq.com
@Desc    :   每日用15个garch模型做出预测值, 观察票选结果
'''


import rpy2.robjects as robjects
import numpy as np
import pandas as pd
import warnings
import tcoreapi_mq as t
import datetime


warnings.simplefilter('ignore')
core = t.TCoreZMQ(quote_port="51864", trade_port="51834")

length = 365
print('开始获取历史收盘价')
df = core.SubHistory('TC.S.SSE.510050', '5K', '2020010200', datetime.datetime.today().strftime('%Y%m%d')+'07')
df = pd.DataFrame(df)
print('获取成功')
csd_idx = [i*48+46 for i in range(round(len(df)/48))][-length-1:]
close = np.log(pd.to_numeric(df['Close'][csd_idx]).reset_index(drop=True).pct_change()+1).dropna()
close = close.rename('adj_lrtn')
close.to_csv('crt_daily.csv', index=False)
robjects.r.source('garch_daily.R')
pred = np.array(round(pd.read_csv('daily_pred.csv').iloc[-1,:],3))
pred[np.isnan(pred)] = 0
print(f'预测之中给出正向预测数为{(pred>0).sum()}, 负向预测数为{(pred<0).sum()}')
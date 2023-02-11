#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   automatic_trading_cta.py
@Time    :   2023/01/03 14:31:12
@Author  :   DingWenjie
@Contact :   359582058@qq.com
@Desc    :   do automatic trading for CTA
'''


import warnings
from cta_utility import Automatic_Trading_CTA as atc

warnings.simplefilter('ignore')
ACCOUNT = 'mvtuat09'
BROKERID = 'DCore_SIM_SS2'
# ACCOUNT = 'y000-mvtuat09'
# BROKERID = 'M2_PAPERTRADE'
strategy_name = ['iv趋势跟踪', '周动量', '三因子']
# strategy_name = ['test']
my_atc = atc(strategy_name, ACCOUNT, BROKERID)
my_atc.show_intraday_position()

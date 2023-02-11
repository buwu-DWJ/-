#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   auto_tab.py
@Time    :   2023/01/09 10:05:33
@Author  :   DingWenjie
@Contact :   359582058@qq.com
@Desc    :   None
'''

from auto_tab_utilities import Auto_Tab

account_list = ['LS', 'LS3', 'LS4', 'DB', 'LS7']
und_list = ['510050', '510300', '510500', '159915']
my_at = Auto_Tab(account_list, und_list)
my_at.auto_tab_gui()
# a = my_at.find_files_given_date('2023年1月5日')
